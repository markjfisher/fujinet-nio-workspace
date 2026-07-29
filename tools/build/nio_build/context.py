from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


def workspace_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def load_shell_env(root: Path) -> dict[str, str]:
    env_script = root / "scripts" / "env.sh"
    cmd = ["bash", "-lc", 'source "$1" >/dev/null && env -0', "_", str(env_script)]
    proc = subprocess.run(cmd, cwd=root, check=True, stdout=subprocess.PIPE)
    env: dict[str, str] = {}
    for item in proc.stdout.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        env[key.decode()] = value.decode(errors="surrogateescape")
    return env


@dataclass
class BuildContext:
    root: Path
    env: dict[str, str]

    @classmethod
    def create(cls) -> "BuildContext":
        root = workspace_dir()
        env = os.environ.copy()
        env.update(load_shell_env(root))
        return cls(root=root, env=env)

    def path(self, name: str) -> Path:
        return Path(self.env[name])

    @property
    def build_dir(self) -> Path:
        return self.path("NIO_BUILD_DIR")

    @property
    def log_dir(self) -> Path:
        return self.path("NIO_LOG_DIR")

    @property
    def image_dir(self) -> Path:
        return self.path("NIO_IMAGE_DIR")

