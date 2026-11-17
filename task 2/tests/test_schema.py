import copy
from pathlib import Path

import pytest

from gps_pipeline.reader import read_json
from gps_pipeline.schema import (
    SchemaValidationError,
    validate_session_structure,
)

SOURCE_FILE = Path("data/raw/gps_session_SES-20261014-AM.json")


def test_valid_session_structure():
    data = read_json(SOURCE_FILE)

    validate_session_structure(data)


def test_rejects_missing_athletes():
    data = read_json(SOURCE_FILE)
    data.pop("athletes")

    with pytest.raises(SchemaValidationError, match="athletes"):
        validate_session_structure(data)


def test_rejects_invalid_athlete_structure():
    data = read_json(SOURCE_FILE)
    data["athletes"][0].pop("samples")

    with pytest.raises(SchemaValidationError, match="samples"):
        validate_session_structure(data)


def test_rejects_invalid_root():
    with pytest.raises(SchemaValidationError, match="root"):
        validate_session_structure(["not", "an", "object"])


def test_does_not_reject_duplicate_athlete_ids():
    data = read_json(SOURCE_FILE)

    # ATH-014 appears twice because of a device change.
    athlete_ids = [athlete["athlete_id"] for athlete in data["athletes"]]

    assert athlete_ids.count("ATH-014") == 2

    validate_session_structure(data)
