"""Deterministic local reference service for a Virtuals ACP evidence job.

The module models one bounded provider offering: validate a public source
manifest and an agent-job result, check their provenance linkage, and emit an
``agent-job-result-v1`` receipt.  Local mode performs no network, wallet,
signing, payment, inference, or ACP mutation.
"""

from __future__ import annotations

import ipaddress
import json
import math
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from .reppo import utc_now

JOB_TYPE = "virtuals-acp.public-evidence-verification"
_MAX_REQUEST_BYTES = 1_000_000
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
_KIND = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_INPUT_NAME = re.compile(r"^[a-z][a-zA-Z0-9._-]{0,63}$")
_ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_SOURCE_TYPES = {
    "api",
    "documentation",
    "repository",
    "schema",
    "example",
    "issue",
    "release",
    "article",
    "other",
}
_PURPOSES = {
    "input",
    "validation",
    "compatibility-check",
    "citation",
    "fixture-basis",
    "schema-reference",
    "other",
}


class TransientProviderError(RuntimeError):
    """A retryable local-provider failure used by adapters and tests."""


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _canonical_size(value: Any) -> int:
    try:
        return len(
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
    except (TypeError, ValueError):
        return _MAX_REQUEST_BYTES + 1


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not _DATE_TIME.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _text(value: Any, minimum: int, maximum: int) -> bool:
    return isinstance(value, str) and minimum <= len(value) <= maximum


def _exact_keys(
    value: Any,
    required: set[str],
    optional: set[str],
    path: str,
    findings: list[str],
) -> bool:
    if not _is_mapping(value):
        findings.append(f"{path} must be an object.")
        return False
    keys = set(value)
    missing = sorted(required - keys)
    extra = sorted(keys - required - optional)
    if missing:
        findings.append(f"{path} is missing required fields: {', '.join(missing)}.")
    if extra:
        findings.append(f"{path} contains undeclared fields: {', '.join(extra)}.")
    return not missing and not extra


def _string_array(
    value: Any,
    path: str,
    findings: list[str],
    *,
    maximum_items: int,
    maximum_length: int,
) -> bool:
    if not isinstance(value, list) or len(value) > maximum_items:
        findings.append(f"{path} must be an array with at most {maximum_items} items.")
        return False
    valid = True
    for index, item in enumerate(value):
        if not _text(item, 1, maximum_length):
            findings.append(
                f"{path}[{index}] must be a non-empty string of at most {maximum_length} characters."
            )
            valid = False
    return valid


def _public_scalar(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return not isinstance(value, str) or len(value) <= 1000
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _public_value(value: Any, depth: int = 0) -> bool:
    if _public_scalar(value):
        return True
    if depth >= 3:
        return False
    if isinstance(value, list):
        return len(value) <= 100 and all(_public_value(item, depth + 1) for item in value)
    if _is_mapping(value):
        return len(value) <= 100 and all(
            isinstance(key, str) and _public_value(item, depth + 1)
            for key, item in value.items()
        )
    return False


def _public_https_url(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 1000:
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if port not in (None, 443):
        return False
    lowered = host.rstrip(".").lower()
    if lowered == "localhost" or lowered.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        address = ipaddress.ip_address(lowered.strip("[]"))
    except ValueError:
        return "." in lowered and not lowered.startswith(".") and not lowered.endswith(".")
    return address.is_global


def _uri(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 2048 or any(
        character.isspace() for character in value
    ):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if not parsed.scheme:
        return False
    return parsed.scheme not in {"http", "https"} or bool(parsed.netloc)


def _bounded_finding(value: str) -> str:
    return value if len(value) <= 500 else value[:497] + "..."


def _validate_usage(value: Any, path: str, findings: list[str]) -> None:
    if not _exact_keys(
        value,
        {"purpose", "derivedFacts"},
        {"limitations"},
        path,
        findings,
    ):
        return
    if value["purpose"] not in _PURPOSES:
        findings.append(f"{path}.purpose is not an allowed value.")
    _string_array(
        value["derivedFacts"],
        f"{path}.derivedFacts",
        findings,
        maximum_items=20,
        maximum_length=300,
    )
    if "limitations" in value:
        _string_array(
            value["limitations"],
            f"{path}.limitations",
            findings,
            maximum_items=20,
            maximum_length=300,
        )


def validate_source_manifest(value: Any) -> list[str]:
    """Return bounded contract findings for a source-manifest-v1 candidate."""

    findings: list[str] = []
    if not _exact_keys(
        value,
        {"schemaVersion", "manifestId", "generatedAt", "subject", "sources"},
        {"notes"},
        "sourceManifest",
        findings,
    ):
        return findings[:50]
    if value["schemaVersion"] != "1.0":
        findings.append("sourceManifest.schemaVersion must equal 1.0.")
    if not isinstance(value["manifestId"], str) or not _ID.fullmatch(value["manifestId"]):
        findings.append("sourceManifest.manifestId is invalid.")
    if _parse_datetime(value["generatedAt"]) is None:
        findings.append("sourceManifest.generatedAt must be an RFC 3339 date-time.")

    subject = value["subject"]
    if _exact_keys(
        subject,
        {"kind", "name"},
        {"version", "description"},
        "sourceManifest.subject",
        findings,
    ):
        if not isinstance(subject["kind"], str) or not _KIND.fullmatch(subject["kind"]):
            findings.append("sourceManifest.subject.kind is invalid.")
        if not _text(subject["name"], 1, 160):
            findings.append("sourceManifest.subject.name is invalid.")
        if "version" in subject and not _text(subject["version"], 1, 80):
            findings.append("sourceManifest.subject.version is invalid.")
        if "description" in subject and not _text(subject["description"], 1, 500):
            findings.append("sourceManifest.subject.description is invalid.")

    sources = value["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        findings.append("sourceManifest.sources must contain between 1 and 100 records.")
    else:
        seen_ids: set[str] = set()
        for index, source in enumerate(sources):
            path = f"sourceManifest.sources[{index}]"
            if not _exact_keys(
                source,
                {"sourceId", "title", "url", "sourceType", "publisher", "accessedAt", "usage"},
                {"retrievedAt", "license", "version", "contentDigest"},
                path,
                findings,
            ):
                continue
            source_id = source["sourceId"]
            if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
                findings.append(f"{path}.sourceId is invalid.")
            elif source_id in seen_ids:
                findings.append(f"{path}.sourceId duplicates another source record.")
            else:
                seen_ids.add(source_id)
            if not _text(source["title"], 1, 240):
                findings.append(f"{path}.title is invalid.")
            if not _uri(source["url"]):
                findings.append(f"{path}.url is invalid.")
            if source["sourceType"] not in _SOURCE_TYPES:
                findings.append(f"{path}.sourceType is not allowed.")
            if not _text(source["publisher"], 1, 160):
                findings.append(f"{path}.publisher is invalid.")
            if _parse_datetime(source["accessedAt"]) is None:
                findings.append(f"{path}.accessedAt must be an RFC 3339 date-time.")
            if "retrievedAt" in source and _parse_datetime(source["retrievedAt"]) is None:
                findings.append(f"{path}.retrievedAt must be an RFC 3339 date-time.")
            for field, limit in (("license", 120), ("version", 120)):
                if field in source and not _text(source[field], 1, limit):
                    findings.append(f"{path}.{field} is invalid.")
            if "contentDigest" in source:
                digest = source["contentDigest"]
                if _exact_keys(digest, {"algorithm", "value"}, set(), f"{path}.contentDigest", findings):
                    if digest["algorithm"] != "sha256" or not isinstance(digest["value"], str) or not re.fullmatch(r"[a-f0-9]{64}", digest["value"]):
                        findings.append(f"{path}.contentDigest is invalid.")
            _validate_usage(source["usage"], f"{path}.usage", findings)
    if "notes" in value:
        _string_array(
            value["notes"],
            "sourceManifest.notes",
            findings,
            maximum_items=20,
            maximum_length=500,
        )
    return findings[:50]


def _validate_job_request(value: Any, findings: list[str]) -> None:
    if not _exact_keys(value, {"summary", "inputs"}, set(), "jobResult.request", findings):
        return
    if not _text(value["summary"], 1, 500):
        findings.append("jobResult.request.summary is invalid.")
    inputs = value["inputs"]
    if not isinstance(inputs, list) or len(inputs) > 50:
        findings.append("jobResult.request.inputs must contain at most 50 records.")
        return
    for index, item in enumerate(inputs):
        path = f"jobResult.request.inputs[{index}]"
        if not _exact_keys(item, {"name", "value"}, set(), path, findings):
            continue
        if not isinstance(item["name"], str) or not _INPUT_NAME.fullmatch(item["name"]):
            findings.append(f"{path}.name is invalid.")
        input_value = item["value"]
        valid = _public_scalar(input_value) or (
            isinstance(input_value, list)
            and len(input_value) <= 100
            and all(_public_scalar(entry) for entry in input_value)
        )
        if not valid:
            findings.append(f"{path}.value is not a bounded public input value.")


def validate_agent_job_result(value: Any) -> list[str]:
    """Return bounded contract findings for an agent-job-result-v1 candidate."""

    findings: list[str] = []
    required = {
        "schemaVersion", "jobId", "jobType", "status", "startedAt", "completedAt",
        "request", "result", "provenance", "errors", "limitations",
    }
    optional = {"cost", "timeout", "freshness"}
    if not _exact_keys(value, required, optional, "jobResult", findings):
        return findings[:50]
    if value["schemaVersion"] != "1.0":
        findings.append("jobResult.schemaVersion must equal 1.0.")
    if not isinstance(value["jobId"], str) or not _ID.fullmatch(value["jobId"]):
        findings.append("jobResult.jobId is invalid.")
    if not isinstance(value["jobType"], str) or not _KIND.fullmatch(value["jobType"]):
        findings.append("jobResult.jobType is invalid.")
    status = value["status"]
    if status not in {"succeeded", "partial", "failed"}:
        findings.append("jobResult.status is not allowed.")
    started = _parse_datetime(value["startedAt"])
    completed = _parse_datetime(value["completedAt"])
    if started is None:
        findings.append("jobResult.startedAt must be an RFC 3339 date-time.")
    if completed is None:
        findings.append("jobResult.completedAt must be an RFC 3339 date-time.")
    if started is not None and completed is not None and completed < started:
        findings.append("jobResult.completedAt precedes startedAt.")
    _validate_job_request(value["request"], findings)

    result = value["result"]
    if status == "failed":
        if result is not None:
            findings.append("jobResult.result must be null when status is failed.")
    elif not _is_mapping(result):
        findings.append("jobResult.result must be an object for succeeded or partial status.")
    if isinstance(result, Mapping):
        if _exact_keys(result, {"summary", "data"}, set(), "jobResult.result", findings):
            if not _text(result["summary"], 1, 1000):
                findings.append("jobResult.result.summary is invalid.")
            data = result["data"]
            if not _is_mapping(data) or len(data) > 100 or not all(
                isinstance(key, str) and _public_value(item) for key, item in data.items()
            ):
                findings.append("jobResult.result.data is not a bounded public object.")

    provenance = value["provenance"]
    if _exact_keys(provenance, {"manifestId"}, {"manifestUrl", "sourceIds"}, "jobResult.provenance", findings):
        if not isinstance(provenance["manifestId"], str) or not _ID.fullmatch(provenance["manifestId"]):
            findings.append("jobResult.provenance.manifestId is invalid.")
        if "manifestUrl" in provenance and not _uri(provenance["manifestUrl"]):
            findings.append("jobResult.provenance.manifestUrl is invalid.")
        if "sourceIds" in provenance:
            source_ids = provenance["sourceIds"]
            valid_source_ids = (
                isinstance(source_ids, list)
                and len(source_ids) <= 100
                and all(
                    isinstance(source_id, str) and _SOURCE_ID.fullmatch(source_id)
                    for source_id in source_ids
                )
            )
            if valid_source_ids and len(source_ids) != len(set(source_ids)):
                valid_source_ids = False
            if not valid_source_ids:
                findings.append("jobResult.provenance.sourceIds is invalid.")

    errors = value["errors"]
    if not isinstance(errors, list) or len(errors) > 50:
        findings.append("jobResult.errors must contain at most 50 records.")
    else:
        for index, error in enumerate(errors):
            path = f"jobResult.errors[{index}]"
            if not _exact_keys(error, {"code", "message"}, {"retryable"}, path, findings):
                continue
            if not isinstance(error["code"], str) or not _ERROR_CODE.fullmatch(error["code"]):
                findings.append(f"{path}.code is invalid.")
            if not _text(error["message"], 1, 500):
                findings.append(f"{path}.message is invalid.")
            if "retryable" in error and not isinstance(error["retryable"], bool):
                findings.append(f"{path}.retryable must be boolean.")
        if status == "failed" and not errors:
            findings.append("jobResult.errors must be non-empty when status is failed.")
    _string_array(value["limitations"], "jobResult.limitations", findings, maximum_items=50, maximum_length=500)

    if "cost" in value:
        cost = value["cost"]
        if _exact_keys(cost, {"amount", "currency", "basis"}, set(), "jobResult.cost", findings):
            if not isinstance(cost["amount"], str) or not re.fullmatch(r"(0|[1-9][0-9]{0,17})(\.[0-9]{1,18})?", cost["amount"]):
                findings.append("jobResult.cost.amount is invalid.")
            if not isinstance(cost["currency"], str) or not re.fullmatch(r"[A-Z][A-Z0-9]{2,11}", cost["currency"]):
                findings.append("jobResult.cost.currency is invalid.")
            if cost["basis"] not in {"measured", "estimated"}:
                findings.append("jobResult.cost.basis is invalid.")
    if "timeout" in value:
        timeout = value["timeout"]
        if _exact_keys(timeout, {"limitMs", "elapsedMs", "timedOut"}, set(), "jobResult.timeout", findings):
            for field in ("limitMs", "elapsedMs"):
                minimum = 1 if field == "limitMs" else 0
                if isinstance(timeout[field], bool) or not isinstance(timeout[field], int) or not minimum <= timeout[field] <= 604800000:
                    findings.append(f"jobResult.timeout.{field} is invalid.")
            if not isinstance(timeout["timedOut"], bool):
                findings.append("jobResult.timeout.timedOut must be boolean.")
    if "freshness" in value:
        freshness = value["freshness"]
        if _exact_keys(freshness, {"evaluatedAt", "status"}, {"dataAsOf", "maxAgeSeconds"}, "jobResult.freshness", findings):
            if _parse_datetime(freshness["evaluatedAt"]) is None:
                findings.append("jobResult.freshness.evaluatedAt is invalid.")
            fresh_status = freshness["status"]
            if fresh_status not in {"fresh", "stale", "unknown"}:
                findings.append("jobResult.freshness.status is invalid.")
            if fresh_status in {"fresh", "stale"} and not {"dataAsOf", "maxAgeSeconds"} <= set(freshness):
                findings.append("jobResult.freshness needs dataAsOf and maxAgeSeconds when freshness is known.")
            if "dataAsOf" in freshness and _parse_datetime(freshness["dataAsOf"]) is None:
                findings.append("jobResult.freshness.dataAsOf is invalid.")
            if "maxAgeSeconds" in freshness and (
                isinstance(freshness["maxAgeSeconds"], bool)
                or not isinstance(freshness["maxAgeSeconds"], int)
                or not 0 <= freshness["maxAgeSeconds"] <= 315360000
            ):
                findings.append("jobResult.freshness.maxAgeSeconds is invalid.")
    return findings[:50]


def _validate_request_envelope(request: Any) -> list[str]:
    findings: list[str] = []
    if _canonical_size(request) > _MAX_REQUEST_BYTES:
        findings.append("request exceeds the 1000000-byte canonical size limit.")
        return findings
    if not _exact_keys(
        request,
        {"schemaVersion", "requestId", "jobType", "mode", "sourceManifest", "jobResult"},
        set(),
        "request",
        findings,
    ):
        return findings
    if request["schemaVersion"] != "1.0":
        findings.append("request.schemaVersion must equal 1.0.")
    if not isinstance(request["requestId"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9._:-]{2,99}", request["requestId"]):
        findings.append("request.requestId is invalid.")
    if request["jobType"] != JOB_TYPE:
        findings.append(f"request.jobType must equal {JOB_TYPE}.")
    if request["mode"] != "local":
        findings.append("Only local mode is implemented by this reference service.")
    if not _is_mapping(request["sourceManifest"]) or not 1 <= len(request["sourceManifest"]) <= 20:
        findings.append("request.sourceManifest must be an object with 1 to 20 properties.")
    if not _is_mapping(request["jobResult"]) or not 1 <= len(request["jobResult"]) <= 30:
        findings.append("request.jobResult must be an object with 1 to 30 properties.")
    return findings[:50]


def _check(check_id: str, findings: Sequence[str], passed_summary: str) -> dict[str, Any]:
    bounded = [_bounded_finding(finding) for finding in findings[:20]]
    return {
        "checkId": check_id,
        "status": "pass" if not bounded else "fail",
        "summary": passed_summary if not bounded else f"{len(bounded)} bounded finding(s) recorded.",
        "findings": bounded,
    }


def _verify_bundle(request: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    manifest = request["sourceManifest"]
    job_result = request["jobResult"]
    manifest_findings = validate_source_manifest(manifest)
    result_findings = validate_agent_job_result(job_result)

    linkage: list[str] = []
    if _is_mapping(manifest) and _is_mapping(job_result):
        manifest_id = manifest.get("manifestId")
        provenance = job_result.get("provenance")
        if not _is_mapping(provenance):
            linkage.append("jobResult.provenance is unavailable for linkage checking.")
        else:
            if provenance.get("manifestId") != manifest_id:
                linkage.append("jobResult.provenance.manifestId does not match sourceManifest.manifestId.")
            manifest_source_ids = {
                source.get("sourceId")
                for source in manifest.get("sources", [])
                if _is_mapping(source) and isinstance(source.get("sourceId"), str)
            }
            referenced = provenance.get("sourceIds", [])
            if isinstance(referenced, list):
                missing = sorted(
                    source_id
                    for source_id in referenced
                    if isinstance(source_id, str) and source_id not in manifest_source_ids
                )
                if missing:
                    linkage.append(
                        "jobResult.provenance.sourceIds contains IDs absent from the manifest: "
                        + ", ".join(missing[:10])
                        + "."
                    )
    else:
        linkage.append("Evidence documents are unavailable for linkage checking.")

    public_policy: list[str] = []
    sources: list[dict[str, str]] = []
    emitted_source_ids: set[str] = set()
    if _is_mapping(manifest) and isinstance(manifest.get("sources"), list):
        for index, source in enumerate(manifest["sources"][:100]):
            if not _is_mapping(source):
                continue
            source_id = source.get("sourceId")
            url = source.get("url")
            if not _public_https_url(url):
                public_policy.append(
                    f"sourceManifest.sources[{index}].url is not an allowed public HTTPS URL."
                )
            elif (
                isinstance(source_id, str)
                and _SOURCE_ID.fullmatch(source_id)
                and source_id not in emitted_source_ids
            ):
                sources.append({"sourceId": source_id, "url": url})
                emitted_source_ids.add(source_id)
    else:
        public_policy.append("No source records are available for public URL policy checking.")

    if _is_mapping(job_result):
        provenance = job_result.get("provenance")
        manifest_url = provenance.get("manifestUrl") if _is_mapping(provenance) else None
        if manifest_url is not None and not _public_https_url(manifest_url):
            public_policy.append("jobResult.provenance.manifestUrl is not an allowed public HTTPS URL.")

    checks = [
        _check("source-manifest-contract", manifest_findings, "The candidate conforms to source-manifest-v1."),
        _check("agent-job-result-contract", result_findings, "The candidate conforms to agent-job-result-v1."),
        _check("provenance-linkage", linkage, "Manifest and source identifiers are consistently linked."),
        _check("public-source-policy", public_policy, "All referenced source locations use allowed public HTTPS URLs."),
    ]
    return checks, sources


def _safe_identifier(request: Any, key: str, fallback: str, pattern: re.Pattern[str]) -> str:
    if _is_mapping(request):
        value = request.get(key)
        if isinstance(value, str) and pattern.fullmatch(value):
            return value
    return fallback


def _request_metadata(request: Any, max_attempts: int) -> tuple[str, str, str, list[dict[str, Any]]]:
    request_id = _safe_identifier(request, "requestId", "invalid-request", re.compile(r"[a-z0-9][a-z0-9._:-]{2,99}"))
    manifest = request.get("sourceManifest") if _is_mapping(request) else None
    job_result = request.get("jobResult") if _is_mapping(request) else None
    manifest_id = _safe_identifier(manifest, "manifestId", "unknown-manifest", _ID)
    source_job_id = _safe_identifier(job_result, "jobId", "unknown-source-job", _ID)
    inputs = [
        {"name": "requestId", "value": request_id},
        {"name": "manifestId", "value": manifest_id},
        {"name": "sourceJobId", "value": source_job_id},
        {"name": "mode", "value": "local"},
        {"name": "maxAttempts", "value": max_attempts},
    ]
    return request_id, manifest_id, source_job_id, inputs


def _freshness(manifest: Any, evaluated_at: str) -> dict[str, Any]:
    timestamps: list[datetime] = []
    if _is_mapping(manifest) and isinstance(manifest.get("sources"), list):
        for source in manifest["sources"]:
            if _is_mapping(source):
                parsed = _parse_datetime(source.get("accessedAt"))
                if parsed is not None:
                    timestamps.append(parsed)
    evaluated = _parse_datetime(evaluated_at)
    if not timestamps or evaluated is None:
        return {"evaluatedAt": evaluated_at, "status": "unknown"}
    data_as_of = max(timestamps)
    max_age = 86400
    age = max(0.0, (evaluated - data_as_of).total_seconds())
    return {
        "evaluatedAt": evaluated_at,
        "status": "fresh" if age <= max_age else "stale",
        "dataAsOf": data_as_of.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "maxAgeSeconds": max_age,
    }


def run_local_evidence_job(
    request: Any,
    *,
    timeout_ms: int = 5000,
    max_attempts: int = 3,
    verifier: Callable[[Mapping[str, Any]], tuple[list[dict[str, Any]], list[dict[str, str]]]] | None = None,
    clock: Callable[[], str] = utc_now,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run a bounded, deterministic local buyer/provider simulation.

    ``verifier`` is injectable for retry/timeout tests and future read-only
    adapters.  Only :class:`TransientProviderError` is retried.
    """

    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or not 1 <= timeout_ms <= 604800000:
        raise ValueError("timeout_ms must be an integer from 1 through 604800000")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
        raise ValueError("max_attempts must be an integer from 1 through 10")

    started_at = clock()
    started_tick = monotonic()
    request_id, manifest_id, _source_job_id, inputs = _request_metadata(request, max_attempts)
    lifecycle: list[dict[str, str]] = [{"status": "open", "at": started_at}]
    envelope_findings = _validate_request_envelope(request)
    attempts = 0
    checks: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    service_error: tuple[str, str, bool] | None = None
    timed_out = False

    if envelope_findings:
        checks = [_check("request-contract", envelope_findings, "The request envelope is valid.")]
    else:
        lifecycle.extend(
            [
                {"status": "budget_set", "at": clock()},
                {"status": "funded", "at": clock()},
            ]
        )
        provider = verifier or _verify_bundle
        while attempts < max_attempts:
            elapsed_before = max(0, int((monotonic() - started_tick) * 1000))
            if elapsed_before >= timeout_ms:
                timed_out = True
                service_error = ("TIMEOUT", "The local provider exceeded its bounded timeout.", True)
                break
            attempts += 1
            try:
                checks, sources = provider(request)
                elapsed_after = max(0, int((monotonic() - started_tick) * 1000))
                if elapsed_after >= timeout_ms:
                    timed_out = True
                    service_error = ("TIMEOUT", "The local provider exceeded its bounded timeout.", True)
                break
            except TransientProviderError:
                if attempts >= max_attempts:
                    service_error = (
                        "RETRY_EXHAUSTED",
                        "The local provider did not succeed within the bounded retry limit.",
                        True,
                    )
            except Exception:
                service_error = (
                    "PROVIDER_ERROR",
                    "The local provider failed without exposing private exception details.",
                    False,
                )
                break

    completed_at = clock()
    elapsed_ms = min(604800000, max(0, int((monotonic() - started_tick) * 1000)))
    limitations = [
        "Local mode simulates the ACP buyer/provider lifecycle without creating, funding, or settling a live Virtuals ACP job.",
        "A passing receipt confirms contract, linkage, and public-location checks; it does not attest that source claims are true or current.",
    ]
    provenance: dict[str, Any] = {"manifestId": manifest_id}
    if sources:
        provenance["sourceIds"] = [source["sourceId"] for source in sources]

    if service_error is not None:
        lifecycle.append({"status": "rejected", "at": completed_at})
        code, message, retryable = service_error
        return {
            "schemaVersion": "1.0",
            "jobId": f"receipt:{request_id}",
            "jobType": JOB_TYPE,
            "status": "failed",
            "startedAt": started_at,
            "completedAt": completed_at,
            "request": {
                "summary": "Verify a bounded public evidence bundle in the local Virtuals ACP reference flow.",
                "inputs": inputs,
            },
            "result": None,
            "provenance": provenance,
            "cost": {"amount": "0", "currency": "USD", "basis": "measured"},
            "timeout": {"limitMs": timeout_ms, "elapsedMs": elapsed_ms, "timedOut": timed_out},
            "freshness": _freshness(request.get("sourceManifest") if _is_mapping(request) else None, completed_at),
            "errors": [{"code": code, "message": message, "retryable": retryable}],
            "limitations": limitations,
        }

    lifecycle.extend(
        [
            {"status": "submitted", "at": completed_at},
            {"status": "completed", "at": completed_at},
        ]
    )
    verdict = "pass" if checks and all(check["status"] == "pass" for check in checks) else "fail"
    return {
        "schemaVersion": "1.0",
        "jobId": f"receipt:{request_id}",
        "jobType": JOB_TYPE,
        "status": "succeeded",
        "startedAt": started_at,
        "completedAt": completed_at,
        "request": {
            "summary": "Verify a bounded public evidence bundle in the local Virtuals ACP reference flow.",
            "inputs": inputs,
        },
        "result": {
            "summary": (
                "All public evidence checks passed."
                if verdict == "pass"
                else "The provider completed verification and recorded one or more failed checks."
            ),
            "data": {
                "verdict": verdict,
                "mode": "local",
                "attempts": attempts,
                "checks": checks,
                "sources": sources,
                "lifecycle": lifecycle,
            },
        },
        "provenance": provenance,
        "cost": {"amount": "0", "currency": "USD", "basis": "measured"},
        "timeout": {"limitMs": timeout_ms, "elapsedMs": elapsed_ms, "timedOut": False},
        "freshness": _freshness(request.get("sourceManifest") if _is_mapping(request) else None, completed_at),
        "errors": [],
        "limitations": limitations,
    }


def receipt_exit_code(receipt: Mapping[str, Any]) -> int:
    """Map a receipt to CLI status: pass=0, findings=2, service failure=1."""

    if receipt.get("status") == "failed":
        return 1
    result = receipt.get("result")
    if isinstance(result, Mapping):
        data = result.get("data")
        if isinstance(data, Mapping):
            return 0 if data.get("verdict") == "pass" else 2
    return 1
