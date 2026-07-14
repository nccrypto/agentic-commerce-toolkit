"""Deterministic, default-deny action-control reference evaluator."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any, Mapping


_PUBLIC_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_ACTION_TYPE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_PARAMETER_NAME = re.compile(r"^[a-z][a-zA-Z0-9._-]{0,63}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_MAX_NUMERIC_MAGNITUDE = 10**18
_APPROVAL_FIELDS = {
    "approvalId",
    "actionId",
    "actionType",
    "actionDigest",
    "decision",
    "issuedAt",
    "expiresAt",
    "issuerType",
    "note",
}
_REQUIRED_APPROVAL_FIELDS = _APPROVAL_FIELDS - {"note"}
_LIMITATIONS = [
    "Authorization is not execution; a separate adapter must perform any approved action.",
    "This control record must contain public inputs only and must not contain credentials, wallet data, account identifiers, or private runtime state.",
]


def _parse_datetime(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not _DATE_TIME.fullmatch(value):
        raise ValueError(f"{field} must be an RFC 3339 date-time string")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError(f"{field} must be an RFC 3339 date-time string") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _validate_scalar(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int) and abs(value) <= _MAX_NUMERIC_MAGNITUDE:
        return
    if (
        isinstance(value, float)
        and math.isfinite(value)
        and abs(value) <= _MAX_NUMERIC_MAGNITUDE
    ):
        return
    if isinstance(value, str) and len(value) <= 1000:
        return
    raise ValueError("parameter values must be bounded public scalars")


def _validate_request(request: Mapping[str, Any]) -> dict[str, Any]:
    required = {"actionId", "actionType", "mode", "summary", "parameters"}
    if not isinstance(request, Mapping) or set(request) != required:
        raise ValueError("request must contain only actionId, actionType, mode, summary, and parameters")

    action_id = request["actionId"]
    action_type = request["actionType"]
    mode = request["mode"]
    summary = request["summary"]
    parameters = request["parameters"]

    if not isinstance(action_id, str) or not _PUBLIC_ID.fullmatch(action_id):
        raise ValueError("actionId must be a stable public identifier")
    if not isinstance(action_type, str) or not _ACTION_TYPE.fullmatch(action_type):
        raise ValueError("actionType must be a bounded public action type")
    if mode not in {"dry-run", "execute"}:
        raise ValueError("mode must be dry-run or execute")
    if not isinstance(summary, str) or not 1 <= len(summary) <= 500:
        raise ValueError("summary must contain between 1 and 500 characters")
    if not isinstance(parameters, list) or len(parameters) > 50:
        raise ValueError("parameters must be a list with at most 50 entries")

    normalized_parameters = []
    parameter_names = set()
    for parameter in parameters:
        if not isinstance(parameter, Mapping) or set(parameter) != {"name", "value"}:
            raise ValueError("each parameter must contain only name and value")
        name = parameter["name"]
        value = parameter["value"]
        if not isinstance(name, str) or not _PARAMETER_NAME.fullmatch(name):
            raise ValueError("parameter names must be bounded public identifiers")
        if name in parameter_names:
            raise ValueError("parameter names must be unique")
        parameter_names.add(name)
        if isinstance(value, list):
            if len(value) > 100:
                raise ValueError("parameter arrays must contain at most 100 values")
            for item in value:
                _validate_scalar(item)
        else:
            _validate_scalar(value)
        normalized_parameters.append({"name": name, "value": value})

    return {
        "actionId": action_id,
        "actionType": action_type,
        "mode": mode,
        "summary": summary,
        "parameters": normalized_parameters,
    }


def action_digest(request: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 digest for the action scope, excluding its mode."""

    normalized = _validate_request(request)
    payload = {
        "actionId": normalized["actionId"],
        "actionType": normalized["actionType"],
        "summary": normalized["summary"],
        "parameters": normalized["parameters"],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_approval(approval: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(approval, Mapping):
        raise ValueError("approval must be an object")
    fields = set(approval)
    if not _REQUIRED_APPROVAL_FIELDS.issubset(fields) or not fields.issubset(_APPROVAL_FIELDS):
        raise ValueError("approval contains missing or undeclared fields")
    if not isinstance(approval["approvalId"], str) or not _PUBLIC_ID.fullmatch(approval["approvalId"]):
        raise ValueError("approvalId must be a stable public identifier")
    if not isinstance(approval["actionId"], str) or not _PUBLIC_ID.fullmatch(approval["actionId"]):
        raise ValueError("approval actionId must be a stable public identifier")
    if not isinstance(approval["actionType"], str) or not _ACTION_TYPE.fullmatch(approval["actionType"]):
        raise ValueError("approval actionType must be bounded")
    if not isinstance(approval["actionDigest"], str) or not _DIGEST.fullmatch(approval["actionDigest"]):
        raise ValueError("approval actionDigest must be a SHA-256 digest")
    if approval["decision"] not in {"approved", "rejected"}:
        raise ValueError("approval decision must be approved or rejected")
    if approval["issuerType"] not in {"human", "policy"}:
        raise ValueError("issuerType must be human or policy")
    _parse_datetime(approval["issuedAt"], "approval.issuedAt")
    _parse_datetime(approval["expiresAt"], "approval.expiresAt")
    if "note" in approval and (
        not isinstance(approval["note"], str) or not 1 <= len(approval["note"]) <= 500
    ):
        raise ValueError("approval note must contain between 1 and 500 characters")
    return dict(approval)


def evaluate_action_control(
    control_id: str,
    request: Mapping[str, Any],
    evaluated_at: str,
    approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a dry-run or execute request without performing the action."""

    if not isinstance(control_id, str) or not _PUBLIC_ID.fullmatch(control_id):
        raise ValueError("controlId must be a stable public identifier")
    normalized = _validate_request(request)
    evaluated_time = _parse_datetime(evaluated_at, "evaluatedAt")
    digest = action_digest(normalized)
    request_record = {
        "actionId": normalized["actionId"],
        "actionType": normalized["actionType"],
        "actionDigest": digest,
        "mode": normalized["mode"],
        "summary": normalized["summary"],
        "parameters": normalized["parameters"],
    }

    if normalized["mode"] == "dry-run":
        if approval is not None:
            raise ValueError("dry-run requests must not include an approval")
        approval_record = None
        decision = {
            "status": "dry-run",
            "mayExecute": False,
            "reasonCode": "DRY_RUN_ONLY",
            "message": "The action was evaluated only; execution is not authorized.",
        }
    elif approval is None:
        approval_record = None
        decision = {
            "status": "rejected",
            "mayExecute": False,
            "reasonCode": "APPROVAL_REQUIRED",
            "message": "Execution is denied because no approval was supplied.",
        }
    else:
        try:
            approval_record = _validate_approval(approval)
        except ValueError:
            approval_record = None
            decision = {
                "status": "rejected",
                "mayExecute": False,
                "reasonCode": "INVALID_APPROVAL",
                "message": "Execution is denied because the approval record is invalid.",
            }
        else:
            issued_at = _parse_datetime(approval_record["issuedAt"], "approval.issuedAt")
            expires_at = _parse_datetime(approval_record["expiresAt"], "approval.expiresAt")
            scoped = (
                approval_record["actionId"] == normalized["actionId"]
                and approval_record["actionType"] == normalized["actionType"]
                and approval_record["actionDigest"] == digest
            )
            if not scoped:
                decision = {
                    "status": "rejected",
                    "mayExecute": False,
                    "reasonCode": "APPROVAL_SCOPE_MISMATCH",
                    "message": "Execution is denied because the approval does not match the action scope.",
                }
            elif issued_at > evaluated_time or expires_at <= issued_at:
                decision = {
                    "status": "rejected",
                    "mayExecute": False,
                    "reasonCode": "INVALID_APPROVAL",
                    "message": "Execution is denied because the approval validity interval is invalid.",
                }
            elif expires_at <= evaluated_time:
                decision = {
                    "status": "rejected",
                    "mayExecute": False,
                    "reasonCode": "APPROVAL_EXPIRED",
                    "message": "Execution is denied because the approval has expired.",
                }
            elif approval_record["decision"] == "rejected":
                decision = {
                    "status": "rejected",
                    "mayExecute": False,
                    "reasonCode": "APPROVAL_REJECTED",
                    "message": "Execution is denied by the supplied approval decision.",
                }
            else:
                decision = {
                    "status": "authorized",
                    "mayExecute": True,
                    "reasonCode": "APPROVED",
                    "message": "The action is authorized for a separate execution adapter.",
                }

    return {
        "schemaVersion": "1.0",
        "controlId": control_id,
        "evaluatedAt": evaluated_at,
        "request": request_record,
        "approval": approval_record,
        "decision": decision,
        "limitations": list(_LIMITATIONS),
    }
