from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from gps_pipeline.bronze import build_bronze_tables
from gps_pipeline.bronze_outputs import write_bronze_tables
from gps_pipeline.gold import build_gold_tables
from gps_pipeline.gold_outputs import write_gold_tables
from gps_pipeline.quality import run_quality_checks
from gps_pipeline.quality_outputs import write_quality_issues
from gps_pipeline.reader import read_json
from gps_pipeline.registration import mark_run_completed, register_input
from gps_pipeline.review import create_review_file
from gps_pipeline.schema import validate_session_structure
from gps_pipeline.silver import build_silver_tables
from gps_pipeline.silver_outputs import write_silver_tables


def _load_quality_rules(config_path: Path) -> dict[str, Any]:
    """Load and minimally validate the versioned YAML rule configuration."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Quality rules file does not exist: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Quality rules configuration must be a YAML object")

    if not config.get("version"):
        raise ValueError("Quality rules configuration is missing version")

    if not isinstance(config.get("rules"), list):
        raise ValueError("Quality rules configuration must contain a rules list")

    return config


def run_pipeline(
    input_path: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """
    Run the complete GPS data pipeline for one session JSON file.

    The project root contains config/ and data/. If omitted, the current
    working directory is used.
    """
    input_path = Path(input_path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    root = Path(project_root) if project_root is not None else Path.cwd()
    data_root = root / "data"

    # 1. Read, validate and identify the incoming session.
    source_data = read_json(input_path)
    validate_session_structure(source_data)

    session_id = source_data["session"]["session_id"]
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session.session_id must be a non-empty string")

    # Load rules before registration so invalid configuration cannot create
    # a registered run that can never complete.
    rules_config = _load_quality_rules(root / "config" / "quality_rules.yaml")
    rule_set_version = str(rules_config["version"])

    # 2. Register the immutable input and establish run lineage.
    manifest_path = data_root / "metadata" / "ingestion_manifest.json"
    registration = register_input(
        source_path=input_path,
        landing_dir=data_root / "landing",
        manifest_path=manifest_path,
        rule_set_version=rule_set_version,
    )

    if registration["status"] == "duplicate":
        return {
            "status": "duplicate",
            "session_id": session_id,
            "run_id": registration["run_id"],
            "input_sha256": registration["input_sha256"],
            "message": "This input and rule-set version have already completed.",
        }

    run_id = registration["run_id"]
    input_sha256 = registration["input_sha256"]

    # 3. Bronze: preserve vendor-oriented source values.
    bronze_tables = build_bronze_tables(source_data)
    bronze_files = write_bronze_tables(
        bronze_tables,
        data_root / "bronze",
        session_id,
    )

    # 4. Silver: create typed, business-oriented entities and measurements.
    silver_tables = build_silver_tables(bronze_tables)
    silver_files = write_silver_tables(
        silver_tables,
        data_root / "silver",
        session_id,
    )

    # 5. Quality: detect issues without changing the Silver source records.
    issues = run_quality_checks(
        tables=silver_tables,
        rules_config=rules_config,
        run_id=run_id,
        input_sha256=input_sha256,
    )
    issue_files = write_quality_issues(
        issues,
        data_root / "quality",
        session_id,
    )

    # 6. Review: create new blank decisions while preserving any existing
    # decisions for stable issue IDs.
    review_path = create_review_file(
        issues,
        data_root / "review",
        session_id,
    )
    review_decisions = pd.read_csv(
        review_path,
        dtype=str,
        keep_default_na=False,
    )

    # 7. Gold: retain all records with quality metadata, and publish a
    # separate trusted subset for downstream consumers.
    gold_tables = build_gold_tables(
        silver_tables=silver_tables,
        issues=issues,
        review_decisions=review_decisions,
    )
    gold_files = write_gold_tables(
        gold_tables,
        data_root / "gold",
        session_id,
    )

    # Only mark the run complete after every output has been written.
    mark_run_completed(manifest_path, run_id)

    summary = {
        "status": "completed",
        "session_id": session_id,
        "run_id": run_id,
        "input_sha256": input_sha256,
        "rule_set_version": rule_set_version,
        "bronze_rows": {name: len(table) for name, table in bronze_tables.items()},
        "silver_rows": {name: len(table) for name, table in silver_tables.items()},
        "quality_issue_count": len(issues),
        "gold_tables": len(gold_tables),
        "trusted_tables": len(gold_tables),
        "files_written": len(bronze_files + silver_files + issue_files + gold_files),
        "review_file": str(review_path),
    }

    print(f"GPS pipeline completed for session {session_id}")
    print(f"Run ID: {run_id}")
    print(f"Quality issues detected: {len(issues)}")
    print(f"Files written: {summary['files_written']}")

    return summary
