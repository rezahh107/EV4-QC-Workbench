from pathlib import Path

import pytest

from ev4_qc_workbench.strict_json import load_file
import ev4_qc_workbench.profiles.ce as ce

REQUIRED_CE_COMMIT = "bc4a901d82fcdbdb131e30058b399508262706c5"
REQUIRED_EXPORTER_ID = "ev4-producer-gate-export-validator"
REQUIRED_EXPORTER_VERSION = "1.1.0"
OBSOLETE_CE_COMMIT = "ff40b2a9d801f34aad03829d0c1c24d85b5d7f08"
OBSOLETE_CE_BRANCH = "fix/ce-external-output-boundary"


def _lock() -> dict:
    return load_file(Path(ce.__file__).with_name("ce-profile.lock.json"), max_bytes=65536)


def test_ce_profile_lock_is_exact():
    lock = _lock()
    assert lock["profile_id"] == "ce"
    assert lock["repository"] == "rezahh107/EV4-Constructability-Engineer-Repo"
    assert lock["acceptance_mode"] == "exact_commit"
    assert lock["required_commit"] == REQUIRED_CE_COMMIT
    assert lock["verified_exporter_id"] == REQUIRED_EXPORTER_ID
    assert lock["verified_exporter_version"] == REQUIRED_EXPORTER_VERSION
    assert lock["public_module"] == "validator.verified_project_gate_exporter"
    assert lock["official_cli_options"] == [
        "--review-draft", "--source-intake", "--source-bundle", "--output", "--repo-root", "--overwrite"
    ]


def test_current_ce_identity_surfaces_do_not_retain_obsolete_feature_authority():
    root = Path(ce.__file__).resolve().parents[4]
    current_surfaces = [
        root / "src/ev4_qc_workbench/profiles/ce/ce-profile.lock.json",
        root / "tests/ce_integration_support.py",
        root / ".github/workflows/validate.yml",
        root / "README.md",
        root / "STATUS.md",
    ]
    for path in current_surfaces:
        text = path.read_text(encoding="utf-8")
        assert OBSOLETE_CE_COMMIT not in text, path
        assert OBSOLETE_CE_BRANCH not in text, path


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("required_commit", "0e7d8756c8452113d42e8f50fc9489b240a01bfe"),
        ("required_commit", "f" * 40),
        ("verified_exporter_version", "1.0.0"),
        ("verified_exporter_version", "1.1.1"),
        ("verified_exporter_id", "alternate-exporter"),
    ],
)
def test_old_or_alternate_identity_does_not_satisfy_lock(field: str, invalid_value: str):
    lock = _lock()
    assert invalid_value != lock[field]
