from pathlib import Path

from ev4_qc_workbench.strict_json import load_file
import ev4_qc_workbench.profiles.ce as ce


def test_ce_profile_lock_is_exact():
    lock = load_file(Path(ce.__file__).with_name("ce-profile.lock.json"), max_bytes=65536)
    assert lock["profile_id"] == "ce"
    assert lock["required_commit"] == "0e7d8756c8452113d42e8f50fc9489b240a01bfe"
    assert lock["public_module"] == "validator.verified_project_gate_exporter"
    assert lock["official_cli_options"] == [
        "--review-draft", "--source-intake", "--source-bundle", "--output", "--repo-root", "--overwrite"
    ]
