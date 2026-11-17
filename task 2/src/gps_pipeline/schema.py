from typing import Any


class SchemaValidationError(ValueError):
    """Raised when the GPS session has an unexpected structure."""


def _require_object(
    value: Any,
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")


def _require_array(
    value: Any,
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{location} must be an array")


def _require_fields(
    value: dict,
    fields: list[str],
    location: str,
    errors: list[str],
) -> None:
    for field in fields:
        if field not in value:
            errors.append(f"{location}.{field} is required")


def validate_session_structure(data: dict[str, Any]) -> None:
    """
    Validate the required structure of a STATSports GPS session.

    Raises:
        SchemaValidationError: If required sections or fields are missing
        or have the wrong structure.
    """

    errors: list[str] = []

    if not isinstance(data, dict):
        raise SchemaValidationError("GPS session root must be a JSON object")

    _require_fields(
        data,
        ["export", "session", "athletes"],
        "root",
        errors,
    )

    export = data.get("export")
    session = data.get("session")
    athletes = data.get("athletes")

    if isinstance(export, dict):
        _require_fields(
            export,
            ["vendor", "product", "export_version", "units"],
            "export",
            errors,
        )

        if "units" in export and not isinstance(export["units"], dict):
            errors.append("export.units must be an object")
    elif export is not None:
        errors.append("export must be an object")

    if isinstance(session, dict):
        _require_fields(
            session,
            [
                "session_id",
                "team",
                "session_type",
                "date",
                "start_utc",
                "end_utc",
                "drills",
            ],
            "session",
            errors,
        )

        if "drills" in session:
            _require_array(session["drills"], "session.drills", errors)

            if isinstance(session["drills"], list):
                for index, drill in enumerate(session["drills"]):
                    location = f"session.drills[{index}]"

                    if not isinstance(drill, dict):
                        errors.append(f"{location} must be an object")
                        continue

                    _require_fields(
                        drill,
                        ["drill_id", "name", "start_utc", "end_utc"],
                        location,
                        errors,
                    )
    elif session is not None:
        errors.append("session must be an object")

    if isinstance(athletes, list):
        if not athletes:
            errors.append("athletes must contain at least one athlete")

        for index, athlete in enumerate(athletes):
            location = f"athletes[{index}]"

            if not isinstance(athlete, dict):
                errors.append(f"{location} must be an object")
                continue

            _require_fields(
                athlete,
                [
                    "athlete_id",
                    "display_name",
                    "position",
                    "device_id",
                    "summary",
                    "drills",
                    "samples",
                ],
                location,
                errors,
            )

            if "summary" in athlete and not isinstance(athlete["summary"], dict):
                errors.append(f"{location}.summary must be an object")

            for field in ["drills", "samples"]:
                if field not in athlete:
                    continue

                value = athlete[field]

                if not isinstance(value, list):
                    errors.append(f"{location}.{field} must be an array")
                    continue

                for child_index, child in enumerate(value):
                    child_location = f"{location}.{field}[{child_index}]"

                    if not isinstance(child, dict):
                        errors.append(f"{child_location} must be an object")
                        continue

                    if field == "drills":
                        _require_fields(
                            child,
                            ["drill_id"],
                            child_location,
                            errors,
                        )

                    if field == "samples":
                        _require_fields(
                            child,
                            ["ts"],
                            child_location,
                            errors,
                        )

    elif athletes is not None:
        errors.append("athletes must be an array")

    if errors:
        details = "\n - ".join(errors)

        raise SchemaValidationError(f"GPS session structure is invalid:\n - {details}")
