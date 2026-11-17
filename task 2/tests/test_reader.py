import pytest

from gps_pipeline.reader import read_json


def test_reader_loads_valid_json():
    data = read_json(
        __import__("pathlib").Path("data/raw/gps_session_SES-20261014-AM.json")
    )

    assert isinstance(data, dict)
    assert "export" in data
    assert "session" in data
    assert "athletes" in data


def test_reader_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        read_json(__import__("pathlib").Path("missing.json"))


def test_reader_rejects_malformed_json(tmp_path):
    bad_file = tmp_path / "invalid.json"
    bad_file.write_text('{"session": ', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        read_json(bad_file)
