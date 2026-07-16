import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_community_validation", ROOT / "scripts" / "run_community_validation.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load the community validation harness")
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)
build_validation_result = HARNESS.build_validation_result
main = HARNESS.main


class CommunityValidationTests(unittest.TestCase):
    def test_harness_exercises_pass_finding_failure_and_local_boundary(self):
        result = build_validation_result(
            "example:community-validation:001",
            "4caed42",
            "2026-07-15T13:00:00Z",
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            [check["checkId"] for check in result["checks"]],
            [
                "passing-fixture",
                "finding-fixture",
                "failure-fixture",
                "local-execution-boundary",
            ],
        )
        self.assertTrue(all(check["status"] == "pass" for check in result["checks"]))
        self.assertEqual(
            result["sharing"],
            {
                "reviewedForSensitiveData": False,
                "publicSubmissionApproved": False,
            },
        )
        self.assertNotIn(str(ROOT), json.dumps(result))

    def test_main_prints_only_json_and_returns_zero(self):
        stdout = io.StringIO()

        exit_code = main(
            [
                "--validation-id",
                "example:community-validation:002",
                "--revision",
                "4caed42",
                "--pretty",
            ],
            stdout=stdout,
            clock=lambda: "2026-07-15T13:05:00Z",
        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["recordedAt"], "2026-07-15T13:05:00Z")
        self.assertTrue(stdout.getvalue().startswith("{\n"))

    def test_fixture_read_failure_is_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-request.json"
            result = build_validation_result(
                "example:community-validation:003",
                "4caed42",
                "2026-07-15T13:10:00Z",
                request_path=missing,
            )

        rendered = json.dumps(result)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errors"][0]["code"], "HARNESS_ERROR")
        self.assertNotIn(str(missing), rendered)
        self.assertNotIn(directory, rendered)

    def test_public_identifiers_are_bounded(self):
        with self.assertRaises(ValueError):
            build_validation_result(
                "Contains Spaces",
                "4caed42",
                "2026-07-15T13:10:00Z",
            )
        with self.assertRaises(ValueError):
            build_validation_result(
                "example:community-validation:004",
                "revision with spaces",
                "2026-07-15T13:10:00Z",
            )


if __name__ == "__main__":
    unittest.main()
