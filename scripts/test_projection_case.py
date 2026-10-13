"""Replay this assistant's reviewed example records, not an automatic TXT extractor."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from storyline import Store
from test_storyline import change, record


EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def entry(layer, who, id, event, t, summary, source, **options):
    row = record(id, event, t, summary, layer, **options)
    row["source"] = source
    return change(layer, who, row)


class ProjectionCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "case")
        initial = [
            entry("world", None, "curfew", "curfew", "T=-20", "城邦实行夜间交通管制，成因未设定", "initial.txt:3", origin="player"),
            entry("objective", "Saki", "wait", "appointment", "T=-2", "与Ren约定桥边见面，等到夜深，Ren未出现", "initial.txt:4", origin="player"),
            entry("objective", "Ren", "admission", "appointment", "T=-2", "突发阑尾炎住院，未能赴约", "initial.txt:4-5", origin="player"),
            entry("subjective", "Saki", "old-belief", "appointment", "T=-1..0", "记得失约，认定Ren不在乎自己，心境紧绷", "initial.txt:6-7", origin="player"),
            entry("subjective", "Ren", "own-memory", "appointment", "T=-2..0", "知道自己因阑尾炎住院未能赴约", "initial.txt:5", origin="player"),
        ]
        p = self.store.prepare(initial, sources=[EXAMPLES / "initial.txt"], tracked=["Saki", "Ren"], through={"Saki": "T=0", "Ren": "T=0"})
        self.initial_version = self.store.commit(p, p["approval"])  # fixture's explicit test-only approval
        self.initial_state = copy.deepcopy(self.store.head()["state"])

    def tearDown(self):
        self.temp.cleanup()

    def batch_one(self):
        old = copy.deepcopy(self.store.head()["state"]["subjective"]["Saki"][0])
        old["available"] = False
        updates = [
            change("subjective", "Saki", old),
            entry("objective", "Saki", "question", "appointment-explanation", "T=1", "桥边询问失约原因，Ren尚未回答", "batch-1.txt:4-5", status="open"),
            entry("objective", "Ren", "approach", "appointment-explanation", "T=1", "走近Saki，尚未回答", "batch-1.txt:4-5", status="open"),
            entry("subjective", "Saki", "reconsider", "appointment", "T=1", "记得失约，心境缓和，认为Ren也许遇到困难，原因未知，尚未决定原谅", "batch-1.txt:2-3"),
        ]
        p = self.store.prepare(updates, sources=[EXAMPLES / "batch-1.txt"], through={"Saki": "T=1", "Ren": "T=1"})
        self.assertEqual(self.store.head()["version"], self.initial_version)
        return self.store.commit(p, p["approval"])

    def test_present_mood_does_not_reveal_objective_secret(self):
        self.batch_one()
        state = self.store.head()["state"]
        self.assertEqual(state["world"], self.initial_state["world"])
        self.assertEqual(state["objective"]["Ren"][0], self.initial_state["objective"]["Ren"][0])
        prior = state["subjective"]["Saki"][0]
        self.assertFalse(prior["available"])
        self.assertEqual(prior["summary"], self.initial_state["subjective"]["Saki"][0]["summary"])
        role = json.dumps(self.store.role_context("Saki"), ensure_ascii=False)
        for secret in ("阑尾炎", "住院", "initial.txt", "认定Ren不在乎"):
            self.assertNotIn(secret, role)
        self.assertIn("也许", role)
        self.assertIn("尚未决定原谅", role)

    def test_new_statement_continuation_and_complete_rollback(self):
        v1 = self.batch_one()
        before = copy.deepcopy(self.store.head())
        old = copy.deepcopy(before["state"]["subjective"]["Saki"][-1])
        old["available"] = False
        p = self.store.prepare([
            change("subjective", "Saki", old),
            entry("objective", "Saki", "hearing", "appointment-explanation", "T=2", "听到Ren解释突然住院，随后沉默，谈话未完", "batch-2.txt:2-4", status="open"),
            entry("objective", "Ren", "explain", "appointment-explanation", "T=2", "告诉Saki当年突然住院，未能赴约", "batch-2.txt:2", status="open"),
            entry("subjective", "Saki", "heard-claim", "appointment-explanation", "T=2", "记得失约；Ren称当时突然住院，尚未核实，愿意听下去，尚未表示原谅", "batch-2.txt:2-4"),
        ], sources=[EXAMPLES / "batch-2.txt"], through={"Saki": "T=2", "Ren": "T=2"})
        self.assertEqual(self.store.head(), before)
        self.store.commit(p, p["approval"])
        role = json.dumps(self.store.role_context("Saki"), ensure_ascii=False)
        self.assertIn("Ren称", role)
        self.assertIn("尚未核实", role)
        self.assertNotIn("阑尾炎", role)
        self.assertNotIn("原因未知", role)
        rows = [r for r in self.store.head()["state"]["objective"]["Saki"] if r["event_id"] == "appointment-explanation"]
        self.assertEqual([r["t"] for r in rows], ["T=1", "T=2"])
        self.assertTrue(all(r["status"] == "open" for r in rows))
        self.store.rollback(v1)
        self.assertEqual(self.store.head(), before)
        self.assertNotIn("住院", json.dumps(self.store.role_context("Saki"), ensure_ascii=False))
        self.store.prepare([], sources=[EXAMPLES / "batch-2.txt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
