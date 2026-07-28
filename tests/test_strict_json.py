import math
import pytest

from ev4_qc_workbench.strict_json import StrictJSONError, dumps_bytes, loads_bytes


def test_strict_json_accepts_bounded_object():
    assert loads_bytes(b'{"a": 1}', max_bytes=100) == {"a": 1}


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'\xef\xbb\xbf{}', b'[]', b'{"a":NaN}', b'\xff'])
def test_strict_json_rejects_invalid_documents(data):
    with pytest.raises(StrictJSONError):
        loads_bytes(data, max_bytes=100)


def test_dump_rejects_nonfinite():
    with pytest.raises(StrictJSONError):
        dumps_bytes({"value": math.inf}, max_bytes=100)
