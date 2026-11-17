from pathlib import Path
import pandas as pd

from gps_pipeline.reader import read_json
from gps_pipeline.schema import validate_session_structure
from gps_pipeline.bronze import build_bronze_tables
from gps_pipeline.silver import build_silver_tables

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "gps_session_SES-20261014-AM.json"
)


def load_silver_tables():
    data = read_json(DATA_PATH)
    validate_session_structure(data)

    bronze = build_bronze_tables(data)
    return build_silver_tables(bronze)


def test_silver_tables_have_expected_row_counts():
    tables = load_silver_tables()

    assert len(tables["session"]) == 1
    assert len(tables["athlete"]) == 6
    assert len(tables["athlete_assignment"]) == 7
    assert len(tables["drill"]) == 2
    assert len(tables["athlete_summary"]) == 7
    assert len(tables["athlete_drill_metric"]) == 14
    assert len(tables["gps_sample"]) == 78


def test_athlete_and_device_assignments_are_separate():
    tables = load_silver_tables()

    athletes = tables["athlete"]
    assignments = tables["athlete_assignment"]

    assert len(athletes[athletes["athlete_id"] == "ATH-014"]) == 1

    athlete_assignments = assignments[assignments["athlete_id"] == "ATH-014"]

    assert len(athlete_assignments) == 2
    assert athlete_assignments["device_id"].nunique() == 2


def test_assignment_ids_are_unique():
    tables = load_silver_tables()

    assignments = tables["athlete_assignment"]

    assert assignments["assignment_id"].is_unique


def test_gps_speed_is_converted_without_replacing_source_value():
    tables = load_silver_tables()

    samples = tables["gps_sample"]

    first_sample = samples.iloc[0]

    assert first_sample["speed_kmh"] == first_sample["speed_ms"] * 3.6


def test_gps_timestamps_are_timezone_aware():
    tables = load_silver_tables()

    samples = tables["gps_sample"]

    assert isinstance(
        samples["ts"].dtype,
        pd.DatetimeTZDtype,
    )

    assert str(samples["ts"].dt.tz) == "UTC"


def test_gps_sample_sequence_is_preserved():
    tables = load_silver_tables()

    samples = tables["gps_sample"]

    athlete_009 = samples[samples["assignment_id"].str.contains("ATH-009")].sort_values(
        "sample_seq"
    )

    timestamps = athlete_009["ts"].tolist()

    assert timestamps[4] > timestamps[5]


def test_silver_retains_suspicious_source_measurements():
    tables = load_silver_tables()

    summaries = tables["athlete_summary"]

    athlete_009 = summaries[summaries["assignment_id"].str.contains("ATH-009")]

    assert athlete_009.iloc[0]["decelerations"] == -2
