from __future__ import annotations

import os
from pathlib import Path

import pytest

import ev4_qc_workbench.profiles.ce.launcher as launcher_module
import ev4_qc_workbench.profiles.ce.tab as tab_module
from ev4_qc_workbench.profiles.ce.launcher import run_export
from ev4_qc_workbench.profiles.ce.models import CEExportResult


def _tree(root: Path) -> tuple[str, ...]:
    return tuple(sorted(str(path.relative_to(root)) for path in root.rglob("*")))


def _outside_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    outside = tmp_path / "outside-inputs"
    return (
        outside / "review-draft.json",
        outside / "source-intake.json",
        outside / "source-bundle.json",
    )


def _forbid_attempt(*args, **kwargs):
    raise AssertionError("create_attempt must not run for CE path-boundary rejection")


@pytest.mark.parametrize("nested", [False, True], ids=["equal-root", "below-root"])
def test_output_folder_inside_ce_is_rejected_before_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nested: bool,
) -> None:
    ce_root = tmp_path / "ce"
    ce_root.mkdir()
    review, intake, bundle = _outside_inputs(tmp_path)
    output_folder = ce_root / "would-not-be-created" if nested else ce_root
    before = _tree(ce_root)
    monkeypatch.setattr(launcher_module, "create_attempt", _forbid_attempt)

    result = run_export(
        repository_path=ce_root,
        review_draft_path=review,
        source_intake_path=intake,
        source_bundle_path=bundle,
        output_folder=output_folder,
    )

    assert result.classification == "CE_PATH_BOUNDARY_INVALID"
    assert "output_folder" in result.reason
    assert result.attempt_path is None
    assert result.output_path is None
    assert _tree(ce_root) == before
    assert not (ce_root / "would-not-be-created").exists()
    assert not (tmp_path / "outside-inputs" / "ev4-qc-results").exists()


@pytest.mark.parametrize(
    "offending_field",
    ["review_draft_path", "source_intake_path", "source_bundle_path"],
)
def test_original_input_inside_ce_is_rejected_before_any_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    offending_field: str,
) -> None:
    ce_root = tmp_path / "ce"
    ce_root.mkdir()
    offending = ce_root / f"{offending_field}.json"
    offending.write_text("{}\n", encoding="utf-8")
    review, intake, bundle = _outside_inputs(tmp_path)
    values = {
        "review_draft_path": review,
        "source_intake_path": intake,
        "source_bundle_path": bundle,
    }
    values[offending_field] = offending
    output_folder = tmp_path / "output"
    before = _tree(ce_root)
    monkeypatch.setattr(launcher_module, "create_attempt", _forbid_attempt)

    result = run_export(
        repository_path=ce_root,
        output_folder=output_folder,
        **values,
    )

    assert result.classification == "CE_PATH_BOUNDARY_INVALID"
    assert offending_field in result.reason
    assert result.attempt_path is None
    assert result.output_path is None
    assert _tree(ce_root) == before
    assert not output_folder.exists()


def test_existing_directory_symlink_resolving_into_ce_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ce_root = tmp_path / "ce"
    ce_root.mkdir()
    link = tmp_path / "ce-link"
    try:
        link.symlink_to(ce_root, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        if os.name == "nt":
            pytest.skip(f"directory symlink fixture unavailable on Windows: {exc}")
        raise
    review, intake, bundle = _outside_inputs(tmp_path)
    monkeypatch.setattr(launcher_module, "create_attempt", _forbid_attempt)

    result = run_export(
        repository_path=ce_root,
        review_draft_path=review,
        source_intake_path=intake,
        source_bundle_path=bundle,
        output_folder=link / "nested-output",
    )

    assert result.classification == "CE_PATH_BOUNDARY_INVALID"
    assert "output_folder" in result.reason
    assert result.attempt_path is None
    assert not (ce_root / "nested-output").exists()


class _Value:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _Button:
    def __init__(self) -> None:
        self.state = "normal"

    def configure(self, *, state: str) -> None:
        self.state = state


def test_gui_boundary_rejection_keeps_settings_and_result_action_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_calls: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(
        tab_module,
        "update_profile_settings",
        lambda *args, **kwargs: settings_calls.append((args, kwargs)),
    )
    tab = object.__new__(tab_module.CETab)
    tab.output = _Value(str(tmp_path / "output"))
    tab.status = _Value()
    tab.detail = _Value()
    tab.open_button = _Button()
    tab.last_attempt = tmp_path / "old-attempt"
    result = CEExportResult(
        success=False,
        classification="CE_PATH_BOUNDARY_INVALID",
        reason="output_folder resolves inside the selected CE repository",
        next_action="Select an external output folder.",
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

    tab._export_complete(result, None)

    assert settings_calls == []
    assert tab.last_attempt is None
    assert tab.open_button.state == "disabled"
    assert tab.status.get() == "CE_PATH_BOUNDARY_INVALID"
