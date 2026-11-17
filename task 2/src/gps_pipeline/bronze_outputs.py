from pathlib import Path

from gps_pipeline.outputs import write_parquet_tables


def write_bronze_tables(
    tables: dict,
    bronze_root: Path,
    session_id: str,
) -> list[Path]:
    """
    Persist Bronze tables as Parquet files under a session folder.
    """
    session_output_dir = bronze_root / session_id

    return write_parquet_tables(
        tables=tables,
        output_dir=session_output_dir,
    )
