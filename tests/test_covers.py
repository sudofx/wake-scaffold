"""Comic-cover rotation stays cosmetic, deterministic, and local."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.covers import active, choose, discover, rotate


class CoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/"assets/covers").mkdir(parents=True)
        for name in ("cover-original.png", "cover-variant-001.png", "cover-variant-002.png"):
            (self.root/"assets/covers"/name).write_bytes(b"cover")
        (self.root/"README.md").write_text("![cover](assets/covers/cover-original.png)")

    def tearDown(self):
        self.temp.cleanup()

    def test_readme_references_one_existing_cover(self):
        self.assertEqual(active(self.root/"README.md", self.root).name, "cover-original.png")

    def test_selection_never_repeats_when_alternatives_exist(self):
        options = discover(self.root)
        current = active(self.root/"README.md", self.root)
        for cycle in range(20):
            self.assertIn(choose(options, current, cycle), options)
            self.assertNotEqual(choose(options, current, cycle), current)

    def test_rotation_selects_only_a_known_file(self):
        changed = rotate(self.root, cycle=7)
        self.assertIn(self.root/changed, discover(self.root))
        self.assertTrue((self.root/changed).is_file())

    def test_single_cover_is_a_safe_noop(self):
        for path in discover(self.root)[1:]:
            path.unlink()
        before = (self.root/"README.md").read_text()
        self.assertIsNone(rotate(self.root, cycle=4))
        self.assertEqual((self.root/"README.md").read_text(), before)

    def test_rotation_has_no_provider_dependency(self):
        with patch("wake.providers.Gemini", side_effect=AssertionError("No model call allowed")):
            self.assertIsNotNone(rotate(self.root, cycle=2))


if __name__ == "__main__":
    unittest.main()
