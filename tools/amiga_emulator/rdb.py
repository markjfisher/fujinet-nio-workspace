"""Wrappers for amitools rdbtool — Amiga Rigid Disk Block operations."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


# Known PFS3 All-In-One DOS type
PFS3AIO_DOS_TYPE = "0x50465303"

# Common Amiga DOS types for reference
DOS_TYPES = {
    "OFS":     "0x444F5300",
    "FFS":     "0x444F5301",
    "OFS-INT": "0x444F5302",
    "FFS-INT": "0x444F5303",
    "OFS-DC":  "0x444F5304",
    "FFS-DC":  "0x444F5305",
    "PFS3":    "0x50465303",
    "SFS":     "0x53465300",
}


def rdbtool() -> list[str]:
    tool = shutil.which("rdbtool")
    if tool:
        return [tool]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "--from", "amitools", "rdbtool"]
    raise SystemExit("rdbtool is required, or install uv/uvx to fetch amitools")


def run_rdb(
    device: str | Path, *commands: str, capture: bool = False, force: bool = False
) -> str:
    """Run rdbtool on device with given commands. Returns stdout if capture=True."""
    base = rdbtool()
    if force:
        base = [*base, "-f"]
    cmd = [*base, str(device), *commands]
    if capture:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    subprocess.run(cmd, check=True)
    return ""


def info(device: str | Path) -> str:
    """Return the full RDB info output for a device."""
    return run_rdb(device, "info", capture=True)


def show(device: str | Path) -> str:
    """Return partition/filesystem table for a device."""
    return run_rdb(device, "show", capture=True)


def create(
    device: str | Path,
    *,
    size: str | None = None,
    cylinders: int | None = None,
    heads: int | None = None,
    sectors: int | None = None,
) -> None:
    """Create a new RDB on the device or image file.

    For new image files pass size (e.g. '2g', '512m').  For an existing file or
    block device the size is derived from the device; -f is passed automatically
    to allow overwriting an existing image.
    """
    create_args: list[str] = ["create"]
    if size is not None:
        create_args += [f"size={size}"]
    if cylinders is not None:
        create_args += ["cyl=%d" % cylinders]
    if heads is not None:
        create_args += ["heads=%d" % heads]
    if sectors is not None:
        create_args += ["secs=%d" % sectors]
    existing = Path(str(device)).exists()
    # rdbtool 'create' only lays out the raw geometry; 'init' writes the RDB header.
    # '+' is rdbtool's command separator — both run in one invocation on the same blkdev.
    run_rdb(device, *create_args, "+", "init", force=existing)


def add_partition(
    device: str | Path,
    name: str,
    *,
    lo_cyl: int | None = None,
    hi_cyl: int | None = None,
    dos_type: str = DOS_TYPES["FFS"],
    flags: int = 0,
    boot_pri: int = 0,
    bootable: bool = False,
    size_mb: int | None = None,
) -> None:
    """Add a partition to an existing RDB.

    Either lo_cyl/hi_cyl or size_mb must be given (size_mb is a convenience
    shorthand — rdbtool itself uses cylinder ranges).
    """
    args = ["add", f"name={name}", f"dostype={dos_type}"]
    if lo_cyl is not None:
        args.append(f"start={lo_cyl}")
    if hi_cyl is not None:
        args.append(f"end={hi_cyl}")
    if size_mb is not None:
        # rdbtool size= expects bytes (suffix 'b') and divides by cylinder size
        args.append(f"size={size_mb * 1024 * 1024}b")
    if bootable:
        flags |= 0x1
    if flags:
        args.append(f"flags={flags}")
    if boot_pri:
        args.append(f"boot_pri={boot_pri}")
    run_rdb(device, *args)


def delete_partition(device: str | Path, name: str) -> None:
    """Delete a named partition from the RDB."""
    run_rdb(device, "delete", name)


def change_partition(
    device: str | Path,
    name: str,
    *,
    new_name: str | None = None,
    dos_type: str | None = None,
    bootable: bool | None = None,
    automount: bool | None = None,
    boot_pri: int | None = None,
    # DosEnv fields accepted by rdbtool change: max_transfer, mask, num_buffer,
    # reserved, pre_alloc, boot_blocks.  Pass as e.g. mask=0x7ffffffe.
    **dosenv: int,
) -> None:
    """Change attributes of an existing partition without touching its data."""
    args = ["change", name]
    if new_name is not None:
        args.append(f"name={new_name}")
    if dos_type is not None:
        args.append(f"dostype={dos_type}")
    if bootable is not None:
        args.append(f"bootable={'true' if bootable else 'false'}")
    if automount is not None:
        args.append(f"automount={'true' if automount else 'false'}")
    if boot_pri is not None:
        args.append(f"pri={boot_pri}")
    for key, value in dosenv.items():
        args.append(f"{key}={value}")
    run_rdb(device, *args)


def fsadd(device: str | Path, fs_binary: Path, dos_type: str) -> None:
    """Embed a filesystem binary (e.g. PFS3aio) into the RDB FileSysHeader list."""
    run_rdb(device, "fsadd", str(fs_binary), f"dostype={dos_type}")


def fsremove(device: str | Path, dos_type: str) -> None:
    """Remove an embedded filesystem from the RDB by its DOS type."""
    run_rdb(device, "fsremove", f"dostype={dos_type}")
