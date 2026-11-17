
# GPS Data Quality Pipeline

A Python data engineering pipeline for processing athlete GPS session
exports and identifying suspicious measurements.

## Architecture

The pipeline follows a modular monolith and layered ETL architecture.

Processing stages:

1. Ingestion and registration
2. Structural validation
3. Data transformation
4. Configurable quality checks
5. Sports Science review
6. Analytical publishing

## Technology

- Python
- Pandas
- PyArrow
- PyYAML
- Pytest

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run tests

```bash
pytest
```

## Run pipeline

```bash
gps-pipeline --input data/raw/gps_session_SES-20261014-AM.json
```
