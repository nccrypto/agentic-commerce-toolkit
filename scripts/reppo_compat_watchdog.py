#!/usr/bin/env python3
"""Silent-on-stability watchdog for Reppo public endpoint compatibility."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


sys.dont_write_bytecode = True

REPO_ROOT = Path.cwd()
if not (REPO_ROOT / "src" / "agentic_commerce").is_dir():
    REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agentic_commerce.reppo import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RESPONSE_BYTES,
    ResponseTooLarge,
    Transport,
    UrllibTransport,
    utc_now,
)


def default_state_file() -> Path:
    state_root = Path(
        os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")
    )
    return state_root / "agentic-commerce-toolkit" / "reppo-watchdog.json"


def size_band(response_bytes: int) -> str:
    ratio = response_bytes / DEFAULT_MAX_RESPONSE_BYTES
    if ratio >= 0.9:
        return "90-100%"
    if ratio >= 0.75:
        return "75-89%"
    if ratio >= 0.5:
        return "50-74%"
    return "under-50%"


def validate_settings(base_url: str, timeout: float, state_file: Path) -> None:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise ValueError("base URL is invalid") from error
    valid = (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and bool(hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and not any(character.isspace() for character in parsed.netloc)
        and base_url.rstrip("/") == DEFAULT_BASE_URL
    )
    if not valid:
        raise ValueError("base URL is invalid")
    try:
        state_file.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("state file must be outside the repository")


def probe(
    transport: Transport,
    *,
    name: str,
    url: str,
    timeout: float,
    collection_key: str | None = None,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "name": name,
        "url": url,
        "httpStatus": None,
        "shape": None,
        "responseBytes": None,
        "sizeBand": None,
        "paginationHonored": None,
        "errorCode": None,
    }
    try:
        response = transport.get(url, timeout=timeout)
    except ResponseTooLarge:
        observation["errorCode"] = "RESPONSE_TOO_LARGE"
        observation["sizeBand"] = "over-cap"
        return observation
    except TimeoutError:
        observation["errorCode"] = "TIMEOUT"
        return observation
    except OSError:
        observation["errorCode"] = "NETWORK_ERROR"
        return observation

    observation["httpStatus"] = response.status
    observation["responseBytes"] = len(response.body)
    observation["sizeBand"] = size_band(len(response.body))
    if not 200 <= response.status < 300:
        observation["shape"] = "http-error"
        observation["errorCode"] = "HTTP_ERROR"
        return observation

    try:
        payload = json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        observation["shape"] = "invalid-json"
        observation["errorCode"] = "INVALID_JSON"
        return observation
    if not isinstance(payload, dict):
        observation["shape"] = "invalid-object"
        observation["errorCode"] = "INVALID_SHAPE"
        return observation

    if collection_key is None:
        observation["shape"] = "object"
        return observation

    data = payload.get("data")
    collection = data.get(collection_key) if isinstance(data, dict) else None
    if not isinstance(collection, list):
        observation["shape"] = f"missing-data.{collection_key}"
        observation["errorCode"] = "INVALID_SHAPE"
        return observation
    observation["shape"] = f"data.{collection_key}"
    observation["itemCount"] = len(collection)
    observation["paginationHonored"] = len(collection) <= 1
    return observation


def compatibility_signature(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "httpStatus": observation["httpStatus"],
        "shape": observation["shape"],
        "sizeBand": observation["sizeBand"],
        "paginationHonored": observation["paginationHonored"],
        "errorCode": observation["errorCode"],
    }


def collect(
    *,
    transport: Transport,
    base_url: str,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = base_url.rstrip("/")
    specs = (
        ("stats", f"{base}/stats", None),
        ("datanets", f"{base}/public/subnets?page=1&limit=1&search=", "subnets"),
        ("pods", f"{base}/public/pods?page=1&limit=1&search=", "pods"),
    )
    observations = {
        name: probe(
            transport,
            name=name,
            url=url,
            timeout=timeout,
            collection_key=collection_key,
        )
        for name, url, collection_key in specs
    }
    signature = {
        name: compatibility_signature(observation)
        for name, observation in observations.items()
    }
    return observations, signature


def changed_fields(previous: Any, current: Any, prefix: str = "") -> list[str]:
    if isinstance(previous, dict) and isinstance(current, dict):
        changes: list[str] = []
        for key in sorted(set(previous) | set(current)):
            path = f"{prefix}.{key}" if prefix else key
            changes.extend(changed_fields(previous.get(key), current.get(key), path))
        return changes
    if previous == current:
        return []
    return [f"{prefix}: {previous!r} -> {current!r}"]


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)
        path.chmod(0o600)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def run_watchdog(
    *,
    transport: Transport,
    state_file: Path,
    clock: Callable[[], str] = utc_now,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 15.0,
) -> str:
    validate_settings(base_url, timeout, state_file)
    observations, signature = collect(
        transport=transport,
        base_url=base_url,
        timeout=timeout,
    )
    previous_signature: dict[str, Any] | None = None
    state_corrupt = False
    if state_file.exists():
        try:
            previous = json.loads(state_file.read_text())
            candidate = previous.get("signature") if isinstance(previous, dict) else None
            if isinstance(candidate, dict):
                previous_signature = candidate
            else:
                state_corrupt = True
        except (OSError, json.JSONDecodeError):
            state_corrupt = True

    checked_at = clock()
    write_state(
        state_file,
        {
            "schemaVersion": "1.0",
            "checkedAt": checked_at,
            "signature": signature,
            "observations": observations,
        },
    )
    if previous_signature is None and not state_corrupt:
        return ""

    changes = changed_fields(previous_signature or {}, signature)
    if not changes and not state_corrupt:
        return ""
    lines = ["Reppo public compatibility change detected."]
    if state_corrupt:
        lines.append("- watchdog state was unreadable and has been reset")
    lines.extend(f"- {change}" for change in changes)
    lines.append(f"- checkedAt: {checked_at}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", type=Path, default=default_state_file())
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    try:
        message = run_watchdog(
            transport=UrllibTransport(),
            state_file=args.state_file,
            timeout=args.timeout,
        )
    except ValueError:
        print("Reppo watchdog configuration is invalid", file=sys.stderr)
        return 2
    if message:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
