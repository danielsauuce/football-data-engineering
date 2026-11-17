from __future__ import annotations

import pandas as pd

TRUSTED_STATUSES = {"clear", "confirmed_ok"}

GOLD_TABLE_NAMES = {
    "session": "gold_session",
    "athlete": "gold_athlete",
    "athlete_assignment": "gold_athlete_assignment",
    "drill": "gold_drill",
    "athlete_summary": "gold_athlete_summary",
    "athlete_drill_metric": "gold_athlete_drill_metric",
    "gps_sample": "gold_gps_sample",
}


def _issue_matches_row(
    issue: pd.Series,
    table_name: str,
    row: pd.Series,
) -> bool:
    """Determine whether an issue belongs to a specific Gold record."""

    issue_table = issue.get("table_name")
    issue_assignment = issue.get("assignment_id")
    issue_drill = issue.get("drill_id")
    issue_sample = issue.get("sample_seq")
    issue_athlete = issue.get("athlete_id")
    issue_session = issue.get("session_id")

    row_assignment = row.get("assignment_id")
    row_drill = row.get("drill_id")
    row_sample = row.get("sample_seq")
    row_athlete = row.get("athlete_id")
    row_session = row.get("session_id")

    # Direct GPS sample issue.
    if issue_table == "gps_sample":
        if table_name != "gps_sample":
            return False

        return issue_assignment == row_assignment and issue_sample == row_sample

    # Direct athlete drill metric issue.
    if issue_table == "athlete_drill_metric":
        if table_name != "athlete_drill_metric":
            return False

        return issue_assignment == row_assignment and issue_drill == row_drill

    # Direct athlete summary issue.
    if issue_table == "athlete_summary":
        if table_name != "athlete_summary":
            return False

        return issue_assignment == row_assignment

    # General session-level issue.
    if pd.notna(issue_session) and table_name == "session":
        return issue_session == row_session

    # General athlete-level issue.
    if pd.notna(issue_athlete) and table_name == "athlete":
        return issue_athlete == row_athlete

    # Assignment-level propagation to its parent assignment.
    if pd.notna(issue_assignment) and table_name == "athlete_assignment":
        return issue_assignment == row_assignment

    return False


def _status_for_issues(
    matched_issues: pd.DataFrame,
    review_decisions: pd.DataFrame,
) -> tuple[str, int]:
    """Resolve a record's quality status from issues and human decisions."""

    issue_count = len(matched_issues)

    if issue_count == 0:
        return "clear", 0

    if review_decisions.empty:
        return "needs_review", issue_count

    decisions = (
        matched_issues[["issue_id"]]
        .merge(
            review_decisions[["issue_id", "decision"]],
            on="issue_id",
            how="left",
        )["decision"]
        .fillna("")
    )

    decisions = decisions.astype(str)

    if decisions.eq("confirmed_error").any():
        return "confirmed_error", issue_count

    if decisions.eq("").any():
        return "needs_review", issue_count

    if decisions.eq("confirmed_ok").all():
        return "confirmed_ok", issue_count

    raise ValueError("Review decisions contain an unsupported status")


def build_gold_tables(
    silver_tables: dict[str, pd.DataFrame],
    issues: pd.DataFrame,
    review_decisions: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Enrich all Silver tables with data-quality status and issue count.

    Original Silver records and their grain are preserved.
    """

    gold_tables = {}

    for silver_name, gold_name in GOLD_TABLE_NAMES.items():

        if silver_name not in silver_tables:
            raise ValueError(f"Missing Silver table: {silver_name}")

        dataframe = silver_tables[silver_name].copy()

        statuses = []
        issue_counts = []

        for _, row in dataframe.iterrows():

            if issues.empty:
                matched = issues
            else:
                mask = issues.apply(
                    lambda issue: _issue_matches_row(
                        issue,
                        silver_name,
                        row,
                    ),
                    axis=1,
                )
                matched = issues.loc[mask]

            status, issue_count = _status_for_issues(
                matched,
                review_decisions,
            )

            statuses.append(status)
            issue_counts.append(issue_count)

        dataframe["dq_status"] = statuses
        dataframe["dq_issue_count"] = issue_counts

        gold_tables[gold_name] = dataframe

    return gold_tables


def build_trusted_tables(
    gold_tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Create consumer-facing tables excluding records that
    need review or have been confirmed erroneous.
    """

    trusted_tables = {}

    for table_name, dataframe in gold_tables.items():
        trusted_tables[table_name] = dataframe.loc[
            dataframe["dq_status"].isin(TRUSTED_STATUSES)
        ].copy()

    return trusted_tables
