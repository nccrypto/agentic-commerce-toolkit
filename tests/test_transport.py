import sys
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agentic_commerce.reppo import (
    DEFAULT_MAX_RESPONSE_BYTES,
    PublicOnlyRedirectHandler,
    ResponseTooLarge,
    UrllibTransport,
)


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def read(self, size=-1):
        return self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return FakeResponse(self.body)


class UrllibTransportTests(unittest.TestCase):
    def test_default_response_cap_accommodates_current_bounded_public_catalog(self):
        self.assertEqual(DEFAULT_MAX_RESPONSE_BYTES, 8_388_608)

    def test_redirects_are_not_followed_to_other_routes(self):
        handler = PublicOnlyRedirectHandler()

        redirected = handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://reppo.ai/api/v1/me",
        )

        self.assertIsNone(redirected)

    def test_response_size_cap_stops_oversized_payload(self):
        opener = FakeOpener(b"123456")
        transport = UrllibTransport(
            opener=opener,
            max_response_bytes=5,
            wall_clock=lambda: "2026-01-02T03:04:05Z",
            monotonic=lambda: 1.0,
        )

        with self.assertRaises(ResponseTooLarge):
            transport.get("https://reppo.ai/api/v1/stats", timeout=2.0)

        request, timeout = opener.calls[0]
        self.assertEqual(timeout, 2.0)
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIn("agentic-commerce-toolkit", request.get_header("User-agent"))

    def test_http_error_is_returned_with_public_status(self):
        class HttpErrorOpener:
            def open(self, request, timeout):
                raise HTTPError(request.full_url, 429, "rate limited", {}, BytesIO(b"{}"))

        transport = UrllibTransport(
            opener=HttpErrorOpener(),
            wall_clock=lambda: "2026-01-02T03:04:05Z",
            monotonic=lambda: 1.0,
        )

        response = transport.get("https://reppo.ai/api/v1/stats", timeout=2.0)

        self.assertEqual(response.status, 429)
        self.assertEqual(response.body, b"{}")


if __name__ == "__main__":
    unittest.main()
