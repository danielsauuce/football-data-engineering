import pandas as pd


def transform_session(data: dict) -> dict[str, pd.DataFrame]:
    """
    Flatten a validated GPS session into three analysis-ready tables.

    Returns:
        athlete_sessions: One row per athlete-device session entry.
        athlete_drills: One row per athlete-device-drill entry.
        gps_samples: One row per GPS observation.
    """
    session = data["session"]
    athletes = data["athletes"]

    # Look up drill metadata so each athlete's drill metrics
    # can be associated with the drill name and time window.
    drill_lookup = {drill["drill_id"]: drill for drill in session["drills"]}

    athlete_session_rows = []
    athlete_drill_rows = []
    gps_sample_rows = []

    for athlete in athletes:
        # Shared identifiers and session context.
        identifiers = {
            "session_id": session["session_id"],
            "session_date": session["date"],
            "team": session["team"],
            "session_type": session["session_type"],
            "athlete_id": athlete["athlete_id"],
            "display_name": athlete["display_name"],
            "position": athlete["position"],
            "device_id": athlete["device_id"],
        }

        # TABLE 1: One row per athlete-device session entry.
        athlete_session_rows.append(
            {
                **identifiers,
                **athlete["summary"],
            }
        )

        # TABLE 2: One row per athlete-device-drill entry.
        for drill_metrics in athlete["drills"]:
            drill_id = drill_metrics["drill_id"]
            drill_metadata = drill_lookup.get(drill_id, {})

            athlete_drill_rows.append(
                {
                    **identifiers,
                    **drill_metrics,
                    "drill_name": drill_metadata.get("name"),
                    "drill_start_utc": drill_metadata.get("start_utc"),
                    "drill_end_utc": drill_metadata.get("end_utc"),
                }
            )

        # TABLE 3: One row per GPS sample.
        # Keep the original array position; do not sort by timestamp.
        for sample_index, sample in enumerate(athlete["samples"]):
            gps_sample_rows.append(
                {
                    **identifiers,
                    "sample_index": sample_index,
                    **sample,
                }
            )

    return {
        "athlete_sessions": pd.DataFrame(athlete_session_rows),
        "athlete_drills": pd.DataFrame(athlete_drill_rows),
        "gps_samples": pd.DataFrame(gps_sample_rows),
    }
