import json
from pathlib import Path
from typing import Any


def read_json(input_path: Path) -> dict[str, Any]:
    """
    Read a JSON file and return its contents.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the file contains invalid JSON.
    """

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    try:
        with input_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {input_path}. "
            f"Line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    except UnicodeDecodeError as exc:
        raise ValueError(f"Unable to decode JSON file as UTF-8: {input_path}") from exc

    return data
