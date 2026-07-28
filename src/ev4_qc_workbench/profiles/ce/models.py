from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CEConnectionResult:
    ok: bool
    repository_path: Path
    code: str
    reason: str
    observed_commit: str | None = None
    required_commit: str | None = None
    child_pid: int | None = None
    public_module_origin: str | None = None
    implementation_module_origin: str | None = None
    exporter_id: str | None = None
    exporter_version: str | None = None


@dataclass(frozen=True)
class CEExportResult:
    success: bool
    classification: str
    reason: str
    next_action: str
    attempt_path: Path | None
    output_path: Path | None
    child_pid: int | None
    cli_exit_code: int | None
    handoff_allowed: bool
    authorization_valid: bool
    output_valid: bool
    observed_commit: str | None
    exporter_id: str | None
    official_result: dict[str, Any] | None
