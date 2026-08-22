"""Host-side helpers for assembling Amiga disk images."""

from __future__ import annotations

import shutil
import subprocess
import re
from pathlib import Path

NIO_LOAD_RESIDENT = (
    "C:fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device\n"
)
DISK_LOAD_RESIDENT = (
    "C:fujinet-load-resident DEVS:fujinet-disk.device fujinet-disk.device\n"
)


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


def run_xdf_optional(image: Path, *commands: str) -> bool:
    """Run an xdftool operation whose target may legitimately be absent."""
    result = subprocess.run(
        [*xdf_tool(), str(image), *commands],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def validate_volume_label(label: str) -> str:
    if not label or len(label) > 30 or any(character in label for character in ":/\\"):
        raise ValueError(
            "volume label must be 1-30 characters and cannot contain ':', '/', or '\\'"
        )
    return label


def prepend_fujinet_resident_loads(
    test_commands: str,
    *,
    load_driver: bool = False,
    load_nio: bool = False,
) -> str:
    """Prepend LoadResident lines. NIO is applied last so it is first on disk."""
    if load_driver:
        test_commands = DISK_LOAD_RESIDENT + test_commands
    if load_nio:
        test_commands = NIO_LOAD_RESIDENT + test_commands
    return test_commands


def startup_sequence_needs_patch(
    *,
    startup_script: bool = False,
    interactive: bool = False,
    load_driver: bool = False,
    load_nio: bool = False,
) -> bool:
    """True when S/Startup-Sequence must be rewritten for a script, generated CLI, or resident load."""
    return startup_script or not interactive or load_driver or load_nio


def startup_command_offset(startup: str, command: str) -> int | None:
    """Return the beginning of an AmigaDOS command line, ignoring C: prefix."""
    match = re.search(
        rf"(?im)^[ \t]*(?:C:)?{re.escape(command)}(?:[ \t].*)?(?:\r?\n|$)",
        startup,
    )
    return match.start() if match is not None else None


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
