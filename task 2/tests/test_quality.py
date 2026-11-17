import pandas as pd

from gps_pipeline.quality import run_quality_checks


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

    config = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "GPS_SPEED_SPIKE",
                "table": "gps_sample",
                "field": "speed_ms",
                "operator": "greater_than",
                "threshold": 10.0,
                "severity": "high",
                "enabled": True,
            }
        ],
    }

    issues = run_quality_checks(
        tables,
        config,
        run_id="RUN-001",
        input_sha256="abc123",
    )

    assert len(issues) == 1
    assert issues.iloc[0]["athlete_id"] == "ATH-007"
    assert issues.iloc[0]["sample_seq"] == 10
    assert issues.iloc[0]["rule_id"] == "GPS_SPEED_SPIKE"


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

    config = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "HEART_RATE_ABOVE_PLAUSIBLE",
                "table": "athlete_summary",
                "field": "max_hr_bpm",
                "operator": "greater_than",
                "threshold": 220,
                "severity": "high",
                "enabled": True,
            }
        ],
    }

    issues = run_quality_checks(
        tables,
        config,
        run_id="RUN-001",
        input_sha256="abc123",
    )

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

    config = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "GPS_SPEED_SPIKE",
                "table": "gps_sample",
                "field": "speed_ms",
                "operator": "greater_than",
                "threshold": 10.0,
                "severity": "high",
                "enabled": True,
            }
        ],
    }

    issues = run_quality_checks(
        tables,
        config,
        run_id="RUN-001",
        input_sha256="abc123",
    )

    assert issues.empty


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

    config = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "GPS_SPEED_SPIKE",
                "table": "gps_sample",
                "field": "speed_ms",
                "operator": "greater_than",
                "threshold": 10.0,
                "severity": "high",
                "enabled": False,
            }
        ],
    }

    issues = run_quality_checks(
        tables,
        config,
        run_id="RUN-001",
        input_sha256="abc123",
    )

    assert issues.empty


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

    tables = {"gps_sample": original}

    config = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "GPS_SPEED_SPIKE",
                "table": "gps_sample",
                "field": "speed_ms",
                "operator": "greater_than",
                "threshold": 10.0,
                "severity": "high",
                "enabled": True,
            }
        ],
    }

    run_quality_checks(
        tables,
        config,
        run_id="RUN-001",
        input_sha256="abc123",
    )

    pd.testing.assert_frame_equal(original, original_copy)


def test_same_input_and_rule_produce_repeatable_issue_id():
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

    config = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "GPS_SPEED_SPIKE",
                "table": "gps_sample",
                "field": "speed_ms",
                "operator": "greater_than",
                "threshold": 10.0,
                "severity": "high",
                "enabled": True,
            }
        ],
    }

    first_run = run_quality_checks(tables, config, "RUN-001", "abc123")

    second_run = run_quality_checks(tables, config, "RUN-002", "abc123")

    assert first_run.iloc[0]["issue_id"] == second_run.iloc[0]["issue_id"]
