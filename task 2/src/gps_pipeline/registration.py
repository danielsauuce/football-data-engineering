import hashlib
import json
import shutil
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def calculate_sha256(file_path: Path) -> str:
    """Calculate a file's SHA-256 fingerprint."""
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def _read_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    """Read the registration manifest, or return an empty list."""
    if not manifest_path.exists():
        return []

    with manifest_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_manifest(
    manifest_path: Path,
    records: list[dict[str, Any]],
) -> None:
    """Write the manifest through a temporary file."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = manifest_path.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)

    temporary_path.replace(manifest_path)


def register_input(
    source_path: Path,
    landing_dir: Path,
    manifest_path: Path,
    rule_set_version: str,
) -> dict[str, Any]:
    """
    Preserve and register an incoming file.

    A previously completed run with the same file hash and
    rule-set version is treated as a duplicate.
    """
    if not source_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source_path}")

    input_hash = calculate_sha256(source_path)
    records = _read_manifest(manifest_path)

    previous_run = next(
        (
            record
            for record in records
            if record["input_sha256"] == input_hash
            and record["rule_set_version"] == rule_set_version
            and record["status"] == "completed"
        ),
        None,
    )

    if previous_run:
        return {
            "status": "duplicate",
            "run_id": previous_run["run_id"],
            "input_sha256": input_hash,
            "landing_path": previous_run["landing_path"],
        }

    landing_dir.mkdir(parents=True, exist_ok=True)

    landing_path = landing_dir / source_path.name

    if landing_path.exists():
        landing_hash = calculate_sha256(landing_path)

        if landing_hash != input_hash:
            raise ValueError(
                "A different file already exists at the landing path. "
                "Refusing to overwrite it."
            )
    else:
        shutil.copy2(source_path, landing_path)

    run_id = str(uuid.uuid4())

    record = {
        "run_id": run_id,
        "source_file": source_path.name,
        "landing_path": str(landing_path),
        "input_sha256": input_hash,
        "rule_set_version": rule_set_version,
        "registered_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "registered",
    }

    records.append(record)
    _write_manifest(manifest_path, records)

    return {
        "status": "registered",
        "run_id": run_id,
        "input_sha256": input_hash,
        "landing_path": str(landing_path),
    }


def mark_run_completed(
    manifest_path: Path,
    run_id: str,
) -> None:
    """Mark a run completed after the full pipeline succeeds."""
    records = _read_manifest(manifest_path)

    for record in records:
        if record["run_id"] == run_id:
            record["status"] = "completed"
            record["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
            _write_manifest(manifest_path, records)
            return

    raise ValueError(f"Run ID not found in manifest: {run_id}")
