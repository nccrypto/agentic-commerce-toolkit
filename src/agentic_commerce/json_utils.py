"""Strict JSON decoding for bounded, untrusted public inputs."""

from __future__ import annotations

import json
import math
from typing import Any


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite JSON number")
    return number


def strict_json_loads(value: str | bytes) -> Any:
    """Reject non-finite numbers and nesting beyond 100 containers.

    Callers must cap input bytes before decoding and handle ValueError,
    UnicodeError, and RecursionError without exposing input details.
    """
    result = json.loads(value, parse_constant=_reject_constant, parse_float=_finite_float)
    pending = [(result, 0)]
    while pending:
        item, depth = pending.pop()
        if isinstance(item, (dict, list)):
            if depth >= 100:
                raise ValueError("JSON nesting exceeds limit")
            children = item.values() if isinstance(item, dict) else item
            pending.extend((child, depth + 1) for child in children)
    return result
