import tempfile
import unittest
from pathlib import Path
from init_workspace import initialize


class WorkspaceTests(unittest.TestCase):
    def test_player_layout_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "story"
            initialize(root, ["Saki"])
            expected = {"Rules.md", "World-Storyline.md", "Character/Saki/Objective.md", "Character/Saki/Subjective.md"}
            self.assertEqual({p.relative_to(root).as_posix() for p in root.rglob("*.md")}, expected)
            subject = root / "Character/Saki/Subjective.md"
            self.assertIn("Saki", subject.read_text(encoding="utf-8"))
            subject.write_text("玩家修改", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                initialize(root, ["Saki", "Other"])
            self.assertEqual(subject.read_text(encoding="utf-8"), "玩家修改")
            self.assertFalse((root / "Character/Other").exists())

    def test_no_automatic_cast_and_path_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "story"
            for names in (["../outside"], ["Saki", "saki"], ["CON"]):
                with self.assertRaises(ValueError):
                    initialize(root, names)
                self.assertFalse(root.exists())
            initialize(root, [])
            self.assertEqual(list((root / "Character").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
