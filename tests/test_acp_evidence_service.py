import copy
import io
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_commerce.acp_evidence import (
    TransientProviderError,
    receipt_exit_code,
    run_local_evidence_job,
)
from agentic_commerce.cli import main


REQUEST_EXAMPLE = ROOT / "examples" / "virtuals-acp-evidence" / "request-v1.example.json"
RESULT_SCHEMA = ROOT / "schemas" / "agent-job-result-v1.schema.json"


def load_request():
    return json.loads(REQUEST_EXAMPLE.read_text(encoding="utf-8"))


class AcpEvidenceServiceTests(unittest.TestCase):
    def test_valid_bundle_passes_all_checks_without_external_execution(self):
        receipt = run_local_evidence_job(
            load_request(),
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        data = receipt["result"]["data"]
        self.assertEqual(receipt["status"], "succeeded")
        self.assertEqual(data["verdict"], "pass")
        self.assertEqual([item["status"] for item in data["checks"]], ["pass"] * 4)
        self.assertEqual(
            [item["status"] for item in data["lifecycle"]],
            ["open", "budget_set", "funded", "submitted", "completed"],
        )
        self.assertEqual(receipt["cost"], {"amount": "0", "currency": "USD", "basis": "measured"})
        self.assertFalse(receipt["timeout"]["timedOut"])
        self.assertEqual(receipt_exit_code(receipt), 0)

    def test_provenance_mismatch_is_a_completed_fail_verdict(self):
        request = load_request()
        request["jobResult"]["provenance"]["manifestId"] = "example:different-manifest"

        receipt = run_local_evidence_job(
            request,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        self.assertEqual(receipt["status"], "succeeded")
        self.assertEqual(receipt["result"]["data"]["verdict"], "fail")
        linkage = next(
            check
            for check in receipt["result"]["data"]["checks"]
            if check["checkId"] == "provenance-linkage"
        )
        self.assertEqual(linkage["status"], "fail")
        self.assertEqual(receipt_exit_code(receipt), 2)

    def test_private_or_credential_shaped_evidence_fails_safely(self):
        request = load_request()
        request["sourceManifest"]["sources"][0]["url"] = "https://127.0.0.1/private"
        request["jobResult"]["privateRuntimeState"] = "not allowed"

        receipt = run_local_evidence_job(
            request,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        checks = {item["checkId"]: item for item in receipt["result"]["data"]["checks"]}
        self.assertEqual(checks["agent-job-result-contract"]["status"], "fail")
        self.assertEqual(checks["public-source-policy"]["status"], "fail")
        rendered = json.dumps(receipt)
        self.assertNotIn("127.0.0.1", rendered)
        self.assertNotIn("not allowed", rendered)

    def test_adversarial_candidate_still_produces_a_conforming_bounded_receipt(self):
        request = load_request()
        request["jobResult"]["provenance"]["sourceIds"] = [{"not": "hashable"}]
        request["jobResult"]["x" * 2000] = "undeclared"
        request["sourceManifest"]["sources"].append(
            copy.deepcopy(request["sourceManifest"]["sources"][0])
        )

        receipt = run_local_evidence_job(
            request,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )
        validator = Draft202012Validator(
            json.loads(RESULT_SCHEMA.read_text(encoding="utf-8")),
            format_checker=FormatChecker(),
        )

        self.assertTrue(validator.is_valid(receipt))
        self.assertEqual(receipt["result"]["data"]["verdict"], "fail")
        self.assertEqual(len(receipt["provenance"]["sourceIds"]), 2)
        findings = [
            finding
            for check in receipt["result"]["data"]["checks"]
            for finding in check["findings"]
        ]
        self.assertTrue(all(len(finding) <= 500 for finding in findings))

    def test_transient_provider_failure_retries_within_bound(self):
        request = load_request()
        calls = []

        def provider(candidate):
            calls.append(candidate["requestId"])
            if len(calls) == 1:
                raise TransientProviderError("synthetic transient failure")
            baseline = run_local_evidence_job(
                copy.deepcopy(candidate),
                clock=lambda: "2026-07-15T12:15:00Z",
                monotonic=lambda: 100.0,
            )
            data = baseline["result"]["data"]
            return data["checks"], data["sources"]

        receipt = run_local_evidence_job(
            request,
            verifier=provider,
            max_attempts=2,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(receipt["result"]["data"]["attempts"], 2)
        self.assertEqual(receipt["result"]["data"]["verdict"], "pass")

    def test_retry_exhaustion_returns_sanitized_failed_receipt(self):
        def provider(_candidate):
            raise TransientProviderError("private provider detail")

        receipt = run_local_evidence_job(
            load_request(),
            verifier=provider,
            max_attempts=2,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["result"])
        self.assertEqual(receipt["errors"][0]["code"], "RETRY_EXHAUSTED")
        self.assertNotIn("private provider detail", json.dumps(receipt))
        self.assertEqual(receipt_exit_code(receipt), 1)

    def test_timeout_after_provider_call_returns_failed_receipt(self):
        ticks = iter([0.0, 0.0, 0.006, 0.006])

        def provider(_candidate):
            return [], []

        receipt = run_local_evidence_job(
            load_request(),
            verifier=provider,
            timeout_ms=5,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: next(ticks),
        )

        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(receipt["timeout"]["timedOut"])
        self.assertEqual(receipt["errors"][0]["code"], "TIMEOUT")

    def test_unsupported_live_mode_is_default_deny(self):
        request = load_request()
        request["mode"] = "virtuals-acp"

        receipt = run_local_evidence_job(
            request,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        self.assertEqual(receipt["result"]["data"]["verdict"], "fail")
        self.assertEqual(receipt["result"]["data"]["checks"][0]["checkId"], "request-contract")
        self.assertEqual(receipt["result"]["data"]["lifecycle"], [
            {"status": "open", "at": "2026-07-15T12:15:00Z"},
            {"status": "submitted", "at": "2026-07-15T12:15:00Z"},
            {"status": "completed", "at": "2026-07-15T12:15:00Z"},
        ])

    def test_cli_runs_local_fixture_and_prints_only_json(self):
        stdout = io.StringIO()

        exit_code = main(
            [
                "virtuals-acp",
                "verify-evidence",
                "--request",
                str(REQUEST_EXAMPLE),
                "--pretty",
            ],
            stdout=stdout,
            clock=lambda: "2026-07-15T12:15:00Z",
            monotonic=lambda: 100.0,
        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["result"]["data"]["verdict"], "pass")
        self.assertTrue(stdout.getvalue().startswith("{\n"))
        self.assertNotIn(str(ROOT), stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
