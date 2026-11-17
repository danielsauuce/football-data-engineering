from pathlib import Path

from gps_pipeline.reader import read_json
from gps_pipeline.schema import validate_session_structure
from gps_pipeline.bronze import build_bronze_tables

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "gps_session_SES-20261014-AM.json"
)


def load_bronze_tables():
    data = read_json(DATA_PATH)
    validate_session_structure(data)
    return build_bronze_tables(data)


def test_bronze_tables_have_expected_row_counts():
    tables = load_bronze_tables()

    assert len(tables["bronze_session_drills"]) == 2
    assert len(tables["bronze_athlete_summary"]) == 7
    assert len(tables["bronze_drill_metric"]) == 14
    assert len(tables["bronze_gps_sample"]) == 78


def test_athlete_device_entries_are_preserved():
    tables = load_bronze_tables()
    summaries = tables["bronze_athlete_summary"]

    athlete_014 = summaries[summaries["athlete_id"] == "ATH-014"]

    assert len(athlete_014) == 2
    assert athlete_014["device_id"].nunique() == 2


def test_bronze_preserves_source_units():
    tables = load_bronze_tables()

    summaries = tables["bronze_athlete_summary"]
    samples = tables["bronze_gps_sample"]

    assert summaries["max_speed_kmh"].notna().all()
    assert samples["speed_ms"].notna().all()

    session_drills = tables["bronze_session_drills"]

    assert session_drills["summary_speed_unit"].unique().tolist() == ["km/h"]
    assert session_drills["sample_speed_unit"].unique().tolist() == ["m/s"]


def test_bronze_preserves_suspicious_values():
    tables = load_bronze_tables()

    summaries = tables["bronze_athlete_summary"]
    samples = tables["bronze_gps_sample"]

    athlete_009 = summaries[summaries["athlete_id"] == "ATH-009"]

    assert athlete_009.iloc[0]["decelerations"] == -2

    athlete_007_samples = samples[samples["athlete_id"] == "ATH-007"]

    assert 12.11 in athlete_007_samples["speed_ms"].values


def test_bronze_preserves_original_gps_sample_order():
    tables = load_bronze_tables()
    samples = tables["bronze_gps_sample"]

    athlete_009 = samples[samples["athlete_id"] == "ATH-009"].sort_values(
        "sample_index"
    )

    timestamps = athlete_009["ts"].tolist()

    assert timestamps[4] > timestamps[5]
