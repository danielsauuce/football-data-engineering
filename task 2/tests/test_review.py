import pandas as pd
import pytest

from gps_pipeline.review import create_review_file


def sample_issues():
    return pd.DataFrame(
        [
            {
                "issue_id": "issue-001",
                "rule_id": "GPS_SPEED_SPIKE",
                "table_name": "gps_sample",
                "row_reference": "assignment-1|sample:4",
                "severity": "high",
                "observed_value": "12.11",
                "expected_condition": "speed_ms greater_than 10",
            },
            {
                "issue_id": "issue-002",
                "rule_id": "HEART_RATE_ZERO",
                "table_name": "gps_sample",
                "row_reference": "assignment-1|sample:8",
                "severity": "medium",
                "observed_value": "0",
                "expected_condition": "hr_bpm equals 0",
            },
        ]
    )


def test_creates_review_file_with_undecided_issues(tmp_path):
    path = create_review_file(
        sample_issues(),
        tmp_path,
        "SESSION-1",
    )

    review = pd.read_csv(path)

    assert len(review) == 2
    assert review["decision"].isna().all()
    assert path.name == "dq_review.csv"


def test_preserves_existing_review_decision(tmp_path):
    path = create_review_file(
        sample_issues(),
        tmp_path,
        "SESSION-1",
    )

    review = pd.read_csv(path, dtype=str, keep_default_na=False)
    review.loc[0, "decision"] = "confirmed_ok"
    review.loc[0, "reviewed_by"] = "Sports Science"
    review.loc[0, "review_comment"] = "Sensor reading verified"

    review.to_csv(path, index=False)

    create_review_file(
        sample_issues(),
        tmp_path,
        "SESSION-1",
    )

    updated = pd.read_csv(path, dtype=str, keep_default_na=False)

    assert updated.loc[0, "decision"] == "confirmed_ok"
    assert updated.loc[0, "reviewed_by"] == "Sports Science"
    assert updated.loc[0, "review_comment"] == "Sensor reading verified"


def test_new_issues_are_added_without_losing_old_decisions(tmp_path):
    path = create_review_file(
        sample_issues(),
        tmp_path,
        "SESSION-1",
    )

    review = pd.read_csv(path, dtype=str, keep_default_na=False)
    review.loc[0, "decision"] = "confirmed_error"
    review.to_csv(path, index=False)

    expanded = pd.concat(
        [
            sample_issues(),
            pd.DataFrame(
                [
                    {
                        "issue_id": "issue-003",
                        "rule_id": "NEW_RULE",
                        "table_name": "gps_sample",
                        "row_reference": "assignment-1|sample:9",
                        "severity": "low",
                        "observed_value": "value",
                        "expected_condition": "example condition",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    create_review_file(
        expanded,
        tmp_path,
        "SESSION-1",
    )

    updated = pd.read_csv(path, dtype=str, keep_default_na=False)

    assert len(updated) == 3
    assert updated.loc[0, "decision"] == "confirmed_error"
    assert updated.loc[2, "decision"] == ""


def test_rejects_duplicate_issue_ids(tmp_path):
    issues = pd.concat(
        [sample_issues(), sample_issues().iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="duplicate issue_id"):
        create_review_file(
            issues,
            tmp_path,
            "SESSION-1",
        )
