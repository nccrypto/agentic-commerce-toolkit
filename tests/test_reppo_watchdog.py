import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "reppo_compat_watchdog.py"
sys.path.insert(0, str(ROOT / "src"))

from agentic_commerce.reppo import TransportResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        return self.responses.pop(0)


def load_watchdog(testcase):
    if not SCRIPT.exists():
        testcase.fail("watchdog script is not implemented")
    spec = importlib.util.spec_from_file_location("reppo_compat_watchdog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def healthy_responses(pod_count=2):
    pods = [{"id": f"p{index}"} for index in range(pod_count)]
    return [
        TransportResponse(404, b"{}", 1, "2026-01-02T03:04:01Z"),
        TransportResponse(
            200,
            b'{"data":{"subnets":[{"id":"s1"}]}}',
            2,
            "2026-01-02T03:04:02Z",
        ),
        TransportResponse(
            200,
            json.dumps({"data": {"pods": pods}}).encode(),
            3,
            "2026-01-02T03:04:03Z",
        ),
    ]


class WatchdogTests(unittest.TestCase):
    def test_first_baseline_and_unchanged_run_are_silent(self):
        module = load_watchdog(self)
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"

            first = module.run_watchdog(
                transport=FakeTransport(healthy_responses()),
                state_file=state_file,
                clock=lambda: "2026-01-02T03:04:06Z",
            )
            second = module.run_watchdog(
                transport=FakeTransport(healthy_responses(pod_count=3)),
                state_file=state_file,
                clock=lambda: "2026-01-03T03:04:06Z",
            )

            self.assertEqual(first, "")
            self.assertEqual(second, "")
            state = json.loads(state_file.read_text())
            self.assertEqual(state["signature"]["stats"]["httpStatus"], 404)
            self.assertFalse(state["signature"]["pods"]["paginationHonored"])
            self.assertNotIn("itemCount", state["signature"]["pods"])
            self.assertEqual(stat.S_IMODE(state_file.stat().st_mode), 0o600)

    def test_compatibility_change_alerts_once_then_becomes_silent(self):
        module = load_watchdog(self)
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"
            module.run_watchdog(
                transport=FakeTransport(healthy_responses()),
                state_file=state_file,
                clock=lambda: "2026-01-02T03:04:06Z",
            )
            changed = healthy_responses()
            changed[2] = TransportResponse(
                503, b"{}", 3, "2026-01-03T03:04:03Z"
            )

            alert = module.run_watchdog(
                transport=FakeTransport(changed),
                state_file=state_file,
                clock=lambda: "2026-01-03T03:04:06Z",
            )
            repeated = module.run_watchdog(
                transport=FakeTransport(changed),
                state_file=state_file,
                clock=lambda: "2026-01-04T03:04:06Z",
            )

            self.assertIn("Reppo public compatibility change detected", alert)
            self.assertIn("pods.httpStatus: 200 -> 503", alert)
            self.assertEqual(repeated, "")

    def test_non_object_state_is_reset_with_an_alert(self):
        module = load_watchdog(self)
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"
            state_file.write_text("null\n")

            try:
                alert = module.run_watchdog(
                    transport=FakeTransport(healthy_responses()),
                    state_file=state_file,
                    clock=lambda: "2026-01-03T03:04:06Z",
                )
            except Exception as error:
                self.fail(f"non-object state escaped reset handling: {type(error).__name__}")

            self.assertIn("state was unreadable and has been reset", alert)
            state = json.loads(state_file.read_text())
            self.assertIn("signature", state)

    def test_invalid_settings_are_rejected_before_transport(self):
        module = load_watchdog(self)
        cases = (
            {"base_url": "file:///tmp/reppo"},
            {"base_url": "https://user:secret@example.test/api/v1"},
            {"base_url": "http://["},
            {"timeout": 0.0},
            {"timeout": -1.0},
            {"timeout": float("nan")},
            {"timeout": float("inf")},
            {"state_file": ROOT / "watchdog-state.json"},
        )
        with tempfile.TemporaryDirectory() as directory:
            for case in cases:
                with self.subTest(case=case):
                    transport = FakeTransport([])
                    arguments = {"state_file": Path(directory) / "state.json"}
                    arguments.update(case)
                    try:
                        module.run_watchdog(
                            transport=transport,
                            **arguments,
                        )
                    except ValueError:
                        pass
                    except Exception as error:
                        self.fail(
                            f"invalid settings escaped preflight: {type(error).__name__}"
                        )
                    else:
                        self.fail("invalid settings were not rejected")
                    self.assertEqual(transport.calls, [])

    def test_documented_command_does_not_create_repository_bytecode(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            repository = temporary_root / "repository"
            ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
            shutil.copytree(ROOT / "scripts", repository / "scripts", ignore=ignore)
            shutil.copytree(ROOT / "src", repository / "src", ignore=ignore)
            state_file = temporary_root / "state.json"
            environment = os.environ.copy()
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(repository / "scripts" / "reppo_compat_watchdog.py"),
                    "--state-file",
                    str(state_file),
                    "--timeout",
                    "-1",
                ],
                cwd=repository,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(list(repository.rglob("__pycache__")), [])


if __name__ == "__main__":
    unittest.main()
