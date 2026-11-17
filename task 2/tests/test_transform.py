from pathlib import Path

from gps_pipeline.reader import read_json
from gps_pipeline.schema import validate_session_structure
from gps_pipeline.transform import transform_session

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "gps_session_SES-20261014-AM.json"
)


def load_transformed_tables():
    data = read_json(DATA_PATH)
    validate_session_structure(data)
    return transform_session(data)


def test_transformation_produces_expected_row_counts():
    tables = load_transformed_tables()

    assert len(tables["athlete_sessions"]) == 7
    assert len(tables["athlete_drills"]) == 14
    assert len(tables["gps_samples"]) == 78


def test_athlete_device_entries_are_not_merged():
    tables = load_transformed_tables()
    sessions = tables["athlete_sessions"]

    athlete_014 = sessions[sessions["athlete_id"] == "ATH-014"]

    assert len(athlete_014) == 2
    assert athlete_014["device_id"].nunique() == 2


def test_gps_samples_preserve_source_order():
    tables = load_transformed_tables()
    samples = tables["gps_samples"]

    athlete_009 = samples[samples["athlete_id"] == "ATH-009"].sort_values(
        "sample_index"
    )

    timestamps = athlete_009["ts"].tolist()

    # The source contains an out-of-order pair.
    assert timestamps[4] > timestamps[5]


def test_source_measurements_are_preserved():
    tables = load_transformed_tables()

    sessions = tables["athlete_sessions"]
    samples = tables["gps_samples"]

    athlete_007 = sessions[sessions["athlete_id"] == "ATH-007"]

    assert athlete_007.iloc[0]["max_speed_kmh"] == 43.6

    athlete_007_samples = samples[samples["athlete_id"] == "ATH-007"]

    assert 12.11 in athlete_007_samples["speed_ms"].values
