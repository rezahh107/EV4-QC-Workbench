from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    """Raised when a bounded strict-JSON contract is violated."""


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJSONError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _constant(token: str) -> None:
    raise StrictJSONError(f"non-finite JSON number: {token}")


def _float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise StrictJSONError(f"non-finite JSON number: {token}")
    return value


def loads_bytes(data: bytes, *, max_bytes: int, object_required: bool = True) -> Any:
    if len(data) > max_bytes:
        raise StrictJSONError("JSON document exceeds its bounded size limit")
    if data.startswith(b"\xef\xbb\xbf"):
        raise StrictJSONError("UTF-8 BOM is not permitted")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_object_pairs,
            parse_constant=_constant,
            parse_float=_float,
        )
    except (UnicodeError, json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(str(exc)) from exc
    if object_required and not isinstance(value, dict):
        raise StrictJSONError("top-level JSON value must be an object")
    return value


def load_file(path: Path, *, max_bytes: int, object_required: bool = True) -> Any:
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise StrictJSONError(f"cannot read JSON document: {exc}") from exc
    return loads_bytes(data, max_bytes=max_bytes, object_required=object_required)


def dumps_bytes(value: Any, *, max_bytes: int) -> bytes:
    try:
        data = (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StrictJSONError(f"value is not strict JSON: {exc}") from exc
    if len(data) > max_bytes:
        raise StrictJSONError("JSON document exceeds its bounded size limit")
    return data


def atomic_write(path: Path, data: bytes) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any, *, max_bytes: int = 2 * 1024 * 1024) -> None:
    atomic_write(Path(path), dumps_bytes(value, max_bytes=max_bytes))
