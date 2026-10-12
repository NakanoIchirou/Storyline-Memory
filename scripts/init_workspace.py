"""Create the player-facing Markdown workspace without overwriting existing files."""
import argparse
import os
from pathlib import Path


def initialize(root, characters):
    root = Path(root).resolve()
    if os.name == "nt" and root.drive.lower() != "d:":
        raise ValueError("Working data must stay on drive D")
    names = list(characters)
    for name in names:
        if (not name or name in (".", "..") or any(c in name for c in '/\\<>:"|?*')
                or any(ord(c) < 32 for c in name) or name.endswith((".", " "))
                or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
            raise ValueError("Use a safe single-folder character name")
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Character names must be unique")
    assets = Path(__file__).resolve().parent.parent / "assets" / "workspace"
    files = [(root / name, (assets / name).read_text(encoding="utf-8"))
             for name in ("Rules.md", "World-Storyline.md")]
    for character in names:
        for name in ("Objective.md", "Subjective.md"):
            files.append((root / "Character" / character / name,
                          (assets / name).read_text(encoding="utf-8").replace("{{character}}", character)))
    # Check every destination before creating anything; an existing project is never reset.
    if any(path.exists() for path, _ in files):
        raise FileExistsError("Workspace files already exist; choose a new directory")
    (root / "Character").mkdir(parents=True, exist_ok=True)
    for path, content in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--characters", nargs="*", default=[])
    args = parser.parse_args()
    print(initialize(args.root, args.characters))
