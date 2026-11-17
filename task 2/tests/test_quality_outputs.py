import pandas as pd

from gps_pipeline.quality_outputs import write_quality_issues


def test_writes_quality_issues_to_session_directory(tmp_path):
    issues = pd.DataFrame(
        [
            {
                "issue_id": "issue-001",
                "run_id": "RUN-001",
                "rule_id": "GPS_SPEED_SPIKE",
                "athlete_id": "ATH-007",
                "observed_value": "12.11",
                "status": "open",
            }
        ]
    )

    paths = write_quality_issues(
        issues,
        tmp_path / "quality",
        "SESSION-1",
    )

    assert len(paths) == 1
    assert paths[0].name == "dq_issue.parquet"
    assert paths[0].exists()


def test_saved_quality_issues_can_be_read_back(tmp_path):
    issues = pd.DataFrame(
        [
            {
                "issue_id": "issue-001",
                "run_id": "RUN-001",
                "rule_id": "GPS_SPEED_SPIKE",
                "athlete_id": "ATH-007",
                "observed_value": "12.11",
                "status": "open",
            }
        ]
    )

    paths = write_quality_issues(
        issues,
        tmp_path / "quality",
        "SESSION-1",
    )

    saved_issues = pd.read_parquet(paths[0])

    assert len(saved_issues) == 1
    assert saved_issues.iloc[0]["rule_id"] == "GPS_SPEED_SPIKE"
    assert saved_issues.iloc[0]["athlete_id"] == "ATH-007"


def test_empty_issues_can_be_persisted(tmp_path):
    issues = pd.DataFrame(
        columns=[
            "issue_id",
            "run_id",
            "rule_id",
            "athlete_id",
            "status",
        ]
    )

    paths = write_quality_issues(
        issues,
        tmp_path / "quality",
        "SESSION-1",
    )

    saved_issues = pd.read_parquet(paths[0])

    assert saved_issues.empty
    assert "issue_id" in saved_issues.columns
