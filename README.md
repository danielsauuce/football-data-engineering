# Football Data Engineering Assessment

This repository contains my submission for the Southampton FC Data Engineer technical assessment. It covers two areas: designing a scalable football tracking data pipeline and building a working GPS data quality pipeline.

The focus throughout was on data reliability, traceability, clear data modelling and making information trustworthy for analysis.

## Project Overview

| Task | Description | Deliverables |
|---|---|---|
| Task 1 | Design a pipeline for processing large football tracking files. | Architecture diagram, ER diagram and technical notes. |
| Task 2 | Build a Python pipeline to process GPS session data and identify suspicious measurements. | Python implementation, Parquet outputs, configurable quality rules, tests and Part B note. |
| Assumptions | Document the assumptions made across both tasks. | Assumptions document. |

## Task 1 – Football Tracking Data Architecture

The first task focuses on designing a data pipeline for large, nested football tracking files.

The proposed architecture covers:

- Processing large JSON files efficiently using streaming and batch processing.
- Flattening nested tracking data into structured, analysis-ready records.
- Separating match, frame and player observation data through an appropriate data model.
- Using schema validation and data quality checks before publishing.
- Handling duplicate deliveries through content hashing and idempotent ingestion.
- Supporting corrected match deliveries through versioning rather than overwriting existing data.

**Deliverables:** 

- `task 1/architecture/` – Pipeline architecture and ER diagrams.
- `task 1/notes/design-decisions.md` – Processing performance and duplicate handling decisions.

## Task 2 – GPS Athlete Data Quality Pipeline

The second task implements a Python pipeline that reads GPS session exports, transforms the data into Parquet tables and identifies suspicious measurements.

The pipeline follows a Medallion Architecture:

```text
GPS Session JSON
       |
       v
Read and Validate
       |
       v
Registration and Landing
       |
       v
Bronze
Preserve source data
       |
       v
Silver
Structure and transform data
       |
       v
Quality Checks
       |
       +------> Quality Issues
       |
       +------> Human Review
       |
       v
Gold
       |
       v
Trusted Gold
```

### Key engineering decisions

- **Validation:** Checks the incoming JSON structure before processing.
- **Registration:** Uses SHA-256 hashing to identify duplicate deliveries and track processing runs.
- **Bronze:** Preserves vendor data and source context.
- **Silver:** Creates structured, typed tables around sessions, athletes, assignments, drills and GPS observations.
- **Data quality:** Uses external YAML rules so thresholds can be adjusted without changing Python code.
- **Review:** Records quality issues and provides a CSV for Sports Science decisions.
- **Gold:** Retains quality information and separates trusted records from records requiring review.

### Technology

- Python
- Pandas
- PyArrow
- Parquet
- YAML
- Pytest

### Running the pipeline

From the `task 2` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the pipeline:

```bash
python main.py --input data/raw/gps_session_SES-20261014-AM.json
```

Run the tests:

```bash
python -m pytest -v
```

### Task 2 deliverables

- `task 2/src/gps_pipeline/` – Pipeline implementation.
- `task 2/config/quality_rules.yaml` – Configurable quality rules.
- `task 2/tests/` – Unit tests.
- `task 2/architecture/` – Pipeline and ER diagrams.
- `task 2/notes/notes.md` – Data quality prevention and correction approach.
- `task 2/data/` – Sample input and generated pipeline outputs.

## Assumptions

Key assumptions made across both tasks are documented in:

`assumptions/assumptions.md`

## Scope

Task 1 is a design proposal, while Task 2 is a working local proof of concept.

The GPS pipeline uses local Parquet storage and CSV-based human review rather than a cloud deployment or database-backed production system. The design considers how the solution could be extended with additional production controls as requirements grow.

---

**The overall objective:** Build data pipelines that are efficient, traceable and reliable, so that the people using the data can make decisions with confidence.
