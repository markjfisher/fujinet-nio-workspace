from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "integration-tests" / "amiberry"
BUILD_DIR = ROOT / "build" / "amiga-e2e-tests"


def xdf_command(environment: dict[str, str]) -> list[str]:
    if shutil.which("xdftool", path=environment.get("PATH")):
        return ["xdftool"]
    if shutil.which("uvx", path=environment.get("PATH")):
        return ["uvx", "--from", "amitools", "xdftool"]
    raise RuntimeError("xdftool or uvx is required")


def load_workspace_env() -> dict[str, str]:
    command = ["bash", "-lc", 'source "$1" >/dev/null && env -0', "_", str(ROOT / "scripts/env.sh")]
    output = subprocess.check_output(command, cwd=ROOT)
    environment = os.environ.copy()
    for item in output.split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            environment[key.decode()] = value.decode(errors="replace")
    return environment


def load_cases() -> dict[str, dict]:
    with (SUITE / "tests.toml").open("rb") as stream:
        return {case["name"]: case for case in tomllib.load(stream)["test"]}


def build_nio_binary(environment: dict[str, str]) -> None:
    """Build the TCP NIO binary without coupling E2E setup to ctest.

    The workspace ``fujinet-tcp`` target also runs the NIO unit tests.  Those
    tests remain part of the normal validation, but a transient unit-test
    failure must not leave the already-buildable E2E harness unable to report
    its own result.
    """
    nio_root = ROOT / "repos" / "fujinet-nio"
    build_dir = nio_root / "build" / "fujibus-tcp-debug"
    binary = build_dir / "fujinet-nio"
    if not binary.is_file():
        subprocess.run(
            ["cmake", "--preset", "fujibus-tcp-debug"],
            cwd=nio_root,
            env=environment,
            check=True,
        )
    subprocess.run(
        ["cmake", "--build", "--preset", "fujibus-tcp-debug-build"],
        cwd=nio_root,
        env=environment,
        check=True,
    )


def pytest_addoption(parser):
    parser.addoption(
        "--run-amiga",
        action="store_true",
        default=False,
        help="run the Amiberry integration tests; otherwise skip them",
    )


@pytest.fixture(scope="session")
def amiga_environment(pytestconfig):
    if not pytestconfig.getoption("--run-amiga") and os.environ.get("AMIGA_E2E") != "1":
        pytest.skip("Amiberry tests disabled; use --run-amiga or AMIGA_E2E=1")

    environment = load_workspace_env()
    required = ("AMIBERRY_OS_ROOT", "AMIBERRY_WORKBENCH_ADF")
    missing = [name for name in required if not Path(environment.get(name, "")).is_file() and not Path(environment.get(name, "")).is_dir()]
    for command in ("amiberry", "socat"):
        if shutil.which(command, path=environment.get("PATH")) is None:
            missing.append(command)
    if not shutil.which("xdftool", path=environment.get("PATH")) and not shutil.which("uvx", path=environment.get("PATH")):
        missing.append("xdftool or uvx")
    if missing:
        pytest.skip("Amiga E2E prerequisites unavailable: " + ", ".join(missing))

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(ROOT / "scripts/build.sh"), "lib-amiga", "apps-amiga", "core-apps-amiga"],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    build_nio_binary(environment)
    return environment


@pytest.fixture(scope="session")
def amiga_cases():
    return load_cases()


@pytest.fixture()
def run_amiga_case(amiga_environment, amiga_cases):
    def run(name: str) -> dict[str, str]:
        case = amiga_cases[name]
        app_dir = ROOT / "repos" / ("nio-apps" if case["project"] == "apps" else "nio-core-apps") / "build" / "amiga" / "bin"
        app = app_dir / case["app"]
        if not app.is_file():
            raise AssertionError(f"Amiga test application was not built: {app}")

        run_dir = BUILD_DIR / name
        run_dir.mkdir(parents=True, exist_ok=True)
        image = run_dir / f"amiga-{name}.hdf"
        startup = SUITE / case["startup"]
        command = [
            str(ROOT / "scripts/build-amiga-test-disk"),
            "--os-root", amiga_environment["AMIBERRY_OS_ROOT"],
            "--boot-adf", amiga_environment["AMIBERRY_WORKBENCH_ADF"],
            "--app", app,
            "--app-name", case["app"],
            "--extra-app-dir", ROOT / "repos/nio-core-apps/build/amiga/bin",
            "--startup-script", startup,
            "--no-workbench",
            "--output", image,
        ]
        subprocess.run(command, cwd=ROOT, env=amiga_environment, check=True)

        test_env = amiga_environment.copy()
        test_env["AMIGA_RUN_DIR"] = str(run_dir)
        # Keep test cases isolated from a manually started NIO or another
        # test process.  The runner will bridge Amiberry to this port.
        case_index = list(amiga_cases).index(name)
        test_env["FUJINET_NIO_PORT"] = str(65510 + case_index)
        test_env["AMIBERRY_PORT"] = str(23470 + case_index)
        runner = subprocess.Popen(
            [str(ROOT / "scripts/run-amiberry-nio"), "--tcp", "--disk", str(image),
             "--timeout", os.environ.get("AMIGA_E2E_TIMEOUT", "20")],
            cwd=ROOT,
            env=test_env,
        )
        quit_sent = False
        try:
            socket_file = run_dir / "amiberry.sock.path"
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not socket_file.is_file():
                if runner.poll() is not None:
                    break
                time.sleep(0.1)
            if socket_file.is_file():
                # Wait for the guest's FujiBus activity to settle.  The test
                # startup sequence types each result file to the CLI, so the
                # framebuffer now contains useful evidence without loading
                # Workbench or imposing a long fixed delay.
                nio_log = run_dir / "fujinet-nio.log"
                activity_deadline = time.monotonic() + 15
                saw_activity = False
                previous = ""
                quiet_since = None
                while time.monotonic() < activity_deadline:
                    current = nio_log.read_text(encoding="utf-8", errors="replace") if nio_log.is_file() else ""
                    if "fujibus: receive:" in current:
                        saw_activity = True
                        if current == previous:
                            quiet_since = quiet_since or time.monotonic()
                            if time.monotonic() - quiet_since >= float(os.environ.get("AMIGA_E2E_SCREENSHOT_QUIET", "0.5")):
                                break
                        else:
                            quiet_since = None
                    previous = current
                    time.sleep(0.1)
                if not saw_activity:
                    raise AssertionError("Amiga guest produced no FujiBus activity before screenshot")
                time.sleep(float(os.environ.get("AMIGA_E2E_SCREENSHOT_DELAY", "1")))
                screenshot = run_dir / "amiberry-screen.png"
                subprocess.run(
                    [str(ROOT / "scripts/amiberry-ipc"), "--socket",
                     socket_file.read_text(encoding="utf-8").strip(),
                     "SCREENSHOT", str(screenshot)],
                    cwd=ROOT,
                    env=test_env,
                    check=False,
                )
                # End the emulator immediately after evidence capture rather
                # than waiting for the safety timeout.
                quit_result = subprocess.run(
                    [str(ROOT / "scripts/amiberry-ipc"), "--socket",
                     socket_file.read_text(encoding="utf-8").strip(), "QUIT"],
                    cwd=ROOT,
                    env=test_env,
                    check=False,
                )
                quit_sent = quit_result.returncode == 0
            return_code = runner.wait()
            # Amiberry exits with 250 when deliberately stopped through its
            # QUIT IPC command.  Other non-zero exits remain failures.
            if return_code and not (quit_sent and return_code == 250):
                raise subprocess.CalledProcessError(return_code, runner.args)
        finally:
            if runner.poll() is None:
                runner.terminate()
                runner.wait(timeout=5)

        results: dict[str, str] = {}
        with tempfile.TemporaryDirectory(prefix="amiga-results-") as result_dir:
            for result_name in case["results"]:
                destination = Path(result_dir) / result_name.replace("/", "_")
                subprocess.run(
                    [*xdf_command(test_env), str(image), "read", result_name, str(destination)],
                    cwd=ROOT,
                    env=test_env,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                results[result_name] = destination.read_text(encoding="latin-1")
        return results

    return run
