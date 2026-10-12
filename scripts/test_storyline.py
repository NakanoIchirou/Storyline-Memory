"""Mechanical tests; authored fixtures do not prove general LLM extraction quality."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from storyline import Store, digest


def record(id, event, time, text, layer="objective", status="closed", available=True, origin="text"):
    r = dict(id=id, event_id=event, t=time, summary=text, status=status, origin=origin, source="fixture.txt:1")
    if layer == "subjective":
        r["available"] = available
    return r


def change(layer, who, row):
    return dict(layer=layer, character=who, record=row)


class StorylineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / "store")
        self.initial = [
            change("world", None, record("w0", "constitution", "T=-20", "城邦立法会设有一百席", "world")),
            change("objective", "A", record("a0", "melody", "T=-10", "A与B在东京听过旋律，暗号为琥珀灯")),
            change("subjective", "A", record("s0", "melody", "T=-10", "记得东京与琥珀灯", "subjective", available=False)),
            change("subjective", "A", record("s1", "opening", "T=0", "不记得旋律的来源，性格冷淡，成因未定", "subjective")),
            change("subjective", "B", record("b0", "melody", "T=0", "仍记得与A一起听过旋律", "subjective")),
        ]
        self.proposal = self.store.prepare(self.initial, tracked=["A", "B"], through={"A": "T=0", "B": "T=0"})
        self.v1 = self.store.commit(self.proposal, self.proposal["approval"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_pre_zero_same_structure_and_no_invented_cause(self):
        head = self.store.head()["state"]
        self.assertEqual(head["world"][0]["t"], "T=-20")
        self.assertEqual(head["subjective"]["A"][1]["summary"], "不记得旋律的来源，性格冷淡，成因未定")
        p = self.store.prepare([change("world", None, record("w1", "reform", "T=1", "立法会改革为一百二十席", "world"))])
        self.store.commit(p, p["approval"])
        self.assertEqual(len(self.store.head()["state"]["world"]), 2)

    def test_private_event_does_not_require_world_update(self):
        p = self.store.prepare([change("objective", "A", record("visit", "meeting", "T=1", "B解释迟到原因；A沉默离开"))])
        self.store.commit(p, p["approval"])
        state = self.store.head()["state"]
        self.assertEqual(state["world"], self.proposal["draft"]["state"]["world"])
        self.assertNotIn("原谅", json.dumps(state, ensure_ascii=False))

    def test_cross_txt_continuation_and_rollback_reprocessing(self):
        one = self.root / "one.txt"
        two = self.root / "two.txt"
        one.write_text("T=1 A与B开始争执，尚未结束。", encoding="utf-8")
        two.write_text("T=2 争执继续。T=3 双方明确和解。", encoding="utf-8")
        row = record("dispute", "relationship-1", "T=1", "争执开始，未结束", status="open")
        p = self.store.prepare([change("objective", "A", row)], sources=[one])
        v2 = self.store.commit(p, p["approval"])
        row.update(t="T=1..3", summary="争执后和解", status="closed")
        p = self.store.prepare([change("objective", "A", row)], sources=[two], through={"A": "T=3", "B": "T=3"})
        self.store.commit(p, p["approval"])
        matches = [r for r in self.store.head()["state"]["objective"]["A"] if r["event_id"] == "relationship-1"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "closed")
        self.store.rollback(v2)
        self.assertEqual(self.store.head()["state"]["objective"]["A"][-1]["status"], "open")
        self.store.prepare([], sources=[two])  # rolled-back input can be read again
        with self.assertRaisesRegex(ValueError, "already processed"):
            self.store.prepare([], sources=[one])

    def test_role_package_omits_secrets_and_old_memories(self):
        p = self.store.prepare([change("subjective", "A", record("s2", "trigger", "T=1", "这段旋律令人莫名熟悉", "subjective"))])
        self.store.commit(p, p["approval"])
        exported = json.dumps(self.store.role_context("A"), ensure_ascii=False)
        for secret in ("琥珀灯", "东京", "source", "objective", "constitution", "仍记得与A"):
            self.assertNotIn(secret, exported)
        self.assertIn("莫名熟悉", exported)
        with self.assertRaises(ValueError):
            self.store.role_context("unknown")

    def test_review_then_exact_approval_and_stale_rejection(self):
        p = self.store.prepare([change("objective", "A", record("new", "candidate", "T=1", "幕后参加排练", origin="offscreen"))])
        self.assertEqual(self.store.head()["version"], self.v1)
        with self.assertRaisesRegex(ValueError, "Approval"):
            self.store.commit(p, "unapproved")
        edited = copy.deepcopy(p)
        edited["draft"]["state"]["objective"]["A"][-1]["summary"] = "改成结婚"
        with self.assertRaisesRegex(ValueError, "Approval"):
            self.store.commit(edited, p["approval"])
        self.store.commit(p, p["approval"])
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.store.commit(self.proposal, self.proposal["approval"])

    def test_complete_rollback_and_fade_preserves_archives(self):
        old = copy.deepcopy(self.store.head())
        p = self.store.prepare([], tracked=["A"], through={"A": "T=8"})
        v2 = self.store.commit(p, p["approval"])
        self.assertIn("B", self.store.head()["state"]["objective"])
        with self.assertRaises(ValueError):
            self.store.role_context("B")
        self.store.rollback(self.v1)
        self.assertEqual(self.store.head(), old)
        self.assertTrue((self.store.versions / (v2 + ".json")).exists())

    def test_no_fourth_layer_or_silent_event_reassignment(self):
        with self.assertRaises(ValueError):
            self.store.prepare([change("subconscious", "A", self.initial[1]["record"])])
        row = copy.deepcopy(self.initial[1]["record"])
        row["event_id"] = "unrelated"
        with self.assertRaisesRegex(ValueError, "event identity"):
            self.store.prepare([change("objective", "A", row)])

    def test_corrupt_version_is_not_loaded(self):
        path = self.store.versions / (self.v1 + ".json")
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["state"]["world"][0]["summary"] = "悄悄改写"
        path.write_text(json.dumps(obj), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.rollback(self.v1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
