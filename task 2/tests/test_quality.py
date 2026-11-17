import json

import pandas as pd
import pytest

from gps_pipeline.quality import run_quality_checks


def make_config(rule):
    """Create a quality configuration containing one rule."""
    return {
        "version": "1.0",
        "rules": [rule],
    }


# --------------------------------------------------
# SINGLE-FIELD RULE TESTS
# --------------------------------------------------


def test_flags_gps_speed_above_threshold():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-007",
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 10,
                    "speed_ms": 12.11,
                },
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-014",
                    "assignment_id": "ASSIGNMENT-2",
                    "sample_seq": 11,
                    "speed_ms": 5.2,
                },
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10.0,
            "severity": "high",
            "enabled": True,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert len(issues) == 1
    assert issues.iloc[0]["athlete_id"] == "ATH-007"
    assert issues.iloc[0]["sample_seq"] == 10
    assert issues.iloc[0]["rule_id"] == "GPS_SPEED_SPIKE"
    assert issues.iloc[0]["status"] == "open"


def test_flags_high_heart_rate():
    tables = {
        "athlete_summary": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-022",
                    "assignment_id": "ASSIGNMENT-1",
                    "max_hr_bpm": 236,
                }
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "HEART_RATE_ABOVE_PLAUSIBLE",
            "table": "athlete_summary",
            "field": "max_hr_bpm",
            "operator": "greater_than",
            "threshold": 220,
            "severity": "high",
            "enabled": True,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert len(issues) == 1
    assert issues.iloc[0]["athlete_id"] == "ATH-022"
    assert issues.iloc[0]["observed_value"] == "236"


def test_valid_records_do_not_create_issues():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-014",
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 1,
                    "speed_ms": 5.2,
                }
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10.0,
            "severity": "high",
            "enabled": True,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert issues.empty
    assert "issue_id" in issues.columns


def test_disabled_rules_are_not_applied():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-007",
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 10,
                    "speed_ms": 12.11,
                }
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10.0,
            "severity": "high",
            "enabled": False,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert issues.empty


# --------------------------------------------------
# DATA PRESERVATION AND ISSUE ID TESTS
# --------------------------------------------------


def test_quality_checks_do_not_modify_source_data():
    original = pd.DataFrame(
        [
            {
                "session_id": "SESSION-1",
                "athlete_id": "ATH-007",
                "assignment_id": "ASSIGNMENT-1",
                "sample_seq": 10,
                "speed_ms": 12.11,
            }
        ]
    )

    original_copy = original.copy(deep=True)

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10.0,
            "severity": "high",
            "enabled": True,
        }
    )

    run_quality_checks(
        {"gps_sample": original},
        config,
        "RUN-001",
        "abc123",
    )

    pd.testing.assert_frame_equal(
        original,
        original_copy,
    )


def test_same_source_and_rule_produce_repeatable_issue_id():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-007",
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 10,
                    "speed_ms": 12.11,
                }
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10.0,
            "severity": "high",
            "enabled": True,
        }
    )

    first_run = run_quality_checks(tables, config, "RUN-001", "abc123")

    second_run = run_quality_checks(tables, config, "RUN-002", "abc123")

    assert first_run.iloc[0]["issue_id"] == second_run.iloc[0]["issue_id"]


def test_changed_input_hash_produces_different_issue_id():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-007",
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 10,
                    "speed_ms": 12.11,
                }
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10.0,
            "severity": "high",
            "enabled": True,
        }
    )

    first_run = run_quality_checks(tables, config, "RUN-001", "abc123")

    second_run = run_quality_checks(tables, config, "RUN-002", "different-hash")

    assert first_run.iloc[0]["issue_id"] != second_run.iloc[0]["issue_id"]


# --------------------------------------------------
# COMPOUND RULE TESTS
# --------------------------------------------------


def test_flags_coordinates_when_both_are_zero():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-031",
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 5,
                    "latitude": 0,
                    "longitude": 0,
                },
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-014",
                    "assignment_id": "ASSIGNMENT-2",
                    "sample_seq": 6,
                    "latitude": 0,
                    "longitude": -1.2,
                },
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_ZERO_COORDINATES",
            "table": "gps_sample",
            "fields": ["latitude", "longitude"],
            "operator": "both_equal",
            "threshold": 0,
            "severity": "high",
            "enabled": True,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert len(issues) == 1
    assert issues.iloc[0]["athlete_id"] == "ATH-031"
    assert issues.iloc[0]["field"] == "latitude, longitude"

    observed = json.loads(issues.iloc[0]["observed_value"])

    assert observed["latitude"] == 0
    assert observed["longitude"] == 0


def test_compound_rule_rejects_wrong_number_of_fields():
    tables = {"gps_sample": pd.DataFrame([{"latitude": 0, "longitude": 0}])}

    config = make_config(
        {
            "rule_id": "GPS_ZERO_COORDINATES",
            "table": "gps_sample",
            "fields": ["latitude"],
            "operator": "both_equal",
            "threshold": 0,
            "severity": "high",
            "enabled": True,
        }
    )

    with pytest.raises(
        ValueError,
        match="exactly two fields",
    ):
        run_quality_checks(tables, config, "RUN-001", "abc123")


# --------------------------------------------------
# TIMESTAMP SEQUENCE TESTS
# --------------------------------------------------


def test_flags_out_of_order_gps_timestamps():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "assignment_id": "ASSIGNMENT-1",
                    "athlete_id": "ATH-009",
                    "sample_seq": 1,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:30",
                        tz="UTC",
                    ),
                },
                {
                    "assignment_id": "ASSIGNMENT-1",
                    "athlete_id": "ATH-009",
                    "sample_seq": 2,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:40",
                        tz="UTC",
                    ),
                },
                {
                    "assignment_id": "ASSIGNMENT-1",
                    "athlete_id": "ATH-009",
                    "sample_seq": 3,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:50",
                        tz="UTC",
                    ),
                },
                {
                    "assignment_id": "ASSIGNMENT-1",
                    "athlete_id": "ATH-009",
                    "sample_seq": 4,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:40",
                        tz="UTC",
                    ),
                },
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_TIMESTAMP_OUT_OF_ORDER",
            "table": "gps_sample",
            "field": "ts",
            "operator": "timestamp_not_increasing",
            "group_by": "assignment_id",
            "order_by": "sample_seq",
            "severity": "medium",
            "enabled": True,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert len(issues) == 1
    assert issues.iloc[0]["sample_seq"] == 4
    assert issues.iloc[0]["athlete_id"] == "ATH-009"
    assert issues.iloc[0]["previous_value"] is not None

    observed = json.loads(issues.iloc[0]["observed_value"])

    assert observed == "2026-10-14 10:12:40+00:00"


def test_timestamp_ordering_is_separate_for_each_assignment():
    tables = {
        "gps_sample": pd.DataFrame(
            [
                {
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 1,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:30",
                        tz="UTC",
                    ),
                },
                {
                    "assignment_id": "ASSIGNMENT-2",
                    "sample_seq": 1,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:20",
                        tz="UTC",
                    ),
                },
                {
                    "assignment_id": "ASSIGNMENT-1",
                    "sample_seq": 2,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:40",
                        tz="UTC",
                    ),
                },
                {
                    "assignment_id": "ASSIGNMENT-2",
                    "sample_seq": 2,
                    "ts": pd.Timestamp(
                        "2026-10-14 10:12:25",
                        tz="UTC",
                    ),
                },
            ]
        )
    }

    config = make_config(
        {
            "rule_id": "GPS_TIMESTAMP_OUT_OF_ORDER",
            "table": "gps_sample",
            "field": "ts",
            "operator": "timestamp_not_increasing",
            "group_by": "assignment_id",
            "order_by": "sample_seq",
            "severity": "medium",
            "enabled": True,
        }
    )

    issues = run_quality_checks(tables, config, "RUN-001", "abc123")

    assert issues.empty


# --------------------------------------------------
# CONFIGURATION VALIDATION TESTS
# --------------------------------------------------


def test_missing_table_raises_clear_error():
    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10,
            "severity": "high",
            "enabled": True,
        }
    )

    with pytest.raises(
        ValueError,
        match="missing table",
    ):
        run_quality_checks({}, config, "RUN-001", "abc123")


def test_missing_field_raises_clear_error():
    tables = {"gps_sample": pd.DataFrame([{"latitude": 50.9}])}

    config = make_config(
        {
            "rule_id": "GPS_SPEED_SPIKE",
            "table": "gps_sample",
            "field": "speed_ms",
            "operator": "greater_than",
            "threshold": 10,
            "severity": "high",
            "enabled": True,
        }
    )

    with pytest.raises(
        ValueError,
        match="missing field",
    ):
        run_quality_checks(tables, config, "RUN-001", "abc123")
