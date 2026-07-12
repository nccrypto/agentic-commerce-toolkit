"""Read-only client for Reppo's public ecosystem endpoints."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_BASE_URL = "https://reppo.ai/api/v1"
SCHEMA_VERSION = "1.0"
DEFAULT_MAX_RESPONSE_BYTES = 8_388_608
MAX_RESULT_LIMIT = 100
MAX_QUERY_LENGTH = 256
USER_AGENT = "agentic-commerce-toolkit/0.1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ResponseTooLarge(Exception):
    """Raised when a public response exceeds the configured safety cap."""


class PublicOnlyRedirectHandler(HTTPRedirectHandler):
    """Refuse redirects so a public route cannot lead to another endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class TransportResponse:
    status: int
    body: bytes
    latency_ms: int
    fetched_at: str


@dataclass(frozen=True)
class InspectionResult:
    envelope: dict[str, Any]
    exit_code: int


class Transport(Protocol):
    def get(self, url: str, *, timeout: float) -> TransportResponse: ...


class UrllibTransport:
    def __init__(
        self,
        *,
        opener: Any | None = None,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        wall_clock: Callable[[], str] = utc_now,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.opener = opener or build_opener(PublicOnlyRedirectHandler())
        self.max_response_bytes = max_response_bytes
        self.wall_clock = wall_clock
        self.monotonic = monotonic

    def get(self, url: str, *, timeout: float) -> TransportResponse:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            method="GET",
        )
        started = self.monotonic()
        try:
            with self.opener.open(request, timeout=timeout) as response:
                body = response.read(self.max_response_bytes + 1)
                status = response.status
        except HTTPError as error:
            try:
                body = error.read(self.max_response_bytes + 1)
                status = error.code
            finally:
                error.close()
        latency_ms = round((self.monotonic() - started) * 1000)
        if len(body) > self.max_response_bytes:
            raise ResponseTooLarge
        return TransportResponse(status, body, latency_ms, self.wall_clock())


class Inspector:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        transport: Transport,
        clock: Callable[[], str],
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport
        self.clock = clock
        self._base_url_valid = self.base_url == DEFAULT_BASE_URL

    def _envelope(
        self,
        command: str,
        *,
        ok: bool,
        partial: bool = False,
        sources: list[dict[str, Any]] | None = None,
        data: Any = None,
        errors: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "command": command,
            "generatedAt": self.clock(),
            "ok": ok,
            "partial": partial,
            "sources": sources or [],
            "data": data,
            "errors": errors or [],
        }

    def _validation_failure(self, command: str, message: str) -> InspectionResult:
        error = {"code": "VALIDATION_ERROR", "message": message}
        return InspectionResult(
            self._envelope(command, ok=False, data=None, errors=[error]), 1
        )

    def _preflight(self, command: str) -> InspectionResult | None:
        if not self._base_url_valid:
            return self._validation_failure(
                command, "base URL must match the canonical Reppo public API"
            )
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            return self._validation_failure(command, "timeout must be finite and positive")
        return None

    def _fetch(
        self,
        url: str,
        *,
        collection_key: str | None = None,
        max_items: int | None = None,
    ) -> tuple[Any, dict[str, Any], dict[str, str] | None]:
        try:
            response = self.transport.get(url, timeout=self.timeout)
        except (ResponseTooLarge, TimeoutError, OSError) as exception:
            if isinstance(exception, ResponseTooLarge):
                code = "RESPONSE_TOO_LARGE"
                message = "Public endpoint response exceeded the size limit"
            elif isinstance(exception, TimeoutError):
                code = "TIMEOUT"
                message = "Public endpoint request timed out"
            else:
                code = "NETWORK_ERROR"
                message = "Public endpoint request failed"
            error = {
                "code": code,
                "message": message,
            }
            source = {
                "url": url,
                "httpStatus": None,
                "latencyMs": None,
                "fetchedAt": None,
                "error": error,
            }
            return None, source, error
        source = {
            "url": url,
            "httpStatus": response.status,
            "latencyMs": response.latency_ms,
            "fetchedAt": response.fetched_at,
            "error": None,
        }
        if not 200 <= response.status < 300:
            error = {
                "code": "HTTP_ERROR",
                "message": f"Public endpoint returned HTTP {response.status}",
            }
            source["error"] = error
            return None, source, error
        try:
            data = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            error = {
                "code": "INVALID_JSON",
                "message": "Public endpoint returned invalid JSON",
            }
            source["error"] = error
            return None, source, error
        if not isinstance(data, dict):
            error = {
                "code": "INVALID_SHAPE",
                "message": "Public endpoint JSON must be an object",
            }
            source["error"] = error
            return None, source, error
        if collection_key is not None:
            payload = data.get("data")
            if not isinstance(payload, dict) or not isinstance(
                payload.get(collection_key), list
            ):
                error = {
                    "code": "INVALID_SHAPE",
                    "message": (
                        "Public listing JSON must contain "
                        f"a data.{collection_key} array"
                    ),
                }
                source["error"] = error
                return None, source, error
            if max_items is not None:
                payload[collection_key] = payload[collection_key][:max_items]
        return data, source, None

    def datanets(self, *, page: int = 1, limit: int = 20, search: str = "") -> InspectionResult:
        if failure := self._preflight("reppo datanets"):
            return failure
        if page <= 0:
            return self._validation_failure(
                "reppo datanets", "page must be a positive integer"
            )
        if not 1 <= limit <= MAX_RESULT_LIMIT:
            return self._validation_failure(
                "reppo datanets", "limit must be between 1 and 100"
            )
        if len(search) > MAX_QUERY_LENGTH:
            return self._validation_failure(
                "reppo datanets", "search must be at most 256 characters"
            )
        query = urlencode({"page": page, "limit": limit, "search": search})
        url = f"{self.base_url}/public/subnets?{query}"
        data, source, error = self._fetch(
            url, collection_key="subnets", max_items=limit
        )
        envelope = self._envelope(
            "reppo datanets",
            ok=error is None,
            sources=[source],
            data=data,
            errors=[error] if error else [],
        )
        return InspectionResult(envelope, 1 if error else 0)

    def pods(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        search: str = "",
        datanet: str | None = None,
        epoch: int | None = None,
    ) -> InspectionResult:
        if failure := self._preflight("reppo pods"):
            return failure
        if page <= 0:
            return self._validation_failure(
                "reppo pods", "page must be a positive integer"
            )
        if not 1 <= limit <= MAX_RESULT_LIMIT:
            return self._validation_failure(
                "reppo pods", "limit must be between 1 and 100"
            )
        if len(search) > MAX_QUERY_LENGTH:
            return self._validation_failure(
                "reppo pods", "search must be at most 256 characters"
            )
        if datanet is not None and len(datanet) > MAX_QUERY_LENGTH:
            return self._validation_failure(
                "reppo pods", "datanet must be at most 256 characters"
            )
        if epoch is not None and epoch < 0:
            return self._validation_failure(
                "reppo pods", "epoch must be a nonnegative integer"
            )
        params: dict[str, Any] = {"page": page, "limit": limit, "search": search}
        if epoch is not None:
            params["filters[currentEpoch]"] = epoch
        if datanet is not None:
            params["filters[subnet]"] = datanet
        url = f"{self.base_url}/public/pods?{urlencode(params)}"
        data, source, error = self._fetch(
            url, collection_key="pods", max_items=limit
        )
        envelope = self._envelope(
            "reppo pods",
            ok=error is None,
            sources=[source],
            data=data,
            errors=[error] if error else [],
        )
        return InspectionResult(envelope, 1 if error else 0)

    def status(self) -> InspectionResult:
        if failure := self._preflight("reppo status"):
            return failure
        urls = {
            "stats": f"{self.base_url}/stats",
            "datanets": f"{self.base_url}/public/subnets?{urlencode({'page': 1, 'limit': 1, 'search': ''})}",
            "pods": f"{self.base_url}/public/pods?{urlencode({'page': 1, 'limit': 1, 'search': ''})}",
        }
        data: dict[str, Any] = {}
        sources: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for name, url in urls.items():
            collection_key = {"datanets": "subnets", "pods": "pods"}.get(name)
            value, source, error = self._fetch(
                url, collection_key=collection_key, max_items=1
            )
            data[name] = value
            sources.append(source)
            if error:
                errors.append(error)
        envelope = self._envelope(
            "reppo status",
            ok=not errors,
            partial=bool(errors) and len(errors) < len(urls),
            sources=sources,
            data=data,
            errors=errors,
        )
        exit_code = 0 if not errors else (2 if len(errors) < len(urls) else 1)
        return InspectionResult(envelope, exit_code)

    def snapshot(self, *, limit: int = 20) -> InspectionResult:
        if failure := self._preflight("reppo snapshot"):
            return failure
        if not 1 <= limit <= MAX_RESULT_LIMIT:
            return self._validation_failure(
                "reppo snapshot", "limit must be between 1 and 100"
            )
        urls = {
            "stats": f"{self.base_url}/stats",
            "datanets": f"{self.base_url}/public/subnets?{urlencode({'page': 1, 'limit': limit, 'search': ''})}",
            "pods": f"{self.base_url}/public/pods?{urlencode({'page': 1, 'limit': limit, 'search': ''})}",
        }
        data: dict[str, Any] = {}
        sources: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for name, url in urls.items():
            collection_key = {"datanets": "subnets", "pods": "pods"}.get(name)
            value, source, error = self._fetch(
                url, collection_key=collection_key, max_items=limit
            )
            data[name] = value
            sources.append(source)
            if error:
                errors.append(error)
        partial = bool(errors) and len(errors) < len(urls)
        envelope = self._envelope(
            "reppo snapshot",
            ok=not errors,
            partial=partial,
            sources=sources,
            data=data,
            errors=errors,
        )
        return InspectionResult(envelope, 0 if not errors else (2 if partial else 1))
