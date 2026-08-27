"""CLI for Amiga RDB (Rigid Disk Block) operations via amitools rdbtool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .rdb import (
    DOS_TYPES,
    PFS3AIO_DOS_TYPE,
    add_partition,
    change_partition,
    create,
    delete_partition,
    fsadd,
    fsremove,
    info,
    show,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amiga-rdb",
        description="Inspect and manage Amiga Rigid Disk Block (RDB) structures on block devices or images.",
    )
    parser.add_argument(
        "device",
        type=str,
        help="block device or disk image (e.g. /dev/loop0, /dev/sdc2, disk.hdf)",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # -- info
    sub.add_parser(
        "info",
        help="show full RDB information (geometry, partitions, filesystems)",
    )

    # -- show
    sub.add_parser(
        "show",
        help="show partition and filesystem table",
    )

    # -- create
    create_p = sub.add_parser(
        "create",
        help="create a new RDB on the device (destructive)",
    )
    create_p.add_argument(
        "--size",
        metavar="SIZE",
        help="image size for new files, e.g. 2g, 512m (rdbtool size= syntax)",
    )
    create_p.add_argument("--cylinders", type=int, help="number of cylinders")
    create_p.add_argument("--heads", type=int, help="number of heads")
    create_p.add_argument("--sectors", type=int, help="sectors per track")

    # -- add-partition
    add_p = sub.add_parser(
        "add-partition",
        help="add a partition to an existing RDB",
    )
    add_p.add_argument("name", help="Amiga partition name (e.g. SDH0)")
    size_group = add_p.add_mutually_exclusive_group(required=True)
    size_group.add_argument("--size", type=int, metavar="MB", help="partition size in MiB")
    size_group.add_argument("--lo-cyl", type=int, help="first cylinder (use with --hi-cyl)")
    add_p.add_argument("--hi-cyl", type=int, help="last cylinder (use with --lo-cyl)")
    add_p.add_argument(
        "--dos-type",
        default="FFS",
        metavar="TYPE",
        help=(
            "DOS type as a built-in name or hex (e.g. PFS3, 0x50465303). "
            f"Built-ins: {', '.join(sorted(DOS_TYPES))}"
        ),
    )
    add_p.add_argument("--bootable", action="store_true", help="set bootable flag")
    add_p.add_argument("--boot-pri", type=int, default=0, help="boot priority (default: 0)")
    add_p.add_argument("--flags", type=lambda x: int(x, 0), default=0, help="raw partition flags")

    # -- delete-partition
    del_p = sub.add_parser(
        "delete-partition",
        help="delete a named partition from the RDB",
    )
    del_p.add_argument("name", help="partition name to delete")

    # -- change-partition
    chg_p = sub.add_parser(
        "change-partition",
        help="change attributes of an existing partition (dos type, name, boot flags) without touching data",
    )
    chg_p.add_argument("name", help="partition name to change (e.g. SDH2)")
    chg_p.add_argument("--new-name", help="rename the partition")
    chg_p.add_argument(
        "--dos-type",
        metavar="TYPE",
        help=(
            "new DOS type as a built-in name or hex. "
            f"Built-ins: {', '.join(sorted(DOS_TYPES))}"
        ),
    )
    chg_p.add_argument("--bootable", action="store_true", default=None, help="set bootable flag")
    chg_p.add_argument("--no-bootable", dest="bootable", action="store_false", help="clear bootable flag")
    chg_p.add_argument("--no-automount", dest="automount", action="store_false", default=None,
                       help="disable automount (hides partition from AmigaOS — workaround for broken delete)")
    chg_p.add_argument("--automount", dest="automount", action="store_true",
                       help="enable automount")
    chg_p.add_argument("--boot-pri", type=int, help="boot priority")
    chg_p.add_argument("--num-buffer", type=int, help="number of DosEnv buffers (e.g. 300)")
    chg_p.add_argument("--mask", type=lambda x: int(x, 0), help="DMA address mask (e.g. 0x7ffffffe)")
    chg_p.add_argument("--max-transfer", type=lambda x: int(x, 0), help="max transfer size (e.g. 0xffffff)")

    # -- fsadd
    fsadd_p = sub.add_parser(
        "fsadd",
        help="embed a filesystem binary into the RDB (e.g. PFS3aio)",
    )
    fsadd_p.add_argument("binary", type=Path, help="filesystem binary file")
    fsadd_p.add_argument(
        "--dos-type",
        default=PFS3AIO_DOS_TYPE,
        metavar="TYPE",
        help=f"DOS type for this filesystem (default: {PFS3AIO_DOS_TYPE} = PFS3aio)",
    )

    # -- fsremove
    fsrem_p = sub.add_parser(
        "fsremove",
        help="remove an embedded filesystem from the RDB by DOS type",
    )
    fsrem_p.add_argument(
        "--dos-type",
        required=True,
        metavar="TYPE",
        help="DOS type to remove (hex or built-in name)",
    )

    return parser


def resolve_dos_type(raw: str) -> str:
    """Accept a built-in name (e.g. PFS3) or a raw hex string (e.g. 0x50465303)."""
    upper = raw.upper()
    if upper in DOS_TYPES:
        return DOS_TYPES[upper]
    # validate it looks like a hex value
    try:
        int(raw, 16) if raw.startswith("0x") or raw.startswith("0X") else int(raw, 16)
    except ValueError:
        raise SystemExit(
            f"Unknown DOS type '{raw}'. Use a built-in name or a 0xRRGGBBAA hex value.\n"
            f"Built-ins: {', '.join(sorted(DOS_TYPES))}"
        )
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "info":
            print(info(args.device), end="")

        elif args.command == "show":
            print(show(args.device), end="")

        elif args.command == "create":
            create(
                args.device,
                size=args.size,
                cylinders=args.cylinders,
                heads=args.heads,
                sectors=args.sectors,
            )
            print(f"RDB created on {args.device}")

        elif args.command == "add-partition":
            dos_type = resolve_dos_type(args.dos_type)
            add_partition(
                args.device,
                args.name,
                lo_cyl=args.lo_cyl,
                hi_cyl=args.hi_cyl,
                dos_type=dos_type,
                flags=args.flags,
                boot_pri=args.boot_pri,
                bootable=args.bootable,
                size_mb=args.size,
            )
            print(f"Partition {args.name!r} added to {args.device}")

        elif args.command == "delete-partition":
            delete_partition(args.device, args.name)
            print(f"Partition {args.name!r} deleted from {args.device}")

        elif args.command == "change-partition":
            dos_type = resolve_dos_type(args.dos_type) if args.dos_type else None
            dosenv = {}
            if args.num_buffer is not None:
                dosenv["num_buffer"] = args.num_buffer
            if args.mask is not None:
                dosenv["mask"] = args.mask
            if args.max_transfer is not None:
                dosenv["max_transfer"] = args.max_transfer
            change_partition(
                args.device,
                args.name,
                new_name=args.new_name,
                dos_type=dos_type,
                bootable=args.bootable,
                automount=args.automount,
                boot_pri=args.boot_pri,
                **dosenv,
            )
            print(f"Partition {args.name!r} updated on {args.device}")

        elif args.command == "fsadd":
            if not args.binary.exists():
                print(f"error: filesystem binary not found: {args.binary}", file=sys.stderr)
                return 1
            dos_type = resolve_dos_type(args.dos_type)
            fsadd(args.device, args.binary, dos_type)
            print(f"Filesystem {dos_type} embedded into {args.device} from {args.binary}")

        elif args.command == "fsremove":
            dos_type = resolve_dos_type(args.dos_type)
            fsremove(args.device, dos_type)
            print(f"Filesystem {dos_type} removed from {args.device}")

    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
