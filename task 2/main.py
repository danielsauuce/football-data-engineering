import argparse
from pathlib import Path

from gps_pipeline.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Process a GPS session export."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the vendor GPS session JSON file.",
    )

    return parser.parse_args()


def main() -> None:
    """Start the GPS pipeline."""

    args = parse_args()

    run_pipeline(input_path=args.input)


if __name__ == "__main__":
    main()
