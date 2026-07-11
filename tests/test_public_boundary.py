import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "check_public_boundary.py"
SPEC = importlib.util.spec_from_file_location("boundary", MODULE_PATH)
boundary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(boundary)


class PublicBoundaryTests(unittest.TestCase):
    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("public example\n", encoding="utf-8")
            self.assertEqual(boundary.scan(root), [])

    def test_env_file_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("TOKEN=placeholder\n", encoding="utf-8")
            self.assertTrue(any("forbidden filename" in item for item in boundary.scan(root)))

    def test_private_path_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.txt").write_text(
                "/Users/example/Documents/private-repo/file.md\n", encoding="utf-8"
            )
            self.assertTrue(any("private local path" in item for item in boundary.scan(root)))

    def test_example_env_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text("TOKEN=replace-me\n", encoding="utf-8")
            self.assertEqual(boundary.scan(root), [])


if __name__ == "__main__":
    unittest.main()
