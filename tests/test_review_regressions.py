"""Synthetic regressions for malformed control and evidence candidates."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

from agentic_commerce.action_control import action_digest, evaluate_action_control
from agentic_commerce.acp_evidence import run_local_evidence_job, validate_agent_job_result
from test_action_control import action_request, matching_approval, EVALUATED_AT


ROOT = Path(__file__).parents[1]


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((ROOT / "examples/virtuals-acp-evidence/request-v1.example.json").read_text())
        self.validator = Draft202012Validator(
            json.loads((ROOT / "schemas/agent-job-result-v1.schema.json").read_text()),
            format_checker=FormatChecker(),
        )

    def receipt(self, request):
        receipt = run_local_evidence_job(
            request, clock=lambda: "2026-07-15T12:15:00Z", monotonic=lambda: 100.0,
        )
        self.validator.validate(receipt)
        self.assertEqual(receipt["status"], "succeeded")
        return receipt

    def test_action_enum_containers_fail_closed(self):
        for value in ([], {}, ["approved"], {"value": "human"}):
            for field in ("decision", "issuerType"):
                with self.subTest(field=field, value=value):
                    request = action_request()
                    record = evaluate_action_control(
                        "example:control", request, EVALUATED_AT,
                        matching_approval(request, **{field: value}),
                    )
                    self.assertEqual(record["decision"]["reasonCode"], "INVALID_APPROVAL")
                    self.assertFalse(record["decision"]["mayExecute"])
                    self.assertIsNone(record["approval"])
            with self.subTest(mode=value):
                request = action_request()
                request["mode"] = value
                with self.assertRaises(ValueError):
                    action_digest(request)

    def test_action_array_snapshot_has_no_input_alias(self):
        request = action_request()
        request["parameters"][0]["value"] = ["synthetic", 2, None]
        record = evaluate_action_control(
            "example:control", request, EVALUATED_AT, matching_approval(request),
        )
        snapshot = copy.deepcopy(record)
        request["parameters"][0]["value"].append("changed")
        self.assertEqual(record, snapshot)
        record["request"]["parameters"][0]["value"].append("record-only")
        self.assertNotIn("record-only", request["parameters"][0]["value"])

    def test_evidence_enum_containers_are_findings_not_crashes(self):
        paths = [
            ("sourceManifest", "sources", 0, "sourceType"),
            ("sourceManifest", "sources", 0, "usage", "purpose"),
            ("jobResult", "status"), ("jobResult", "cost", "basis"),
            ("jobResult", "freshness", "status"),
        ]
        for path in paths:
            for value in ([], {}, ["fresh"], {"value": "measured"}):
                with self.subTest(path=path, value=value):
                    request = copy.deepcopy(self.request)
                    request["jobResult"]["cost"] = {"amount": "0", "currency": "USD", "basis": "measured"}
                    request["jobResult"]["freshness"] = {"evaluatedAt": EVALUATED_AT, "status": "unknown"}
                    target = request
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                    self.assertEqual(self.receipt(request)["result"]["data"]["verdict"], "fail")

    def test_non_array_sources_do_not_crash_linkage(self):
        for value in (None, 3, False, {}, "invalid"):
            with self.subTest(value=value):
                request = copy.deepcopy(self.request)
                request["sourceManifest"]["sources"] = value
                self.assertEqual(self.receipt(request)["result"]["data"]["verdict"], "fail")

    def test_decimal_schema_agrees_with_runtime(self):
        for amount in ("0", "0.01", "123.456", "999999999999999999.123456789012345678",
                       "-1", "01", "1e2", "1.", r"1\x2", "1.1234567890123456789"):
            with self.subTest(amount=amount):
                candidate = copy.deepcopy(self.request["jobResult"])
                candidate["cost"] = {"amount": amount, "currency": "USD", "basis": "measured"}
                self.assertEqual(self.validator.is_valid(candidate), not validate_agent_job_result(candidate))

    def test_noncanonical_ip_aliases_are_not_public_sources(self):
        hosts = ("127.1", "0177.0.0.1", "0x7f.0.0.1", "127.0.1", "2130706433",
                 "0x7f000001", "017700000001", "0x7f.1", "127.1.", "8.8.2056",
                 "127.0.0.1", "[::1]", "[::ffff:127.0.0.1]", "10.0.0.1",
                 "%31%32%37.1", "example.com..", "example..com", "@example.com",
                 "example.com:444", "example.local", "example.internal", "localHost",
                 "exa\nmple.com", "example.com\\evil", "[2606:4700:4700::1111%25eth0]")
        for host in hosts:
            for field in ("source", "manifest"):
                with self.subTest(host=host, field=field):
                    request = copy.deepcopy(self.request)
                    url = "https://" + host + "/synthetic"
                    if field == "source":
                        request["sourceManifest"]["sources"][0]["url"] = url
                    else:
                        request["jobResult"]["provenance"]["manifestUrl"] = url
                    receipt = self.receipt(request)
                    policy = next(c for c in receipt["result"]["data"]["checks"] if c["checkId"] == "public-source-policy")
                    self.assertEqual(policy["status"], "fail")
                    self.assertNotIn(url, json.dumps(receipt))

    def test_public_dns_and_canonical_global_ips_remain_allowed_without_dns(self):
        for host in ("example.com", "EXAMPLE.com.", "8.8.8.8", "[2606:4700:4700::1111]",
                     "docs.example.com:443", "xn--bcher-kva.example"):
            with self.subTest(host=host):
                request = copy.deepcopy(self.request)
                request["sourceManifest"]["sources"][0]["url"] = "https://" + host + "/synthetic"
                with patch("socket.getaddrinfo", side_effect=AssertionError("DNS is forbidden")):
                    receipt = self.receipt(request)
                self.assertEqual(receipt["result"]["data"]["verdict"], "pass")

    def test_findings_do_not_echo_unknown_keys_or_missing_ids(self):
        marker = "SYNTHETIC-UNTRUSTED-MARKER"
        for path in ((), ("jobResult",), ("sourceManifest", "subject"),
                     ("sourceManifest", "sources", 0, "usage"), ("jobResult", "provenance")):
            with self.subTest(path=path):
                request = copy.deepcopy(self.request)
                target = request
                for key in path:
                    target = target[key]
                target[marker] = "not public"
                self.assertNotIn(marker, json.dumps(self.receipt(request)))
        for source_id in (marker, marker.lower(), marker * 50):
            with self.subTest(source_id=source_id):
                request = copy.deepcopy(self.request)
                request["jobResult"]["provenance"]["sourceIds"] = [source_id]
                receipt = self.receipt(request)
                self.assertEqual(receipt["result"]["data"]["verdict"], "fail")
                self.assertNotIn(source_id[:30], json.dumps(receipt))

    def test_invalid_source_id_containers_fail_linkage_without_echo(self):
        for value in (None, {}, 3, [None], [{}], [[]]):
            with self.subTest(value=value):
                request = copy.deepcopy(self.request)
                request["jobResult"]["provenance"]["sourceIds"] = value
                receipt = self.receipt(request)
                linkage = next(c for c in receipt["result"]["data"]["checks"] if c["checkId"] == "provenance-linkage")
                self.assertEqual(linkage["status"], "fail")

    def test_canonical_size_fails_closed_for_deep_or_unicode_input(self):
        deep = []
        for _ in range(2000):
            deep = [deep]
        for value in (deep, "\ud800"):
            with self.subTest(kind=type(value).__name__):
                request = copy.deepcopy(self.request)
                request["jobResult"]["result"]["data"]["synthetic"] = value
                receipt = self.receipt(request)
                self.assertEqual(receipt["result"]["data"]["verdict"], "fail")
        # Encoder depth limits differ by Python version; exercise its explicit
        # failure path deterministically without changing process-wide limits.
        for error in (RecursionError, UnicodeError):
            with self.subTest(error=error.__name__):
                with patch("agentic_commerce.acp_evidence.json.dumps", side_effect=error):
                    receipt = self.receipt(self.request)
                self.assertEqual(receipt["result"]["data"]["checks"][0]["checkId"], "request-contract")
                self.assertEqual(receipt["result"]["data"]["verdict"], "fail")

    def test_happy_fixture_is_unchanged(self):
        expected = json.loads((ROOT / "examples/virtuals-acp-evidence/receipt-v1.example.json").read_text())
        self.assertEqual(self.receipt(self.request), expected)