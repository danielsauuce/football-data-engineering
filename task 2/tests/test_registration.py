import json

from pathlib import Path

from gps_pipeline.registration import (
    calculate_sha256,
    mark_run_completed,
    register_input,
)


def test_calculates_sha256(tmp_path):
    source = tmp_path / "session.json"
    source.write_text('{"session_id": "SESSION-001"}')

    result = calculate_sha256(source)

    assert len(result) == 64


def test_registers_and_preserves_input(tmp_path):
    source = tmp_path / "session.json"
    source.write_text('{"session_id": "SESSION-001"}')

    landing_dir = tmp_path / "landing"
    manifest = tmp_path / "metadata" / "manifest.json"

    result = register_input(
        source,
        landing_dir,
        manifest,
        rule_set_version="v1",
    )

    landing_path = Path(result["landing_path"])

    assert result["status"] == "registered"
    assert landing_path.exists()
    assert landing_path.read_bytes() == source.read_bytes()
    assert calculate_sha256(landing_path) == result["input_sha256"]


def test_completed_duplicate_is_skipped(tmp_path):
    source = tmp_path / "session.json"
    source.write_text('{"session_id": "SESSION-001"}')

    landing_dir = tmp_path / "landing"
    manifest = tmp_path / "metadata" / "manifest.json"

    first_run = register_input(source, landing_dir, manifest, "v1")

    mark_run_completed(manifest, first_run["run_id"])

    second_run = register_input(source, landing_dir, manifest, "v1")

    assert second_run["status"] == "duplicate"
    assert second_run["run_id"] == first_run["run_id"]


def test_same_file_with_new_rule_version_is_registered(tmp_path):
    source = tmp_path / "session.json"
    source.write_text('{"session_id": "SESSION-001"}')

    landing_dir = tmp_path / "landing"
    manifest = tmp_path / "metadata" / "manifest.json"

    first_run = register_input(source, landing_dir, manifest, "v1")

    mark_run_completed(manifest, first_run["run_id"])

    second_run = register_input(source, landing_dir, manifest, "v2")

    assert second_run["status"] == "registered"
    assert second_run["run_id"] != first_run["run_id"]


def test_failed_run_can_be_retried(tmp_path):
    source = tmp_path / "session.json"
    source.write_text('{"session_id": "SESSION-001"}')

    landing_dir = tmp_path / "landing"
    manifest = tmp_path / "metadata" / "manifest.json"

    first_run = register_input(source, landing_dir, manifest, "v1")

    # The first run remains registered, not completed.
    second_run = register_input(source, landing_dir, manifest, "v1")

    assert first_run["status"] == "registered"
    assert second_run["status"] == "registered"
    assert first_run["run_id"] != second_run["run_id"]


def test_does_not_overwrite_different_landing_file(tmp_path):
    source = tmp_path / "session.json"
    source.write_text('{"session_id": "SESSION-001"}')

    landing_dir = tmp_path / "landing"
    landing_dir.mkdir()

    (landing_dir / "session.json").write_text('{"session_id": "DIFFERENT-SESSION"}')

    manifest = tmp_path / "metadata" / "manifest.json"

    try:
        register_input(source, landing_dir, manifest, "v1")
        assert False, "Expected landing collision to fail"
    except ValueError as exc:
        assert "Refusing to overwrite" in str(exc)
