from pathlib import Path

from ev4_qc_workbench.attempts import copy_bytes_verified, create_attempt


def test_attempt_and_snapshot_are_unique_and_byte_exact(tmp_path: Path):
    source = tmp_path / "source.json"
    source.write_bytes(b'{"x":1}\n')
    first = create_attempt(tmp_path / "out", profile_id="ce")
    second = create_attempt(tmp_path / "out", profile_id="ce")
    assert first.name == "attempt-0001"
    assert second.name == "attempt-0002"
    target = first / "input-snapshot" / "review-draft.json"
    copy_bytes_verified(source, target)
    assert target.read_bytes() == source.read_bytes()
