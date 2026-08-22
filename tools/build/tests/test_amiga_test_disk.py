from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nio_build.context import BuildContext
from nio_build.tasks import Build


class RecordingRunner:
    def __init__(self, driver_root: Path) -> None:
        self.driver_root = driver_root
        self.calls: list[tuple[str, list[str], Path | None]] = []

    def require_dir(self, path: Path) -> None:
        if not path.is_dir():
            raise SystemExit(f"Missing directory: {path}")

    def run(self, name: str, argv, *, cwd=None, extra_env=None) -> None:
        command = [str(arg) for arg in argv]
        self.calls.append((name, command, cwd))
        if name == "amiga-nio-broker-native":
            build = self.driver_root / "build" / "amiga"
            build.mkdir(parents=True, exist_ok=True)
            (build / "fujinet-nio.device").write_bytes(b"nio")
            (build / "fujinet-load-resident").write_bytes(b"loader")
            (build / "fujinet-disk.device").write_bytes(b"disk")
            (build / "fujinet-mount").write_bytes(b"mount")


class AmigaTestDiskBootstrapTests(unittest.TestCase):
    def _prepare(self, tmp: Path, *, interactive: bool) -> tuple[Build, RecordingRunner]:
        driver_root = tmp / "driver"
        (driver_root / "amiga").mkdir(parents=True)
        core = tmp / "core-apps"
        core.mkdir()
        app = tmp / "wifitest"
        app.write_bytes(b"app")
        base_hdf = tmp / "base.hdf"
        base_hdf.write_bytes(b"hdf")
        env = {
            "FUJINET_NIO_DRIVER": str(driver_root),
            "NIO_CORE_APPS": str(core),
            "NIO_BUILD_DIR": str(tmp / "build"),
            "NIO_LOG_DIR": str(tmp / "logs"),
            "NIO_IMAGE_DIR": str(tmp / "images"),
            "AMIGA_ENV_BASE_HDF": str(base_hdf),
            "AMIGA_TEST_APP": "wifitest",
        }
        if interactive:
            env["AMIGA_TEST_INTERACTIVE"] = "1"
        ctx = BuildContext(root=tmp, env=env)
        build = Build(ctx)
        runner = RecordingRunner(driver_root)
        build.runner = runner

        def fake_app() -> tuple[str, Path]:
            return "wifitest", app

        build.amiga_test_app = fake_app  # type: ignore[method-assign]
        build.core_apps_amiga = lambda: None  # type: ignore[method-assign]
        return build, runner

    def _assert_broker_build_then_load_nio(
        self, runner: RecordingRunner, *, interactive: bool, with_driver: bool = False
    ) -> None:
        names = [name for name, _, _ in runner.calls]
        self.assertIn("amiga-nio-broker-native", names)
        self.assertIn("amiga-test-disk", names)
        self.assertLess(
            names.index("amiga-nio-broker-native"),
            names.index("amiga-test-disk"),
        )
        native_name, native_cmd, native_cwd = runner.calls[names.index("amiga-nio-broker-native")]
        self.assertEqual(native_cmd, ["make", "native"])
        self.assertEqual(native_cwd, runner.driver_root / "amiga")

        _, disk_cmd, _ = runner.calls[names.index("amiga-test-disk")]
        self.assertIn("--load-nio", disk_cmd)
        self.assertIn("--nio-device", disk_cmd)
        self.assertIn("--resident-loader", disk_cmd)
        self.assertNotIn("--startup-script", disk_cmd)
        if with_driver:
            self.assertIn("--load-driver", disk_cmd)
            self.assertLess(
                disk_cmd.index("--load-nio"),
                disk_cmd.index("--load-driver"),
            )
        else:
            self.assertNotIn("--load-driver", disk_cmd)
        if interactive:
            self.assertIn("--interactive", disk_cmd)
        else:
            self.assertNotIn("--interactive", disk_cmd)

        nio_device = runner.driver_root / "build" / "amiga" / "fujinet-nio.device"
        loader = runner.driver_root / "build" / "amiga" / "fujinet-load-resident"
        self.assertEqual(
            Path(disk_cmd[disk_cmd.index("--nio-device") + 1]),
            nio_device,
        )
        self.assertEqual(
            Path(disk_cmd[disk_cmd.index("--resident-loader") + 1]),
            loader,
        )

    def test_generated_amiga_test_disk_builds_broker_and_passes_load_nio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            build, runner = self._prepare(tmp, interactive=False)
            build.amiga_test_disk()
            self._assert_broker_build_then_load_nio(runner, interactive=False)

    def test_interactive_amiga_test_disk_builds_broker_and_passes_load_nio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            build, runner = self._prepare(tmp, interactive=True)
            build.amiga_test_disk()
            self._assert_broker_build_then_load_nio(runner, interactive=True)

    def test_with_driver_amiga_test_disk_passes_load_driver_and_load_nio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            build, runner = self._prepare(tmp, interactive=False)
            build.amiga_test_disk(with_driver=True)
            self._assert_broker_build_then_load_nio(
                runner, interactive=False, with_driver=True
            )
            _, disk_cmd, _ = runner.calls[
                [name for name, _, _ in runner.calls].index("amiga-test-disk")
            ]
            disk_device = runner.driver_root / "build" / "amiga" / "fujinet-disk.device"
            self.assertEqual(
                Path(disk_cmd[disk_cmd.index("--disk-device") + 1]),
                disk_device,
            )


if __name__ == "__main__":
    unittest.main()
