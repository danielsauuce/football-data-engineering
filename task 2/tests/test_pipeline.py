from pathlib import Path

import pytest

from gps_pipeline.pipeline import run_pipeline
from gps_pipeline.schema import SchemaValidationError


def test_pipeline_rejects_missing_input(tmp_path):
    """The pipeline must reject a file that does not exist."""

    input_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        run_pipeline(input_file)


def test_pipeline_rejects_invalid_session_structure(tmp_path):
    """An existing JSON file must still satisfy the GPS data contract."""

    input_file = tmp_path / "session.json"
    input_file.write_text("{}", encoding="utf-8")

    with pytest.raises(
        SchemaValidationError,
        match="GPS session structure is invalid",
    ):
        run_pipeline(input_file)
