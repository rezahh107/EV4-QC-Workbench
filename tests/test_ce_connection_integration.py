from pathlib import Path
import subprocess

import pytest

from ev4_qc_workbench.profiles.ce.launcher import verify_connection
from ce_integration_support import ce_root, independent_clone

pytestmark = [pytest.mark.integration, pytest.mark.windows]


def test_exact_checkout_and_fresh_child_are_verified():
    root = ce_root()
    first = verify_connection(root)
    second = verify_connection(root)
    assert first.ok, first.reason
    assert first.observed_commit == "0e7d8756c8452113d42e8f50fc9489b240a01bfe"
    assert first.child_pid and second.child_pid and first.child_pid != second.child_pid
    assert first.public_module_origin == str((root / "validator/verified_project_gate_exporter.py").resolve())


def test_alternate_commit_and_wrong_remote_are_rejected(tmp_path: Path):
    clone = independent_clone(tmp_path)
    subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", "HEAD^"], check=True)
    assert not verify_connection(clone).ok
    subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", "main"], check=True)
    subprocess.run(["git", "-C", str(clone), "remote", "set-url", "origin", "https://github.com/example/wrong.git"], check=True)
    assert not verify_connection(clone).ok


def test_tracked_mutations_rejected_and_untracked_allowed(tmp_path: Path):
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
    assert not verify_connection(clone).ok
    subprocess.run(["git", "-C", str(clone), "reset", "--hard", "HEAD"], check=True, stdout=subprocess.DEVNULL)
    (clone / "untracked-metadata.tmp").write_text("metadata", encoding="utf-8")
    assert verify_connection(clone).ok
