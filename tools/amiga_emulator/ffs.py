"""Resolve the host-side FastFileSystem Amiberry needs for hard-drive boots."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_local_amiga_env(root: Path) -> dict[str, str]:
    """Load local/amiga.env key=value pairs without shell evaluation."""
    env_file = root / "local" / "amiga.env"
    result: dict[str, str] = {}
    if not env_file.is_file():
        return result
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _try_load_env_manifest(
    root: Path, env_id: str, machine_id: str | None
) -> dict[str, Any] | None:
    envs_root = root / "build" / "amiga-envs"
    candidates: list[Path] = []
    if machine_id:
        candidates.append(envs_root / env_id / machine_id / "manifest.json")
    candidates.append(envs_root / env_id / "manifest.json")
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def _existing_file(*candidates: Path) -> str | None:
    for candidate in candidates:
        expanded = candidate.expanduser()
        if expanded.is_file():
            return str(expanded.resolve())
    return None


def resolve_fast_file_system(
    root: Path,
    environment: dict[str, str] | None = None,
    manifest: dict[str, Any] | None = None,
) -> str | None:
    """Return a host FastFileSystem path, or None if none can be found.

    Resolution order:
    1. AMIBERRY_FAST_FILE_SYSTEM when it points at an existing file
    2. ``fast_file_system`` / sibling of ``base_hdf`` from a built env manifest
    3. sibling of AMIGA_ENV_BASE_HDF
    4. AMIGA_WB32_EXPANDED/L/FastFileSystem (or FastFileSystem at the root)
    """
    merged = {**load_local_amiga_env(root), **dict(os.environ)}
    if environment:
        merged.update(environment)

    explicit = merged.get("AMIBERRY_FAST_FILE_SYSTEM", "")
    if explicit:
        found = _existing_file(Path(explicit))
        if found:
            return found

    if manifest is None:
        env_id = merged.get("AMIGA_ENV_ID", "")
        machine_id = merged.get("AMIGA_MACHINE_ID", "") or None
        if env_id:
            manifest = _try_load_env_manifest(root, env_id, machine_id)

    if manifest:
        recorded = manifest.get("fast_file_system")
        if recorded:
            found = _existing_file(Path(str(recorded)))
            if found:
                return found
        base_hdf = manifest.get("base_hdf")
        if base_hdf:
            found = _existing_file(Path(str(base_hdf)).parent / "FastFileSystem")
            if found:
                return found

    base_hdf = merged.get("AMIGA_ENV_BASE_HDF", "")
    if base_hdf:
        found = _existing_file(Path(base_hdf).parent / "FastFileSystem")
        if found:
            return found

    expanded = merged.get("AMIGA_WB32_EXPANDED", "")
    if expanded:
        base = Path(expanded)
        found = _existing_file(base / "L" / "FastFileSystem", base / "FastFileSystem")
        if found:
            return found
    return None
