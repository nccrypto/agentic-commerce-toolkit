"""Command-line interface for public agentic-commerce inspection."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Sequence, TextIO

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
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    transport: Transport | None = None,
    clock: Callable[[], str] = utc_now,
) -> int:
    args = build_parser().parse_args(argv)
    output = stdout or sys.stdout
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
    dump_options: dict[str, Any] = {"sort_keys": True}
    if args.pretty:
        dump_options["indent"] = 2
    else:
        dump_options["separators"] = (",", ":")
    print(json.dumps(result.envelope, **dump_options), file=output)
    return result.exit_code
