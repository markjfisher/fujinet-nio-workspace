from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nio_build import cli
from nio_build.context import BuildContext
from nio_build.runner import Runner
from nio_build.tasks import Build, build_tasks


class RP2350TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bridge = self.root / "custom-firmware" / "bridges" / "rp2350-zorro"
        self.bridge.mkdir(parents=True)
        self.ctx = BuildContext(self.root, {
            "FUJINET_NIO": str(self.root / "custom-firmware"),
            "NIO_LOG_DIR": str(self.root / "logs"),
            "NIO_IMAGE_DIR": str(self.root / "images"),
            "PATH": "",
        })
        self.build = Build(self.ctx)
        self.build.runner = Mock(spec=Runner)
        self.tasks = build_tasks(self.build)

    def commands(self):
        return [call.args[1] for call in self.build.runner.run.call_args_list]

    def test_host_bootstraps_and_tests_both_presets_without_sdk_or_arm(self):
        self.ctx.env["PICO_SDK_PATH"] = "/missing/sdk"
        self.tasks["rp2350-pio-tests"].action(self.build)
        self.assertEqual(self.commands(), [
            ["python3", "scripts/bootstrap.py", "--mode", "host"],
            ["cmake", "--preset", "host"],
            ["cmake", "--build", "--preset", "host"],
            ["ctest", "--preset", "host"],
            ["cmake", "--preset", "host-release"],
            ["cmake", "--build", "--preset", "host-release"],
            ["ctest", "--preset", "host-release"],
        ])
        for call in self.build.runner.run.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": self.bridge})

    def test_firmware_uses_workspace_toolchain_and_only_firmware_preset(self):
        compiler = self.root / "build/toolchains/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin"
        compiler.mkdir(parents=True)
        (compiler / "arm-none-eabi-gcc").touch()
        (compiler / "arm-none-eabi-gcc").chmod(0o755)
        with redirect_stdout(StringIO()):
            self.tasks["rp2350-firmware"].action(self.build)
        self.assertEqual(self.commands(), [
            ["python3", "scripts/bootstrap.py", "--mode", "firmware"],
            ["cmake", "--preset", "firmware"],
            ["cmake", "--build", "--preset", "firmware"],
        ])
        for call in self.build.runner.run.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": self.bridge, "extra_env": {"PICO_TOOLCHAIN_PATH": str(compiler)}})
        self.assertNotIn("PICO_TOOLCHAIN_PATH", self.ctx.env)

    def test_generator_build_uses_own_cache_and_never_loads_hardware(self):
        compiler = self.root / "generator-compiler" / "arm-none-eabi-gcc"
        compiler.parent.mkdir()
        compiler.touch()
        compiler.chmod(0o755)
        cache = self.bridge / "build/stimulus-rp2040/CMakeCache.txt"
        cache.parent.mkdir(parents=True)
        cache.write_text(f"CMAKE_C_COMPILER:FILEPATH={compiler}\n")
        with redirect_stdout(StringIO()):
            self.tasks["rp2040-stimulus"].action(self.build)
        self.assertEqual(self.commands(), [
            ["python3", "scripts/bootstrap.py", "--mode", "stimulus"],
            ["cmake", "--preset", "stimulus-rp2040"],
            ["cmake", "--build", "--preset", "stimulus-rp2040"],
        ])
        self.assertTrue(all(call.kwargs == {"cwd": self.bridge, "extra_env": {}}
                            for call in self.build.runner.run.call_args_list))

    def test_generator_explain_is_discoverable_and_does_not_build(self):
        with patch.object(BuildContext, "create", return_value=self.ctx), patch.object(Runner, "run") as run:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(["--list"]), 0)
                self.assertEqual(cli.main(["--explain", "rp2040-stimulus"]), 0)
            self.assertIn("rp2040-stimulus", output.getvalue())
            self.assertIn("PICO_TOOLCHAIN_PATH", output.getvalue())
            self.assertIn("feasibility_stimulus", output.getvalue())
            run.assert_not_called()

    def test_explicit_toolchain_and_sdk_are_preserved(self):
        compiler = self.root / "chosen-compiler" / "bin"
        compiler.mkdir(parents=True)
        (compiler / "arm-none-eabi-gcc").touch()
        (compiler / "arm-none-eabi-gcc").chmod(0o755)
        self.ctx.env.update(PICO_TOOLCHAIN_PATH=str(compiler.parent), PICO_SDK_PATH="/chosen/sdk")
        with patch("nio_build.tasks.shutil.which") as which, redirect_stdout(StringIO()):
            self.build.rp2350_firmware()
        which.assert_not_called()
        self.assertEqual(self.ctx.env["PICO_SDK_PATH"], "/chosen/sdk")
        for call in self.build.runner.run.call_args_list:
            self.assertEqual(call.kwargs["extra_env"], {})

    def test_path_compiler_wins_over_local_fallback(self):
        local = self.root / "build/toolchains/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin"
        local.mkdir(parents=True)
        (local / "arm-none-eabi-gcc").touch()
        (local / "arm-none-eabi-gcc").chmod(0o755)
        with patch("nio_build.tasks.shutil.which", return_value="/chosen/arm-none-eabi-gcc") as which, redirect_stdout(StringIO()):
            self.build.rp2350_firmware()
        which.assert_called_once_with("arm-none-eabi-gcc", path="")
        self.assertTrue(all(call.kwargs["extra_env"] == {} for call in self.build.runner.run.call_args_list))

    def test_missing_compiler_fails_before_bootstrap(self):
        with self.assertRaisesRegex(SystemExit, "PICO_TOOLCHAIN_PATH"):
            self.build.rp2350_firmware()
        self.build.runner.run.assert_not_called()

    def test_invalid_explicit_and_nonexecutable_local_compilers_fail(self):
        self.ctx.env["PICO_TOOLCHAIN_PATH"] = str(self.root / "missing")
        with self.assertRaisesRegex(SystemExit, "No executable"):
            self.build.rp2350_firmware()
        del self.ctx.env["PICO_TOOLCHAIN_PATH"]
        local = self.root / "build/toolchains/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin"
        local.mkdir(parents=True)
        (local / "arm-none-eabi-gcc").touch()
        with self.assertRaisesRegex(SystemExit, "PICO_TOOLCHAIN_PATH"):
            self.build.rp2350_firmware()
        self.build.runner.run.assert_not_called()

    def test_existing_cmake_compiler_works_without_environment_override(self):
        compiler = self.root / "cached-compiler" / "arm-none-eabi-gcc"
        compiler.parent.mkdir()
        compiler.touch()
        compiler.chmod(0o755)
        cache = self.bridge / "build/firmware/CMakeCache.txt"
        cache.parent.mkdir(parents=True)
        cache.write_text(f"CMAKE_C_COMPILER:FILEPATH={compiler}\n")
        with redirect_stdout(StringIO()):
            self.build.rp2350_firmware()
        self.assertTrue(all(call.kwargs["extra_env"] == {} for call in self.build.runner.run.call_args_list))

    def test_combined_workflow_stops_on_either_test_failure(self):
        for preset, count in (("host", 4), ("host-release", 7)):
            with self.subTest(preset=preset):
                self.build.runner.run.reset_mock()
                def fail_test(name, argv, **kwargs):
                    if argv == ["ctest", "--preset", preset]:
                        raise SystemExit(8)
                self.build.runner.run.side_effect = fail_test
                with self.assertRaises(SystemExit) as result:
                    self.tasks["rp2350"].action(self.build)
                self.assertEqual(result.exception.code, 8)
                self.assertEqual(len(self.commands()), count)
                self.assertFalse(any("firmware" in command for command in self.commands()))

    def test_combined_workflow_reaches_firmware_after_both_tests(self):
        with patch("nio_build.tasks.shutil.which", return_value="/compiler"), redirect_stdout(StringIO()):
            self.tasks["rp2350"].action(self.build)
        commands = self.commands()
        self.assertEqual(len(commands), 10)
        self.assertEqual(commands[6], ["ctest", "--preset", "host-release"])
        self.assertEqual(commands[7], ["python3", "scripts/bootstrap.py", "--mode", "firmware"])
        self.assertEqual(commands[9], ["cmake", "--build", "--preset", "firmware"])

    def test_cli_lists_and_explains_targets_without_starting_builds(self):
        with patch.object(BuildContext, "create", return_value=self.ctx), patch.object(Runner, "run") as run:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(["--list"]), 0)
            for name in ("rp2350", "rp2350-pio-tests", "rp2350-firmware"):
                self.assertIn(name, {line.split()[0] for line in output.getvalue().splitlines() if line.strip()})
                self.assertFalse(self.tasks[name].hidden)
                help_output = StringIO()
                with redirect_stdout(help_output):
                    self.assertEqual(cli.main(["--explain", name]), 0)
                self.assertIn("PICO_TOOLCHAIN_PATH", help_output.getvalue())
                self.assertIn("bridge_capture.{elf,uf2}", help_output.getvalue())
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
