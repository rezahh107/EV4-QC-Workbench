import pytest

from ev4_qc_workbench.process_launcher import PROCESS_START_MECHANISM, ProcessLaunchError, _validate_result


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
