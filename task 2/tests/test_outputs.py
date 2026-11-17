from pathlib import Path

import pandas as pd

from gps_pipeline.outputs import write_parquet_tables


def test_writes_each_table_as_parquet(tmp_path):
    tables = {
        "athlete_sessions": pd.DataFrame(
            {
                "athlete_id": ["ATH-014", "ATH-007"],
                "total_distance_m": [6120.4, 5900.0],
            }
        ),
        "athlete_drills": pd.DataFrame(
            {
                "athlete_id": ["ATH-014"],
                "drill_id": ["D1"],
            }
        ),
        "gps_samples": pd.DataFrame(
            {
                "athlete_id": ["ATH-014"],
                "speed_ms": [1.86],
            }
        ),
    }

    written_files = write_parquet_tables(tables, tmp_path)

    assert len(written_files) == 3

    for table_name, expected_dataframe in tables.items():
        output_path = tmp_path / f"{table_name}.parquet"

        assert output_path.exists()

        actual_dataframe = pd.read_parquet(output_path)

        pd.testing.assert_frame_equal(
            actual_dataframe,
            expected_dataframe,
        )


def test_does_not_leave_staging_directory_behind(tmp_path):
    tables = {
        "athlete_sessions": pd.DataFrame(
            {
                "athlete_id": ["ATH-014"],
            }
        ),
    }

    write_parquet_tables(tables, tmp_path)

    remaining_files = list(tmp_path.iterdir())

    assert len(remaining_files) == 1
    assert remaining_files[0].name == "athlete_sessions.parquet"


def test_failed_write_does_not_replace_existing_output(
    tmp_path,
    monkeypatch,
):
    output_path = tmp_path / "athlete_sessions.parquet"

    original_dataframe = pd.DataFrame(
        {
            "athlete_id": ["ATH-014"],
        }
    )
    original_dataframe.to_parquet(output_path, index=False)

    new_dataframe = pd.DataFrame(
        {
            "athlete_id": ["ATH-007"],
        }
    )

    def fail_to_parquet(*args, **kwargs):
        raise OSError("Simulated disk write failure")

    monkeypatch.setattr(
        pd.DataFrame,
        "to_parquet",
        fail_to_parquet,
    )

    try:
        write_parquet_tables(
            {"athlete_sessions": new_dataframe},
            tmp_path,
        )
        assert False, "Expected the write to fail"
    except OSError as exc:
        assert "Simulated disk write failure" in str(exc)

    # The previous output should remain unchanged.
    monkeypatch.undo()

    actual_dataframe = pd.read_parquet(output_path)

    pd.testing.assert_frame_equal(
        actual_dataframe,
        original_dataframe,
    )
