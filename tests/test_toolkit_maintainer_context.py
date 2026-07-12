import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "toolkit_maintainer_context.py"


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, *, cwd, timeout, env=None):
        self.calls.append(
            {"command": command, "cwd": cwd, "timeout": timeout, "env": env}
        )
        stdout = (
            "https://github.com/nccrypto/agentic-commerce-toolkit.git"
            if command == ["git", "remote", "get-url", "origin"]
            else "synthetic read-only result"
        )
        return {
            "ok": True,
            "exitCode": 0,
            "stdout": stdout,
        }


def load_collector(testcase):
    if not SCRIPT.exists():
        testcase.fail("maintainer context script is not implemented")
    spec = importlib.util.spec_from_file_location("toolkit_maintainer_context", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MaintainerContextTests(unittest.TestCase):
    def test_collector_uses_only_read_only_commands(self):
        module = load_collector(self)
        runner = FakeRunner()

        with patch.dict(
            os.environ,
            {
                "GH_TOKEN": "synthetic-readonly-token",
                "SYNTHETIC_SECRET": "must-not-inherit",
            },
        ):
            context = module.collect_context(
                repo=ROOT,
                runner=runner,
                clock=lambda: "2026-01-02T03:04:06Z",
            )

        commands = [call["command"] for call in runner.calls]
        flattened = " ".join(" ".join(command) for command in commands)
        for forbidden in ("commit", "push", "issue create", "pr create", "release create"):
            self.assertNotIn(forbidden, flattened)
        self.assertEqual(commands[0], ["git", "remote", "get-url", "origin"])
        self.assertEqual(
            commands[2],
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        )
        for call in runner.calls[:4]:
            environment = call["env"]
            self.assertIsNotNone(environment)
            self.assertNotIn("SYNTHETIC_SECRET", environment)
            for key in environment:
                self.assertFalse(
                    any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD"))
                )
        for call in runner.calls[4:]:
            environment = call["env"]
            self.assertEqual(environment.get("GH_TOKEN"), "synthetic-readonly-token")
            self.assertNotIn("SYNTHETIC_SECRET", environment)
        tests_call = runner.calls[2]
        self.assertEqual(tests_call["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertNotEqual(tests_call["cwd"].resolve(), ROOT.resolve())
        self.assertFalse(tests_call["cwd"].exists())
        boundary_call = runner.calls[3]
        self.assertEqual(boundary_call["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(boundary_call["cwd"].resolve(), ROOT.resolve())
        self.assertEqual(context["schemaVersion"], "1.0")
        self.assertEqual(context["collectedAt"], "2026-01-02T03:04:06Z")
        self.assertEqual(context["repository"], "nccrypto/agentic-commerce-toolkit")
        self.assertTrue(context["checks"])

    def test_collector_rejects_a_different_repository(self):
        module = load_collector(self)
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                module.collect_context(repo=Path(directory), runner=runner)


if __name__ == "__main__":
    unittest.main()
