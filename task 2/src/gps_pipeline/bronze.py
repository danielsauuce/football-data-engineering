import pandas as pd


def build_bronze_tables(data: dict) -> dict[str, pd.DataFrame]:
    """
    Flatten the vendor JSON into four source-oriented Bronze tables.

    Source values and measurement units are preserved.
    GPS samples retain their original array order.
    """
    export = data["export"]
    session = data["session"]
    athletes = data["athletes"]

    session_context = {
        "session_id": session["session_id"],
        "team": session["team"],
        "session_type": session["session_type"],
        "session_date": session["date"],
        "session_start_utc": session["start_utc"],
        "session_end_utc": session["end_utc"],
        "sample_rate_hz": session.get("sample_rate_hz"),
        "sample_note": session.get("sample_note"),
        "vendor": export["vendor"],
        "product": export["product"],
        "export_version": export["export_version"],
        "distance_unit": export["units"].get("distance"),
        "summary_speed_unit": export["units"].get("speed_summary"),
        "sample_speed_unit": export["units"].get("speed_samples"),
    }

    # 1. Session and drill definitions.
    session_drill_rows = []

    for drill_index, drill in enumerate(session["drills"]):
        session_drill_rows.append(
            {
                **session_context,
                "drill_index": drill_index,
                **drill,
            }
        )

    # 2. Vendor athlete summaries.
    athlete_summary_rows = []

    # 3. Athlete drill measurements.
    drill_metric_rows = []

    # 4. Individual GPS observations.
    gps_sample_rows = []

    for athlete_index, athlete in enumerate(athletes):
        athlete_context = {
            "session_id": session["session_id"],
            "athlete_index": athlete_index,
            "athlete_id": athlete["athlete_id"],
            "display_name": athlete["display_name"],
            "position": athlete["position"],
            "device_id": athlete["device_id"],
        }

        athlete_summary_rows.append(
            {
                **athlete_context,
                **athlete["summary"],
            }
        )

        for drill_index, drill_metric in enumerate(athlete["drills"]):
            drill_metric_rows.append(
                {
                    **athlete_context,
                    "drill_metric_index": drill_index,
                    **drill_metric,
                }
            )

        for sample_index, sample in enumerate(athlete["samples"]):
            gps_sample_rows.append(
                {
                    **athlete_context,
                    "sample_index": sample_index,
                    **sample,
                }
            )

    return {
        "bronze_session_drills": pd.DataFrame(session_drill_rows),
        "bronze_athlete_summary": pd.DataFrame(athlete_summary_rows),
        "bronze_drill_metric": pd.DataFrame(drill_metric_rows),
        "bronze_gps_sample": pd.DataFrame(gps_sample_rows),
    }
