import pandas as pd

from gps_pipeline.gold_outputs import write_gold_tables


def sample_gold_tables():
    return {
        "gold_athlete_summary": pd.DataFrame(
            [
                {
                    "assignment_id": "A1",
                    "total_distance_m": 5000,
                    "dq_status": "clear",
                    "dq_issue_count": 0,
                },
                {
                    "assignment_id": "A2",
                    "total_distance_m": 4000,
                    "dq_status": "needs_review",
                    "dq_issue_count": 1,
                },
                {
                    "assignment_id": "A3",
                    "total_distance_m": 4500,
                    "dq_status": "confirmed_ok",
                    "dq_issue_count": 1,
                },
                {
                    "assignment_id": "A4",
                    "total_distance_m": 3000,
                    "dq_status": "confirmed_error",
                    "dq_issue_count": 1,
                },
            ]
        ),
        "gold_gps_sample": pd.DataFrame(
            [
                {
                    "assignment_id": "A1",
                    "sample_seq": 1,
                    "dq_status": "clear",
                    "dq_issue_count": 0,
                },
                {
                    "assignment_id": "A1",
                    "sample_seq": 2,
                    "dq_status": "needs_review",
                    "dq_issue_count": 1,
                },
            ]
        ),
    }


def test_writes_gold_tables_to_session_directory(tmp_path):
    tables = sample_gold_tables()

    paths = write_gold_tables(
        tables,
        tmp_path / "gold",
        "SESSION-1",
    )

    gold_dir = tmp_path / "gold" / "SESSION-1"

    assert (gold_dir / "gold_athlete_summary.parquet").exists()
    assert (gold_dir / "gold_gps_sample.parquet").exists()

    assert len(paths) == 4


def test_writes_trusted_tables_to_separate_directory(tmp_path):
    tables = sample_gold_tables()

    write_gold_tables(
        tables,
        tmp_path / "gold",
        "SESSION-1",
    )

    trusted_dir = tmp_path / "gold" / "SESSION-1" / "trusted"

    assert (trusted_dir / "gold_athlete_summary.parquet").exists()
    assert (trusted_dir / "gold_gps_sample.parquet").exists()


def test_trusted_output_excludes_unreviewed_and_confirmed_errors(tmp_path):
    tables = sample_gold_tables()

    write_gold_tables(
        tables,
        tmp_path / "gold",
        "SESSION-1",
    )

    trusted_path = (
        tmp_path / "gold" / "SESSION-1" / "trusted" / "gold_athlete_summary.parquet"
    )

    trusted = pd.read_parquet(trusted_path)

    assert trusted["assignment_id"].tolist() == ["A1", "A3"]


def test_complete_gold_output_retains_all_records(tmp_path):
    tables = sample_gold_tables()

    write_gold_tables(
        tables,
        tmp_path / "gold",
        "SESSION-1",
    )

    gold_path = tmp_path / "gold" / "SESSION-1" / "gold_athlete_summary.parquet"

    gold = pd.read_parquet(gold_path)

    assert len(gold) == 4
    assert "needs_review" in gold["dq_status"].values
    assert "confirmed_error" in gold["dq_status"].values


def test_trusted_output_preserves_quality_metadata(tmp_path):
    tables = sample_gold_tables()

    write_gold_tables(
        tables,
        tmp_path / "gold",
        "SESSION-1",
    )

    trusted_path = (
        tmp_path / "gold" / "SESSION-1" / "trusted" / "gold_athlete_summary.parquet"
    )

    trusted = pd.read_parquet(trusted_path)

    assert "dq_status" in trusted.columns
    assert "dq_issue_count" in trusted.columns
