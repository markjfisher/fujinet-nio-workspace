"""Host-side helpers for assembling Amiga disk images."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def xdf_tool() -> list[str]:
    tool = shutil.which("xdftool")
    if tool:
        return [tool]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "--from", "amitools", "xdftool"]
    raise SystemExit("xdftool is required, or install uv/uvx to fetch amitools")


def run_xdf(image: Path, *commands: str) -> None:
    subprocess.run([*xdf_tool(), str(image), *commands], check=True)


def archive_tool() -> tuple[str, str]:
    for name in ("7z", "7zz"):
        tool = shutil.which(name)
        if tool:
            return "7z", tool
    tool = shutil.which("lha")
    if tool:
        return "lha", tool
    raise SystemExit(
        "An LHA extractor is required for disk archive installation "
        "(install 7z/7zz or lha)"
    )


def extract_archive(archive: Path, destination: Path) -> None:
    kind, tool = archive_tool()
    destination.mkdir(parents=True, exist_ok=True)
    if kind == "7z":
        command = [tool, "x", "-y", f"-o{destination}", str(archive)]
    else:
        command = [tool, "x", str(archive), str(destination)]
    subprocess.run(command, check=True)


def install_tree(image: Path, source: Path, destination: str = "") -> None:
    """Copy a host tree into an Amiga filesystem, preserving its layout."""
    def supported(path: Path) -> bool:
        try:
            path.relative_to(source).as_posix().encode("latin-1")
        except UnicodeEncodeError:
            return False
        return True

    directories = sorted(
        (path for path in source.rglob("*") if path.is_dir() and supported(path)),
        key=lambda path: (len(path.relative_to(source).parts), str(path)),
    )
    for directory in directories:
        relative = directory.relative_to(source).as_posix()
        target = "/".join(part for part in (destination, relative) if part)
        run_xdf(image, "makedir", target)
    for path in sorted(
        path for path in source.rglob("*") if path.is_file() and supported(path)
    ):
        relative = path.relative_to(source).as_posix()
        target = "/".join(part for part in (destination, relative) if part)
        run_xdf(image, "write", str(path), target)
