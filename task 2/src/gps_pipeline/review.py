from pathlib import Path

import pandas as pd

REVIEW_COLUMNS = [
    "issue_id",
    "rule_id",
    "table_name",
    "row_reference",
    "severity",
    "observed_value",
    "expected_condition",
    "decision",
    "reviewed_by",
    "reviewed_at_utc",
    "review_comment",
]

VALID_DECISIONS = {
    "confirmed_ok",
    "confirmed_error",
}


def create_review_file(
    issues: pd.DataFrame,
    review_root: Path,
    session_id: str,
) -> Path:
    """
    Create or update the Sports Science review CSV.

    Existing decisions are preserved using issue_id as the
    stable identifier. New issues start with blank decisions.
    """

    review_dir = review_root / session_id
    review_dir.mkdir(parents=True, exist_ok=True)

    review_path = review_dir / "dq_review.csv"

    missing_columns = [
        column for column in ["issue_id"] if column not in issues.columns
    ]

    if missing_columns:
        raise ValueError(f"Issues DataFrame is missing columns: {missing_columns}")

    duplicate_ids = issues["issue_id"].duplicated()

    if duplicate_ids.any():
        raise ValueError("Issues contain duplicate issue_id values")

    available_issue_columns = [
        column for column in REVIEW_COLUMNS if column in issues.columns
    ]

    review = issues[available_issue_columns].copy()

    for column in REVIEW_COLUMNS:
        if column not in review.columns:
            review[column] = ""

    review = review[REVIEW_COLUMNS]

    # Preserve previous human decisions.
    if review_path.exists():
        previous = pd.read_csv(
            review_path,
            dtype=str,
            keep_default_na=False,
        )

        if previous["issue_id"].duplicated().any():
            raise ValueError("Existing review file contains duplicate issue IDs")

        previous = previous.set_index("issue_id")

        for index, row in review.iterrows():
            issue_id = row["issue_id"]

            if issue_id not in previous.index:
                continue

            old = previous.loc[issue_id]

            for column in [
                "decision",
                "reviewed_by",
                "reviewed_at_utc",
                "review_comment",
            ]:
                if column in old.index:
                    review.at[index, column] = old[column]

    # Validate preserved decisions.
    invalid = review["decision"].ne("") & ~review["decision"].isin(VALID_DECISIONS)

    if invalid.any():
        raise ValueError("Review file contains an invalid decision")

    temporary_path = review_path.with_suffix(".tmp")

    review.to_csv(
        temporary_path,
        index=False,
    )

    temporary_path.replace(review_path)

    return review_path
