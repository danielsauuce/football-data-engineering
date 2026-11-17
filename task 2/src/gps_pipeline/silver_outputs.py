from pathlib import Path

from gps_pipeline.outputs import write_parquet_tables


def write_silver_tables(
    tables: dict,
    silver_root: Path,
    session_id: str,
) -> list[Path]:
    """
    Persist Silver tables as Parquet files under a session folder.
    """
    session_output_dir = silver_root / session_id

    return write_parquet_tables(
        tables=tables,
        output_dir=session_output_dir,
    )
