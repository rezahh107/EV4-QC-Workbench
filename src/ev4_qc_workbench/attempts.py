from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .strict_json import atomic_write, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_attempt(output_folder: Path, *, profile_id: str) -> Path:
    base = Path(output_folder).expanduser().resolve() / "ev4-qc-results"
    base.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1_000_000):
        attempt = base / f"attempt-{number:04d}"
        try:
            attempt.mkdir()
        except FileExistsError:
            continue
        (attempt / "input-snapshot").mkdir()
        (attempt / "generated-artifacts").mkdir()
        write_json(
            attempt / "attempt-metadata.json",
            {
                "schema_version": "1.0",
                "profile_id": profile_id,
                "attempt_id": attempt.name,
                "started_at_utc": utc_now(),
                "attempt_path": str(attempt),
            },
        )
        return attempt
    raise RuntimeError("No unique attempt directory is available")


def copy_bytes_verified(source: Path, destination: Path) -> str:
    src = Path(source).expanduser().resolve(strict=True)
    if not src.is_file() or src.is_symlink():
        raise ValueError(f"Input is not a regular file: {src}")
    data = src.read_bytes()
    atomic_write(Path(destination), data)
    if Path(destination).read_bytes() != data:
        Path(destination).unlink(missing_ok=True)
        raise ValueError(f"Snapshot bytes differ: {src.name}")
    return src.name


def write_summary(attempt: Path, *, code: str, reason: str, next_action: str) -> None:
    atomic_write(
        Path(attempt) / "execution-summary.txt",
        f"{code}: {reason}\nNext action: {next_action}\n".encode("utf-8"),
    )
