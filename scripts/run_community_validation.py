"""Run the network-free Phase 4 community validation protocol."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentic_commerce.acp_evidence import (  # noqa: E402
    TransientProviderError,
    receipt_exit_code,
    run_local_evidence_job,
)

_VALIDATION_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_REVISION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
REQUEST_EXAMPLE = (
    ROOT / "examples" / "virtuals-acp-evidence" / "request-v1.example.json"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _platform() -> str:
    return sys.platform if sys.platform in {"linux", "darwin", "win32"} else "other"


def _check(check_id: str, passed: bool, passed_summary: str, failed_summary: str) -> dict[str, str]:
    return {
        "checkId": check_id,
        "status": "pass" if passed else "fail",
        "summary": passed_summary if passed else failed_summary,
    }


def _validate_inputs(validation_id: str, revision: str, recorded_at: str) -> None:
    if not _VALIDATION_ID.fullmatch(validation_id):
        raise ValueError("validation_id must be a bounded public identifier")
    if not _REVISION.fullmatch(revision):
        raise ValueError("revision must be a bounded public tag or commit identifier")
    if not _DATE_TIME.fullmatch(recorded_at):
        raise ValueError("recorded_at must be an RFC 3339 date-time")
    datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))


def build_validation_result(
    validation_id: str,
    revision: str,
    recorded_at: str,
    *,
    request_path: Path = REQUEST_EXAMPLE,
) -> dict[str, Any]:
    """Exercise pass, finding, and bounded provider-failure paths."""

    _validate_inputs(validation_id, revision, recorded_at)
    checks: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    static_clock: Callable[[], str] = lambda: recorded_at
    static_monotonic: Callable[[], float] = lambda: 100.0

    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))

        passing = run_local_evidence_job(
            copy.deepcopy(request),
            clock=static_clock,
            monotonic=static_monotonic,
        )
        passing_data = passing.get("result", {}).get("data", {})
        pass_ok = (
            receipt_exit_code(passing) == 0
            and passing.get("status") == "succeeded"
            and passing_data.get("verdict") == "pass"
            and all(item.get("status") == "pass" for item in passing_data.get("checks", []))
        )
        checks.append(
            _check(
                "passing-fixture",
                pass_ok,
                "The published evidence fixture produced a successful pass receipt.",
                "The published evidence fixture did not produce the expected pass receipt.",
            )
        )

        mismatched = copy.deepcopy(request)
        mismatched["jobResult"]["provenance"]["manifestId"] = "example:community-mismatch"
        finding = run_local_evidence_job(
            mismatched,
            clock=static_clock,
            monotonic=static_monotonic,
        )
        finding_data = finding.get("result", {}).get("data", {})
        finding_ok = (
            receipt_exit_code(finding) == 2
            and finding.get("status") == "succeeded"
            and finding_data.get("verdict") == "fail"
            and any(
                item.get("checkId") == "provenance-linkage"
                and item.get("status") == "fail"
                for item in finding_data.get("checks", [])
            )
        )
        checks.append(
            _check(
                "finding-fixture",
                finding_ok,
                "A synthetic provenance mismatch produced a completed fail verdict and exit code 2.",
                "The synthetic provenance mismatch did not produce the expected bounded finding.",
            )
        )

        def transient_failure(_candidate: Any) -> Any:
            raise TransientProviderError("synthetic detail must not be returned")

        failed = run_local_evidence_job(
            copy.deepcopy(request),
            verifier=transient_failure,
            max_attempts=2,
            clock=static_clock,
            monotonic=static_monotonic,
        )
        failure_rendered = json.dumps(failed, sort_keys=True)
        failure_ok = (
            receipt_exit_code(failed) == 1
            and failed.get("status") == "failed"
            and failed.get("result") is None
            and failed.get("errors", [{}])[0].get("code") == "RETRY_EXHAUSTED"
            and "synthetic detail" not in failure_rendered
        )
        checks.append(
            _check(
                "failure-fixture",
                failure_ok,
                "Bounded retry exhaustion produced a sanitized failed receipt and exit code 1.",
                "The retry-exhaustion path did not produce the expected sanitized failure receipt.",
            )
        )

        local_only_ok = (
            passing.get("cost")
            == {"amount": "0", "currency": "USD", "basis": "measured"}
            and passing_data.get("mode") == "local"
            and [item.get("status") for item in passing_data.get("lifecycle", [])]
            == ["open", "budget_set", "funded", "submitted", "completed"]
        )
        checks.append(
            _check(
                "local-execution-boundary",
                local_only_ok,
                "The reference flow remained local, zero-cost, and explicitly simulated.",
                "The reference flow did not preserve its expected local execution boundary.",
            )
        )
    except Exception:
        checks = [
            _check(
                "harness-execution",
                False,
                "The community validation harness completed.",
                "The harness could not complete using the published fixture.",
            )
        ]
        errors.append(
            {
                "code": "HARNESS_ERROR",
                "message": "The harness failed without exposing local exception or path details.",
            }
        )

    failed_checks = [item for item in checks if item["status"] == "fail"]
    if failed_checks and not errors:
        errors.append(
            {
                "code": "VALIDATION_CHECK_FAILED",
                "message": f"{len(failed_checks)} bounded community validation check(s) failed.",
            }
        )

    return {
        "schemaVersion": "1.0",
        "validationId": validation_id,
        "recordedAt": recorded_at,
        "toolkitRevision": revision,
        "environment": {
            "pythonVersion": ".".join(str(part) for part in sys.version_info[:3]),
            "platform": _platform(),
        },
        "status": "failed" if failed_checks else "passed",
        "checks": checks,
        "errors": errors,
        "limitations": [
            "This harness exercises synthetic local fixtures and does not prove a live ACP job, payment, settlement, or upstream endorsement.",
            "The generated record excludes raw logs and must still receive human sensitive-data review before public submission.",
        ],
        "sharing": {
            "reviewedForSensitiveData": False,
            "publicSubmissionApproved": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--recorded-at", default=None)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    clock: Callable[[], str] = utc_now,
) -> int:
    args = build_parser().parse_args(argv)
    output = stdout or sys.stdout
    try:
        result = build_validation_result(
            args.validation_id,
            args.revision,
            args.recorded_at or clock(),
        )
    except ValueError as exc:
        build_parser().error(str(exc))
    options: dict[str, Any] = {"sort_keys": True}
    if args.pretty:
        options["indent"] = 2
    else:
        options["separators"] = (",", ":")
    print(json.dumps(result, **options), file=output)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
