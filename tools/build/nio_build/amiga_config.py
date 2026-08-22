"""Named Amiberry Workbench profiles."""

from __future__ import annotations

import json
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


def _load_local_amiga_env(root: Path) -> dict[str, str]:
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
            result[key.strip()] = value.strip()
    return result


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


def resolve_fast_file_system(
    manifest: dict[str, Any],
    root: Path,
    environment: dict[str, str] | None = None,
) -> str | None:
    """Return the host FastFileSystem path for a built Amiga environment."""
    recorded = manifest.get("fast_file_system")
    if recorded and Path(recorded).is_file():
        return str(Path(recorded).resolve())

    base_hdf = manifest.get("base_hdf")
    if base_hdf:
        sibling = Path(base_hdf).parent / "FastFileSystem"
        if sibling.is_file():
            return str(sibling.resolve())

    local_env = {**_load_local_amiga_env(root), **(environment or {})}
    expanded = local_env.get("AMIGA_WB32_EXPANDED", "")
    if expanded:
        for rel in ("L/FastFileSystem", "FastFileSystem"):
            candidate = Path(expanded).expanduser() / rel
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def _load_env_manifest(root: Path, env_id: str, machine_id: str | None) -> dict[str, Any]:
    """Load build/amiga-envs/<env_id>[/<machine_id>]/manifest.json."""
    envs_root = root / "build" / "amiga-envs"
    if machine_id:
        machine_path = envs_root / env_id / machine_id / "manifest.json"
        agnostic_path = envs_root / env_id / "manifest.json"
        if machine_path.is_file():
            manifest_path = machine_path
        elif agnostic_path.is_file():
            manifest_path = agnostic_path
        else:
            raise SystemExit(
                f"AmigaOS environment '{env_id}/{machine_id}' has not been built.\n"
                f"Run: scripts/amiga-env build {env_id} --machine {machine_id}"
            )
    else:
        manifest_path = envs_root / env_id / "manifest.json"
        if not manifest_path.is_file():
            raise SystemExit(
                f"AmigaOS environment '{env_id}' has not been built.\n"
                f"Run: scripts/amiga-env build {env_id}"
            )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _load_machine_profile(root: Path, machine_id: str) -> dict[str, Any]:
    """Load configs/amiga/machines/<machine_id>.yaml."""
    machine_path = root / "configs" / "amiga" / "machines" / f"{machine_id}.yaml"
    if not machine_path.is_file():
        raise SystemExit(f"Machine profile not found: {machine_path}")
    with machine_path.open("r", encoding="utf-8") as fh:
        profile = yaml.safe_load(fh) or {}
    uae_config = profile.get("uae_config", "")
    if uae_config:
        resolved = (root / "configs" / "amiga" / uae_config).resolve()
        profile["uae_config"] = str(resolved)
    return profile


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
    # Merge local/amiga.env so workbenches.yaml can reference variables like
    # ${AMIGA_WB32_KICKSTART} even when build.sh does not source env.sh first.
    local_env = _load_local_amiga_env(root)
    environment = {**local_env, **(environment or {})}

    # Resolve environment + machine references to a concrete disk and kickstart.
    env_id: str | None = result.pop("environment", None)
    machine_id: str | None = result.pop("machine", None)
    if env_id:
        manifest = _load_env_manifest(root, env_id, machine_id)
        result.setdefault("harddrive", manifest["base_hdf"])
        result.setdefault("kickstart", manifest["kickstart"])
        if manifest.get("rom_key"):
            result.setdefault("rom_key", manifest["rom_key"])
        result["_env_id"] = env_id
        result["_machine_id"] = machine_id
    if machine_id and not env_id:
        # machine without environment: just apply hardware settings
        machine_profile = _load_machine_profile(root, machine_id)
        result.setdefault("uae_config", machine_profile.get("uae_config", ""))
        if "settings" not in result:
            result["settings"] = machine_profile.get("settings", {})
        result["_machine_id"] = machine_id
    elif machine_id and env_id:
        machine_profile = _load_machine_profile(root, machine_id)
        result.setdefault("uae_config", machine_profile.get("uae_config", ""))
        if "settings" not in result:
            result["settings"] = machine_profile.get("settings", {})

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
