
from pathlib import Path

import pandas as pd

from gps_pipeline.gold import build_trusted_tables
from gps_pipeline.outputs import write_parquet_tables


def write_gold_tables(
    gold_tables: dict[str, pd.DataFrame],
    gold_root: Path,
    session_id: str,
) -> list[Path]:
    """
    Persist complete Gold tables and trusted consumer tables.

    Complete tables retain all records and their quality statuses.
    Trusted tables exclude needs_review and confirmed_error records.
    """

    session_output_dir = gold_root / session_id
    trusted_output_dir = session_output_dir / "trusted"

    # Publish all Gold records.
    written_files = write_parquet_tables(
        tables=gold_tables,
        output_dir=session_output_dir,
    )

    # Build and publish trusted consumer datasets.
    trusted_tables = build_trusted_tables(gold_tables)

    trusted_files = write_parquet_tables(
        tables=trusted_tables,
        output_dir=trusted_output_dir,
    )

    return written_files + trusted_files
