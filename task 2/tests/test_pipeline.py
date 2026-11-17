
import pytest

from gps_pipeline.pipeline import run_pipeline


def test_pipeline_rejects_missing_input(tmp_path):
    """A missing input file should fail clearly."""

    missing_file = tmp_path / "missing_session.json"

    with pytest.raises(FileNotFoundError):
        run_pipeline(missing_file)



def test_pipeline_accepts_existing_input(tmp_path):
    """An existing file should reach the pipeline."""

    input_file = tmp_path / "session.json"
    input_file.write_text("{}", encoding="utf-8")

    run_pipeline(input_file)
