"""Named Amiberry Workbench profiles."""

from __future__ import annotations

import os
import string
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - depends on host setup
    raise SystemExit(
        "Amiga Workbench profiles require PyYAML; install it with "
        "'python3 -m pip install PyYAML'"
    ) from exc


def _expand(value: Any, root: Path, environment: dict[str, str]) -> Any:
    if not isinstance(value, str):
        return value
    variables = dict(os.environ)
    variables.update(environment)
    expanded = os.path.expanduser(string.Template(value).safe_substitute(variables))
    path = Path(expanded)
    if not path.is_absolute():
        path = root / path
    return str(path)


def load_profile(path: Path, name: str, root: Path, environment: dict[str, str] | None = None) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    if not isinstance(document, dict):
        raise SystemExit(f"Amiga profile file must contain a mapping: {path}")

    profiles = document.get("profiles", {})
    if not isinstance(profiles, dict):
        raise SystemExit(f"Amiga profile 'profiles' must be a mapping: {path}")
    selected = name or str(document.get("default", "wb3.2"))
    profile = profiles.get(selected)
    if not isinstance(profile, dict):
        available = ", ".join(sorted(str(key) for key in profiles))
        raise SystemExit(f"Unknown Amiga Workbench profile '{selected}'; available: {available}")

    result = dict(profile)
    environment = environment or {}
    config_keys = [key for key in ("config_file", "uae_config") if key in result]
    if len(config_keys) > 1:
        raise SystemExit(
            f"Amiga profile must use only one of config_file/uae_config: {selected}"
        )
    if config_keys:
        result["uae_config"] = result.pop(config_keys[0])
    for key in ("disk", "harddrive", "kickstart", "rom_key",
                "fast_file_system", "uae_config"):
        if key in result:
            result[key] = _expand(result[key], root, environment)
    archive_keys = [key for key in ("install_archives", "install_archive") if key in result]
    if len(archive_keys) > 1:
        raise SystemExit(
            f"Amiga profile must use only one of install_archives/install_archive: {selected}"
        )
    if archive_keys:
        archives = result.pop(archive_keys[0])
        if not isinstance(archives, list):
            raise SystemExit(f"Amiga profile archive list must be a list: {selected}")
        result["install_archives"] = [
            _expand(archive, root, environment) for archive in archives
        ]
    settings = result.get("settings", {})
    if not isinstance(settings, dict):
        raise SystemExit(f"Amiga profile settings must be a mapping: {selected}")
    result["settings"] = {str(key): str(value).lower() if isinstance(value, bool) else str(value)
                           for key, value in settings.items()}
    result["name"] = selected
    return result
