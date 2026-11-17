from pathlib import Path

import pandas as pd

from gps_pipeline.outputs import write_parquet_tables


def write_quality_issues(
    issues: pd.DataFrame,
    quality_root: Path,
    session_id: str,
) -> list[Path]:
    """
    Persist detected data-quality issues for a session.
    """

    session_output_dir = quality_root / session_id

    return write_parquet_tables(
        tables={"dq_issue": issues},
        output_dir=session_output_dir,
    )
