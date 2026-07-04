from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by user environment
    raise SystemExit("Missing Python package: PyYAML") from exc


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EMULATORS = ROOT / "configs" / "atari" / "emulators.yaml"
DEFAULT_ALTIRRA_PROFILE = ROOT / "configs" / "atari" / "profiles" / "altirra.yaml"
DEFAULT_ATARI800_PROFILE = ROOT / "configs" / "atari" / "profiles" / "atari800-pal-800xl.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def expand(value: str | None) -> str | None:
    if value is None:
        return None
    return os.path.expanduser(os.path.expandvars(value))


def abs_path(value: str | None) -> str | None:
    expanded = expand(value)
    if not expanded:
        return expanded
    return str(Path(expanded).resolve())


def sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def emulator_command(name: str, emulators_path: Path) -> list[str]:
    emulators = load_yaml(emulators_path)
    defs = emulators.get("emulators", {})
    if name not in defs:
        raise ValueError(f"Unknown emulator '{name}'. Available: {', '.join(sorted(defs))}")
    cfg = defs[name]
    env_name = cfg.get("command_env")
    command = os.environ.get(env_name, "") if env_name else ""
    if not command:
        command = cfg.get("default_command", name)
    return shlex.split(str(command))


def profile_startup(args: Any, profile: dict[str, Any]) -> tuple[str | None, list[str]]:
    startup = profile.get("startup", {}) or {}
    program = args.program or startup.get("program")
    disks = [str(v) for v in sequence(startup.get("disks"))]
    disks.extend(args.disk or [])
    return expand(program) if program else None, [expand(d) or d for d in disks]


def add_common_run_args(parser: Any, default_profile: Path) -> None:
    parser.add_argument("-p", "--profile", type=Path, default=default_profile)
    parser.add_argument("--emulators", type=Path, default=DEFAULT_EMULATORS)
    parser.add_argument("--program", help="Program/XEX/COM to load instead of profile startup.program")
    parser.add_argument("--disk", action="append", help="Disk image to attach; may be repeated")
    parser.add_argument("--symbols", help="Symbol file to load in emulator debugger")
    parser.add_argument("--dry-run", action="store_true", help="Print command without launching")


def run_command(cmd: list[str], dry_run: bool, env: dict[str, str] | None = None) -> int:
    prefix = ""
    if env:
        prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in sorted(env.items()))
        prefix += " "
    print(prefix + shlex.join(cmd))
    if dry_run:
        return 0
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.call(cmd, env=merged_env)
