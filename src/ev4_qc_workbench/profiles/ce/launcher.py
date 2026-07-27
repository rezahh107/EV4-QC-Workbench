from __future__ import annotations

from pathlib import Path
from typing import Any

from ev4_qc_workbench.attempts import copy_bytes_verified, create_attempt, write_summary
from ev4_qc_workbench.process_launcher import ProcessLaunchError, launch_profile_operation
from ev4_qc_workbench.strict_json import write_json

from .models import CEConnectionResult, CEExportResult

PROFILE_ID = "ce"
CHILD_MODULE = "ev4_qc_workbench.profiles.ce.process_child"


def _text(value: Any, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid CE Profile result field: {field}")
    return value


def _resolved_without_creation(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _equals_or_descends_from(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        # Different Windows drives and unrelated roots are not containment.
        return False


def _containment_violation(
    *,
    repository_path: Path,
    review_draft_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_folder: Path,
) -> tuple[str, Path, Path] | None:
    root = _resolved_without_creation(repository_path)
    candidates = (
        ("review_draft_path", review_draft_path),
        ("source_intake_path", source_intake_path),
        ("source_bundle_path", source_bundle_path),
        ("output_folder", output_folder),
    )
    for field, candidate in candidates:
        resolved = _resolved_without_creation(candidate)
        if _equals_or_descends_from(resolved, root):
            return field, resolved, root
    return None


def _boundary_rejection(reason: str) -> CEExportResult:
    return CEExportResult(
        success=False,
        classification="CE_PATH_BOUNDARY_INVALID",
        reason=reason,
        next_action="Select original inputs and an output folder outside the selected CE checkout.",
        attempt_path=None,
        output_path=None,
        child_pid=None,
        cli_exit_code=None,
        handoff_allowed=False,
        authorization_valid=False,
        output_valid=False,
        observed_commit=None,
        exporter_id=None,
        official_result=None,
    )


def verify_connection(repository_path: Path) -> CEConnectionResult:
    path = Path(repository_path).expanduser().resolve()
    try:
        outcome = launch_profile_operation(
            child_module=CHILD_MODULE,
            profile_id=PROFILE_ID,
            operation="verify_connection",
            profile_payload={"repository_path": str(path)},
        )
        value = outcome.profile_payload
        required = {
            "connection_ok", "code", "reason", "repository_identity", "observed_commit",
            "required_commit", "tracked_worktree_clean", "untracked_metadata_allowed",
            "public_module_origin", "implementation_module_origin", "exporter_id", "exporter_version",
        }
        if set(value) != required or value.get("connection_ok") is not True:
            raise ValueError("Malformed CE connection result")
        return CEConnectionResult(
            True,
            path,
            _text(value["code"], "code"),
            _text(value["reason"], "reason"),
            _text(value["observed_commit"], "observed_commit"),
            _text(value["required_commit"], "required_commit"),
            outcome.child_pid,
            _text(value["public_module_origin"], "public_module_origin"),
            _text(value["implementation_module_origin"], "implementation_module_origin"),
            _text(value["exporter_id"], "exporter_id"),
            _text(value["exporter_version"], "exporter_version"),
        )
    except (ProcessLaunchError, ValueError, OSError) as exc:
        code = exc.code if isinstance(exc, ProcessLaunchError) else "CE_CONNECTION_PROTOCOL_FAILED"
        reason = exc.reason if isinstance(exc, ProcessLaunchError) else str(exc)
        return CEConnectionResult(False, path, code, reason, child_pid=getattr(exc, "child_pid", None))


def _classification_text(classification: str, report: dict[str, Any]) -> tuple[bool, str, str]:
    if classification == "CE_EXPORT_VALID_HANDOFF_ALLOWED":
        return True, "Official CE CLI produced a valid authorized export.", "Open the result folder and use the CE Project Gate artifact."
    if classification == "CE_EXPORT_VALID_HANDOFF_BLOCKED":
        return False, "Official CE CLI produced a valid export with handoff blocked.", "Resolve CE-owned diagnostics before continuation."
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), list) else []
    message = next((item.get("message") for item in diagnostics if isinstance(item, dict) and isinstance(item.get("message"), str)), None)
    return False, message or "Official CE CLI rejected the inputs.", "Correct the Review Draft or source evidence and run again."


def run_export(
    *,
    repository_path: Path,
    review_draft_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_folder: Path,
) -> CEExportResult:
    try:
        violation = _containment_violation(
            repository_path=repository_path,
            review_draft_path=review_draft_path,
            source_intake_path=source_intake_path,
            source_bundle_path=source_bundle_path,
            output_folder=output_folder,
        )
    except (OSError, RuntimeError) as exc:
        return _boundary_rejection(f"Unable to resolve the CE path boundary safely: {type(exc).__name__}")
    if violation is not None:
        field, resolved, root = violation
        return _boundary_rejection(
            f"{field} resolves inside the selected CE repository: {resolved} (CE root: {root})"
        )

    attempt = create_attempt(output_folder, profile_id=PROFILE_ID)
    snapshot = attempt / "input-snapshot"
    review = snapshot / "review-draft.json"
    intake = snapshot / "source-intake.json"
    bundle = snapshot / "source-bundle.json"
    output = attempt / "generated-artifacts" / "ce-project-gate.json"
    try:
        copy_bytes_verified(review_draft_path, review)
        copy_bytes_verified(source_intake_path, intake)
        copy_bytes_verified(source_bundle_path, bundle)
        outcome = launch_profile_operation(
            child_module=CHILD_MODULE,
            profile_id=PROFILE_ID,
            operation="run_export",
            profile_payload={
                "repository_path": str(Path(repository_path).expanduser().resolve()),
                "review_draft_path": str(review),
                "source_intake_path": str(intake),
                "source_bundle_path": str(bundle),
                "output_path": str(output),
            },
        )
        value = outcome.profile_payload
        required = {
            "classification", "cli_exit_code", "official_result", "output_path",
            "repository_identity", "observed_commit", "required_commit", "tracked_worktree_clean",
            "untracked_metadata_allowed", "public_module_origin", "implementation_module_origin",
            "exporter_id", "exporter_version",
        }
        if set(value) != required or not isinstance(value.get("official_result"), dict):
            raise ValueError("Malformed CE export result")
        classification = _text(value["classification"], "classification")
        report = value["official_result"]
        success, reason, next_action = _classification_text(classification, report)
        write_json(attempt / "generated-artifacts" / "ce-cli-result.json", report)
        write_json(
            attempt / "diagnostics.json",
            {
                "classification": classification,
                "reason": reason,
                "next_action": next_action,
                "official_diagnostics": report.get("diagnostics", []),
            },
        )
        write_summary(attempt, code=classification, reason=reason, next_action=next_action)
        return CEExportResult(
            success=success,
            classification=classification,
            reason=reason,
            next_action=next_action,
            attempt_path=attempt,
            output_path=output if output.is_file() else None,
            child_pid=outcome.child_pid,
            cli_exit_code=value["cli_exit_code"],
            handoff_allowed=bool(report["handoff_allowed"]),
            authorization_valid=bool(report["authorization_valid"]),
            output_valid=bool(report["output_valid"]),
            observed_commit=_text(value["observed_commit"], "observed_commit"),
            exporter_id=_text(value["exporter_id"], "exporter_id"),
            official_result=report,
        )
    except (ProcessLaunchError, ValueError, OSError) as exc:
        classification = "CE_EXECUTION_PROTOCOL_FAILED"
        reason = exc.reason if isinstance(exc, ProcessLaunchError) else str(exc)
        next_action = "Review the selected paths and exact CE checkout, then retry."
        write_json(
            attempt / "diagnostics.json",
            {"classification": classification, "reason": reason, "next_action": next_action},
        )
        write_summary(attempt, code=classification, reason=reason, next_action=next_action)
        return CEExportResult(
            success=False,
            classification=classification,
            reason=reason,
            next_action=next_action,
            attempt_path=attempt,
            output_path=None,
            child_pid=getattr(exc, "child_pid", None),
            cli_exit_code=None,
            handoff_allowed=False,
            authorization_valid=False,
            output_valid=False,
            observed_commit=None,
            exporter_id=None,
            official_result=None,
        )
