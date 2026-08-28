"""xdftool wrappers for Amiga ADF (floppy) image operations."""

from __future__ import annotations

import shutil
from pathlib import Path

from .disk import run_xdf, run_xdf_optional

# Standard Amiga DD floppy: 80 tracks × 2 sides × 11 sectors × 512 B
ADF_DD_SIZE = "880k"
ADF_HD_SIZE = "1760k"

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
    """
    import tempfile, shutil as _shutil

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    # xdftool pack derives the volume label from the *directory name* it is
    # given, not from a flag.  Stage to a temp dir named after the label so the
    # on-disk name is correct.
    with tempfile.TemporaryDirectory(prefix="amiga-adf-") as tmp:
        staged = Path(tmp) / label
        _shutil.copytree(source_dir, staged)
        run_xdf(output, "pack", str(staged), fs, f"size={size}")


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
    run_xdf(output, "create", f"size={size}")
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
