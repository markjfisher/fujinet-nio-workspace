from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from .context import BuildContext


def _git_ref_line(name: str, path: Path) -> str:
    if not (path / ".git").exists():
        return f"{name}=missing"
    try:
        ref = subprocess.check_output(["git", "-C", str(path), "rev-parse", "--short", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError:
        ref = "unborn"
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(path), "symbolic-ref", "--quiet", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        branch = "detached"
    dirty = " dirty" if subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True) else ""
    return f"{name}={ref} branch={branch}{dirty}"


def _default_qemu_image(ctx: BuildContext) -> str:
    if ctx.env.get("OUTPUT_IMAGE"):
        return ctx.env["OUTPUT_IMAGE"]
    qemu_manifest = ctx.root / "manifests" / "disks" / "qemu-msdos-apps.yaml"
    qemu_repo_manifest = ctx.path("FUJINET_QEMU_MSDOS") / "manifests" / "apps.yaml"
    if ctx.env.get("APPS_MANIFEST") or qemu_manifest.exists() or qemu_repo_manifest.exists():
        return str(ctx.path("FUJINET_QEMU_MSDOS") / "build" / "msdos-nio-apps.qcow2")
    return str(ctx.path("FUJINET_QEMU_MSDOS") / "build" / "msdos-nio.qcow2")


def default_msdos_apps_manifest(ctx: BuildContext) -> str:
    if ctx.env.get("APPS_MANIFEST"):
        return ctx.env["APPS_MANIFEST"]
    path = ctx.root / "manifests" / "disks" / "msdos-apps.yaml"
    if path.exists():
        return str(path)
    repo_path = ctx.path("FUJINET_QEMU_MSDOS") / "manifests" / "apps.yaml"
    if repo_path.exists():
        return str(repo_path)
    return str(ctx.path("FUJINET_QEMU_MSDOS") / "manifests" / "apps.example.yaml")


def default_qemu_msdos_apps_manifest(ctx: BuildContext) -> str:
    if ctx.env.get("APPS_MANIFEST"):
        return ctx.env["APPS_MANIFEST"]
    path = ctx.root / "manifests" / "disks" / "qemu-msdos-apps.yaml"
    if path.exists():
        return str(path)
    repo_path = ctx.path("FUJINET_QEMU_MSDOS") / "manifests" / "apps.yaml"
    if repo_path.exists():
        return str(repo_path)
    return str(ctx.path("FUJINET_QEMU_MSDOS") / "manifests" / "apps.example.yaml")


def default_msdos_boot_config_manifest(ctx: BuildContext) -> str:
    return ctx.env.get(
        "MSDOS_BOOT_CONFIG_MANIFEST",
        str(ctx.root / "manifests" / "disks" / "msdos-boot-config.yaml"),
    )


def write_manifest(ctx: BuildContext) -> None:
    ctx.build_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"built_at={datetime.now().astimezone().isoformat()}",
        f"workspace={ctx.root}",
    ]
    repos = [
        ("workspace", ctx.root),
        ("fujinet-nio", ctx.path("FUJINET_NIO")),
        ("fujinet-nio-lib", ctx.path("FUJINET_NIO_LIB")),
        ("nio-apps", ctx.path("NIO_APPS")),
        ("nio-core-apps", ctx.path("NIO_CORE_APPS")),
        ("nio-config", ctx.path("NIO_CONFIG")),
        ("fujinet-qemu-msdos", ctx.path("FUJINET_QEMU_MSDOS")),
        ("fujinet-nio-driver", ctx.path("FUJINET_NIO_DRIVER")),
        ("fn-rom", ctx.path("FN_ROM")),
        ("cc65-clib", ctx.path("CC65_CLIB")),
        ("bounce-world-client-nio", ctx.path("BOUNCE_WORLD_CLIENT_NIO")),
        ("fujinet-emulator-bridge", ctx.path("FUJINET_EMULATOR_BRIDGE")),
        ("AltirraSDL", ctx.root / "repos" / "AltirraSDL"),
    ]
    lines.extend(_git_ref_line(name, path) for name, path in repos)
    keys = [
        "FUJINET_NIO_TCP_DEBUG_BIN",
        "FUJINET_NIO_TCP_RELEASE_BIN",
        "FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN",
        "ALTIRRA_WORKSPACE_BIN",
        "NIO_APPS_MSDOS_BIN",
        "NIO_APPS_ATARI_BIN",
        "NIO_CORE_APPS_MSDOS_BIN",
        "NIO_CORE_APPS_ATARI_BIN",
        "NIO_CONFIG_MSDOS_BIN",
        "NIO_CONFIG_ATARI_BIN",
    ]
    lines.extend(f"{key.lower()}={ctx.env[key]}" for key in keys if key in ctx.env)
    lines.extend(
        [
            f"msdos_apps_manifest={default_msdos_apps_manifest(ctx)}",
            f"qemu_msdos_apps_manifest={default_qemu_msdos_apps_manifest(ctx)}",
            f"msdos_boot_config_manifest={default_msdos_boot_config_manifest(ctx)}",
            f"msdos_apps_image={ctx.image_dir / 'msdos-apps.img'}",
            f"msdos_boot_config_image={ctx.image_dir / 'msdos-boot-config.img'}",
            f"legacy_msdos_image={ctx.image_dir / 'nio-apps.img'}",
            f"legacy_manifest_apps_image={ctx.image_dir / 'msdos-nio-apps.img'}",
            f"bounce_world_msdos_image={ctx.image_dir / 'bwcn-msdos.img'}",
            f"qemu_image={_default_qemu_image(ctx)}",
        ]
    )
    out = ctx.build_dir / "manifest.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
