from pathlib import Path

import pytest

from ev4_qc_workbench.process_launcher import (
    PROCESS_START_MECHANISM,
    ProcessLaunchError,
    _child_command,
    _child_environment,
    _validate_result,
)


def valid():
    return {
        "protocol_version": "1.0",
        "request_id": "req",
        "profile_id": "ce",
        "operation": "verify_connection",
        "child_pid": 42,
        "status": "completed",
        "process_start_mechanism": PROCESS_START_MECHANISM,
        "profile_payload": {"ok": True},
    }


def test_transport_binds_identity_and_payload():
    outcome = _validate_result(valid(), request_id="req", profile_id="ce", operation="verify_connection")
    assert outcome.child_pid == 42
    assert outcome.profile_payload == {"ok": True}


@pytest.mark.parametrize("field,value", [("request_id", "other"), ("profile_id", "architect"), ("operation", "other"), ("status", "unknown")])
def test_transport_rejects_identity_and_status_drift(field, value):
    result = valid()
    result[field] = value
    with pytest.raises(ProcessLaunchError):
        _validate_result(result, request_id="req", profile_id="ce", operation="verify_connection")


def test_child_command_uses_isolated_interpreter_private_pycache_and_no_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "poison-parent-path"))
    request = tmp_path / "request.json"
    result = tmp_path / "result.json"
    pycache = tmp_path / "private-pycache"
    command = _child_command(
        child_module="ev4_qc_workbench.profiles.ce.process_child",
        request_path=request,
        result_path=result,
        pycache_path=pycache,
    )
    environment = _child_environment()

    assert command[1:5] == ["-I", "-X", f"pycache_prefix={pycache}", "-m"]
    assert command[5] == "ev4_qc_workbench.profiles.ce.process_child"
    assert "PYTHONPATH" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"
