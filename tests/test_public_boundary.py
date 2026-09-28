import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "check_public_boundary.py"
SPEC = importlib.util.spec_from_file_location("boundary", MODULE_PATH)
boundary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(boundary)


class PublicBoundaryTests(unittest.TestCase):
    def init_repository(self, root):
        subprocess.run(["git", "init", "-q", str(root)], check=True)

    def test_tracked_files_in_skipped_directories_are_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repository(root)
            directories = sorted(boundary.SKIP_DIRS - {".git"})
            (root / ".gitignore").write_text("\n".join(directories) + "\n")
            for directory in directories:
                target = root / directory / "auth.json"
                target.parent.mkdir()
                target.write_text("internal-example\n", encoding="utf-8")
                subprocess.run(["git", "-C", str(root), "add", "-f", "--", str(target)], check=True)
            with patch.dict("os.environ", {"PUBLIC_BOUNDARY_PRIVATE_TERMS": "internal-example"}):
                findings = boundary.scan(root)
            for directory in directories:
                self.assertIn(f"{directory}/auth.json: forbidden filename", findings)
                self.assertIn(f"{directory}/auth.json:1: configured private identifier", findings)
                if directory.startswith("."):
                    self.assertIn(f"{directory}/auth.json: forbidden hidden or private directory", findings)

    def test_all_files_mode_does_not_invoke_git(self):
        # Git metadata must not be needed in strict candidate mode.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            target = root / "node_modules" / "auth.json"
            target.parent.mkdir()
            target.write_text("{}\n")
            with patch.object(boundary.subprocess, "run", side_effect=AssertionError("unexpected Git")):
                self.assertIn("node_modules/auth.json: forbidden filename", boundary.scan(root, all_files=True))

    def test_git_enumeration_failure_does_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            with patch.object(boundary.subprocess, "run", side_effect=FileNotFoundError):
                with self.assertRaisesRegex(RuntimeError, "cannot enumerate tracked files"):
                    boundary.scan(root)

    def test_untracked_local_venv_is_skipped_in_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repository(root)
            target = root / ".venv" / "auth.json"
            target.parent.mkdir()
            target.write_text("{}\n")
            self.assertEqual(boundary.scan(root), [])

    def test_export_without_git_scans_skipped_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in boundary.SKIP_DIRS - {".git"}:
                target = root / directory / "auth.json"
                target.parent.mkdir()
                target.write_text("{}\n")
                self.assertIn(f"{directory}/auth.json: forbidden filename", boundary.scan(root))

    def test_scan_root_under_skipped_ancestor_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "node_modules" / "export"
            root.mkdir(parents=True)
            (root / "auth.json").write_text("{}\n")
            self.assertIn("auth.json: forbidden filename", boundary.scan(root))

    def test_all_files_cli_scans_untracked_candidate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repository(root)
            target = root / "node_modules" / "auth.json"
            target.parent.mkdir()
            target.write_text("{}\n")
            result = subprocess.run(
                [sys.executable, "-B", str(MODULE_PATH), "--all-files", str(root)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("node_modules/auth.json: forbidden filename", result.stdout)

    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("public example\n", encoding="utf-8")
            self.assertEqual(boundary.scan(root), [])

    def test_public_documentation_is_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "Authorization: Bearer " + "x" * 24 + "\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any("probable bearer token" in item for item in boundary.scan(root))
            )

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

    def test_hidden_runtime_directory_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hidden_state = root / ".local-agent" / "config.json"
            hidden_state.parent.mkdir()
            hidden_state.write_text("{}\n", encoding="utf-8")
            self.assertTrue(
                any("hidden or private directory" in item for item in boundary.scan(root))
            )

    def test_named_non_public_system_reference_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "This was copied from the private Example monorepo.\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "named non-public system reference" in item
                    for item in boundary.scan(root)
                )
            )

    def test_lowercase_repository_slug_reference_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "This was copied from the private example-tool repo.\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "named non-public system reference" in item
                    for item in boundary.scan(root)
                )
            )

    def test_lowercase_single_word_private_reference_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "This was copied from the private atlas repository.\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "named non-public system reference" in item
                    for item in boundary.scan(root)
                )
            )

    def test_configured_private_identifier_is_blocked_without_echoing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_identifier = "internal-example"
            (root / "README.md").write_text(
                f"Uses {private_identifier} for local state.\n",
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"PUBLIC_BOUNDARY_PRIVATE_TERMS": private_identifier},
                clear=False,
            ):
                findings = boundary.scan(root)
            self.assertTrue(
                any("configured private identifier" in item for item in findings)
            )
            self.assertNotIn(private_identifier, "\n".join(findings))

    def test_configured_private_identifier_scans_builtin_allowlist_files(self):
        private_identifier = "internal-example"
        for relative_path in (
            Path("scripts/check_public_boundary.py"),
            Path("tests/test_public_boundary.py"),
        ):
            with self.subTest(path=relative_path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                target = root / relative_path
                target.parent.mkdir(parents=True)
                target.write_text(private_identifier + "\n", encoding="utf-8")
                with patch.dict(
                    "os.environ",
                    {"PUBLIC_BOUNDARY_PRIVATE_TERMS": private_identifier},
                    clear=False,
                ):
                    findings = boundary.scan(root)
                self.assertTrue(
                    any("configured private identifier" in item for item in findings)
                )

    def test_standard_user_agent_terms_are_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "client.py").write_text(
                'USER_AGENT = "example/1.0"\nheader = "User-Agent"\n',
                encoding="utf-8",
            )
            self.assertEqual(boundary.scan(root), [])

    def test_common_editor_directories_are_skipped(self):
        for directory in (".idea", ".vscode"):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                editor_file = root / directory / "settings.json"
                self.init_repository(root)
                editor_file.parent.mkdir()
                editor_file.write_text("{}\n", encoding="utf-8")
                self.assertEqual(boundary.scan(root), [])

    def test_example_env_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text("TOKEN=replace-me\n", encoding="utf-8")
            self.assertEqual(boundary.scan(root), [])


if __name__ == "__main__":
    unittest.main()
