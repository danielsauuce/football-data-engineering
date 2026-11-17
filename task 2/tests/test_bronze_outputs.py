from pathlib import Path

import pandas as pd

from gps_pipeline.reader import read_json
from gps_pipeline.schema import validate_session_structure
from gps_pipeline.bronze import build_bronze_tables
from gps_pipeline.bronze_outputs import write_bronze_tables

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "gps_session_SES-20261014-AM.json"
)


def test_bronze_tables_are_written_to_session_folder(tmp_path):
    data = read_json(DATA_PATH)
    validate_session_structure(data)

    tables = build_bronze_tables(data)

    written_files = write_bronze_tables(
        tables=tables,
        bronze_root=tmp_path,
        session_id=data["session"]["session_id"],
    )

    expected_names = {
        "bronze_session_drills.parquet",
        "bronze_athlete_summary.parquet",
        "bronze_drill_metric.parquet",
        "bronze_gps_sample.parquet",
    }

    actual_names = {path.name for path in written_files}

    assert actual_names == expected_names

    session_dir = tmp_path / data["session"]["session_id"]
    assert session_dir.exists()


def test_bronze_parquet_files_preserve_row_counts(tmp_path):
    data = read_json(DATA_PATH)
    validate_session_structure(data)

    tables = build_bronze_tables(data)

    write_bronze_tables(
        tables,
        tmp_path,
        data["session"]["session_id"],
    )

    session_dir = tmp_path / data["session"]["session_id"]

    expected_counts = {
        "bronze_session_drills": 2,
        "bronze_athlete_summary": 7,
        "bronze_drill_metric": 14,
        "bronze_gps_sample": 78,
    }

    for table_name, expected_count in expected_counts.items():
        dataframe = pd.read_parquet(session_dir / f"{table_name}.parquet")

        assert len(dataframe) == expected_count


def test_bronze_parquet_preserves_suspicious_values(tmp_path):
    data = read_json(DATA_PATH)
    validate_session_structure(data)

    tables = build_bronze_tables(data)

    write_bronze_tables(
        tables,
        tmp_path,
        data["session"]["session_id"],
    )

    session_dir = tmp_path / data["session"]["session_id"]

    summaries = pd.read_parquet(session_dir / "bronze_athlete_summary.parquet")

    athlete_009 = summaries[summaries["athlete_id"] == "ATH-009"]

    assert athlete_009.iloc[0]["decelerations"] == -2
