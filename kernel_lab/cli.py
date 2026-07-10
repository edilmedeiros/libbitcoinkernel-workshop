"""Command line interface for the workshop solution."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from . import chainstate
from . import pbk_compat as compat
from . import tutorial
from .objects import describe_block, describe_transaction, load_block, load_transaction
from .script import verify_prevout_fixture


def print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


def cmd_parse_block(args: argparse.Namespace) -> int:
    # TODO: (#2) load the file data/blocks-main/102-fund-alice.hex
    # and create a Block object. Print the blockhash.
    loaded = load_block(args.path)
    print_lines(describe_block(loaded))
    return 0


def cmd_parse_tx(args: argparse.Namespace) -> int:
    # TODO: (#1) load the file data/tx/103-alice-pays-bob.hex
    loaded = load_transaction(args.path)
    print_lines(describe_transaction(loaded))
    return 0


def cmd_check_block(args: argparse.Namespace) -> int:
    try:
        loaded = load_block(args.path)
    except Exception as exc:  # noqa: BLE001 - CLI should explain parse failure.
        print(f"source: {args.path}")
        print("parse_ok: false")
        print(f"error: {type(exc).__name__}: {exc}")
        return 1

    print(f"source: {args.path}")
    print("parse_ok: true")
    print(f"hash: {compat.block_hash(loaded.obj)}")
    ok, detail = compat.check_block(loaded.obj)
    print(f"context_free_valid: {str(ok).lower()}")
    print(f"detail: {detail}")
    return 0 if ok else 2


def cmd_verify_script(args: argparse.Namespace) -> int:
    ok, lines = verify_prevout_fixture(args.path)
    print_lines(lines)
    return 0 if ok else 2


def cmd_replay_main(args: argparse.Namespace) -> int:
    result = chainstate.run_replay_main(args.kernel_datadir, reset=not args.no_reset)
    print_lines(chainstate.scenario_lines(result))
    return 0


def cmd_missing_prev(args: argparse.Namespace) -> int:
    result = chainstate.run_missing_prev(args.kernel_datadir, reset=not args.no_reset)
    print_lines(chainstate.scenario_lines(result))
    return 0


def cmd_reorg(args: argparse.Namespace) -> int:
    result = chainstate.run_reorg(args.kernel_datadir, reset=not args.no_reset)
    print_lines(chainstate.scenario_lines(result))
    return 0


def cmd_walkthrough(args: argparse.Namespace) -> int:
    sections: list[tuple[str, Callable[[], int]]] = [
        ("parse block", lambda: cmd_parse_block(argparse.Namespace(path=Path("data/blocks-main/102-fund-alice.hex")))),
        ("parse transaction", lambda: cmd_parse_tx(argparse.Namespace(path=Path("data/tx/103-alice-pays-bob.hex")))),
        ("check valid block", lambda: cmd_check_block(argparse.Namespace(path=Path("data/blocks-main/102-fund-alice.hex")))),
        ("check bad merkle block", lambda: cmd_check_block(argparse.Namespace(path=Path("data/blocks-invalid/102-bad-merkle.hex")))),
        ("verify correct script context", lambda: cmd_verify_script(argparse.Namespace(path=Path("data/prevouts/103-input0-correct.json")))),
        ("verify wrong amount", lambda: cmd_verify_script(argparse.Namespace(path=Path("data/prevouts/103-input0-wrong-amount.json")))),
        ("verify wrong script", lambda: cmd_verify_script(argparse.Namespace(path=Path("data/prevouts/103-input0-wrong-script.json")))),
        ("replay main", lambda: cmd_replay_main(args)),
        ("missing previous context", lambda: cmd_missing_prev(args)),
        ("reorg", lambda: cmd_reorg(args)),
    ]
    worst = 0
    for title, fn in sections:
        print(f"== {title} ==")
        code = fn()
        worst = max(worst, code)
    return 0 if worst in {0, 2} else worst


def cmd_tutorial(args: argparse.Namespace) -> int:
    if args.action not in {"show", "overview", "next", "previous"}:
        print(
            "kernel-lab tutorial: action must be one of overview, next, previous",
            file=sys.stderr,
        )
        return 2
    return tutorial.run_tutorial(args.action, plain=args.plain)


# Define command line commands
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kernel-lab",
        description=(
            "A libbitcoinkernel tutorial tool for exploring Bitcoin validation "
            "without building a node."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "tutorial",
        help="Show the current instructional lesson without running commands.",
    )
    p.add_argument(
        "action",
        nargs="?",
        default="show",
        metavar="{overview,next,previous}",
    )
    p.add_argument(
        "--plain",
        action="store_true",
        help="Print tutorial text without colors or panels.",
    )
    p.set_defaults(func=cmd_tutorial)

    ## 1. Parsing and object inspection
    p = sub.add_parser("parse-block")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_parse_block)

    p = sub.add_parser("parse-tx")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_parse_tx)

    p = sub.add_parser("check-block")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_check_block)

    p = sub.add_parser("verify-script")
    p.add_argument("path", type=Path)
    p.set_defaults(func=cmd_verify_script)

    for name, func in [
        ("replay-main", cmd_replay_main),
        ("missing-prev", cmd_missing_prev),
        ("reorg", cmd_reorg),
        ("walkthrough", cmd_walkthrough),
    ]:
        p = sub.add_parser(name)
        p.add_argument("--kernel-datadir", type=Path, required=True)
        p.add_argument("--no-reset", action="store_true")
        p.set_defaults(func=func)

    return parser


# Main logic: process command line and finish
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except compat.KernelApiError as exc:
        print(f"kernel api error: {exc}", file=sys.stderr)
        return 3


# Entry point
if __name__ == "__main__":
    raise SystemExit(main())
