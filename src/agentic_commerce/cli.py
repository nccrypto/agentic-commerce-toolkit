"""Command-line interface for public agentic-commerce inspection."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

from .acp_evidence import receipt_exit_code, run_local_evidence_job
from .reppo import DEFAULT_BASE_URL, Inspector, Transport, UrllibTransport, utc_now


def _common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=10.0, metavar="SEC")
    parser.add_argument("--pretty", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-commerce")
    ecosystems = parser.add_subparsers(dest="ecosystem", required=True)
    reppo = ecosystems.add_parser("reppo", help="inspect Reppo public endpoints")
    commands = reppo.add_subparsers(dest="reppo_command", required=True)

    status = commands.add_parser("status", help="probe all public endpoints")
    _common_options(status)

    datanets = commands.add_parser("datanets", help="list public datanets")
    datanets.add_argument("--page", type=int, default=1)
    datanets.add_argument("--limit", type=int, default=20)
    datanets.add_argument("--search", default="")
    _common_options(datanets)

    pods = commands.add_parser("pods", help="list public pods")
    pods.add_argument("--page", type=int, default=1)
    pods.add_argument("--limit", type=int, default=20)
    pods.add_argument("--search", default="")
    pods.add_argument("--datanet")
    pods.add_argument("--epoch", type=int)
    _common_options(pods)

    snapshot = commands.add_parser("snapshot", help="aggregate public ecosystem data")
    snapshot.add_argument("--limit", type=int, default=20)
    _common_options(snapshot)

    virtuals = ecosystems.add_parser(
        "virtuals-acp", help="run bounded Virtuals ACP reference flows"
    )
    virtuals_commands = virtuals.add_subparsers(
        dest="virtuals_command", required=True
    )
    evidence = virtuals_commands.add_parser(
        "verify-evidence", help="verify a public evidence bundle in local mode"
    )
    evidence.add_argument("--request", required=True, metavar="FILE")
    evidence.add_argument("--timeout-ms", type=int, default=5000)
    evidence.add_argument("--max-attempts", type=int, default=3)
    evidence.add_argument("--pretty", action="store_true")
    return parser


def _print_json(value: Any, *, pretty: bool, output: TextIO) -> None:
    dump_options: dict[str, Any] = {"sort_keys": True}
    if pretty:
        dump_options["indent"] = 2
    else:
        dump_options["separators"] = (",", ":")
    print(json.dumps(value, **dump_options), file=output)


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    transport: Transport | None = None,
    clock: Callable[[], str] = utc_now,
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    args = build_parser().parse_args(argv)
    output = stdout or sys.stdout
    if args.ecosystem == "virtuals-acp":
        try:
            request_path = Path(args.request)
            if request_path.stat().st_size > 1_000_000:
                raise ValueError("oversized input")
            request = json.loads(request_path.read_text(encoding="utf-8"))
            receipt = run_local_evidence_job(
                request,
                timeout_ms=args.timeout_ms,
                max_attempts=args.max_attempts,
                clock=clock,
                monotonic=monotonic,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            _print_json(
                {
                    "error": {
                        "code": "INPUT_ERROR",
                        "message": "Unable to read a bounded local evidence request.",
                    }
                },
                pretty=args.pretty,
                output=output,
            )
            return 1
        _print_json(receipt, pretty=args.pretty, output=output)
        return receipt_exit_code(receipt)

    inspector = Inspector(
        base_url=args.base_url,
        timeout=args.timeout,
        transport=transport or UrllibTransport(),
        clock=clock,
    )
    if args.reppo_command == "status":
        result = inspector.status()
    elif args.reppo_command == "datanets":
        result = inspector.datanets(page=args.page, limit=args.limit, search=args.search)
    elif args.reppo_command == "pods":
        result = inspector.pods(
            page=args.page,
            limit=args.limit,
            search=args.search,
            datanet=args.datanet,
            epoch=args.epoch,
        )
    else:
        result = inspector.snapshot(limit=args.limit)
    _print_json(result.envelope, pretty=args.pretty, output=output)
    return result.exit_code
