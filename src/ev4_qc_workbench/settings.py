from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .strict_json import StrictJSONError, load_file, write_json

SCHEMA_VERSION = "1.0"


def settings_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "EV4QCWorkbench" / "settings.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "profiles": {}}
    try:
        value = load_file(path, max_bytes=128 * 1024)
    except StrictJSONError:
        return {"schema_version": SCHEMA_VERSION, "profiles": {}}
    if value.get("schema_version") != SCHEMA_VERSION or not isinstance(value.get("profiles"), dict):
        return {"schema_version": SCHEMA_VERSION, "profiles": {}}
    return value


def profile_settings(profile_id: str) -> dict[str, Any]:
    value = load_settings().get("profiles", {}).get(profile_id, {})
    return dict(value) if isinstance(value, dict) else {}


def update_profile_settings(profile_id: str, **fields: str) -> None:
    value = load_settings()
    profiles = value.setdefault("profiles", {})
    current = profiles.get(profile_id)
    if not isinstance(current, dict):
        current = {}
    for key, item in fields.items():
        if item:
            current[key] = item
    profiles[profile_id] = current
    write_json(settings_path(), value, max_bytes=128 * 1024)
