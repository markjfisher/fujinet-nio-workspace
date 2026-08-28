"""Single entry point for Amiga tooling.

Top-level subcommand groups:

  amiga rdb   <device> <subcommand>  -- RDB partition management (rdbtool)
  amiga adf   <subcommand>           -- ADF floppy image operations (xdftool)
  amiga ipc   [options] <command>    -- Amiberry Unix IPC socket client
  amiga type  [options] <text>       -- Send keystrokes to Amiberry guest

Invoke via scripts/amiga, which activates the project-managed venv.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# RDB subcommands
# ---------------------------------------------------------------------------

def _build_rdb_parser(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    from .rdb import DOS_TYPES, PFS3AIO_DOS_TYPE

    rdb = sub.add_parser("rdb", help="RDB partition management (rdbtool)")
    rdb.add_argument("device", help="block device or disk image (e.g. /dev/loop0, disk.hdf)")
    rsub = rdb.add_subparsers(dest="rdb_command", metavar="SUBCOMMAND")
    rsub.required = True

    rsub.add_parser("info", help="show full RDB information")
    rsub.add_parser("show", help="show partition and filesystem table")

    cp = rsub.add_parser("create", help="create a new RDB (destructive)")
    cp.add_argument("--size", metavar="SIZE", help="image size for new files, e.g. 2g, 512m")
    cp.add_argument("--cylinders", type=int)
    cp.add_argument("--heads", type=int)
    cp.add_argument("--sectors", type=int)

    ap = rsub.add_parser("add-partition", help="add a partition to an existing RDB")
    ap.add_argument("name", help="Amiga partition name (e.g. SDH0)")
    sg = ap.add_mutually_exclusive_group(required=True)
    sg.add_argument("--size", type=int, metavar="MB", help="partition size in MiB")
    sg.add_argument("--lo-cyl", type=int, help="first cylinder (use with --hi-cyl)")
    ap.add_argument("--hi-cyl", type=int)
    ap.add_argument("--dos-type", default="FFS", metavar="TYPE",
                    help=f"DOS type name or hex. Built-ins: {', '.join(sorted(DOS_TYPES))}")
    ap.add_argument("--bootable", action="store_true")
    ap.add_argument("--boot-pri", type=int, default=0)
    ap.add_argument("--flags", type=lambda x: int(x, 0), default=0)

    chg = rsub.add_parser("change-partition",
                           help="change partition metadata without touching data")
    chg.add_argument("name", help="partition name (e.g. SDH2)")
    chg.add_argument("--new-name")
    chg.add_argument("--dos-type", metavar="TYPE")
    chg.add_argument("--bootable", action="store_true", default=None)
    chg.add_argument("--no-bootable", dest="bootable", action="store_false")
    chg.add_argument("--no-automount", dest="automount", action="store_false", default=None)
    chg.add_argument("--automount", dest="automount", action="store_true")
    chg.add_argument("--boot-pri", type=int)
    chg.add_argument("--num-buffer", type=int, help="DosEnv buffer count (e.g. 300)")
    chg.add_argument("--mask", type=lambda x: int(x, 0),
                     help="DMA address mask (e.g. 0x7ffffffe)")
    chg.add_argument("--max-transfer", type=lambda x: int(x, 0),
                     help="max transfer size (e.g. 0xffffff)")

    dp = rsub.add_parser("delete-partition", help="delete a named partition")
    dp.add_argument("name")

    fa = rsub.add_parser("fsadd", help="embed a filesystem binary into the RDB")
    fa.add_argument("binary", type=Path)
    fa.add_argument("--dos-type", default=PFS3AIO_DOS_TYPE, metavar="TYPE",
                    help=f"default: {PFS3AIO_DOS_TYPE} (PFS3aio)")

    fr = rsub.add_parser("fsremove", help="remove an embedded filesystem by DOS type")
    fr.add_argument("--dos-type", required=True, metavar="TYPE")


def _run_rdb(args: argparse.Namespace) -> int:
    from .rdb import (
        DOS_TYPES, add_partition, change_partition, create,
        delete_partition, fsadd, fsremove, info, show,
    )

    def resolve(raw: str) -> str:
        upper = raw.upper()
        if upper in DOS_TYPES:
            return DOS_TYPES[upper]
        try:
            int(raw, 16)
        except ValueError:
            raise SystemExit(
                f"Unknown DOS type '{raw}'. Built-ins: {', '.join(sorted(DOS_TYPES))}"
            )
        return raw

    dev = args.device
    cmd = args.rdb_command

    if cmd == "info":
        print(info(dev), end="")
    elif cmd == "show":
        print(show(dev), end="")
    elif cmd == "create":
        create(dev, size=args.size, cylinders=args.cylinders,
               heads=args.heads, sectors=args.sectors)
        print(f"RDB created on {dev}")
    elif cmd == "add-partition":
        dos_type = resolve(args.dos_type)
        add_partition(dev, args.name, lo_cyl=args.lo_cyl, hi_cyl=args.hi_cyl,
                      dos_type=dos_type, flags=args.flags, boot_pri=args.boot_pri,
                      bootable=args.bootable, size_mb=args.size)
        print(f"Partition {args.name!r} added to {dev}")
    elif cmd == "change-partition":
        dos_type = resolve(args.dos_type) if args.dos_type else None
        dosenv = {}
        if args.num_buffer is not None:
            dosenv["num_buffer"] = args.num_buffer
        if args.mask is not None:
            dosenv["mask"] = args.mask
        if args.max_transfer is not None:
            dosenv["max_transfer"] = args.max_transfer
        change_partition(dev, args.name, new_name=args.new_name, dos_type=dos_type,
                         bootable=args.bootable, automount=args.automount,
                         boot_pri=args.boot_pri, **dosenv)
        print(f"Partition {args.name!r} updated on {dev}")
    elif cmd == "delete-partition":
        delete_partition(dev, args.name)
        print(f"Partition {args.name!r} deleted from {dev}")
    elif cmd == "fsadd":
        if not args.binary.exists():
            print(f"error: filesystem binary not found: {args.binary}", file=sys.stderr)
            return 1
        dos_type = resolve(args.dos_type)
        fsadd(dev, args.binary, dos_type)
        print(f"Filesystem {dos_type} embedded into {dev}")
    elif cmd == "fsremove":
        dos_type = resolve(args.dos_type)
        fsremove(dev, dos_type)
        print(f"Filesystem {dos_type} removed from {dev}")
    return 0


# ---------------------------------------------------------------------------
# ADF subcommands
# ---------------------------------------------------------------------------

def _build_adf_parser(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    from .adf import ADF_DD_SIZE, ADF_HD_SIZE, ADF_VALID_SIZES, FS_TYPES

    adf = sub.add_parser("adf", help="ADF floppy image operations (xdftool)")
    asub = adf.add_subparsers(dest="adf_command", metavar="SUBCOMMAND")
    asub.required = True

    cr = asub.add_parser("create", help="create an ADF from a directory or blank")
    cr.add_argument("output", type=Path, help="output .adf file")
    cr.add_argument("--from-dir", type=Path, metavar="DIR",
                    help="pack this host directory into the ADF")
    cr.add_argument("--label", default="Workbench",
                    help="Amiga volume label (default: Workbench)")
    cr.add_argument("--fs", default="ffs", choices=FS_TYPES,
                    help="filesystem type (default: ffs)")
    cr.add_argument("--size", default=ADF_DD_SIZE, choices=ADF_VALID_SIZES,
                    help=f"floppy size: {ADF_DD_SIZE} = DD (default, auto-promotes to HD "
                         f"if needed), {ADF_HD_SIZE} = HD. ADF is a physical floppy "
                         f"format — for larger content use HDF.")

    ls = asub.add_parser("list", help="list files in an ADF")
    ls.add_argument("adf", type=Path)

    rd = asub.add_parser("read", help="extract a file from an ADF")
    rd.add_argument("adf", type=Path)
    rd.add_argument("src", help="Amiga path inside the ADF (e.g. C/Dir)")
    rd.add_argument("dest", type=Path, help="host destination path")

    wr = asub.add_parser("write", help="write a host file into an ADF")
    wr.add_argument("adf", type=Path)
    wr.add_argument("src", type=Path, help="host source file")
    wr.add_argument("dest", help="Amiga destination path (e.g. C/MyProg)")


def _run_adf(args: argparse.Namespace) -> int:
    from .adf import create_blank, create_from_dir, list_files, read_file, write_file

    cmd = args.adf_command

    if cmd == "create":
        if args.from_dir:
            if not args.from_dir.is_dir():
                print(f"error: not a directory: {args.from_dir}", file=sys.stderr)
                return 1
            create_from_dir(args.output, args.from_dir,
                            label=args.label, fs=args.fs, size=args.size)
            print(f"ADF created from {args.from_dir}: {args.output}")
        else:
            create_blank(args.output, label=args.label, fs=args.fs, size=args.size)
            print(f"Blank ADF created: {args.output}")
    elif cmd == "list":
        print(list_files(args.adf), end="")
    elif cmd == "read":
        read_file(args.adf, args.src, args.dest)
        print(f"Extracted {args.src} -> {args.dest}")
    elif cmd == "write":
        if not args.src.is_file():
            print(f"error: source not found: {args.src}", file=sys.stderr)
            return 1
        write_file(args.adf, args.src, args.dest)
        print(f"Wrote {args.src} -> {args.dest} in {args.adf}")
    return 0


# ---------------------------------------------------------------------------
# IPC / type passthrough subcommands
# ---------------------------------------------------------------------------

def _build_ipc_parser(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    ipc = sub.add_parser("ipc", help="Amiberry Unix IPC socket client")
    ipc.add_argument("--socket", dest="socket_path",
                     help="Amiberry IPC socket path")
    ipc.add_argument("--timeout", type=float, default=2.0)
    ipc.add_argument("command", help="IPC command, e.g. GET_STATUS")
    ipc.add_argument("argument", nargs="*")


def _build_type_parser(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    typ = sub.add_parser("type", help="send keystrokes to the Amiberry guest")
    typ.add_argument("--socket", dest="socket_path",
                     help="Amiberry IPC socket path")
    typ.add_argument("--delay", type=float, default=0.03,
                     help="per-keystroke delay in seconds (default: 0.03)")
    typ.add_argument("--screenshot", metavar="PATH",
                     help="save a screenshot after typing")
    typ.add_argument("--settle", type=float, default=1.0,
                     help="wait this many seconds before the screenshot")
    typ.add_argument("text", help="text to type, with {token} specials")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amiga",
        description="Amiga tooling: RDB management, ADF images, Amiberry IPC and keyboard.",
    )
    sub = parser.add_subparsers(dest="group", metavar="GROUP")
    sub.required = True
    _build_rdb_parser(sub)
    _build_adf_parser(sub)
    _build_ipc_parser(sub)
    _build_type_parser(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.group == "rdb":
            return _run_rdb(args)
        elif args.group == "adf":
            return _run_adf(args)
        elif args.group == "ipc":
            from .ipc import main as ipc_main
            # Reconstruct argv for the ipc module's own parser
            ipc_argv = []
            if args.socket_path:
                ipc_argv += ["--socket", args.socket_path]
            ipc_argv += ["--timeout", str(args.timeout)]
            ipc_argv += [args.command] + list(args.argument)
            return ipc_main(ipc_argv)
        elif args.group == "type":
            from .keyboard import main as keyboard_main
            type_argv = []
            if args.socket_path:
                type_argv += ["--socket", args.socket_path]
            type_argv += ["--delay", str(args.delay)]
            if args.screenshot:
                type_argv += ["--screenshot", args.screenshot]
            type_argv += ["--settle", str(args.settle)]
            type_argv += [args.text]
            return keyboard_main(type_argv)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
