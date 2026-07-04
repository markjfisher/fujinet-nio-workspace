from __future__ import annotations

import argparse
import sys

from . import altirra as altirra_cmds
from . import atari800 as atari800_cmds


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="atari-run",
        description="Launch Atari emulators from neutral fujinet-nio profiles.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    altirra_cmds.register_subcommands(sub)
    atari800_cmds.register_subcommands(sub)

    args = parser.parse_args()
    try:
        raise SystemExit(args.fn(args))
    except (OSError, ValueError) as exc:
        print(f"atari-run: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
