from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


def write_parquet_tables(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
) -> list[Path]:
    """
    Write transformed DataFrames as Parquet files.

    All files are staged successfully before replacing the
    corresponding output files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files = []

    with TemporaryDirectory(
        prefix=".parquet_staging_",
        dir=output_dir,
    ) as temporary_dir:
        staging_dir = Path(temporary_dir)

        # First write every table to a temporary location.
        staged_files = {}

        for table_name, dataframe in tables.items():
            staged_path = staging_dir / f"{table_name}.parquet"

            dataframe.to_parquet(
                staged_path,
                index=False,
                engine="pyarrow",
            )

            staged_files[table_name] = staged_path

        for table_name, staged_path in staged_files.items():
            output_path = output_dir / f"{table_name}.parquet"
            staged_path.replace(output_path)
            written_files.append(output_path)

    return written_files
