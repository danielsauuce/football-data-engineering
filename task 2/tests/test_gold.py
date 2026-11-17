import pandas as pd
import pytest

from gps_pipeline.gold import (
    build_gold_tables,
    build_trusted_tables,
)


def make_silver_tables():
    return {
        "session": pd.DataFrame(
            [
                {"session_id": "SESSION-1", "team": "First Team"},
            ]
        ),
        "athlete": pd.DataFrame(
            [
                {"athlete_id": "ATH-001", "display_name": "Player 1"},
                {"athlete_id": "ATH-002", "display_name": "Player 2"},
            ]
        ),
        "athlete_assignment": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-001",
                    "device_id": "GPS-001",
                    "assignment_id": "ASSIGN-001",
                },
                {
                    "session_id": "SESSION-1",
                    "athlete_id": "ATH-002",
                    "device_id": "GPS-002",
                    "assignment_id": "ASSIGN-002",
                },
            ]
        ),
        "drill": pd.DataFrame(
            [
                {
                    "session_id": "SESSION-1",
                    "drill_id": "DRILL-001",
                    "drill_name": "Warm up",
                },
            ]
        ),
        "athlete_summary": pd.DataFrame(
            [
                {
                    "assignment_id": "ASSIGN-001",
                    "total_distance_m": 5000,
                    "max_speed_kmh": 38,
                },
                {
                    "assignment_id": "ASSIGN-002",
                    "total_distance_m": 4000,
                    "max_speed_kmh": 25,
                },
            ]
        ),
        "athlete_drill_metric": pd.DataFrame(
            [
                {
                    "assignment_id": "ASSIGN-001",
                    "drill_id": "DRILL-001",
                    "total_distance_m": 1000,
                },
            ]
        ),
        "gps_sample": pd.DataFrame(
            [
                {
                    "assignment_id": "ASSIGN-001",
                    "sample_seq": 1,
                    "speed_kmh": 20,
                },
                {
                    "assignment_id": "ASSIGN-001",
                    "sample_seq": 2,
                    "speed_kmh": 45,
                },
                {
                    "assignment_id": "ASSIGN-002",
                    "sample_seq": 1,
                    "speed_kmh": 18,
                },
            ]
        ),
    }


def make_issues():
    return pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-001",
                "table_name": "gps_sample",
                "row_reference": "ASSIGN-001|sample:2",
                "session_id": "SESSION-1",
                "athlete_id": "ATH-001",
                "assignment_id": "ASSIGN-001",
                "drill_id": None,
                "sample_seq": 2,
            },
            {
                "issue_id": "ISSUE-002",
                "table_name": "athlete_summary",
                "row_reference": "ASSIGN-001",
                "session_id": "SESSION-1",
                "athlete_id": "ATH-001",
                "assignment_id": "ASSIGN-001",
                "drill_id": None,
                "sample_seq": None,
            },
        ]
    )


def empty_reviews():
    return pd.DataFrame(columns=["issue_id", "decision"])


def test_builds_all_seven_gold_tables():
    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        empty_reviews(),
    )

    assert len(gold) == 7

    assert set(gold) == {
        "gold_session",
        "gold_athlete",
        "gold_athlete_assignment",
        "gold_drill",
        "gold_athlete_summary",
        "gold_athlete_drill_metric",
        "gold_gps_sample",
    }


def test_every_gold_table_has_quality_columns():
    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        empty_reviews(),
    )

    for dataframe in gold.values():
        assert "dq_status" in dataframe.columns
        assert "dq_issue_count" in dataframe.columns


def test_unresolved_gps_issue_only_affects_matching_sample():
    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        empty_reviews(),
    )

    gps = gold["gold_gps_sample"]

    assert gps.loc[0, "dq_status"] == "clear"
    assert gps.loc[1, "dq_status"] == "needs_review"
    assert gps.loc[2, "dq_status"] == "clear"

    assert gps.loc[1, "dq_issue_count"] == 1


def test_unresolved_summary_issue_affects_matching_assignment():
    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        empty_reviews(),
    )

    summary = gold["gold_athlete_summary"]

    assert summary.loc[0, "dq_status"] == "needs_review"
    assert summary.loc[1, "dq_status"] == "clear"


def test_confirmed_ok_issue_is_accepted():
    reviews = pd.DataFrame(
        [
            {"issue_id": "ISSUE-001", "decision": "confirmed_ok"},
            {"issue_id": "ISSUE-002", "decision": "confirmed_ok"},
        ]
    )

    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        reviews,
    )

    gps = gold["gold_gps_sample"]

    assert gps.loc[1, "dq_status"] == "confirmed_ok"
    assert gps.loc[1, "dq_issue_count"] == 1


def test_confirmed_error_is_excluded_from_trusted_data():
    reviews = pd.DataFrame(
        [
            {"issue_id": "ISSUE-001", "decision": "confirmed_error"},
        ]
    )

    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        reviews,
    )

    trusted = build_trusted_tables(gold)

    gps = trusted["gold_gps_sample"]

    assert len(gps) == 2
    assert "needs_review" not in gps["dq_status"].values
    assert "confirmed_error" not in gps["dq_status"].values


def test_unreviewed_records_are_excluded_from_trusted_data():
    gold = build_gold_tables(
        make_silver_tables(),
        make_issues(),
        empty_reviews(),
    )

    trusted = build_trusted_tables(gold)

    gps = trusted["gold_gps_sample"]

    assert len(gps) == 2
    assert gps["dq_status"].eq("clear").all()


def test_records_without_issues_are_clear():
    gold = build_gold_tables(
        make_silver_tables(),
        pd.DataFrame(),
        empty_reviews(),
    )

    for dataframe in gold.values():
        assert dataframe["dq_status"].eq("clear").all()
        assert dataframe["dq_issue_count"].eq(0).all()


def test_missing_silver_table_raises_error():
    tables = make_silver_tables()
    del tables["gps_sample"]

    with pytest.raises(ValueError, match="Missing Silver table"):
        build_gold_tables(
            tables,
            make_issues(),
            empty_reviews(),
        )


def test_source_silver_data_is_not_modified():
    silver = make_silver_tables()
    original = silver["gps_sample"].copy(deep=True)

    build_gold_tables(
        silver,
        make_issues(),
        empty_reviews(),
    )

    pd.testing.assert_frame_equal(
        silver["gps_sample"],
        original,
    )


def test_multiple_issues_counted_on_same_record():
    issues = pd.concat(
        [
            make_issues(),
            pd.DataFrame(
                [
                    {
                        "issue_id": "ISSUE-003",
                        "table_name": "gps_sample",
                        "row_reference": "ASSIGN-001|sample:2",
                        "session_id": "SESSION-1",
                        "athlete_id": "ATH-001",
                        "assignment_id": "ASSIGN-001",
                        "drill_id": None,
                        "sample_seq": 2,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )

    gold = build_gold_tables(
        make_silver_tables(),
        issues,
        empty_reviews(),
    )

    gps = gold["gold_gps_sample"]

    assert gps.loc[1, "dq_issue_count"] == 2


def test_confirmed_error_takes_precedence_over_confirmed_ok():
    reviews = pd.DataFrame(
        [
            {"issue_id": "ISSUE-001", "decision": "confirmed_ok"},
            {"issue_id": "ISSUE-003", "decision": "confirmed_error"},
        ]
    )

    issues = pd.concat(
        [
            make_issues().iloc[[0]],
            pd.DataFrame(
                [
                    {
                        "issue_id": "ISSUE-003",
                        "table_name": "gps_sample",
                        "row_reference": "ASSIGN-001|sample:2",
                        "session_id": "SESSION-1",
                        "athlete_id": "ATH-001",
                        "assignment_id": "ASSIGN-001",
                        "drill_id": None,
                        "sample_seq": 2,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )

    gold = build_gold_tables(
        make_silver_tables(),
        issues,
        reviews,
    )

    assert gold["gold_gps_sample"].loc[1, "dq_status"] == "confirmed_error"
