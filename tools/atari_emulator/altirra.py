from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .common import (
    abs_path,
    add_common_run_args,
    DEFAULT_ALTIRRA_PROFILE,
    emulator_command,
    load_yaml,
    profile_startup,
    run_command,
    sequence,
)


def _bool_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _device_arg(device: Any) -> str:
    if isinstance(device, str):
        return device
    if not isinstance(device, dict):
        raise ValueError(f"Altirra device entry must be a mapping or string: {device!r}")

    kind = device.get("type", "custom")
    params = device.get("params", {}) or {}
    if not isinstance(params, dict):
        raise ValueError(f"Altirra device params must be a mapping: {device!r}")

    parts = [str(kind)]
    for key, value in params.items():
        if key == "path":
            value = abs_path(str(value))
        parts.append(f"{key}={_bool_value(value)}")
    return ",".join(parts)


def _append_host_path(cmd: list[str], entry: Any) -> None:
    if isinstance(entry, str):
        cmd.extend(["--hdpath", abs_path(entry) or entry])
        return
    if not isinstance(entry, dict):
        raise ValueError(f"Altirra host path entry must be a mapping or string: {entry!r}")

    path = entry.get("path")
    if not path:
        raise ValueError(f"Altirra host path entry missing path: {entry!r}")

    mode = str(entry.get("mode", "ro")).lower()
    if mode in {"rw", "write", "writable"}:
        switch = "--hdpathrw"
    elif mode in {"ro", "read", "readonly"}:
        switch = "--hdpath"
    else:
        raise ValueError(f"Unsupported Altirra host path mode: {mode}")

    cmd.extend([switch, abs_path(str(path)) or str(path)])


def _rom_root(profile: dict[str, Any], key: str, env_name: str) -> str | None:
    cfg = profile.get("altirra", {}) or {}
    roots = cfg.get("rom_roots", {}) or {}
    value = roots.get(key) or os.environ.get(env_name)
    if not value:
        return None
    expanded = os.path.expandvars(str(value))
    if "$" in expanded:
        expanded = os.environ.get(env_name, "")
    return abs_path(expanded) if expanded else None


def _render_settings(profile: dict[str, Any]) -> tempfile.TemporaryDirectory[str] | None:
    cfg = profile.get("altirra", {}) or {}
    template = cfg.get("settings_template")
    if not template:
        return None

    template_path = Path(abs_path(str(template)) or str(template))
    text = template_path.read_text(encoding="utf-8")

    os_roms = _rom_root(profile, "os", "ATARI_OS_ROMS")
    basic_roms = _rom_root(profile, "basic", "ATARI_BASIC_ROMS")
    missing = []
    if not os_roms:
        missing.append("altirra.rom_roots.os or ATARI_OS_ROMS")
    if not basic_roms:
        missing.append("altirra.rom_roots.basic or ATARI_BASIC_ROMS")
    if missing:
        raise ValueError("Missing ROM root value(s): " + ", ".join(missing))

    text = text.replace("__OS_ROMS__", os_roms)
    text = text.replace("__BASIC_ROMS__", basic_roms)

    tmp = tempfile.TemporaryDirectory(prefix="fujinet-atari-")
    settings_path = Path(tmp.name) / "altirra" / "settings.ini"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(text, encoding="utf-8")
    return tmp


def _patched_atdevice_path(path: str, tmp_root: Path, cfg: dict[str, Any]) -> str:
    src = Path(abs_path(path) or path)
    text = src.read_text(encoding="utf-8")
    if os.environ.get("ATARI_NETSIO_ATDEVICE_DEBUG", "0") != "0":
        text, count = re.subn(r'option "debug":\s*(true|false)\s*;', 'option "debug": true;', text, count=1)
        if count != 1:
            raise ValueError(f"Could not enable debug option in {src}")

    command_ack_delay_tics = cfg.get("netsio_command_ack_delay_tics")
    if command_ack_delay_tics is not None:
        delay = int(command_ack_delay_tics)
        text, count = re.subn(
            r"\s*//Thread\.sleep\(1800\); // 1 ms delay \(850 us - 16 ms\) before sending ACK/NAK to data frame",
            f"\n    Debug.log(\"NIO command ACK delay: {delay} tics\");"
            f"\n    Thread.sleep({delay}); // configured delay before command ACK/NAK",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"Could not patch command ACK delay in {src}")

    dst = tmp_root / src.name
    dst.write_text(text, encoding="utf-8")
    return str(dst)


def _append_bool_switch(cmd: list[str], value: Any, enabled: str, disabled: str) -> None:
    if value is None:
        return
    cmd.append(enabled if bool(value) else disabled)


def _is_altirrasdl_command(cmd: list[str]) -> bool:
    if not cmd:
        return False
    executable = Path(cmd[0]).name.lower()
    return executable == "altirrasdl"


def _requires_altirrasdl(profile: dict[str, Any]) -> bool:
    cfg = profile.get("altirra", {}) or {}
    template = str(cfg.get("settings_template") or "").lower()
    return "altirrasdl" in template


def _validate_command(cmd: list[str], profile: dict[str, Any]) -> None:
    if _requires_altirrasdl(profile) and not _is_altirrasdl_command(cmd):
        command = " ".join(cmd) if cmd else "<empty>"
        raise ValueError(
            "This profile uses AltirraSDL settings and native --options, "
            f"but the configured Altirra command is '{command}'. "
            "Unset ALTIRRA_BIN or set ALTIRRA_BIN=AltirraSDL."
        )


def _append_machine_switches(cmd: list[str], profile: dict[str, Any]) -> None:
    machine = profile.get("machine", {}) or {}

    system = str(machine.get("system", "")).lower()
    if system:
        valid = {"800", "800xl", "1200xl", "130xe", "xegs", "1400xl", "5200"}
        if system not in valid:
            raise ValueError(f"Unsupported Altirra hardware mode: {system}")
        cmd.extend(["--hardware", system])

    video = str(machine.get("video", "")).lower()
    if video:
        valid = {"ntsc", "pal", "secam", "ntsc50", "pal60"}
        if video not in valid:
            raise ValueError(f"Unsupported Altirra video standard: {video}")
        cmd.append(f"--{video}")

    ram_kb = machine.get("ram_kb")
    if ram_kb is not None:
        cmd.extend(["--memsize", f"{ram_kb}K"])

    direct = {
        "kernel": "--kernel",
        "kernel_ref": "--kernelref",
        "basic_ref": "--basicref",
        "artifact": "--artifact",
        "axlon_memsize": "--axlonmemsize",
        "high_banks": "--highbanks",
        "diskemu": "--diskemu",
    }
    for key, switch in direct.items():
        value = machine.get(key)
        if value is not None:
            cmd.extend([switch, str(value)])

    _append_bool_switch(cmd, machine.get("basic"), "--basic", "--nobasic")
    _append_bool_switch(cmd, machine.get("stereo"), "--stereo", "--nostereo")
    _append_bool_switch(cmd, machine.get("vsync"), "--vsync", "--novsync")
    _append_bool_switch(cmd, machine.get("fastboot"), "--fastboot", "--nofastboot")
    _append_bool_switch(cmd, machine.get("accurate_disk"), "--accuratedisk", "--noaccuratedisk")
    _append_bool_switch(cmd, machine.get("burst_io"), "--burstio", "--noburstio")

    sio_patch = machine.get("sio_patch")
    if sio_patch is not None:
        if isinstance(sio_patch, bool):
            cmd.append("--siopatch" if sio_patch else "--nosiopatch")
        else:
            mode = str(sio_patch).lower()
            mapping = {
                "on": "--siopatch",
                "true": "--siopatch",
                "safe": "--siopatchsafe",
                "off": "--nosiopatch",
                "false": "--nosiopatch",
            }
            if mode not in mapping:
                raise ValueError(f"Unsupported Altirra SIO patch mode: {mode}")
            cmd.append(mapping[mode])


def build_command(args: Any) -> tuple[list[str], dict[str, str], tempfile.TemporaryDirectory[str] | None]:
    profile = load_yaml(args.profile)
    cfg = profile.get("altirra", {}) or {}
    cmd = emulator_command("altirra", args.emulators)
    _validate_command(cmd, profile)
    env = {}
    settings_tmp = _render_settings(profile)
    debug_device_tmp: tempfile.TemporaryDirectory[str] | None = None
    patch_atdevice = (
        os.environ.get("ATARI_NETSIO_ATDEVICE_DEBUG", "0") != "0"
        or cfg.get("netsio_command_ack_delay_tics") is not None
    )
    if settings_tmp is not None:
        env["XDG_CONFIG_HOME"] = settings_tmp.name
    if patch_atdevice:
        debug_device_tmp = tempfile.TemporaryDirectory(prefix="fujinet-atdevice-")
        device_root = Path(debug_device_tmp.name)
        if settings_tmp is not None:
            settings_tmp._atdevice_debug_tmp = debug_device_tmp  # type: ignore[attr-defined]
        else:
            settings_tmp = debug_device_tmp

    program, disks = profile_startup(args, profile)

    profile_ini = abs_path(cfg.get("profile"))
    if cfg.get("portable", True):
        cmd.append("/portable")
    if profile_ini:
        cmd.append(f"/portablealt:{profile_ini}")
        cmd.append(f"/profile:{profile_ini}")
    _append_machine_switches(cmd, profile)
    if cfg.get("debug", False):
        cmd.append("/debug")

    if args.symbols:
        cmd.append(f"/debugcmd:.loadsym {abs_path(args.symbols)}")
    for debug_cmd in sequence(cfg.get("debug_commands")):
        cmd.append(f"/debugcmd:{str(debug_cmd)}")

    for device in sequence(cfg.get("devices")):
        if debug_device_tmp is not None and isinstance(device, dict):
            params = device.get("params", {}) or {}
            if isinstance(params, dict) and "path" in params:
                device = dict(device)
                device["params"] = dict(params)
                device["params"]["path"] = _patched_atdevice_path(str(params["path"]), device_root, cfg)
        cmd.extend(["--adddevice", _device_arg(device)])
    for host_path in sequence(cfg.get("host_paths")):
        _append_host_path(cmd, host_path)

    for disk in disks:
        cmd.append(abs_path(disk) or disk)
    if program:
        cmd.extend(["--run", abs_path(program) or program])
    return cmd, env, settings_tmp


def cmd_altirra(args: Any) -> int:
    cmd, env, settings_tmp = build_command(args)
    try:
        return run_command(cmd, args.dry_run, env=env)
    finally:
        if settings_tmp is not None:
            settings_tmp.cleanup()


def register_subcommands(subparsers: Any) -> None:
    parser = subparsers.add_parser("altirra", help="Run an Atari profile with Altirra")
    add_common_run_args(parser, DEFAULT_ALTIRRA_PROFILE)
    parser.set_defaults(fn=cmd_altirra)
