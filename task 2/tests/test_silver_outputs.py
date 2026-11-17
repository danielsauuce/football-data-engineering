from pathlib import Path

import pandas as pd

from gps_pipeline.reader import read_json
from gps_pipeline.schema import validate_session_structure
from gps_pipeline.bronze import build_bronze_tables
from gps_pipeline.silver import build_silver_tables
from gps_pipeline.silver_outputs import write_silver_tables

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "gps_session_SES-20261014-AM.json"
)


def build_tables():
    data = read_json(DATA_PATH)
    validate_session_structure(data)

    bronze = build_bronze_tables(data)
    silver = build_silver_tables(bronze)

    return data, silver


def test_silver_tables_are_written_to_session_folder(tmp_path):
    data, tables = build_tables()

    paths = write_silver_tables(
        tables,
        tmp_path,
        data["session"]["session_id"],
    )

    expected_names = {
        "session.parquet",
        "athlete.parquet",
        "athlete_assignment.parquet",
        "drill.parquet",
        "athlete_summary.parquet",
        "athlete_drill_metric.parquet",
        "gps_sample.parquet",
    }

    assert {path.name for path in paths} == expected_names

    session_dir = tmp_path / data["session"]["session_id"]
    assert session_dir.exists()


def test_silver_parquet_files_preserve_row_counts(tmp_path):
    data, tables = build_tables()

    write_silver_tables(
        tables,
        tmp_path,
        data["session"]["session_id"],
    )

    session_dir = tmp_path / data["session"]["session_id"]

    for table_name, expected in tables.items():
        actual = pd.read_parquet(session_dir / f"{table_name}.parquet")

        assert len(actual) == len(expected)


def test_silver_parquet_preserves_utc_timestamps(tmp_path):
    data, tables = build_tables()

    write_silver_tables(
        tables,
        tmp_path,
        data["session"]["session_id"],
    )

    session_dir = tmp_path / data["session"]["session_id"]

    samples = pd.read_parquet(session_dir / "gps_sample.parquet")

    assert isinstance(
        samples["ts"].dtype,
        pd.DatetimeTZDtype,
    )
    assert str(samples["ts"].dt.tz) == "UTC"


def test_silver_parquet_preserves_assignment_keys(tmp_path):
    data, tables = build_tables()

    write_silver_tables(
        tables,
        tmp_path,
        data["session"]["session_id"],
    )

    session_dir = tmp_path / data["session"]["session_id"]

    assignments = pd.read_parquet(session_dir / "athlete_assignment.parquet")

    assert assignments["assignment_id"].is_unique

    athlete_014 = assignments[assignments["athlete_id"] == "ATH-014"]

    assert len(athlete_014) == 2
