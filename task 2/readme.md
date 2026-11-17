# GPS Athlete Data Quality Pipeline

## 1. Overview

A Python data pipeline that processes STATSports GPS session exports into analysis-ready Parquet tables, detects suspicious measurements and separates trusted data from records requiring review.

Built with Python, Pandas, PyArrow and YAML using a local file-based architecture.

## 2. Pipeline Architecture

```text
GPS Session JSON
       |
       v
Read & Validate
       |
       v
Registration & Landing
       |
       v
Bronze → Preserve vendor data
       |
       v
Silver → Model business entities
       |
       v
Quality Checks
       |
       +----> dq_issue.parquet
       |
       +----> dq_review.csv
       |
       v
Gold → All records + quality metadata
       |
       v
Trusted Gold → Cleared records only
```

### Pipeline stages

| Stage | Responsibility |
|---|---|
| Validation | Checks JSON structure and required fields; rejects invalid input |
| Registration | Calculates SHA-256, tracks runs and skips completed duplicates |
| Bronze | Flattens vendor data while preserving original values and units |
| Silver | Creates typed, business-oriented tables and derived measurements |
| Quality | Applies configurable rules and records triggered issues |
| Review | Provides a CSV for Sports Science decisions |
| Gold | Adds quality status and issue counts; publishes trusted datasets |

## 3. Why Bronze, Silver and Gold?

- **Bronze:** Preserves source values and vendor context for traceability.
- **Silver:** Provides consistent business entities, relationships and analytical measurements.
- **Gold:** Adds data quality information and separates trusted records from records requiring review.

This separation makes it possible to trace an analytical value back to its original source without losing suspicious measurements.

## 4. Data Model and Grain

Grain defines what one row represents.

| Table | Grain | Purpose |
|---|---|---|
| `session` | One row per session | Session information |
| `athlete` | One row per athlete | Athlete identity |
| `athlete_assignment` | One row per athlete-device assignment | Tracks device assignments |
| `drill` | One row per drill per session | Drill information |
| `athlete_summary` | One row per athlete-device assignment | Session performance metrics |
| `athlete_drill_metric` | One row per assignment per drill | Drill performance metrics |
| `gps_sample` | One row per GPS observation | Movement and sensor measurements |

Bronze contains four source-oriented tables representing session drills, athlete summaries, drill metrics and GPS samples.

Gold retains the seven Silver table grains and adds `dq_status` and `dq_issue_count` to every record.

## 5. Data Quality and Review

Quality rules are maintained in `config/quality_rules.yaml`, allowing Sports Science to adjust thresholds without changing Python code.

Current checks cover GPS speed, heart rate, coordinates, timestamp ordering and negative deceleration values.

Detected issues are stored in `dq_issue.parquet`, recording the triggered rule and affected record.

Sports Science can record decisions in `dq_review.csv`:

- `confirmed_ok` – measurement is acceptable.
- `confirmed_error` – measurement is erroneous.

Gold uses four statuses:

| Status | Meaning |
|---|---|
| `clear` | No issues detected |
| `needs_review` | Awaiting human review |
| `confirmed_ok` | Approved by Sports Science |
| `confirmed_error` | Confirmed erroneous |

All records remain in Gold. Trusted Gold only includes `clear` and `confirmed_ok` records.

## 6. Installation and Execution

**Requirements:** Python 3.10+

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the pipeline from the project root:

```bash
python main.py --input data/raw/gps_session_SES-20261014-AM.json
```

Run tests:

```bash
python -m pytest -v
```

## 7. Output Structure

```text
data/
├── raw/
├── landing/
├── bronze/<session_id>/
├── silver/<session_id>/
├── quality/<session_id>/
├── review/<session_id>/
├── gold/<session_id>/
│   └── trusted/
└── metadata/
```

## 8. Scope and Limitations

This implementation uses local Parquet files rather than a database or cloud platform. Human review is represented through CSV rather than a user interface.

Production deployment would require additional controls for concurrent processing, access management, monitoring and controlled republishing after review decisions.