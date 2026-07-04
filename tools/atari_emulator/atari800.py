from __future__ import annotations

from typing import Any

from .common import (
    abs_path,
    add_common_run_args,
    DEFAULT_ATARI800_PROFILE,
    emulator_command,
    load_yaml,
    profile_startup,
    run_command,
)


def build_command(args: Any) -> list[str]:
    profile = load_yaml(args.profile)
    machine = profile.get("machine", {}) or {}
    cfg = profile.get("atari800", {}) or {}
    cmd = emulator_command("atari800", args.emulators)

    program, disks = profile_startup(args, profile)

    system = str(machine.get("system", "")).lower()
    if system in {"800xl", "xl"}:
        cmd.append("-xl")
    elif system in {"130xe", "xe"}:
        cmd.append("-xe")
    elif system:
        cmd.append(f"-{system}")

    video = str(machine.get("video", "")).lower()
    if video in {"pal", "ntsc"}:
        cmd.append(f"-{video}")

    config = abs_path(cfg.get("config"))
    if config:
        cmd.extend(["-config", config])

    os_rom = abs_path((machine.get("rom", {}) or {}).get("os"))
    if os_rom:
        cmd.extend(["-osa_rom", os_rom])

    if cfg.get("windowed", True):
        cmd.append("-windowed")

    for idx, disk in enumerate(disks, start=1):
        cmd.extend([f"-{idx}", abs_path(disk) or disk])
    if program:
        cmd.extend(["-run", abs_path(program) or program])
    return cmd


def cmd_atari800(args: Any) -> int:
    return run_command(build_command(args), args.dry_run)


def register_subcommands(subparsers: Any) -> None:
    parser = subparsers.add_parser("atari800", help="Run an Atari profile with atari800")
    add_common_run_args(parser, DEFAULT_ATARI800_PROFILE)
    parser.set_defaults(fn=cmd_atari800)
