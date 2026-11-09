"""Synthetic malformed-input regressions; no network requests."""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from http.client import IncompleteRead
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agentic_commerce.cli import main
from agentic_commerce.reppo import Inspector, TransportResponse


class SequenceTransport:
    def __init__(self, values):
        self.values = iter(values)

    def get(self, url, *, timeout):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return TransportResponse(200, value, 1, "2026-01-02T03:04:05Z")


class InputHardeningTests(unittest.TestCase):
    def test_bad_upstream_json_preserves_other_sources(self):
        bodies = [
            b'{"n":NaN}', b'{"n":Infinity}', b'{"n":-Infinity}',
            b'{"n":1e999}', b'{"n":' + b'9' * 5000 + b'}',
            b'[' * 1200 + b'0' + b']' * 1200,
        ]
        for body in bodies:
            with self.subTest(body=body[:30]):
                result = Inspector(
                    transport=SequenceTransport([
                        body, b'{"data":{"subnets":[]}}', b'{"data":{"pods":[]}}',
                    ]), clock=lambda: "2026-01-02T03:04:06Z",
                ).snapshot()
                self.assertEqual(result.exit_code, 2)
                self.assertEqual(result.envelope["errors"][0]["code"], "INVALID_JSON")
                json.dumps(result.envelope, allow_nan=False)

    def test_http_framing_failure_preserves_other_sources(self):
        result = Inspector(
            transport=SequenceTransport([
                IncompleteRead(b"synthetic detail"),
                b'{"data":{"subnets":[]}}', b'{"data":{"pods":[]}}',
            ]), clock=lambda: "2026-01-02T03:04:06Z",
        ).status()
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.envelope["errors"][0]["code"], "NETWORK_ERROR")
        self.assertNotIn("synthetic detail", json.dumps(result.envelope))

    def test_watchdog_handles_decoder_and_transport_failures(self):
        spec = importlib.util.spec_from_file_location(
            "hardening_watchdog", ROOT / "scripts" / "reppo_compat_watchdog.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for value, expected in [
            (b'{"n":NaN}', "INVALID_JSON"),
            (b'{"n":1e999}', "INVALID_JSON"),
            (b'[' * 1200 + b'0' + b']' * 1200, "INVALID_JSON"),
            (b'{"n":' + b'9' * 5000 + b'}', "INVALID_JSON"),
            (IncompleteRead(b"synthetic detail"), "NETWORK_ERROR"),
        ]:
            with self.subTest(expected=expected):
                observation = module.probe(
                    SequenceTransport([value]), name="stats",
                    url="https://reppo.ai/api/v1/stats", timeout=1,
                )
                self.assertEqual(observation["errorCode"], expected)

    def test_cli_rejects_deep_and_nonfinite_local_json(self):
        for body in [b'[' * 1200 + b'0' + b']' * 1200, b'{"n":NaN}']:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "request.json"
                path.write_bytes(body)
                output = io.StringIO()
                code = main([
                    "virtuals-acp", "verify-evidence", "--request", str(path),
                ], stdout=output)
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(output.getvalue())["error"]["code"], "INPUT_ERROR")


if __name__ == "__main__":
    unittest.main()
