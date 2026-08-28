"""xdftool wrappers for Amiga ADF (floppy) image operations."""

from __future__ import annotations

import shutil
from pathlib import Path

import subprocess

from .disk import run_xdf, run_xdf_optional, xdf_tool

# ADF images are physical floppy emulations — only two valid sizes exist.
# DD: 80 tracks × 2 sides × 11 sectors × 512 B = 880 KB
# HD: 80 tracks × 2 sides × 22 sectors × 512 B = 1760 KB
# For larger content use HDF (hard disk image) via scripts/amiga adf create-hdf.
ADF_DD_SIZE = "880k"
ADF_HD_SIZE = "1760k"
ADF_VALID_SIZES = (ADF_DD_SIZE, ADF_HD_SIZE)

FS_TYPES = ("ofs", "ffs", "ofs-intl", "ffs-intl", "ofs-dc", "ffs-dc")


def create_from_dir(
    output: Path,
    source_dir: Path,
    *,
    label: str = "Workbench",
    fs: str = "ffs",
    size: str = ADF_DD_SIZE,
) -> None:
    """Create an ADF image by packing a host directory tree.

    xdftool's `pack` command creates the image, formats it, and copies the
    tree in one shot.  The volume label comes from --label; the host directory
    name is not used.

    If size is the default (880k = DD floppy) but the content doesn't fit,
    the size is automatically promoted to HD (1760k) before trying.  If HD
    still doesn't fit, a clear error is raised suggesting HDF instead.  Pass
    an explicit --size to skip auto-promotion.
    """
    import tempfile, shutil as _shutil

    output.parent.mkdir(parents=True, exist_ok=True)

    # xdftool pack derives the volume label from the *directory name* it is
    # given, not from a flag.  Stage to a temp dir named after the label so the
    # on-disk name is correct.
    with tempfile.TemporaryDirectory(prefix="amiga-adf-") as tmp:
        staged = Path(tmp) / label
        _shutil.copytree(source_dir, staged)

        # ADF is a physical floppy format: only DD (880k) and HD (1760k) are valid.
        # Auto-promote from DD to HD if the default was requested; if the caller
        # pinned a specific size, honour it and report a clear error on failure.
        if size == ADF_DD_SIZE:
            sizes_to_try = [ADF_DD_SIZE, ADF_HD_SIZE]
        else:
            sizes_to_try = [size]

        # xdftool pack uses type=adf_hd (not size=) to select HD format.
        # DD is the default when no type option is given.
        _SIZE_TO_TYPE = {ADF_DD_SIZE: None, ADF_HD_SIZE: "adf_hd"}

        last_combined = ""
        for attempt_size in sizes_to_try:
            output.unlink(missing_ok=True)
            cmd = [*xdf_tool(), str(output), "pack", str(staged), fs]
            adf_type = _SIZE_TO_TYPE[attempt_size]
            if adf_type:
                cmd.append(f"type={adf_type}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if attempt_size != size:
                    print(f"  Note: content too large for DD floppy ({size}), "
                          f"using HD floppy ({attempt_size})")
                return
            last_combined = result.stdout + result.stderr
            if "No Free Blocks" not in last_combined:
                import sys as _sys
                print(last_combined, end="", file=_sys.stderr)
                raise subprocess.CalledProcessError(result.returncode, result.args)

        content_kb = sum(
            f.stat().st_size for f in source_dir.rglob("*") if f.is_file()
        ) // 1024
        raise ValueError(
            f"Directory content (~{content_kb} KB) is too large for any ADF floppy "
            f"(HD floppy max is {ADF_HD_SIZE} = 1760 KB). "
            f"ADF images are physical floppy emulations with fixed sizes. "
            f"Use HDF format for larger content: "
            f"'scripts/build-amiga-hdf' or 'uvx --from amitools xdftool disk.hdf pack <dir> ffs size=<n>m'."
        )


def create_from_files(
    output: Path,
    files: list[Path],
    *,
    label: str = "Workbench",
    fs: str = "ffs",
    size: str = ADF_DD_SIZE,
) -> None:
    """Create an ADF image from a flat list of host files.

    Files are staged into a temporary directory (flat — no subdirectory
    structure) and packed with xdftool.  The volume label is set by *label*.
    Auto-promotes from DD to HD if content does not fit; raises ValueError
    if it exceeds HD capacity.
    """
    import tempfile, shutil as _shutil

    with tempfile.TemporaryDirectory(prefix="amiga-adf-") as tmp:
        staged = Path(tmp) / label
        staged.mkdir()
        for src in files:
            _shutil.copy2(src, staged / src.name)
        create_from_dir(output, staged, label=label, fs=fs, size=size)


def create_blank(
    output: Path,
    *,
    label: str = "Blank",
    fs: str = "ffs",
    size: str = ADF_DD_SIZE,
) -> None:
    """Create an empty formatted ADF image with no files."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    create_arg = "type=adf_hd" if size == ADF_HD_SIZE else "type=adf"
    run_xdf(output, "create", create_arg)
    run_xdf(output, "format", label, fs)


def list_files(adf: Path) -> str:
    """Return the directory listing of an ADF as a string."""
    import subprocess, shutil as _shutil
    tool = _shutil.which("xdftool")
    uvx = _shutil.which("uvx")
    cmd = [tool] if tool else ([uvx, "--from", "amitools", "xdftool"] if uvx else None)
    if cmd is None:
        raise SystemExit("xdftool is required, or install uv/uvx to fetch amitools")
    result = subprocess.run([*cmd, str(adf), "list"], check=True,
                            capture_output=True, text=True)
    return result.stdout


def read_file(adf: Path, adf_path: str, dest: Path) -> None:
    """Extract a single file from an ADF to a host path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_xdf(adf, "read", adf_path, str(dest))


def write_file(adf: Path, src: Path, adf_path: str) -> None:
    """Write a host file into an ADF at the given Amiga path."""
    run_xdf(adf, "write", str(src), adf_path)
