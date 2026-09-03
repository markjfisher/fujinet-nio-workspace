from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from amiga_emulator.ftp import (
    FtpConfig,
    build_put_script,
    compose_lftp_script,
    load_ftp_config,
    parse_files_arg,
    run_lftp,
    transfer_files,
    transfer_script,
)
from amiga_emulator.cli import build_parser, main as cli_main


RELEASE_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "configs"
    / "amiga"
    / "ftp"
    / "release.txt"
)


class FtpConfigTests(unittest.TestCase):
    def test_loads_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiga.env"
            path.write_text(
                "FTP_HOST=ftp.example.test\n"
                "FTP_USER=guest\n"
                "FTP_PASS=s3cret\n"
                "FTP_APP=/opt/lftp\n",
                encoding="utf-8",
            )
            config = load_ftp_config(path, environ={})
        self.assertEqual(config.host, "ftp.example.test")
        self.assertEqual(config.user, "guest")
        self.assertEqual(config.password, "s3cret")
        self.assertEqual(config.app, "/opt/lftp")

    def test_process_env_overrides_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiga.env"
            path.write_text(
                "FTP_HOST=from-file\nFTP_USER=file-user\nFTP_PASS=file-pass\n",
                encoding="utf-8",
            )
            config = load_ftp_config(
                path,
                environ={
                    "FTP_HOST": "from-env",
                    "FTP_USER": "env-user",
                    "FTP_PASS": "env-pass",
                    "FTP_APP": "custom-lftp",
                },
            )
        self.assertEqual(config.host, "from-env")
        self.assertEqual(config.user, "env-user")
        self.assertEqual(config.password, "env-pass")
        self.assertEqual(config.app, "custom-lftp")

    def test_missing_vars_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiga.env"
            path.write_text("FTP_HOST=only-host\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                load_ftp_config(path, environ={})
        self.assertIn("FTP_USER", str(caught.exception))
        self.assertIn("FTP_PASS", str(caught.exception))

    def test_defaults_ftp_app_to_lftp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiga.env"
            path.write_text(
                "FTP_HOST=h\nFTP_USER=u\nFTP_PASS=p\n",
                encoding="utf-8",
            )
            config = load_ftp_config(path, environ={})
        self.assertEqual(config.app, "lftp")


class FtpScriptTests(unittest.TestCase):
    def test_parse_files_arg(self) -> None:
        files = parse_files_arg("/tmp/a,/tmp/b , /tmp/c")
        self.assertEqual(files, [Path("/tmp/a"), Path("/tmp/b"), Path("/tmp/c")])

    def test_build_put_script(self) -> None:
        script = build_put_script(
            [Path("/build/fapp"), Path("/build/clock")],
            "/dev/NIO/C/",
        )
        self.assertIn("put /build/fapp -o /dev/NIO/C/fapp", script)
        self.assertIn("put /build/clock -o /dev/NIO/C/clock", script)
        self.assertTrue(script.strip().endswith("bye"))

    def test_compose_prepends_open_and_keeps_body(self) -> None:
        config = FtpConfig(host="192.0.2.10", user="ami", password="secret", app="lftp")
        composed = compose_lftp_script(
            config,
            "put local.bin -o /remote/local.bin\nbye\n",
        )
        self.assertTrue(composed.startswith("open -u ami,secret 192.0.2.10\n"))
        self.assertIn("put local.bin -o /remote/local.bin", composed)
        self.assertIn("bye", composed)

    def test_compose_does_not_duplicate_open(self) -> None:
        config = FtpConfig(host="192.0.2.10", user="ami", password="secret", app="lftp")
        composed = compose_lftp_script(
            config,
            "open already.example\nput x -o /x\nbye\n",
        )
        self.assertNotIn("open -u", composed)
        self.assertIn("open already.example", composed)


class FtpRunTests(unittest.TestCase):
    def test_run_lftp_uses_dash_f_without_cli_open_options(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(cmd, cwd):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            return SimpleNamespace(returncode=0)

        config = FtpConfig(host="h", user="ami", password="secret", app="lftp")
        with tempfile.TemporaryDirectory() as directory:
            code = run_lftp(
                "open -u ami,secret h\nbye\n",
                config,
                cwd=Path(directory),
                runner=fake_run,
            )
        self.assertEqual(code, 0)
        cmd = captured["cmd"]
        self.assertEqual(cmd[0], "lftp")
        self.assertEqual(cmd[1], "-f")
        self.assertTrue(str(cmd[2]).endswith(".lftp"))
        self.assertNotIn("-u", cmd)

    def test_transfer_files_rejects_missing_sources(self) -> None:
        config = FtpConfig(host="h", user="u", password="p", app="lftp")
        with self.assertRaises(SystemExit) as caught:
            transfer_files(
                [Path("/no/such/file.bin")],
                "/dev/NIO/C/",
                config,
                cwd=Path("/tmp"),
                runner=lambda *a, **k: SimpleNamespace(returncode=0),
            )
        self.assertIn("not found", str(caught.exception))

    def test_transfer_script_reads_instructions(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(cmd, cwd):
            captured["script"] = Path(cmd[2]).read_text(encoding="utf-8")
            return SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "xfer.txt"
            script.write_text("put foo -o /remote/foo\nbye\n", encoding="utf-8")
            config = FtpConfig(host="host.test", user="u", password="p", app="lftp")
            code = transfer_script(
                script, config, cwd=Path(directory), runner=fake_run
            )
        self.assertEqual(code, 0)
        self.assertIn("open -u u,p host.test", captured["script"])
        self.assertIn("put foo -o /remote/foo", captured["script"])

    def test_dry_run_does_not_invoke_lftp(self) -> None:
        called = []

        def fake_run(*args, **kwargs):
            called.append((args, kwargs))
            return SimpleNamespace(returncode=99)

        config = FtpConfig(host="h", user="u", password="p", app="lftp")
        with tempfile.TemporaryDirectory() as directory:
            code = run_lftp(
                "open -u u,p h\nbye\n",
                config,
                cwd=Path(directory),
                runner=fake_run,
                dry_run=True,
            )
        self.assertEqual(code, 0)
        self.assertEqual(called, [])

    def test_verbose_prints_invocation(self) -> None:
        config = FtpConfig(host="h", user="u", password="p", app="lftp")
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch(
            "amiga_emulator.ftp.sys.stderr", stderr
        ):
            run_lftp(
                "open -u u,p h\nbye\n",
                config,
                cwd=Path(directory),
                runner=lambda *a, **k: SimpleNamespace(returncode=0),
                verbose=True,
            )
        dumped = stderr.getvalue()
        self.assertIn("invoke: lftp -f ", dumped)
        self.assertIn("open -u u,p h", dumped)

    def test_quiet_by_default(self) -> None:
        config = FtpConfig(host="h", user="u", password="p", app="lftp")
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch(
            "amiga_emulator.ftp.sys.stderr", stderr
        ):
            run_lftp(
                "open -u u,p h\nbye\n",
                config,
                cwd=Path(directory),
                runner=lambda *a, **k: SimpleNamespace(returncode=0),
            )
        self.assertEqual(stderr.getvalue(), "")


class FtpCliTests(unittest.TestCase):
    def test_parser_accepts_script(self) -> None:
        args = build_parser().parse_args(
            ["ftp", "--script", "configs/amiga/ftp/release.txt"]
        )
        self.assertEqual(args.group, "ftp")
        self.assertEqual(args.script, Path("configs/amiga/ftp/release.txt"))

    def test_parser_accepts_files_and_target(self) -> None:
        args = build_parser().parse_args(
            ["ftp", "--files", "/a,/b", "--target-dir", "/dev/NIO/C/"]
        )
        self.assertEqual(args.files, "/a,/b")
        self.assertEqual(args.target_dir, "/dev/NIO/C/")

    def test_cli_files_mode_invokes_lftp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "fapp"
            src.write_bytes(b"app")
            env_file = root / "amiga.env"
            env_file.write_text(
                "FTP_HOST=192.0.2.8\nFTP_USER=guest\nFTP_PASS=pw\nFTP_APP=lftp\n",
                encoding="utf-8",
            )
            captured: dict[str, object] = {}

            def fake_run(cmd, cwd):
                captured["cmd"] = cmd
                captured["cwd"] = cwd
                captured["script"] = Path(cmd[2]).read_text(encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with patch("amiga_emulator.ftp.subprocess.run", fake_run), patch(
                "amiga_emulator.ftp.shutil.which", return_value="/usr/bin/lftp"
            ):
                code = cli_main(
                    [
                        "ftp",
                        "--env-file",
                        str(env_file),
                        "--files",
                        str(src),
                        "--target-dir",
                        "/dev/NIO/C/",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual(captured["cmd"][:2], ["lftp", "-f"])
        self.assertIn(f"put {src} -o /dev/NIO/C/fapp", captured["script"])
        self.assertIn("open -u guest,pw 192.0.2.8", captured["script"])


class ReleaseScriptTests(unittest.TestCase):
    def test_release_script_splits_devs_and_c(self) -> None:
        text = RELEASE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            "put repos/fujinet-nio-driver/build/amiga/fujinet-nio.device "
            "-o /dev/NIO/Devs/fujinet-nio.device",
            text,
        )
        self.assertIn(
            "put repos/fujinet-nio-driver/build/amiga/fujinet-disk.device "
            "-o /dev/NIO/Devs/fujinet-disk.device",
            text,
        )
        self.assertIn(
            "put repos/nio-core-apps/build/amiga/bin/fmount -o /dev/NIO/C/fmount",
            text,
        )
        self.assertNotIn("/dev/NIO/C/fujinet-nio.device", text)
        self.assertNotIn("/dev/NIO/Devs/fapp", text)
        self.assertTrue(text.strip().endswith("bye"))
