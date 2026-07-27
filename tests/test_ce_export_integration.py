from pathlib import Path
import subprocess

import pytest

from ev4_qc_workbench.profiles.ce.launcher import run_export
from ce_integration_support import ce_root, materialize_inputs

pytestmark = [pytest.mark.integration, pytest.mark.windows]


def _ce_state(root: Path) -> tuple[str, bytes, bytes]:
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"]
    )
    index = subprocess.check_output(["git", "-C", str(root), "ls-files", "-s"])
    return head, status, index


@pytest.mark.parametrize(
    ("mode", "classification", "exit_code"),
    [
        ("authorized", "CE_EXPORT_VALID_HANDOFF_ALLOWED", 0),
        ("blocked", "CE_EXPORT_VALID_HANDOFF_BLOCKED", 2),
        ("invalid", "CE_EXPORT_INVALID", 1),
    ],
)
def test_official_cli_cases_and_snapshot(mode: str, classification: str, exit_code: int, tmp_path: Path):
    review, intake, bundle = materialize_inputs(tmp_path / "inputs", mode)
    originals = {path.name: path.read_bytes() for path in (review, intake, bundle)}
    result = run_export(
        repository_path=ce_root(),
        review_draft_path=review,
        source_intake_path=intake,
        source_bundle_path=bundle,
        output_folder=tmp_path / "output",
    )
    assert result.classification == classification, result.reason
    assert result.cli_exit_code == exit_code
    assert result.attempt_path is not None
    assert {path.name: path.read_bytes() for path in (review, intake, bundle)} == originals
    snapshot = result.attempt_path / "input-snapshot"
    assert (snapshot / "review-draft.json").read_bytes() == review.read_bytes()
    assert (snapshot / "source-intake.json").read_bytes() == intake.read_bytes()
    assert (snapshot / "source-bundle.json").read_bytes() == bundle.read_bytes()
    if exit_code in {0, 2}:
        assert result.output_valid and result.output_path and result.output_path.is_file()
    else:
        assert not result.output_valid and result.output_path is None


def test_actual_ce_paths_are_rejected_before_attempt_or_dependency_write(tmp_path: Path) -> None:
    root = ce_root()
    review, intake, bundle = materialize_inputs(tmp_path / "inputs", "authorized")
    forbidden_output = root / "workbench-must-not-create"
    before = _ce_state(root)

    output_result = run_export(
        repository_path=root,
        review_draft_path=review,
        source_intake_path=intake,
        source_bundle_path=bundle,
        output_folder=forbidden_output,
    )
    input_result = run_export(
        repository_path=root,
        review_draft_path=root / "README.md",
        source_intake_path=intake,
        source_bundle_path=bundle,
        output_folder=tmp_path / "safe-output",
    )

    assert output_result.classification == "CE_PATH_BOUNDARY_INVALID"
    assert output_result.attempt_path is None
    assert output_result.output_path is None
    assert input_result.classification == "CE_PATH_BOUNDARY_INVALID"
    assert "review_draft_path" in input_result.reason
    assert input_result.attempt_path is None
    assert input_result.output_path is None
    assert not forbidden_output.exists()
    assert not (tmp_path / "safe-output").exists()
    assert _ce_state(root) == before
