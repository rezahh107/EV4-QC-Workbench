from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.machinery
import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from ev4_qc_workbench.process_launcher import PROCESS_START_MECHANISM, PROTOCOL_VERSION
from ev4_qc_workbench.strict_json import StrictJSONError, load_file, loads_bytes, write_json

PROFILE_ID = "ce"
MAX_REQUEST_BYTES = 128 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024
LOCK_PATH = Path(__file__).with_name("ce-profile.lock.json")
PUBLIC_PATH = Path("validator/verified_project_gate_exporter.py")
IMPLEMENTATION_PATH = Path("validator/_verified_project_gate_exporter_impl.py")


class CEChildError(RuntimeError):
    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def _git(root: Path, *args: str, allowed: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as exc:
        raise CEChildError("CE_CHECKOUT_IDENTITY_INVALID", f"Git unavailable: {type(exc).__name__}") from exc
    if result.returncode not in allowed:
        raise CEChildError(
            "CE_CHECKOUT_IDENTITY_INVALID",
            result.stderr.strip() or f"git {' '.join(args)} failed",
        )
    return result


def _normalize_remote(remote: str) -> str | None:
    value = remote.strip().removesuffix("/").removesuffix(".git")
    prefixes = ("https://github.com/", "http://github.com/", "git@github.com:", "ssh://git@github.com/")
    for prefix in prefixes:
        if value.startswith(prefix):
            return value.removeprefix(prefix).strip("/")
    return None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _lock() -> dict[str, Any]:
    value = load_file(LOCK_PATH, max_bytes=64 * 1024)
    expected = {
        "schema_version",
        "profile_id",
        "repository",
        "required_commit",
        "acceptance_mode",
        "public_module",
        "public_entry_point",
        "public_script",
        "official_cli_options",
        "verified_exporter_id",
        "verified_exporter_version",
    }
    if set(value) != expected or value.get("profile_id") != PROFILE_ID:
        raise CEChildError("CE_PROFILE_LOCK_INVALID", "CE Profile Lock is malformed")
    return value


def _require_isolated_interpreter(root: Path | None = None) -> None:
    if sys.flags.isolated != 1:
        raise CEChildError("CE_IMPORT_BOUNDARY_INVALID", "CE Profile child is not running in Python isolated mode")
    prefix = sys.pycache_prefix
    if not isinstance(prefix, str) or not prefix:
        raise CEChildError("CE_IMPORT_BOUNDARY_INVALID", "CE Profile child has no private bytecode-cache prefix")
    if root is not None and _inside(Path(prefix), root):
        raise CEChildError("CE_IMPORT_BOUNDARY_INVALID", "CE bytecode cache must remain outside the selected CE checkout")


def _no_ce_modules_loaded() -> None:
    loaded = sorted(name for name in sys.modules if name == "validator" or name.startswith("validator."))
    if loaded:
        raise CEChildError("CE_IMPORT_BOUNDARY_INVALID", f"CE modules loaded before checkout verification: {loaded[0]}")


def _module_origin(module: Any) -> Path | None:
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str) or not origin:
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
    if not isinstance(origin, str) or not origin or origin in {"built-in", "frozen"}:
        return None
    try:
        return Path(origin).expanduser().resolve(strict=False)
    except OSError:
        return None


def _no_repo_modules_loaded(root: Path) -> None:
    for name, module in sorted(sys.modules.items()):
        origin = _module_origin(module)
        if origin is not None and _inside(origin, root):
            raise CEChildError(
                "CE_IMPORT_BOUNDARY_INVALID",
                f"Repository-local module loaded before CE checkout verification: {name}",
            )


def _untracked_or_ignored_paths(root: Path) -> list[str]:
    values: set[str] = set()
    commands = (
        ("ls-files", "--others", "--exclude-standard", "-z"),
        ("ls-files", "--others", "--ignored", "--exclude-standard", "-z"),
    )
    for command in commands:
        output = _git(root, *command).stdout
        values.update(item for item in output.split("\0") if item)
    return sorted(values)


def _import_capable_local_paths(root: Path) -> list[str]:
    suffixes = tuple(sorted(importlib.machinery.all_suffixes(), key=len, reverse=True))
    contaminated: list[str] = []
    for relative in _untracked_or_ignored_paths(root):
        path = root / relative
        name = path.name
        if name.endswith(suffixes):
            contaminated.append(relative)
            continue
        if path.is_symlink() and name.isidentifier():
            contaminated.append(relative)
    return contaminated


def _assert_import_contamination_absent(root: Path) -> None:
    contaminated = _import_capable_local_paths(root)
    if contaminated:
        raise CEChildError(
            "CE_CHECKOUT_IMPORT_CONTAMINATION",
            f"Untracked or ignored repository-local import material is forbidden: {contaminated[0]}",
        )


def _verify_checkout_identity(root: Path, lock: dict[str, Any]) -> tuple[str, str]:
    _require_isolated_interpreter(root)
    top = Path(_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != root:
        raise CEChildError("CE_CHECKOUT_IDENTITY_INVALID", "Selected path is not the CE repository root")
    remote = _normalize_remote(_git(root, "remote", "get-url", "origin").stdout)
    if remote != lock["repository"]:
        raise CEChildError("CE_CHECKOUT_IDENTITY_INVALID", "CE repository identity mismatch")
    commit = _git(root, "rev-parse", "HEAD").stdout.strip()
    if commit != lock["required_commit"]:
        raise CEChildError("CE_CHECKOUT_IDENTITY_INVALID", "CE checkout does not match the required commit")
    if _git(root, "diff", "--quiet", "HEAD", "--", allowed=(0, 1)).returncode != 0:
        raise CEChildError("CE_CHECKOUT_IDENTITY_INVALID", "CE tracked working tree differs from HEAD")
    if _git(root, "diff", "--cached", "--quiet", allowed=(0, 1)).returncode != 0:
        raise CEChildError("CE_CHECKOUT_IDENTITY_INVALID", "CE index contains staged tracked changes")
    _assert_import_contamination_absent(root)
    return remote, commit


def _verify_loaded_repo_modules(root: Path) -> int:
    checked = 0
    for name, module in sorted(sys.modules.items()):
        origin = _module_origin(module)
        if origin is None or not _inside(origin, root):
            continue
        if origin.is_symlink() or not origin.is_file():
            raise CEChildError("CE_MODULE_ORIGIN_MISMATCH", f"Repository-local module origin is not a regular file: {name}")
        relative = origin.relative_to(root.resolve()).as_posix()
        tracked = _git(root, "ls-files", "--error-unmatch", "--", relative, allowed=(0, 1))
        if tracked.returncode != 0:
            raise CEChildError("CE_MODULE_ORIGIN_MISMATCH", f"Repository-local execution origin is not tracked at HEAD: {relative}")
        expected_blob = _git(root, "rev-parse", f"HEAD:{relative}").stdout.strip()
        observed_blob = _git(root, "hash-object", "--no-filters", "--", str(origin)).stdout.strip()
        if observed_blob != expected_blob:
            raise CEChildError("CE_MODULE_ORIGIN_MISMATCH", f"Repository-local execution bytes differ from HEAD: {relative}")
        checked += 1
    return checked


def _recheck_before_execution(root: Path, lock: dict[str, Any]) -> None:
    _verify_checkout_identity(root, lock)
    _verify_loaded_repo_modules(root)


def _verify_and_import(root: Path) -> tuple[dict[str, Any], Any, Any, dict[str, Any]]:
    lock = _lock()
    _require_isolated_interpreter()
    _no_ce_modules_loaded()
    root = Path(root).expanduser().resolve(strict=True)
    remote, commit = _verify_checkout_identity(root, lock)
    _no_ce_modules_loaded()
    _no_repo_modules_loaded(root)
    for relative in (PUBLIC_PATH, IMPLEMENTATION_PATH):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise CEChildError("CE_PUBLIC_CLI_SURFACE_INVALID", f"Required public file is unavailable: {relative}")
    sys.path.insert(0, str(root))
    public = importlib.import_module(lock["public_module"])
    implementation = importlib.import_module("validator._verified_project_gate_exporter_impl")
    expected_public = (root / PUBLIC_PATH).resolve(strict=True)
    expected_impl = (root / IMPLEMENTATION_PATH).resolve(strict=True)
    observed_public = Path(public.__file__).resolve(strict=True)
    observed_impl = Path(implementation.__file__).resolve(strict=True)
    if observed_public != expected_public or observed_impl != expected_impl:
        raise CEChildError("CE_MODULE_ORIGIN_MISMATCH", "CE public module origin mismatch")
    if tuple(getattr(public, "OFFICIAL_CLI_OPTIONS", ())) != tuple(lock["official_cli_options"]):
        raise CEChildError("CE_PUBLIC_CLI_SURFACE_INVALID", "Official CLI options differ from Profile Lock")
    if getattr(public, "VERIFIED_EXPORTER_ID", None) != lock["verified_exporter_id"]:
        raise CEChildError("CE_PUBLIC_CLI_SURFACE_INVALID", "Exporter identity differs from Profile Lock")
    if getattr(public, "VERIFIED_EXPORTER_VERSION", None) != lock["verified_exporter_version"]:
        raise CEChildError("CE_PUBLIC_CLI_SURFACE_INVALID", "Exporter version differs from Profile Lock")
    main = getattr(public, lock["public_entry_point"], None)
    if not callable(main):
        raise CEChildError("CE_PUBLIC_CLI_SURFACE_INVALID", "Official public main is not callable")
    repo_local_module_count = _verify_loaded_repo_modules(root)
    _verify_checkout_identity(root, lock)
    identity = {
        "repository_identity": remote,
        "observed_commit": commit,
        "required_commit": lock["required_commit"],
        "tracked_worktree_clean": True,
        "untracked_metadata_allowed": True,
        "public_module_origin": str(observed_public),
        "implementation_module_origin": str(observed_impl),
        "exporter_id": public.VERIFIED_EXPORTER_ID,
        "exporter_version": public.VERIFIED_EXPORTER_VERSION,
        "official_cli_options": list(public.OFFICIAL_CLI_OPTIONS),
        "isolated_mode": True,
        "private_pycache_outside_ce": True,
        "repo_local_module_count": repo_local_module_count,
    }
    return lock, public, implementation, identity


def _verify_connection(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"repository_path"} or not isinstance(payload.get("repository_path"), str):
        raise CEChildError("MALFORMED_REQUEST", "CE connection request is malformed")
    _, _, _, identity = _verify_and_import(Path(payload["repository_path"]))
    return {
        "connection_ok": True,
        "code": "CE_CHECKOUT_IDENTITY_VALID",
        "reason": "Exact CE checkout and official public CLI surface verified.",
        **identity,
    }


def _run_export(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "repository_path",
        "review_draft_path",
        "source_intake_path",
        "source_bundle_path",
        "output_path",
    }
    if set(payload) != expected or any(not isinstance(payload.get(key), str) or not payload[key] for key in expected):
        raise CEChildError("MALFORMED_REQUEST", "CE export request is malformed")
    root = Path(payload["repository_path"]).expanduser().resolve(strict=True)
    for key in ("review_draft_path", "source_intake_path", "source_bundle_path", "output_path"):
        if _inside(Path(payload[key]), root):
            raise CEChildError("CE_OUTPUT_BOUNDARY_INVALID", "Workbench inputs and outputs must remain outside CE repository")
    lock, public, _, identity = _verify_and_import(root)
    argv = [
        "--review-draft", payload["review_draft_path"],
        "--source-intake", payload["source_intake_path"],
        "--source-bundle", payload["source_bundle_path"],
        "--output", payload["output_path"],
        "--repo-root", str(root),
    ]
    _recheck_before_execution(root, lock)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            exit_code = public.main(argv)
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    if exit_code not in {0, 1, 2}:
        raise CEChildError("CE_EXECUTION_PROTOCOL_FAILED", f"Unexpected CE CLI exit code: {exit_code}")
    try:
        report = loads_bytes(buffer.getvalue().encode("utf-8"), max_bytes=1024 * 1024)
    except StrictJSONError as exc:
        raise CEChildError("CE_EXECUTION_PROTOCOL_FAILED", f"Malformed CE CLI JSON: {exc}") from exc
    handoff = report.get("handoff_allowed")
    authorization = report.get("authorization_valid")
    output_valid = report.get("output_valid")
    output_written = report.get("output_written")
    if not all(isinstance(value, bool) for value in (handoff, authorization, output_valid, output_written)):
        raise CEChildError("CE_EXECUTION_PROTOCOL_FAILED", "CE CLI report is missing Boolean result fields")
    output_path = Path(payload["output_path"])
    if exit_code == 0:
        classification = "CE_EXPORT_VALID_HANDOFF_ALLOWED"
        consistent = handoff and authorization and output_valid and output_written and output_path.is_file()
    elif exit_code == 2:
        classification = "CE_EXPORT_VALID_HANDOFF_BLOCKED"
        consistent = (not handoff) and (not authorization) and output_valid and output_written and output_path.is_file()
    else:
        classification = "CE_EXPORT_INVALID"
        consistent = (not handoff) and (not authorization) and (not output_valid) and (not output_written) and not output_path.exists()
    if not consistent:
        raise CEChildError("CE_EXECUTION_PROTOCOL_FAILED", "CE CLI exit and report semantics are inconsistent")
    return {
        "classification": classification,
        "cli_exit_code": exit_code,
        "official_result": report,
        "output_path": str(output_path),
        **identity,
    }


def _validate_request(value: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    expected = {"protocol_version", "request_id", "profile_id", "operation", "profile_payload"}
    if set(value) != expected or value.get("protocol_version") != PROTOCOL_VERSION:
        raise CEChildError("MALFORMED_REQUEST", "Request envelope is malformed")
    request_id = value.get("request_id")
    operation = value.get("operation")
    payload = value.get("profile_payload")
    if value.get("profile_id") != PROFILE_ID or not isinstance(request_id, str) or not request_id:
        raise CEChildError("MALFORMED_REQUEST", "Request identity is invalid")
    if operation not in {"verify_connection", "run_export"} or not isinstance(payload, dict):
        raise CEChildError("MALFORMED_REQUEST", "Unknown CE operation")
    return request_id, operation, payload


def _common(request_id: str, operation: str, status: str) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "profile_id": PROFILE_ID,
        "operation": operation,
        "child_pid": os.getpid(),
        "status": status,
        "process_start_mechanism": PROCESS_START_MECHANISM,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    request_id = "unknown"
    operation = "unknown"
    try:
        _require_isolated_interpreter()
        request = load_file(args.request, max_bytes=MAX_REQUEST_BYTES)
        request_id, operation, payload = _validate_request(request)
        profile_payload = _verify_connection(payload) if operation == "verify_connection" else _run_export(payload)
        result = {**_common(request_id, operation, "completed"), "profile_payload": profile_payload}
    except Exception as exc:
        code = exc.code if isinstance(exc, CEChildError) else "CE_CHILD_EXCEPTION"
        reason = exc.reason if isinstance(exc, CEChildError) else f"{type(exc).__name__}: {str(exc)[:2048]}"
        result = {**_common(request_id, operation, "error"), "error_code": code, "error_reason": reason}
    try:
        write_json(args.result, result, max_bytes=MAX_RESULT_BYTES)
    except Exception:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
