from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

from .context import BuildContext


def log_name(name: str) -> str:
    return "".join("_" if ch in "/: " else ch for ch in name)


class Runner:
    def __init__(self, ctx: BuildContext):
        self.ctx = ctx
        self.ctx.log_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.image_dir.mkdir(parents=True, exist_ok=True)

    def require_dir(self, path: Path) -> None:
        if not path.is_dir():
            raise SystemExit(f"Missing directory: {path}\nRun: git submodule update --init --recursive")

    def run(
        self,
        name: str,
        argv: Sequence[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        extra_env: Mapping[str, str] | None = None,
    ) -> None:
        log = self.ctx.log_dir / f"{log_name(name)}.log"
        print(f"==> {name}")
        print(f"    log: {log}")
        env = self.ctx.env.copy()
        if extra_env:
            env.update(extra_env)
        with log.open("w", encoding="utf-8", errors="replace") as fh:
            proc = subprocess.Popen(
                [os.fspath(arg) for arg in argv],
                cwd=cwd or self.ctx.root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="")
                fh.write(line)
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(rc)

