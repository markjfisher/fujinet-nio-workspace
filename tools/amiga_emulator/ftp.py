"""Generic lftp client for pushing or fetching files to an Amiga FTP server.

Credentials and the client binary come from ``local/amiga.env`` (or another
env file), not from this module.

``lftp -u`` is an ``open`` option and cannot be combined with ``-f``. The
working form is ``lftp -f <script>`` with ``open -u user,pass host`` inside
the generated script.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FTP_VARS = ("FTP_HOST", "FTP_USER", "FTP_PASS")
DEFAULT_FTP_APP = "lftp"


def workspace_root() -> Path:
    """Return the workspace root (two levels above this package)."""
    return Path(__file__).resolve().parent.parent.parent


def default_env_file() -> Path:
    return workspace_root() / "local" / "amiga.env"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE env file. Returns {} if the file is absent."""
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value[:1] in ('"', "'"):
            quote = raw_value[0]
            end = raw_value.find(quote, 1)
            value = raw_value[1:end] if end != -1 else raw_value[1:]
        else:
            value = re.split(r"\s+#", raw_value, maxsplit=1)[0].strip()
        value = value.replace("$HOME", str(Path.home())).replace("~", str(Path.home()))
        result[key] = value
    return result


@dataclass(frozen=True)
class FtpConfig:
    host: str
    user: str
    password: str
    app: str


def load_ftp_config(
    env_file: Path | None = None,
    environ: dict[str, str] | None = None,
) -> FtpConfig:
    """Load FTP settings from an env file, with process env taking precedence."""
    env_path = env_file if env_file is not None else default_env_file()
    file_vals = parse_env_file(env_path)
    env = os.environ if environ is None else environ

    def pick(name: str, default: str = "") -> str:
        if name in env and env[name] != "":
            return env[name]
        return file_vals.get(name, default)

    missing = [name for name in REQUIRED_FTP_VARS if not pick(name)]
    if missing:
        hint = env_path if env_path.is_file() else f"{env_path} (copy local/amiga.env.example)"
        raise SystemExit(
            f"Missing FTP settings: {', '.join(missing)}. Set them in {hint}."
        )

    app = pick("FTP_APP", DEFAULT_FTP_APP) or DEFAULT_FTP_APP
    return FtpConfig(
        host=pick("FTP_HOST"),
        user=pick("FTP_USER"),
        password=pick("FTP_PASS"),
        app=app,
    )


def parse_files_arg(raw: str) -> list[Path]:
    return [Path(part.strip()) for part in raw.split(",") if part.strip()]


def quote_lftp_path(path: str) -> str:
    if any(ch in path for ch in ' \t"\''):
        return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return path


def build_put_script(files: list[Path], target_dir: str) -> str:
    """Build lftp ``put`` commands that land each file in ``target_dir``."""
    remote_dir = target_dir.rstrip("/")
    lines: list[str] = []
    for src in files:
        remote = f"{remote_dir}/{src.name}"
        lines.append(
            f"put {quote_lftp_path(str(src))} -o {quote_lftp_path(remote)}"
        )
    lines.append("bye")
    return "\n".join(lines) + "\n"


def _has_command(body: str, command: str) -> bool:
    prefix = command.lower() + " "
    for line in body.splitlines():
        stripped = line.strip().lower()
        if stripped == command.lower() or stripped.startswith(prefix):
            return True
    return False


def compose_lftp_script(config: FtpConfig, body: str) -> str:
    """Prepend ``open -u user,pass host`` unless the body already opens; ensure ``bye``."""
    text = body.strip() + "\n"
    if not _has_command(text, "open"):
        creds = quote_lftp_path(f"{config.user},{config.password}")
        text = f"open -u {creds} {quote_lftp_path(config.host)}\n{text}"
    if not _has_command(text, "bye"):
        text = text.rstrip() + "\nbye\n"
    return text if text.endswith("\n") else text + "\n"


def _print_invocation(argv: list[str], cwd: Path, script_text: str) -> None:
    print(f"cwd: {cwd}", file=sys.stderr)
    print("invoke: " + " ".join(argv), file=sys.stderr)
    print("----- lftp script -----", file=sys.stderr)
    print(script_text, file=sys.stderr, end="" if script_text.endswith("\n") else "\n")
    print("-----", file=sys.stderr)


def run_lftp(
    script_text: str,
    config: FtpConfig,
    *,
    cwd: Path,
    runner: Callable[..., Any] | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Write ``script_text`` and invoke ``lftp -f <file>`` (auth lives in ``open -u``)."""
    run = runner or subprocess.run
    app_path = config.app
    if not dry_run and "/" not in app_path and shutil.which(app_path) is None and runner is None:
        raise SystemExit(
            f"{app_path!r} not found on PATH. Install it or set FTP_APP in local/amiga.env."
        )

    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".lftp", delete=False, encoding="utf-8"
    )
    script_path = Path(handle.name)
    try:
        handle.write(script_text)
        handle.close()
        argv = [app_path, "-f", str(script_path)]
        if verbose:
            _print_invocation(argv, cwd, script_text)
        if dry_run:
            return 0
        result = run(argv, cwd=str(cwd))
        return int(result.returncode)
    finally:
        script_path.unlink(missing_ok=True)


def transfer_files(
    files: list[Path],
    target_dir: str,
    config: FtpConfig,
    *,
    cwd: Path,
    runner: Callable[..., Any] | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    missing = [p for p in files if not p.is_file()]
    if missing:
        names = "\n".join(f"  {p}" for p in missing)
        raise SystemExit(f"error: source file(s) not found:\n{names}")
    body = build_put_script(files, target_dir)
    return run_lftp(
        compose_lftp_script(config, body),
        config,
        cwd=cwd,
        runner=runner,
        dry_run=dry_run,
        verbose=verbose,
    )


def transfer_script(
    script_path: Path,
    config: FtpConfig,
    *,
    cwd: Path,
    runner: Callable[..., Any] | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    if not script_path.is_file():
        raise SystemExit(f"error: lftp script not found: {script_path}")
    body = script_path.read_text(encoding="utf-8")
    return run_lftp(
        compose_lftp_script(config, body),
        config,
        cwd=cwd,
        runner=runner,
        dry_run=dry_run,
        verbose=verbose,
    )


def add_ftp_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--script",
        type=Path,
        help="lftp instructions file (put/get/bye); executed with lftp -f",
    )
    parser.add_argument(
        "--files",
        help="comma-separated local files to upload",
    )
    parser.add_argument(
        "--target-dir",
        help="remote directory for --files (e.g. /dev/NIO/C/)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="env file with FTP_HOST/FTP_USER/FTP_PASS/FTP_APP "
             "(default: local/amiga.env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not run lftp; pair with --verbose to inspect the generated script",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print cwd, lftp argv, and the generated script",
    )


def validate_ftp_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if bool(args.script) == bool(args.files):
        parser.error("specify exactly one of --script or --files")
    if args.files and not args.target_dir:
        parser.error("--files requires --target-dir")
    if args.target_dir and not args.files:
        parser.error("--target-dir is only valid with --files")


def run_from_args(args: argparse.Namespace) -> int:
    config = load_ftp_config(args.env_file)
    cwd = workspace_root()
    if args.script:
        script = args.script
        if not script.is_file():
            script = cwd / script
        return transfer_script(
            script,
            config,
            cwd=cwd,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    files = parse_files_arg(args.files)
    if not files:
        raise SystemExit("error: --files must list at least one path")
    return transfer_files(
        files,
        args.target_dir,
        config,
        cwd=cwd,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="amiga ftp",
        description="Transfer files to or from an Amiga FTP server via lftp.",
    )
    add_ftp_arguments(parser)
    args = parser.parse_args(argv)
    validate_ftp_args(parser, args)
    try:
        return run_from_args(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
