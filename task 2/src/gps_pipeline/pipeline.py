from pathlib import Path

def run_pipeline(input_path: Path) -> None:
    """
    Execute the GPS session pipeline.

    Stages will be implemented incrementally:
    1. Ingestion and registration
    2. Structural validation
    3. Transformation
    4. Quality checks
    5. Review decisions
    6. Publishing
    """

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {input_path}"
        )

    print(f"Starting GPS pipeline for: {input_path.name}")

    # Processing stages will be connected here.

    print("Pipeline scaffold is ready.")
