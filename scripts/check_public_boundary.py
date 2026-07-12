#!/usr/bin/env python3
"""Conservative public-boundary scanner for repository files."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", ".idea", ".venv", ".vscode", "venv", "node_modules",
    "__pycache__", ".pytest_cache",
}
FORBIDDEN_FILENAMES = {
    ".env", "auth.json", "cookies.sqlite", "session.db", "sessions.db",
    "id_rsa", "id_ed25519", "seed.txt", "wallet.json",
}
FORBIDDEN_PATH_PARTS = {"reports", "logs"}
ALLOWED_HIDDEN_DIRS = {".github"}
TEXT_SUFFIXES = {
    "", ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".csv", ".xml",
}
PATTERNS = {
    "private local path": re.compile(r"(?:/Users|/home)/[^/\s]+/"),
    "named non-public system reference": re.compile(
        r"\b(?:private|non-public)\s+"
        r"[a-z0-9][a-z0-9_-]*"
        r"(?:\s+[a-z0-9][a-z0-9_-]*){0,2}\s+"
        r"(?:repository|repo|monorepo|runtime|system|fleet)\b",
        re.IGNORECASE,
    ),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "probable EVM private key assignment": re.compile(
        r"(?:PRIVATE_KEY|SECRET_KEY)\s*[:=]\s*[\"']?0x[a-fA-F0-9]{64}\b"
    ),
    "probable bearer token": re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{20,}"),
}
ALLOWLIST_FILES = {"scripts/check_public_boundary.py", "tests/test_public_boundary.py"}


def configured_private_patterns() -> tuple[re.Pattern[str], ...]:
    terms = os.environ.get("PUBLIC_BOUNDARY_PRIVATE_TERMS", "")
    return tuple(
        re.compile(re.escape(term.strip()), re.IGNORECASE)
        for term in terms.split(",")
        if term.strip()
    )


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    private_patterns = configured_private_patterns()
    for path in iter_files(root):
        rel = path.relative_to(root)
        if path.name in FORBIDDEN_FILENAMES or path.name.startswith(".env."):
            if path.name != ".env.example":
                findings.append(f"{rel}: forbidden filename")
        directory_parts = rel.parts[:-1]
        if any(part in FORBIDDEN_PATH_PARTS for part in directory_parts) or any(
            part.startswith(".") and part not in ALLOWED_HIDDEN_DIRS
            for part in directory_parts
        ):
            findings.append(f"{rel}: forbidden hidden or private directory")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{rel}: non-text file requires manual review")
            continue
        if rel.as_posix() not in ALLOWLIST_FILES:
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append(f"{rel}:{line}: {label}")
        for pattern in private_patterns:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line}: configured private identifier")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings = scan(root)
    if findings:
        print("Public-boundary check FAILED:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Public-boundary check passed: {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
