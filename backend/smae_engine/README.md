# SMAE Engine

Resilient nutritional data extraction pipeline using Gemini 2.5 Flash and BigQuery.

## Overview
The SMAE Engine is designed to process complex nutritional PDFs (SMAE tables) by isolating pages and extracting structured data into BigQuery. It implements a page-level retry logic and a Dead Letter Table (DLT) strategy to ensure high reliability.

## Structure
- `source_code/`: Main Python implementation and schemas.
- `tests/`: Unit tests (backend/smae_engine/).
- `notebooks/`: Verification notebooks for manual prototyping.

## Usage
To run the engine locally:
```bash
uv run --group smae-engine python -m backend.smae_engine.source_code.main
```

## Data Architecture
- **Dataset**: `nutrimental_information`
- **Tables**:
  - `food_equivalents`: Success table (Partitioned by ingestion_at, SCD Type 2).
  - `extraction_dead_letter`: Failure logging table.

## Standards
Follows the project's **Resilient Ingestion Strategy** (Knowledge Item).
