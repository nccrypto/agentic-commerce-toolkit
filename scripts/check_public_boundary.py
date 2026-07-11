#!/usr/bin/env python3
"""Conservative public-boundary scanner for repository files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
FORBIDDEN_FILENAMES = {
    ".env", "auth.json", "cookies.sqlite", "session.db", "sessions.db",
    "id_rsa", "id_ed25519", "seed.txt", "wallet.json",
}
FORBIDDEN_PATH_PARTS = {".hermes", "reports", "logs"}
TEXT_SUFFIXES = {
    "", ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".csv", ".xml",
}
PATTERNS = {
    "private local path": re.compile(r"/Users/[^/\s]+/(?:Documents|\.hermes)/"),
    "private project reference": re.compile(
        r"(?:hermes-agents|reppo-helper|cnc_strategy_supervisor|cnc_content_agent)",
        re.IGNORECASE,
    ),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "probable EVM private key assignment": re.compile(
        r"(?:PRIVATE_KEY|SECRET_KEY)\s*[:=]\s*[\"']?0x[a-fA-F0-9]{64}\b"
    ),
    "probable bearer token": re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{20,}"),
}
ALLOWLIST_FILES = {"README.md", "DESIGN.md", "PUBLIC_BOUNDARY.md", "scripts/check_public_boundary.py", "tests/test_public_boundary.py"}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in iter_files(root):
        rel = path.relative_to(root)
        if path.name in FORBIDDEN_FILENAMES or path.name.startswith(".env."):
            if path.name != ".env.example":
                findings.append(f"{rel}: forbidden filename")
        if any(part in FORBIDDEN_PATH_PARTS for part in rel.parts[:-1]):
            findings.append(f"{rel}: forbidden generated/private directory")
        if path.suffix.lower() not in TEXT_SUFFIXES or rel.as_posix() in ALLOWLIST_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{rel}: non-text file requires manual review")
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line}: {label}")
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
