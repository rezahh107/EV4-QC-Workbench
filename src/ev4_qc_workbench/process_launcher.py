from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .strict_json import StrictJSONError, load_file, write_json

PROTOCOL_VERSION = "1.0"
PROCESS_START_MECHANISM = "subprocess_exec_new_python_interpreter"
MAX_REQUEST_BYTES = 128 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 3600


@dataclass(frozen=True)
class ProcessOutcome:
    child_pid: int
    profile_payload: dict[str, Any]
    process_start_mechanism: str


class ProcessLaunchError(RuntimeError):
    def __init__(self, code: str, reason: str, child_pid: int | None = None):
        super().__init__(f"{code}: {reason}")
        self.code = code
        self.reason = reason
        self.child_pid = child_pid


def _child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _child_command(
    *,
    child_module: str,
    request_path: Path,
    result_path: Path,
    pycache_path: Path,
) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-X",
        f"pycache_prefix={pycache_path}",
        "-m",
        child_module,
        "--request",
        str(request_path),
        "--result",
        str(result_path),
    ]


def _validate_result(
    value: dict[str, Any], *, request_id: str, profile_id: str, operation: str
) -> ProcessOutcome:
    common = {
        "protocol_version",
        "request_id",
        "profile_id",
        "operation",
        "child_pid",
        "status",
        "process_start_mechanism",
    }
    if value.get("protocol_version") != PROTOCOL_VERSION:
        raise ProcessLaunchError("CHILD_RESULT_IDENTITY_MISMATCH", "protocol mismatch")
    if value.get("request_id") != request_id:
        raise ProcessLaunchError("CHILD_RESULT_IDENTITY_MISMATCH", "request identity mismatch")
    if value.get("profile_id") != profile_id:
        raise ProcessLaunchError("CHILD_RESULT_IDENTITY_MISMATCH", "Profile identity mismatch")
    if value.get("operation") != operation:
        raise ProcessLaunchError("CHILD_RESULT_IDENTITY_MISMATCH", "operation identity mismatch")
    child_pid = value.get("child_pid")
    if not isinstance(child_pid, int) or isinstance(child_pid, bool) or child_pid <= 0:
        raise ProcessLaunchError("CHILD_RESULT_SCHEMA_INVALID", "child PID is invalid")
    if value.get("process_start_mechanism") != PROCESS_START_MECHANISM:
        raise ProcessLaunchError(
            "CHILD_RESULT_IDENTITY_MISMATCH",
            "process-start mechanism mismatch",
            child_pid,
        )
    status = value.get("status")
    if status == "error":
        if set(value) != common | {"error_code", "error_reason"}:
            raise ProcessLaunchError("CHILD_RESULT_SCHEMA_INVALID", "child error is malformed", child_pid)
        code = value.get("error_code")
        reason = value.get("error_reason")
        if not isinstance(code, str) or not code or not isinstance(reason, str) or not reason:
            raise ProcessLaunchError("CHILD_RESULT_SCHEMA_INVALID", "child error fields are invalid", child_pid)
        raise ProcessLaunchError(code, reason, child_pid)
    if status != "completed" or set(value) != common | {"profile_payload"}:
        raise ProcessLaunchError("CHILD_RESULT_SCHEMA_INVALID", "child result is malformed", child_pid)
    payload = value.get("profile_payload")
    if not isinstance(payload, dict):
        raise ProcessLaunchError("CHILD_RESULT_SCHEMA_INVALID", "Profile payload must be an object", child_pid)
    return ProcessOutcome(child_pid, payload, PROCESS_START_MECHANISM)


def launch_profile_operation(
    *,
    child_module: str,
    profile_id: str,
    operation: str,
    profile_payload: dict[str, Any],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> ProcessOutcome:
    if not child_module.startswith(f"ev4_qc_workbench.profiles.{profile_id}."):
        raise ProcessLaunchError("PROFILE_CHILD_INVALID", "Profile child module is not code-owned")
    request_id = uuid.uuid4().hex
    request = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "profile_id": profile_id,
        "operation": operation,
        "profile_payload": profile_payload,
    }
    with tempfile.TemporaryDirectory(prefix=f"ev4-qc-{profile_id}-") as temporary:
        folder = Path(temporary)
        request_path = folder / "request.json"
        result_path = folder / "result.json"
        pycache_path = folder / "pycache"
        pycache_path.mkdir()
        write_json(request_path, request, max_bytes=MAX_REQUEST_BYTES)
        environment = _child_environment()
        command = _child_command(
            child_module=child_module,
            request_path=request_path,
            result_path=result_path,
            pycache_path=pycache_path,
        )
        try:
            completed = subprocess.run(
                command,
                cwd=folder,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProcessLaunchError("CHILD_TIMEOUT", "Profile child timed out") from exc
        except OSError as exc:
            raise ProcessLaunchError("CHILD_STARTUP_FAILED", type(exc).__name__) from exc
        if completed.returncode != 0:
            raise ProcessLaunchError(
                "CHILD_ABNORMAL_EXIT",
                f"Profile child exited with code {completed.returncode}",
            )
        try:
            result = load_file(result_path, max_bytes=MAX_RESULT_BYTES)
        except StrictJSONError as exc:
            raise ProcessLaunchError("CHILD_RESULT_MALFORMED", str(exc)) from exc
        return _validate_result(
            result,
            request_id=request_id,
            profile_id=profile_id,
            operation=operation,
        )
