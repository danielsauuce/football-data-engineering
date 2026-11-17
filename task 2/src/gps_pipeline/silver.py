import pandas as pd


def build_silver_tables(
    bronze_tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Model source-oriented Bronze tables into business-oriented
    Silver entities and measurement tables.
    """
    session_drills = bronze_tables["bronze_session_drills"]
    athlete_summaries = bronze_tables["bronze_athlete_summary"]
    drill_metrics = bronze_tables["bronze_drill_metric"]
    gps_samples = bronze_tables["bronze_gps_sample"]

    # ---------------------------------------------------------
    # 1. SESSION
    # One row per session.
    # ---------------------------------------------------------
    sessions = (
        session_drills[
            [
                "session_id",
                "team",
                "session_type",
                "session_date",
                "session_start_utc",
                "session_end_utc",
            ]
        ]
        .drop_duplicates(subset=["session_id"])
        .copy()
    )

    sessions["session_start_utc"] = pd.to_datetime(
        sessions["session_start_utc"], utc=True
    )
    sessions["session_end_utc"] = pd.to_datetime(sessions["session_end_utc"], utc=True)
    sessions["session_date"] = pd.to_datetime(sessions["session_date"]).dt.date

    # ---------------------------------------------------------
    # 2. ATHLETE
    # One row per unique athlete.
    # ---------------------------------------------------------
    athletes = (
        athlete_summaries[
            [
                "athlete_id",
                "display_name",
                "position",
            ]
        ]
        .drop_duplicates(subset=["athlete_id"])
        .copy()
    )

    # ---------------------------------------------------------
    # 3. ATHLETE ASSIGNMENT
    # One row per athlete-device assignment in a session.
    # ---------------------------------------------------------
    assignments = (
        athlete_summaries[
            [
                "session_id",
                "athlete_id",
                "device_id",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    assignments["assignment_id"] = (
        assignments["session_id"]
        + "|"
        + assignments["athlete_id"]
        + "|"
        + assignments["device_id"]
    )

    # ---------------------------------------------------------
    # 4. DRILL
    # One row per drill in a session.
    # ---------------------------------------------------------
    drills = (
        session_drills[
            [
                "session_id",
                "drill_id",
                "name",
                "start_utc",
                "end_utc",
            ]
        ]
        .rename(
            columns={
                "name": "drill_name",
                "start_utc": "drill_start_utc",
                "end_utc": "drill_end_utc",
            }
        )
        .copy()
    )

    drills["drill_start_utc"] = pd.to_datetime(drills["drill_start_utc"], utc=True)
    drills["drill_end_utc"] = pd.to_datetime(drills["drill_end_utc"], utc=True)

    # Create a reusable assignment lookup.
    assignment_lookup = assignments[
        [
            "session_id",
            "athlete_id",
            "device_id",
            "assignment_id",
        ]
    ]

    # ---------------------------------------------------------
    # 5. ATHLETE SUMMARY
    # One row per athlete assignment.
    # ---------------------------------------------------------
    athlete_summary = athlete_summaries.merge(
        assignment_lookup,
        on=["session_id", "athlete_id", "device_id"],
        how="left",
        validate="one_to_one",
    )

    summary_columns = [
        "assignment_id",
        "total_distance_m",
        "hsr_distance_m",
        "sprint_distance_m",
        "max_speed_kmh",
        "accelerations",
        "decelerations",
        "avg_hr_bpm",
        "max_hr_bpm",
        "player_load",
    ]

    athlete_summary = athlete_summary[summary_columns].copy()

    # ---------------------------------------------------------
    # 6. ATHLETE DRILL METRIC
    # One row per athlete assignment and drill.
    # ---------------------------------------------------------
    athlete_drill_metric = drill_metrics.merge(
        assignment_lookup,
        on=["session_id", "athlete_id", "device_id"],
        how="left",
        validate="many_to_one",
    )

    athlete_drill_metric = athlete_drill_metric[
        [
            "assignment_id",
            "drill_id",
            "total_distance_m",
            "hsr_distance_m",
            "max_speed_kmh",
        ]
    ].copy()

    # ---------------------------------------------------------
    # 7. GPS SAMPLE
    # One row per assignment and sample sequence.
    # ---------------------------------------------------------
    gps_sample = gps_samples.merge(
        assignment_lookup,
        on=["session_id", "athlete_id", "device_id"],
        how="left",
        validate="many_to_one",
    )

    gps_sample = gps_sample.rename(
        columns={
            "sample_index": "sample_seq",
        }
    )

    gps_sample["ts"] = pd.to_datetime(gps_sample["ts"], utc=True)

    # Preserve source speed in m/s and derive km/h.
    gps_sample["speed_kmh"] = pd.to_numeric(gps_sample["speed_ms"]) * 3.6

    gps_sample = gps_sample[
        [
            "assignment_id",
            "sample_seq",
            "ts",
            "lat",
            "lon",
            "speed_ms",
            "speed_kmh",
            "hr_bpm",
            "hdop",
            "satellites",
        ]
    ].copy()

    return {
        "session": sessions,
        "athlete": athletes,
        "athlete_assignment": assignments,
        "drill": drills,
        "athlete_summary": athlete_summary,
        "athlete_drill_metric": athlete_drill_metric,
        "gps_sample": gps_sample,
    }
