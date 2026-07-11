import io
import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agentic_commerce.cli import main
from agentic_commerce.reppo import TransportResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        return self.responses.pop(0)


class CliTests(unittest.TestCase):
    def test_datanets_prints_only_json_and_returns_zero(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"subnets": []}}',
                    5,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        stdout = io.StringIO()

        exit_code = main(
            ["reppo", "datanets", "--limit", "3", "--pretty"],
            stdout=stdout,
            transport=transport,
            clock=lambda: "2026-01-02T03:04:06Z",
        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["command"], "reppo datanets")
        self.assertTrue(stdout.getvalue().startswith("{\n"))
        self.assertIn("limit=3", transport.calls[0][0])

    def test_invalid_timeout_returns_json_error_before_network(self):
        transport = FakeTransport([])
        stdout = io.StringIO()

        exit_code = main(
            ["reppo", "status", "--timeout", "0"],
            stdout=stdout,
            transport=transport,
            clock=lambda: "2026-01-02T03:04:06Z",
        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(transport.calls, [])
        self.assertEqual(payload["errors"][0]["code"], "VALIDATION_ERROR")

    def test_partial_status_prints_json_and_returns_two(self):
        transport = FakeTransport(
            [
                TransportResponse(500, b"{}", 1, "2026-01-02T03:04:01Z"),
                TransportResponse(200, b'{"data": {"subnets": []}}', 2, "2026-01-02T03:04:02Z"),
                TransportResponse(200, b'{"data": {"pods": []}}', 3, "2026-01-02T03:04:03Z"),
            ]
        )
        stdout = io.StringIO()

        exit_code = main(
            ["reppo", "status"],
            stdout=stdout,
            transport=transport,
            clock=lambda: "2026-01-02T03:04:06Z",
        )

        self.assertEqual(exit_code, 2)
        self.assertTrue(json.loads(stdout.getvalue())["partial"])

    def test_nonfinite_timeout_is_rejected_before_network(self):
        transport = FakeTransport([])
        stdout = io.StringIO()

        exit_code = main(
            ["reppo", "snapshot", "--timeout", "nan"],
            stdout=stdout,
            transport=transport,
            clock=lambda: "2026-01-02T03:04:06Z",
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
