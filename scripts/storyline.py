"""Local three-layer drafts and snapshots. No model calls or agent runtime."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def atomic_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def validate(state):
    if set(state) != {"world", "objective", "subjective", "meta"}:
        raise ValueError("Exactly three layers and operational meta are required")
    meta = state["meta"]
    if set(meta) != {"tracked", "through", "processed"}:
        raise ValueError("Invalid operational metadata")
    tracked = meta["tracked"]
    if not isinstance(tracked, list) or any(not isinstance(x, str) or not x for x in tracked) or len(set(tracked)) != len(tracked):
        raise ValueError("Tracked character IDs must be unique nonempty strings")
    if not isinstance(meta["through"], dict) or set(meta["through"]) != set(tracked):
        raise ValueError("Coverage must be explicit for all tracked characters")
    if not isinstance(meta["processed"], list) or any(not isinstance(x, str) or len(x) != 64 for x in meta["processed"]):
        raise ValueError("Invalid input hashes")
    groups = [("world", state["world"])]
    for layer in ("objective", "subjective"):
        if not isinstance(state[layer], dict) or not set(tracked).issubset(state[layer]):
            raise ValueError("Each tracked character requires both personal layers")
        groups.extend((layer, rows) for rows in state[layer].values())
    if set(state["objective"]) != set(state["subjective"]):
        raise ValueError("Archived characters require both personal layers too")
    for layer, rows in groups:
        if not isinstance(rows, list):
            raise ValueError("Layer records must be lists")
        ids = set()
        for row in rows:
            required = {"id", "event_id", "t", "summary", "status", "origin", "source"}
            if not isinstance(row, dict) or set(row) != required | ({"available"} if layer == "subjective" else set()):
                raise ValueError("Invalid record fields")
            if any(not isinstance(row[k], str) or not row[k].strip() for k in required):
                raise ValueError("Record values must be nonempty strings")
            if row["id"] in ids:
                raise ValueError("Duplicate record ID")
            ids.add(row["id"])
            if row["status"] not in ("open", "closed", "state"):
                raise ValueError("Invalid event status")
            if row["origin"] not in ("text", "player", "inference", "offscreen"):
                raise ValueError("Invalid provenance")
            if layer == "subjective" and type(row["available"]) is not bool:
                raise ValueError("Current cognition requires an availability flag")


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if os.name == "nt" and self.root.drive.lower() != "d:":
            raise ValueError("This project's working data must stay on drive D")
        self.head_path = self.root / "HEAD.json"
        self.versions = self.root / "versions"

    def head(self):
        if not self.head_path.exists():
            return {"version": None, "state": {"world": [], "objective": {}, "subjective": {}, "meta": {"tracked": [], "through": {}, "processed": []}}}
        head = read(self.head_path)
        snap = self.snapshot(head["version"])
        if head["state"] != snap["state"]:
            raise ValueError("HEAD does not match its snapshot")
        return head

    def snapshot(self, version):
        if not isinstance(version, str) or len(version) != 64 or any(c not in "0123456789abcdef" for c in version):
            raise ValueError("Invalid version")
        snap = read(self.versions / (version + ".json"))
        if digest(snap) != version:
            raise ValueError("Snapshot integrity failure")
        validate(snap["state"])
        return snap

    def prepare(self, changes, sources=(), tracked=None, through=None):
        head = self.head()
        state = copy.deepcopy(head["state"])
        if tracked is not None:
            state["meta"]["tracked"] = tracked
            for layer in ("objective", "subjective"):
                for who in tracked:
                    state[layer].setdefault(who, [])
            state["meta"]["through"] = {who: state["meta"]["through"].get(who) for who in tracked}
        if through is not None:
            state["meta"]["through"].update(through)
        inputs = []
        for source in sources:
            path = Path(source)
            h = hashlib.sha256(path.read_bytes()).hexdigest()
            if h in state["meta"]["processed"]:
                raise ValueError("TXT already processed; do not commit it again")
            state["meta"]["processed"].append(h)
            inputs.append({"path": str(path.resolve()), "sha256": h})
        for change in changes:
            if set(change) != {"layer", "character", "record"}:
                raise ValueError("Invalid change")
            layer, who, record = change["layer"], change["character"], change["record"]
            if layer not in ("world", "objective", "subjective"):
                raise ValueError("No additional Storyline layers")
            if layer == "world":
                if who is not None:
                    raise ValueError("World records have no character owner")
                rows = state["world"]
            else:
                if who not in state["meta"]["tracked"]:
                    raise ValueError("Character must be selected by player")
                rows = state[layer][who]
            record = copy.deepcopy(record)
            pos = next((i for i, row in enumerate(rows) if row["id"] == record["id"]), None)
            if pos is None:
                rows.append(record)
            else:
                if rows[pos]["event_id"] != record["event_id"]:
                    raise ValueError("An existing record cannot silently change its event identity")
                rows[pos] = record
        validate(state)
        draft = {"base": head["version"], "state": state, "changes": changes, "inputs": inputs}
        return {"approval": digest(draft), "draft": draft}

    def commit(self, proposal, approval):
        draft = proposal["draft"]
        if approval != digest(draft) or proposal["approval"] != approval:
            raise ValueError("Approval does not match this exact draft")
        if draft["base"] != self.head()["version"]:
            raise ValueError("Stale draft: review again against current version")
        validate(draft["state"])
        snapshot = {"parent": draft["base"], "state": draft["state"], "inputs": draft["inputs"], "approval": approval}
        version = digest(snapshot)
        path = self.versions / (version + ".json")
        if not path.exists():
            atomic_write(path, snapshot)
        # Snapshot first, one atomic pointer replacement for all three layers.
        atomic_write(self.head_path, {"version": version, "state": snapshot["state"]})
        return version

    def rollback(self, version):
        snap = self.snapshot(version)
        atomic_write(self.head_path, {"version": version, "state": snap["state"]})

    def role_context(self, character):
        state = self.head()["state"]
        if character not in state["meta"]["tracked"]:
            raise ValueError("Character is not currently tracked")
        # Export only actor-visible content. No source paths, event IDs, truth labels,
        # objective history, other characters, or unavailable old memories.
        return {"character": character, "cognition": [{"t": row["t"], "summary": row["summary"]}
                for row in state["subjective"][character] if row["available"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("request")
    prep.add_argument("--out", required=True)
    commit = sub.add_parser("commit")
    commit.add_argument("proposal")
    commit.add_argument("--approval", required=True)
    back = sub.add_parser("rollback")
    back.add_argument("version")
    role = sub.add_parser("role")
    role.add_argument("character")
    sub.add_parser("show")
    args = parser.parse_args()
    store = Store(args.root)
    if args.command == "prepare":
        request = read(args.request)
        result = store.prepare(**request)
        atomic_write(args.out, result)
        print(result["approval"])
    elif args.command == "commit":
        print(store.commit(read(args.proposal), args.approval))
    elif args.command == "rollback":
        store.rollback(args.version)
        print(args.version)
    else:
        result = store.role_context(args.character) if args.command == "role" else store.head()
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
