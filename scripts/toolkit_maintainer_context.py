#!/usr/bin/env python3
"""Collect bounded, read-only maintenance context for the public toolkit."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PUBLIC_REPOSITORY = "nccrypto/agentic-commerce-toolkit"
PUBLIC_REMOTES = {
    "https://github.com/nccrypto/agentic-commerce-toolkit",
    "https://github.com/nccrypto/agentic-commerce-toolkit.git",
    "git@github.com:nccrypto/agentic-commerce-toolkit.git",
}
MAX_OUTPUT_CHARS = 12_000
SAFE_ENVIRONMENT_KEYS = {
    "GH_CONFIG_DIR",
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "SSL_CERT_FILE",
    "TERM",
    "TMPDIR",
    "XDG_CONFIG_HOME",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "exitCode": None, "stdout": "command unavailable"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "exitCode": None, "stdout": "command timed out"}
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[-MAX_OUTPUT_CHARS:]
    return {
        "ok": completed.returncode == 0,
        "exitCode": completed.returncode,
        "stdout": output,
    }


def safe_environment(*, repo: Path, python: bool = False) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in SAFE_ENVIRONMENT_KEYS
    }
    if python:
        environment["HOME"] = "/nonexistent"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = str(repo / "src")
    return environment


def validate_public_repository(
    *,
    repo: Path,
    runner: Callable[..., dict[str, Any]],
    environment: dict[str, str],
) -> None:
    required = (
        repo / "PUBLIC_BOUNDARY.md",
        repo / "pyproject.toml",
        repo / "scripts" / "check_public_boundary.py",
    )
    if not all(path.is_file() for path in required):
        raise ValueError("repository identity check failed")
    identity = runner(
        ["git", "remote", "get-url", "origin"],
        cwd=repo,
        timeout=30,
        env=environment,
    )
    if not identity.get("ok") or identity.get("stdout", "").strip() not in PUBLIC_REMOTES:
        raise ValueError("repository identity check failed")


def collect_context(
    *,
    repo: Path,
    runner: Callable[..., dict[str, Any]] = run_command,
    clock: Callable[[], str] = utc_now,
) -> dict[str, Any]:
    repo = repo.resolve()
    public_environment = safe_environment(repo=repo)
    github_environment = public_environment.copy()
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if value := os.environ.get(key):
            github_environment[key] = value
    boundary_environment = safe_environment(repo=repo, python=True)
    validate_public_repository(
        repo=repo,
        runner=runner,
        environment=public_environment,
    )
    with tempfile.TemporaryDirectory(prefix="agentic-commerce-review-") as directory:
        snapshot = Path(directory) / "repository"
        shutil.copytree(
            repo,
            snapshot,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                "*.pyc",
                "*.egg-info",
                ".env",
                ".env.*",
                "reports",
                "logs",
            ),
        )
        python_environment = safe_environment(repo=snapshot, python=True)
        commands: tuple[
            tuple[str, list[str], int, dict[str, str], Path], ...
        ] = (
            (
                "gitStatus",
                ["git", "status", "--short", "--branch"],
                30,
                public_environment,
                repo,
            ),
            (
                "tests",
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-v",
                ],
                180,
                python_environment,
                snapshot,
            ),
            (
                "publicBoundary",
                [sys.executable, "-B", "scripts/check_public_boundary.py", "."],
                60,
                boundary_environment,
                repo,
            ),
            (
                "githubRepository",
                [
                    "gh",
                    "repo",
                    "view",
                    PUBLIC_REPOSITORY,
                    "--json",
                    "nameWithOwner,visibility,defaultBranchRef,issues,updatedAt,url",
                ],
                60,
                github_environment,
                repo,
            ),
            (
                "githubRuns",
                [
                    "gh",
                    "run",
                    "list",
                    "--repo",
                    PUBLIC_REPOSITORY,
                    "--limit",
                    "5",
                    "--json",
                    "status,conclusion,workflowName,headSha,createdAt,url",
                ],
                60,
                github_environment,
                repo,
            ),
            (
                "githubIssues",
                [
                    "gh",
                    "issue",
                    "list",
                    "--repo",
                    PUBLIC_REPOSITORY,
                    "--limit",
                    "20",
                    "--json",
                    "number,title,state,labels,updatedAt,url",
                ],
                60,
                github_environment,
                repo,
            ),
        )
        checks = {
            name: runner(command, cwd=cwd, timeout=timeout, env=env)
            for name, command, timeout, env, cwd in commands
        }
    return {
        "schemaVersion": "1.0",
        "collectedAt": clock(),
        "repository": PUBLIC_REPOSITORY,
        "mode": "read-only",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        context = collect_context(repo=args.repo.resolve())
    except ValueError:
        print("Toolkit repository identity validation failed", file=sys.stderr)
        return 2
    print(json.dumps(context, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
