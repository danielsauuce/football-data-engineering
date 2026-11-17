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


def _make_issue_id(
    rule_set_version: str,
    rule_id: str,
    table_name: str,
    row_reference: str,
) -> str:
    """Generate a repeatable ID for a rule violation."""

    identity = "|".join(
        [
            rule_set_version,
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
    """Evaluate a rule involving multiple fields."""

    if operator not in SUPPORTED_COMPOUND_OPERATORS:
        raise ValueError(f"Unsupported compound operator: {operator}")

    if operator == "both_equal":
        if len(fields) != 2:
            raise ValueError("The both_equal operator requires exactly two fields")

        return dataframe[fields[0]].eq(threshold) & dataframe[fields[1]].eq(threshold)

    raise ValueError(f"Unsupported compound operator: {operator}")


def run_quality_checks(
    tables: dict[str, pd.DataFrame],
    rules_config: dict[str, Any],
    run_id: str,
    input_sha256: str,
) -> pd.DataFrame:
    """
    Apply enabled YAML quality rules to Silver tables.

    Returns one issue record per violating source record and rule.
    Source DataFrames are never modified.
    """

    issues: list[dict[str, Any]] = []

    rule_set_version = str(rules_config["version"])

    for rule in rules_config["rules"]:

        if not rule.get("enabled", True):
            continue

        rule_id = rule["rule_id"]
        table_name = rule["table"]
        operator = rule["operator"]
        threshold = rule["threshold"]
        severity = rule["severity"]

        if table_name not in tables:
            raise ValueError(f"Rule {rule_id} references missing table: {table_name}")

        dataframe = tables[table_name]

        if "fields" in rule:
            fields = rule["fields"]

            missing_fields = [name for name in fields if name not in dataframe.columns]

            if missing_fields:
                raise ValueError(
                    f"Rule {rule_id} references missing fields: " f"{missing_fields}"
                )

            violations = _evaluate_compound_condition(
                dataframe,
                fields,
                operator,
                threshold,
            ).fillna(False)

            field = ", ".join(fields)

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
                threshold,
            ).fillna(False)

        for row_index, row in dataframe.loc[violations].iterrows():

            row_reference = _get_row_reference(
                row,
                table_name,
                row_index,
            )

            issue_id = _make_issue_id(
                rule_set_version,
                rule_id,
                table_name,
                row_reference,
            )

            if "fields" in rule:
                observed_value = {name: row[name] for name in rule["fields"]}
            else:
                observed_value = row[field]

            if isinstance(observed_value, dict):
                observed_value = {
                    key: (value.item() if hasattr(value, "item") else value)
                    for key, value in observed_value.items()
                }
            elif hasattr(observed_value, "item"):
                observed_value = observed_value.item()

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
                    "observed_value": json.dumps(
                        observed_value,
                        default=str,
                    ),
                    "expected_condition": (f"{field} {operator} {threshold}"),
                    "severity": severity,
                    "status": "open",
                }
            )

    return pd.DataFrame(issues)
