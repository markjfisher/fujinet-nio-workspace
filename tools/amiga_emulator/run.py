"""Run Amiberry with a FujiNet NIO serial bridge.

This is the implementation behind scripts/run-amiberry-nio.  The shell
script remains as a compatibility entry point for existing workflows.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import TextIO

from . import ipc

ROOT = Path(__file__).resolve().parents[2]


def env_path(name: str, default: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(os.environ.get(name, default))))


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"Required command not found: {name}")


def require_file(path: Path, description: str = "Required file") -> None:
    if not path.is_file():
        raise SystemExit(f"{description} not found: {path}")


def wait_for_tcp(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise SystemExit(f"TCP endpoint did not become available: {host}:{port}")


def wait_for_links(*paths: Path, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(path.is_symlink() for path in paths):
            return
        time.sleep(0.1)
    names = ", ".join(str(path) for path in paths)
    raise SystemExit(f"Serial PTY links were not created: {names}")


def wait_for_logged_ipc_socket(log: Path, timeout: float = 5.0) -> Path | None:
    """Return this Amiberry process's socket, as reported in its log."""
    pattern = re.compile(r"IPC: Listening on (.+?)\s*$", re.MULTILINE)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            match = pattern.search(log.read_text(encoding="utf-8", errors="replace"))
        except FileNotFoundError:
            match = None
        if match:
            return Path(match.group(1))
        time.sleep(0.05)
    return None


def wait_for_log_line(log: Path, text: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if text in log.read_text(encoding="utf-8", errors="replace"):
                return
        except FileNotFoundError:
            pass
        time.sleep(0.05)
    raise TimeoutError(f"Amiberry log did not contain {text!r}")


def terminate_process(process: subprocess.Popen[object] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


class AmigaRunner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.amiberry: subprocess.Popen[object] | None = None
        self.bridge: subprocess.Popen[object] | None = None
        self.nio: subprocess.Popen[object] | None = None
        self.log_handles: list[TextIO] = []
        self.run_dir = Path(os.environ.get("AMIGA_RUN_DIR", ROOT / "build/amiga-e2e"))
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.rom_dir = self.run_dir / "rom"
        self.rom_dir.mkdir(parents=True, exist_ok=True)

        self.amiberry_bin = os.environ.get("AMIBERRY_BIN", "amiberry")
        self.kickstart = env_path(
            "AMIBERRY_KICKSTART",
            "${HOME}/dev/amiga/amigaOS3.2/ROM/kickCDTVa1000a500a2000a600.rom",
        )
        os_root = env_path("AMIBERRY_OS_ROOT", "${HOME}/dev/amiga/amigaOS3.2")
        self.fast_file_system = env_path(
            "AMIBERRY_FAST_FILE_SYSTEM", str(os_root / "L/FastFileSystem")
        )
        self.disk = Path(args.disk or os.environ.get("AMIBERRY_DISK", ""))
        self.serial_mode = os.environ.get("AMIBERRY_SERIAL_MODE", "tcp")
        self.host = os.environ.get("AMIBERRY_HOST", "127.0.0.1")
        self.nio_host = os.environ.get("FUJINET_HOST", "127.0.0.1")
        self.nio_port = int(os.environ.get("FUJINET_NIO_PORT", os.environ.get("FUJINET_PORT", "65504")))
        self.amiga_port = int(os.environ.get("AMIBERRY_PORT", "23462"))
        self.nio_bin = Path(os.environ.get(
            "FUJINET_NIO_BIN", ROOT / "repos/fujinet-nio/build/fujibus-tcp-debug/fujinet-nio"
        ))
        self.nio_rs232_bin = Path(os.environ.get(
            "FUJINET_NIO_RS232_BIN", ROOT / "repos/fujinet-nio/build/fujibus-rs232-debug/fujinet-nio"
        ))
        self.external_nio = args.external_nio
        self.nio_log = Path(os.environ.get("NIO_LOG", self.run_dir / "fujinet-nio.log"))
        self.amiberry_log = Path(os.environ.get("AMIBERRY_LOG", self.run_dir / "amiberry.log"))
        self.bridge_log = Path(os.environ.get("BRIDGE_LOG", self.run_dir / "bridge.log"))
        self.config_dir = self.run_dir / "fujinet-data"
        self.amiga_pty = self.run_dir / "amiga-serial"
        self.nio_pty = self.run_dir / "nio-serial"
        self.ipc_socket: Path | None = None
        self.debugger_controller: subprocess.Popen[object] | None = None

    def validate(self) -> None:
        require_command(self.amiberry_bin)
        require_command("socat")
        require_file(self.kickstart)
        require_file(self.disk, "Amiga disk")
        if self.disk.suffix.lower() == ".hdf":
            require_file(self.fast_file_system)
        if self.serial_mode not in ("tcp", "pty"):
            raise SystemExit(f"Unknown Amiga serial mode: {self.serial_mode}")
        if self.serial_mode == "pty":
            if self.external_nio:
                raise SystemExit("--external-nio is only supported with --tcp")
            require_file(self.nio_rs232_bin)
        elif not self.external_nio:
            require_file(self.nio_bin)
        uae_config = os.environ.get("AMIBERRY_UAE_CONFIG", "")
        if uae_config:
            require_file(Path(uae_config), "Amiberry UAE configuration")

    def open_log(self, path: Path) -> TextIO:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w", encoding="utf-8", errors="replace")
        self.log_handles.append(handle)
        return handle

    def start_process(
        self,
        command: list[str],
        log: Path,
        *,
        cwd: Path | None = None,
    ) -> subprocess.Popen[object]:
        handle = self.open_log(log)
        return subprocess.Popen(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT)

    def write_nio_config(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        config = self.config_dir / "fujinet.yaml"
        config.write_text(
            "fujinet:\n"
            "  device_name: \"amiga-test\"\n"
            "boot:\n"
            "  mode: config\n"
            "  config_uri: \"persist:/boot/autorun.img\"\n"
            "  readonly: true\n"
            "wifi:\n"
            "  enabled: false\n"
            "  ssid: \"\"\n"
            "  passphrase: \"\"\n"
            "devices:\n"
            "  modem:\n"
            "    enabled: false\n"
            "    sniffer_enabled: false\n"
            "  cpm:\n"
            "    enabled: false\n"
            "    ccp_image: \"\"\n"
            "  printer:\n"
            "    enabled: false\n"
            "netsio:\n"
            "  enabled: false\n"
            "  host: \"localhost\"\n"
            "  port: 9997\n"
            "clock:\n"
            "  timezone: \"UTC\"\n"
            "  enabled: true\n"
            "channel:\n"
            "  pty_path: \"\"\n"
            f"  tcp_host: \"{self.nio_host}\"\n"
            f"  tcp_port: {self.nio_port}\n"
            "  serial_port: \"/dev/ttyUSB0\"\n"
            "  uart:\n"
            "    baud_rate: 115200\n"
            "    data_bits: 8\n"
            "    parity: none\n"
            "    stop_bits: 1\n"
            "    flow_control: none\n"
            "    tx_gap_us: 0\n",
            encoding="utf-8",
        )

    def start_transport(self) -> str | None:
        if self.serial_mode == "pty":
            for path in (self.amiga_pty, self.nio_pty):
                path.unlink(missing_ok=True)
            bridge_args = ["-d", "-d"]
            if os.environ.get("SOCAT_HEXDUMP") == "1":
                bridge_args.extend(["-x", "-v"])
            self.bridge = self.start_process(
                ["socat", *bridge_args,
                 f"pty,raw,echo=0,link={self.amiga_pty}",
                 f"pty,raw,echo=0,link={self.nio_pty}"],
                self.bridge_log,
            )
            wait_for_links(self.amiga_pty, self.nio_pty)
            serial_device = os.path.realpath(self.amiga_pty)
            nio_device = os.path.realpath(self.nio_pty)
            print(f"Amiga PTY: {self.amiga_pty}")
            print(f"NIO PTY:   {self.nio_pty}")
            print(f"Amiga device: {serial_device}")
            print(f"NIO device:   {nio_device}")
            self.write_nio_config()
            env = os.environ.copy()
            env["FN_SERIAL_PORT"] = nio_device
            env["FN_SERIAL_BAUD"] = "19200"
            log = self.open_log(self.nio_log)
            self.nio = subprocess.Popen(
                [str(self.nio_rs232_bin)], cwd=self.run_dir, env=env,
                stdout=log, stderr=subprocess.STDOUT,
            )
            return serial_device

        if not self.external_nio:
            self.write_nio_config()
            self.nio = self.start_process(
                [str(self.nio_bin)], self.nio_log, cwd=self.run_dir
            )
        else:
            print(f"Using existing FujiNet NIO on {self.nio_host}:{self.nio_port}")
        wait_for_tcp(self.nio_host, self.nio_port)
        return None

    def amiberry_command(self, serial_device: str | None) -> list[str]:
        disk_args = ["-0", str(self.disk)]
        if self.disk.suffix.lower() == ".hdf":
            disk_args = ["-W", f"DH0:{self.disk}"]
        settings: list[str] = []
        raw_settings = os.environ.get("AMIBERRY_EXTRA_SETTINGS", "")
        if raw_settings:
            settings = [item for item in raw_settings.split(";") if item]
        config_args: list[str] = []
        uae_config = os.environ.get("AMIBERRY_UAE_CONFIG", "")
        if uae_config:
            config_args = ["--config", uae_config]
        serial_port = serial_device or f"tcp://{self.host}:{self.amiga_port}"
        command = [self.amiberry_bin, "--log", *config_args, "-G", "-w", "-1",
                   "-r", str(self.rom_dir / "kickstart.rom"), *disk_args,
                   "-s", f"serial_port={serial_port}",
                   "-s", "serial_hardware_ctsrts=false",
                   "-s", "serial_status=false",
                   "-s", "serial_direct=true",
                   "-s", f"cpu_type={os.environ.get('AMIBERRY_CPU_TYPE', '68000')}",
                   "-s", "cpu_compatible=true"]
        extra_floppy = os.environ.get("AMIBERRY_EXTRA_FLOPPY_0", "")
        if extra_floppy:
            command.extend(["-0", extra_floppy])
        for setting in settings:
            command.extend(["-s", setting])
        return command

    def start_amiberry(self, serial_device: str | None) -> None:
        shutil.copy2(self.kickstart, self.rom_dir / "kickstart.rom")
        if self.disk.suffix.lower() == ".hdf":
            shutil.copy2(self.fast_file_system, self.rom_dir / "FastFileSystem")
        print(f"Starting Amiberry with {self.disk}")
        self.amiberry = self.start_process(self.amiberry_command(serial_device), self.amiberry_log)
        try:
            logged_socket = wait_for_logged_ipc_socket(self.amiberry_log)
            if logged_socket is None:
                raise FileNotFoundError("Amiberry IPC was not reported in its log")
            # The listening message belongs to the process just launched and
            # is a stronger identity check than sending PING to a shared
            # well-known socket. Some Amiberry releases also leave PING
            # replies unterminated, which made discovery discard a live
            # endpoint and forced integration tests to wait for timeout.
            deadline = time.monotonic() + 2
            while not logged_socket.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            if not logged_socket.exists():
                raise FileNotFoundError(f"Amiberry IPC socket was not created: {logged_socket}")
            self.ipc_socket = logged_socket
            (self.run_dir / "amiberry.sock.path").write_text(
                str(self.ipc_socket) + "\n", encoding="utf-8"
            )
            print(f"Amiberry IPC socket: {self.ipc_socket}")
            if os.environ.get("AMIGA_E2E_BEGINIO_TRACE") == "1":
                # Start before opening the serial bridge: that bridge releases
                # the guest startup sequence and its first device requests.
                ipc.request(self.ipc_socket, "DEBUG_ACTIVATE")
                self.debugger_controller = self.start_process(
                    [sys.executable, "-m", "amiga_emulator.beginio_trace",
                     "--socket", str(self.ipc_socket),
                     "--output-dir", str(self.run_dir)],
                    self.run_dir / "beginio-controller.log", cwd=ROOT,
                )
            elif os.environ.get("AMIGA_E2E_TASK_SNAPSHOT") == "1":
                self.debugger_controller = self.start_process(
                    [sys.executable, "-m", "amiga_emulator.task_snapshot",
                     "--socket", str(self.ipc_socket),
                     "--output-dir", str(self.run_dir)],
                    self.run_dir / "task-snapshot-controller.log", cwd=ROOT,
                )
        except (FileNotFoundError, OSError):
            # IPC is optional in Amiberry builds; serial testing must still work.
            pass
        if self.serial_mode == "tcp":
            # Connecting here is not a harmless readiness check: Amiberry
            # treats every TCP connection as a serial session, so the probe
            # can reset the guest before the real socat bridge is attached.
            wait_for_log_line(self.amiberry_log, "TCP: Listening")
            print("Bridging Amiberry TCP to FujiNet NIO TCP")
            bridge_args = ["-d", "-d"]
            if os.environ.get("SOCAT_HEXDUMP") == "1":
                bridge_args.extend(["-x", "-v"])
            self.bridge = self.start_process(
                ["socat", *bridge_args,
                 f"TCP:{self.host}:{self.amiga_port}",
                 f"TCP:{self.nio_host}:{self.nio_port}"],
                self.bridge_log,
            )

    def run(self) -> int:
        self.validate()
        serial_device = self.start_transport()
        self.start_amiberry(serial_device)
        try:
            if self.args.timeout:
                self.amiberry.wait(timeout=self.args.timeout)
            else:
                self.amiberry.wait()
        except subprocess.TimeoutExpired:
            pass
        print(f"Amiberry logs: {self.amiberry_log}")
        print(f"FujiNet NIO logs: {self.nio_log}")
        print(f"Bridge logs: {self.bridge_log}")
        return self.amiberry.returncode or 0

    def cleanup(self) -> None:
        terminate_process(self.debugger_controller)
        terminate_process(self.bridge)
        terminate_process(self.amiberry)
        terminate_process(self.nio)
        for path in (self.amiga_pty, self.nio_pty):
            path.unlink(missing_ok=True)
        for handle in self.log_handles:
            handle.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk", "--adf", dest="disk", help="Amiga ADF or HDF to boot")
    parser.add_argument("--timeout", type=float, default=0, help="Stop after seconds; 0 means interactive")
    parser.add_argument("--pty", action="store_true", help="Use PTYs and the FujiNet RS232 profile")
    parser.add_argument("--tcp", action="store_true", help="Use Amiberry TCP serial mode (default)")
    parser.add_argument("--nio-port", type=int, help="FujiNet NIO TCP port")
    parser.add_argument("--amiga-port", type=int, help="Amiberry TCP serial port")
    parser.add_argument("--external-nio", action="store_true", help="Use an already-running FujiNet NIO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Convert SIGTERM to SystemExit so the finally block runs cleanup().
    # Python does not run finally blocks on bare SIGTERM by default.
    signal.signal(signal.SIGTERM, lambda _s, _f: sys.exit(130))

    args = parse_args(argv)
    if args.pty:
        os.environ["AMIBERRY_SERIAL_MODE"] = "pty"
    elif args.tcp:
        os.environ["AMIBERRY_SERIAL_MODE"] = "tcp"
    if args.nio_port is not None:
        os.environ["FUJINET_NIO_PORT"] = str(args.nio_port)
    if args.amiga_port is not None:
        os.environ["AMIBERRY_PORT"] = str(args.amiga_port)
    runner = AmigaRunner(args)
    try:
        return runner.run()
    except KeyboardInterrupt:
        return 130
    finally:
        runner.cleanup()


if __name__ == "__main__":
    sys.exit(main())
