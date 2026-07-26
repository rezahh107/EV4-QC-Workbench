from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def ce_root() -> Path:
    value = os.environ.get("EV4_CE_REPO")
    if not value:
        pytest.skip("integration-only: set EV4_CE_REPO")
    return Path(value).resolve()


def independent_clone(tmp_path: Path) -> Path:
    root = ce_root()
    target = tmp_path / "ce-clone"
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(root), str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "checkout", "--quiet", "main"], check=True)
    return target


def materialize_inputs(workspace: Path, mode: str) -> tuple[Path, Path, Path]:
    root = ce_root()
    script = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2]); mode = sys.argv[3]
sys.path.insert(0, str(root)); sys.path.insert(0, str(root / "tests"))
from exporter_test_support import _real_source_pair, _write_json
from verified_exporter_test_support import _geometry_draft
from validator.payload_assembler import sha256_json
intake, source, intake_path, bundle_path = _real_source_pair(out)
if mode in {"authorized", "invalid"}:
    intake["unresolved_evidence"] = []
    source["payload"]["unresolved_evidence"] = []
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = sha256_json(source)
    _write_json(intake_path, intake); _write_json(bundle_path, source)
draft = _geometry_draft(intake_path)
if mode == "invalid": draft["schema_id"] = "invalid-schema"
_write_json(out / "review-draft.json", draft)
'''
    workspace.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-c", script, str(root), str(workspace), mode], cwd=root, check=True)
    return workspace / "review-draft.json", workspace / "ce-input.json", workspace / "architect-source-bundle.json"
