from pathlib import Path
import subprocess
import sys
import types

import pytest

from ev4_qc_workbench.process_launcher import PROCESS_START_MECHANISM, launch_profile_operation
from ev4_qc_workbench.profiles.ce.launcher import CHILD_MODULE, verify_connection
from ce_integration_support import (
    REQUIRED_CE_COMMIT,
    ce_root,
    independent_clone,
)

pytestmark = [pytest.mark.integration, pytest.mark.windows]

LOCKED_CLI_OPTIONS = [
    "--review-draft",
    "--source-intake",
    "--source-bundle",
    "--output",
    "--repo-root",
    "--overwrite",
]


def test_exact_checkout_and_fresh_child_are_verified():
    root = ce_root()
    first = verify_connection(root)
    second = verify_connection(root)
    assert first.ok, first.reason
    assert first.observed_commit == REQUIRED_CE_COMMIT
    assert first.required_commit == REQUIRED_CE_COMMIT
    assert first.exporter_id == "ev4-producer-gate-export-validator"
    assert first.exporter_version == "1.1.0"
    assert first.child_pid and second.child_pid and first.child_pid != second.child_pid
    assert first.public_module_origin == str((root / "validator/verified_project_gate_exporter.py").resolve())
    assert first.implementation_module_origin == str((root / "validator/_verified_project_gate_exporter_impl.py").resolve())


def test_parent_validator_poison_cannot_cross_fresh_exec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ce_root()
    fake_package = types.ModuleType("validator")
    fake_package.__path__ = []  # type: ignore[attr-defined]
    fake_public = types.ModuleType("validator.verified_project_gate_exporter")
    fake_public.VERIFIED_EXPORTER_ID = "poisoned-parent-exporter"
    fake_public.VERIFIED_EXPORTER_VERSION = "999.0.0"
    fake_impl = types.ModuleType("validator._verified_project_gate_exporter_impl")
    monkeypatch.setitem(sys.modules, "validator", fake_package)
    monkeypatch.setitem(sys.modules, "validator.verified_project_gate_exporter", fake_public)
    monkeypatch.setitem(sys.modules, "validator._verified_project_gate_exporter_impl", fake_impl)

    outcomes = [
        launch_profile_operation(
            child_module=CHILD_MODULE,
            profile_id="ce",
            operation="verify_connection",
            profile_payload={"repository_path": str(root)},
        )
        for _ in range(2)
    ]

    assert outcomes[0].process_start_mechanism == PROCESS_START_MECHANISM
    assert outcomes[1].process_start_mechanism == PROCESS_START_MECHANISM
    assert outcomes[0].child_pid != outcomes[1].child_pid
    for outcome in outcomes:
        payload = outcome.profile_payload
        assert payload["observed_commit"] == REQUIRED_CE_COMMIT
        assert payload["exporter_id"] == "ev4-producer-gate-export-validator"
        assert payload["exporter_version"] == "1.1.0"
        assert payload["official_cli_options"] == LOCKED_CLI_OPTIONS
        assert payload["isolated_mode"] is True
        assert payload["private_pycache_outside_ce"] is True
        assert payload["repo_local_module_count"] > 0
        assert payload["public_module_origin"] == str(
            (root / "validator/verified_project_gate_exporter.py").resolve()
        )
        assert payload["implementation_module_origin"] == str(
            (root / "validator/_verified_project_gate_exporter_impl.py").resolve()
        )


def test_parent_pythonpath_poison_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = ce_root()
    poison_root = tmp_path / "parent-pythonpath-poison"
    package = poison_root / "jsonschema"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "raise RuntimeError('parent PYTHONPATH poison executed')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(poison_root))

    result = verify_connection(root)

    assert result.ok, result.reason
    assert result.observed_commit == REQUIRED_CE_COMMIT


def test_alternate_commit_and_wrong_remote_are_rejected(tmp_path: Path):
    clone = independent_clone(tmp_path)
    subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", "--detach", "HEAD^"], check=True)
    alternate = verify_connection(clone)
    assert not alternate.ok
    assert alternate.code == "CE_CHECKOUT_IDENTITY_INVALID"
    subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", "--detach", REQUIRED_CE_COMMIT], check=True)
    subprocess.run(["git", "-C", str(clone), "remote", "set-url", "origin", "https://github.com/example/wrong.git"], check=True)
    wrong_remote = verify_connection(clone)
    assert not wrong_remote.ok
    assert wrong_remote.code == "CE_CHECKOUT_IDENTITY_INVALID"


def test_tracked_mutations_rejected_and_harmless_untracked_metadata_allowed(tmp_path: Path):
    clone = independent_clone(tmp_path)
    tracked = clone / "README.md"
    original = tracked.read_bytes()
    tracked.write_bytes(original + b"\nprobe\n")
    assert not verify_connection(clone).ok
    tracked.write_bytes(original)
    subprocess.run(["git", "-C", str(clone), "add", "README.md"], check=True)
    tracked.write_bytes(original + b"\nstaged-probe\n")
    subprocess.run(["git", "-C", str(clone), "add", "README.md"], check=True)
    tracked.write_bytes(original)
    staged = verify_connection(clone)
    assert not staged.ok
    assert staged.code == "CE_CHECKOUT_IDENTITY_INVALID"
    subprocess.run(["git", "-C", str(clone), "reset", "--hard", "HEAD"], check=True, stdout=subprocess.DEVNULL)
    (clone / "untracked-metadata.tmp").write_text("metadata", encoding="utf-8")
    assert verify_connection(clone).ok


def test_repo_local_source_and_ignored_bytecode_poison_are_rejected_before_import(tmp_path: Path):
    clone = independent_clone(tmp_path)
    source_poison = clone / "jsonschema.py"
    source_poison.write_text(
        "raise RuntimeError('repo-local source poison executed')\n",
        encoding="utf-8",
    )
    source_result = verify_connection(clone)
    assert not source_result.ok
    assert source_result.code == "CE_CHECKOUT_IMPORT_CONTAMINATION"
    assert "jsonschema.py" in source_result.reason

    source_poison.unlink()
    pycache = clone / "validator" / "__pycache__"
    pycache.mkdir(exist_ok=True)
    bytecode_poison = pycache / "repo_poison.cpython-311.pyc"
    bytecode_poison.write_bytes(b"not-valid-bytecode")
    bytecode_result = verify_connection(clone)
    assert not bytecode_result.ok
    assert bytecode_result.code == "CE_CHECKOUT_IMPORT_CONTAMINATION"
    assert "repo_poison" in bytecode_result.reason
