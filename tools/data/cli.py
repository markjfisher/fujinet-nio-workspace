from __future__ import annotations

import argparse
import sys

from . import compress as compress_cmds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="data",
        description="Workspace data tooling (compression, conversion, and related utilities).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    compress_cmds.register_subcommands(sub)

    args = parser.parse_args(argv)
    try:
        return int(args.fn(args))
    except (OSError, ValueError) as exc:
        print(f"data: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
