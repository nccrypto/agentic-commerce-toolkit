import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
FIXTURES = Path(__file__).parent / "fixtures" / "reppo"

from agentic_commerce.reppo import Inspector, ResponseTooLarge, TransportResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        return self.responses.pop(0)


class RaisingTransport:
    def __init__(self, error):
        self.error = error
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        raise self.error


class ReppoInspectorTests(unittest.TestCase):
    def test_datanets_constructs_encoded_public_url(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"subnets": []}}',
                    12,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets(page=2, limit=7, search="model & data")

        self.assertEqual(
            transport.calls,
            [
                (
                    "https://reppo.ai/api/v1/public/subnets?page=2&limit=7&search=model+%26+data",
                    10.0,
                )
            ],
        )
        self.assertEqual(result.envelope["data"], {"data": {"subnets": []}})

    def test_datanets_rejects_invalid_values_before_transport(self):
        transport = FakeTransport([])
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets(page=0, limit=-1)

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.exit_code, 1)
        self.assertFalse(result.envelope["ok"])
        self.assertEqual(result.envelope["sources"], [])
        self.assertEqual(result.envelope["errors"][0]["code"], "VALIDATION_ERROR")

    def test_datanets_rejects_limit_above_public_output_cap(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"subnets": []}}',
                    1,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets(limit=101)

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "limit must be between 1 and 100",
        )

    def test_datanets_rejects_oversized_search_before_transport(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"subnets": []}}',
                    1,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets(search="x" * 257)

        self.assertEqual(transport.calls, [])
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "search must be at most 256 characters",
        )

    def test_http_error_is_structured_and_retains_source_metadata(self):
        transport = FakeTransport(
            [TransportResponse(503, b'{"detail": "upstream unavailable"}', 31, "2026-01-02T03:04:05Z")]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets()

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.envelope["errors"][0]["code"], "HTTP_ERROR")
        self.assertEqual(result.envelope["sources"][0]["httpStatus"], 503)
        self.assertEqual(result.envelope["sources"][0]["error"]["code"], "HTTP_ERROR")
        self.assertNotIn("upstream unavailable", str(result.envelope))

    def test_invalid_json_is_structured(self):
        transport = FakeTransport(
            [TransportResponse(200, b"not-json", 4, "2026-01-02T03:04:05Z")]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets()

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.envelope["data"], None)
        self.assertEqual(result.envelope["errors"][0]["code"], "INVALID_JSON")

    def test_non_object_json_is_rejected_as_invalid_shape(self):
        transport = FakeTransport(
            [TransportResponse(200, b"[]", 4, "2026-01-02T03:04:05Z")]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets()

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.envelope["errors"][0]["code"], "INVALID_SHAPE")

    def test_listing_requires_the_expected_collection(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"pods": []}}',
                    4,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets()

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.envelope["errors"][0]["code"], "INVALID_SHAPE")

    def test_pods_constructs_all_public_filters(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"pods": [{"id": "p1"}, {"id": "p2"}]}}',
                    8,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.pods(page=3, limit=1, search="vision", datanet="subnet/a", epoch=0)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            transport.calls[0][0],
            "https://reppo.ai/api/v1/public/pods?page=3&limit=1&search=vision&filters%5BcurrentEpoch%5D=0&filters%5Bsubnet%5D=subnet%2Fa",
        )
        self.assertEqual(result.envelope["data"]["data"]["pods"], [{"id": "p1"}])

    def test_pods_rejects_negative_epoch_before_transport(self):
        transport = FakeTransport([])
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.pods(epoch=-1)

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.envelope["errors"][0]["code"], "VALIDATION_ERROR")

    def test_pods_rejects_limit_above_public_output_cap(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"pods": []}}',
                    1,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.pods(limit=101)

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "limit must be between 1 and 100",
        )

    def test_pods_rejects_oversized_search_before_transport(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"pods": []}}',
                    1,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.pods(search="x" * 257)

        self.assertEqual(transport.calls, [])
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "search must be at most 256 characters",
        )

    def test_pods_rejects_oversized_datanet_filter_before_transport(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"pods": []}}',
                    1,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.pods(datanet="x" * 257)

        self.assertEqual(transport.calls, [])
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "datanet must be at most 256 characters",
        )

    def test_status_reports_three_public_probes_independently(self):
        transport = FakeTransport(
            [
                TransportResponse(200, (FIXTURES / "stats.json").read_bytes(), 1, "2026-01-02T03:04:01Z"),
                TransportResponse(200, (FIXTURES / "subnets.json").read_bytes(), 2, "2026-01-02T03:04:02Z"),
                TransportResponse(200, (FIXTURES / "pods.json").read_bytes(), 3, "2026-01-02T03:04:03Z"),
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.status()

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.envelope["ok"])
        self.assertEqual(result.envelope["data"]["stats"]["data"]["totalPods"], 3)
        self.assertEqual(
            result.envelope["data"]["datanets"]["data"]["subnets"][0]["id"],
            "synthetic-subnet-1",
        )
        self.assertEqual(
            result.envelope["data"]["pods"]["data"]["pods"][0]["id"],
            "synthetic-pod-1",
        )
        self.assertEqual(len(result.envelope["sources"]), 3)

    def test_status_returns_partial_and_exit_two_when_one_probe_fails(self):
        transport = FakeTransport(
            [
                TransportResponse(503, b"{}", 1, "2026-01-02T03:04:01Z"),
                TransportResponse(200, b'{"data": {"subnets": []}}', 2, "2026-01-02T03:04:02Z"),
                TransportResponse(200, b'{"data": {"pods": []}}', 3, "2026-01-02T03:04:03Z"),
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.status()

        self.assertEqual(result.exit_code, 2)
        self.assertFalse(result.envelope["ok"])
        self.assertTrue(result.envelope["partial"])
        self.assertIsNone(result.envelope["data"]["stats"])
        self.assertEqual(result.envelope["data"]["datanets"], {"data": {"subnets": []}})

    def test_snapshot_retains_successful_data_during_partial_failure(self):
        transport = FakeTransport(
            [
                TransportResponse(200, b'{"data": {"totalPods": 8}}', 1, "2026-01-02T03:04:01Z"),
                TransportResponse(503, b"{}", 2, "2026-01-02T03:04:02Z"),
                TransportResponse(200, b'{"data": {"pods": [{"id": "p1"}]}}', 3, "2026-01-02T03:04:03Z"),
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.snapshot(limit=5)

        self.assertEqual(result.exit_code, 2)
        self.assertTrue(result.envelope["partial"])
        self.assertEqual(result.envelope["data"]["stats"], {"data": {"totalPods": 8}})
        self.assertIsNone(result.envelope["data"]["datanets"])
        self.assertEqual(result.envelope["data"]["pods"]["data"]["pods"][0]["id"], "p1")
        self.assertIn("limit=5", transport.calls[1][0])
        self.assertIn("limit=5", transport.calls[2][0])

    def test_snapshot_rejects_invalid_limit_before_transport(self):
        transport = FakeTransport([])
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.snapshot(limit=0)

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.envelope["errors"][0]["code"], "VALIDATION_ERROR")

    def test_snapshot_rejects_limit_above_public_output_cap(self):
        transport = FakeTransport(
            [
                TransportResponse(200, b'{"data": {}}', 1, "2026-01-02T03:04:01Z"),
                TransportResponse(200, b'{"data": {"subnets": []}}', 1, "2026-01-02T03:04:02Z"),
                TransportResponse(200, b'{"data": {"pods": []}}', 1, "2026-01-02T03:04:03Z"),
            ]
        )
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.snapshot(limit=101)

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "limit must be between 1 and 100",
        )

    def test_response_size_error_is_a_secret_safe_source_failure(self):
        transport = RaisingTransport(ResponseTooLarge())
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets()

        self.assertEqual(result.envelope["errors"][0]["code"], "RESPONSE_TOO_LARGE")
        self.assertIsNone(result.envelope["sources"][0]["httpStatus"])
        self.assertIsNone(result.envelope["sources"][0]["latencyMs"])

    def test_timeout_is_structured_without_exception_details(self):
        transport = RaisingTransport(TimeoutError("socket detail should not escape"))
        inspector = Inspector(transport=transport, clock=lambda: "2026-01-02T03:04:06Z")

        result = inspector.datanets()

        self.assertEqual(result.envelope["errors"][0]["code"], "TIMEOUT")
        self.assertNotIn("socket detail", str(result.envelope))

    def test_base_url_with_credentials_is_rejected_before_transport(self):
        transport = FakeTransport([])
        inspector = Inspector(
            base_url="https://user:secret@example.test/api/v1",
            transport=transport,
            clock=lambda: "2026-01-02T03:04:06Z",
        )

        result = inspector.datanets()

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.envelope["errors"][0]["code"], "VALIDATION_ERROR")
        self.assertNotIn("secret", str(result.envelope))

    def test_custom_base_url_is_rejected_before_transport(self):
        transport = FakeTransport(
            [
                TransportResponse(
                    200,
                    b'{"data": {"subnets": []}}',
                    1,
                    "2026-01-02T03:04:05Z",
                )
            ]
        )
        inspector = Inspector(
            base_url="https://mirror.example/api/v1",
            transport=transport,
            clock=lambda: "2026-01-02T03:04:06Z",
        )

        result = inspector.datanets()

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.envelope["errors"][0]["code"], "VALIDATION_ERROR")
        self.assertEqual(
            result.envelope["errors"][0]["message"],
            "base URL must match the canonical Reppo public API",
        )

    def test_malformed_base_url_is_rejected_before_transport(self):
        for base_url in ("http://[", "http://example.test:abc/api/v1"):
            with self.subTest(base_url=base_url):
                transport = FakeTransport([])
                try:
                    inspector = Inspector(
                        base_url=base_url,
                        transport=transport,
                        clock=lambda: "2026-01-02T03:04:06Z",
                    )
                    result = inspector.datanets()
                except Exception as error:
                    self.fail(f"malformed base URL escaped validation: {type(error).__name__}")

                self.assertEqual(transport.calls, [])
                self.assertEqual(result.exit_code, 1)
                self.assertEqual(
                    result.envelope["errors"][0]["code"], "VALIDATION_ERROR"
                )


if __name__ == "__main__":
    unittest.main()
