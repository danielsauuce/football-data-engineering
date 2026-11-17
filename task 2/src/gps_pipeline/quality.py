from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

SUPPORTED_OPERATORS = {
    "greater_than",
    "less_than",
    "equals",
}

SUPPORTED_COMPOUND_OPERATORS = {
    "both_equal",
}

TIMESTAMP_OPERATOR = "timestamp_not_increasing"

ISSUE_COLUMNS = [
    "issue_id",
    "run_id",
    "input_sha256",
    "rule_set_version",
    "rule_id",
    "table_name",
    "row_reference",
    "session_id",
    "athlete_id",
    "assignment_id",
    "drill_id",
    "sample_seq",
    "field",
    "observed_value",
    "previous_value",
    "expected_condition",
    "severity",
    "status",
]


def _make_issue_id(
    rule_set_version: str,
    input_sha256: str,
    rule_id: str,
    table_name: str,
    row_reference: str,
) -> str:
    """
    Generate a repeatable ID for a rule violation.

    The same source file, rule version, rule and source row
    will produce the same issue ID.
    """

    identity = "|".join(
        [
            rule_set_version,
            input_sha256,
            rule_id,
            table_name,
            row_reference,
        ]
    )

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _get_row_reference(
    row: pd.Series,
    table_name: str,
    row_index: Any,
) -> str:
    """Build a reference to the source record that triggered an issue."""

    if "assignment_id" in row and pd.notna(row["assignment_id"]):
        reference = str(row["assignment_id"])

        if table_name == "gps_sample" and "sample_seq" in row:
            return f"{reference}|sample:{row['sample_seq']}"

        if table_name == "athlete_drill_metric" and "drill_id" in row:
            return f"{reference}|drill:{row['drill_id']}"

        return reference

    if "session_id" in row and pd.notna(row["session_id"]):
        return str(row["session_id"])

    return str(row_index)


def _evaluate_condition(
    series: pd.Series,
    operator: str,
    threshold: Any,
) -> pd.Series:
    """Evaluate a single-field quality rule."""

    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(f"Unsupported single-field operator: {operator}")

    if operator == "greater_than":
        return series > threshold

    if operator == "less_than":
        return series < threshold

    if operator == "equals":
        return series == threshold

    raise ValueError(f"Unsupported operator: {operator}")


def _evaluate_compound_condition(
    dataframe: pd.DataFrame,
    fields: list[str],
    operator: str,
    threshold: Any,
) -> pd.Series:
    """Evaluate a quality rule involving multiple fields."""

    if operator not in SUPPORTED_COMPOUND_OPERATORS:
        raise ValueError(f"Unsupported compound operator: {operator}")

    if operator == "both_equal":
        if len(fields) != 2:
            raise ValueError("The both_equal operator requires exactly two fields")

        return dataframe[fields[0]].eq(threshold) & dataframe[fields[1]].eq(threshold)

    raise ValueError(f"Unsupported compound operator: {operator}")


def _evaluate_timestamp_sequence(
    dataframe: pd.DataFrame,
    field: str,
    group_by: str,
    order_by: str,
) -> tuple[pd.Series, pd.Series]:
    """
    Compare each timestamp with the previous timestamp
    within the same assignment, using original sample order.

    Returns:
        violations: Boolean Series aligned to the input index.
        previous_values: Previous timestamp for each source row.
    """

    required_columns = [field, group_by, order_by]

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns for timestamp sequence rule: " f"{missing_columns}"
        )

    if not dataframe.index.is_unique:
        raise ValueError("Timestamp validation requires a unique DataFrame index")

    ordered = dataframe.sort_values(
        [group_by, order_by],
        kind="stable",
    )

    previous_values = ordered.groupby(group_by, sort=False)[field].shift(1)

    violations = (
        ordered[field].notna()
        & previous_values.notna()
        & (ordered[field] <= previous_values)
    )

    return (
        violations.reindex(dataframe.index, fill_value=False),
        previous_values.reindex(dataframe.index),
    )


def _json_value(value: Any) -> str:
    """Convert observed values into a Parquet-friendly JSON string."""

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, dict):
        value = {
            key: item.item() if hasattr(item, "item") else item
            for key, item in value.items()
        }

    return json.dumps(value, default=str)


def run_quality_checks(
    tables: dict[str, pd.DataFrame],
    rules_config: dict[str, Any],
    run_id: str,
    input_sha256: str,
) -> pd.DataFrame:
    """
    Apply enabled YAML quality rules to Silver tables.

    Returns one issue record for each violating source record and rule.

    Source DataFrames are never modified.
    """

    if "version" not in rules_config:
        raise ValueError("Quality rules configuration is missing version")

    if "rules" not in rules_config:
        raise ValueError("Quality rules configuration is missing rules")

    issues: list[dict[str, Any]] = []

    rule_set_version = str(rules_config["version"])

    for rule in rules_config["rules"]:

        if not rule.get("enabled", True):
            continue

        rule_id = rule["rule_id"]
        table_name = rule["table"]
        operator = rule["operator"]
        severity = rule["severity"]

        if table_name not in tables:
            raise ValueError(f"Rule {rule_id} references missing table: {table_name}")

        dataframe = tables[table_name]

        previous_values = None

        # ----------------------------------------------
        # Timestamp sequence rule
        # ----------------------------------------------

        if operator == TIMESTAMP_OPERATOR:
            field = rule["field"]

            violations, previous_values = _evaluate_timestamp_sequence(
                dataframe=dataframe,
                field=field,
                group_by=rule["group_by"],
                order_by=rule["order_by"],
            )

        # ----------------------------------------------
        # Compound rule
        # ----------------------------------------------

        elif "fields" in rule:
            fields = rule["fields"]

            missing_fields = [name for name in fields if name not in dataframe.columns]

            if missing_fields:
                raise ValueError(
                    f"Rule {rule_id} references missing fields: " f"{missing_fields}"
                )

            violations = _evaluate_compound_condition(
                dataframe=dataframe,
                fields=fields,
                operator=operator,
                threshold=rule["threshold"],
            ).fillna(False)

            field = ", ".join(fields)

        # ----------------------------------------------
        # Single-field rule
        # ----------------------------------------------

        else:
            field = rule["field"]

            if field not in dataframe.columns:
                raise ValueError(
                    f"Rule {rule_id} references missing field "
                    f"'{field}' in table '{table_name}'"
                )

            violations = _evaluate_condition(
                dataframe[field],
                operator,
                rule["threshold"],
            ).fillna(False)

        # ----------------------------------------------
        # Create issue records
        # ----------------------------------------------

        for row_index, row in dataframe.loc[violations].iterrows():

            row_reference = _get_row_reference(
                row,
                table_name,
                row_index,
            )

            issue_id = _make_issue_id(
                rule_set_version=rule_set_version,
                input_sha256=input_sha256,
                rule_id=rule_id,
                table_name=table_name,
                row_reference=row_reference,
            )

            if operator == TIMESTAMP_OPERATOR:
                observed_value = row[field]
                previous_value = previous_values.loc[row_index]

            elif "fields" in rule:
                observed_value = {name: row[name] for name in rule["fields"]}
                previous_value = None

            else:
                observed_value = row[field]
                previous_value = None

            if operator == TIMESTAMP_OPERATOR:
                expected_condition = f"{field} must be later than previous sample"
            else:
                expected_condition = f"{field} {operator} " f"{rule['threshold']}"

            issues.append(
                {
                    "issue_id": issue_id,
                    "run_id": run_id,
                    "input_sha256": input_sha256,
                    "rule_set_version": rule_set_version,
                    "rule_id": rule_id,
                    "table_name": table_name,
                    "row_reference": row_reference,
                    "session_id": row.get("session_id"),
                    "athlete_id": row.get("athlete_id"),
                    "assignment_id": row.get("assignment_id"),
                    "drill_id": row.get("drill_id"),
                    "sample_seq": row.get("sample_seq"),
                    "field": field,
                    "observed_value": _json_value(observed_value),
                    "previous_value": (
                        str(previous_value)
                        if previous_value is not None and pd.notna(previous_value)
                        else None
                    ),
                    "expected_condition": expected_condition,
                    "severity": severity,
                    "status": "open",
                }
            )

    return pd.DataFrame(
        issues,
        columns=ISSUE_COLUMNS,
    )
