# SMAE Engine Module

## Overview
The SMAE Engine is responsible for extracting standardized nutritional data from SMAE (Sistema Mexicano de Alimentos Equivalentes) PDF documents using Gemini 2.5 Flash.

## Architecture
The engine follows a resilient, page-by-page processing strategy:
1. **Split**: Isolates individual PDF pages to prevent "context flooding" and allow granular retries.
2. **Screen**: Uses Gemini to identify if a page contains a relevant table.
3. **Extract**: Performs structured extraction into a Pydantic-validated schema.
4. **DLQ**: Failed pages are logged to a Dead Letter Table in BigQuery for later re-processing.

## Data Schema (BigQuery)

### `nutritional_info`
| Column | Type | Description |
| :--- | :--- | :--- |
| `food_uuid` | STRING | Deterministic UUID from food name and source URI. |
| `family_group` | STRING | Nutritional family group (e.g., VERDURAS). |
| `food` | STRING | Name of the food item. |
| `suggested_quantity` | STRING | Suggested portion size. |
| `unit` | STRING | Unit of measurement (e.g., pieza, taza). |
| `gross_weight_grams` | FLOAT | Gross weight including non-edible parts. |
| `net_weight_grams` | FLOAT | Net edible weight. |
| `energy_kcal` | FLOAT | Energy content in kilocalories. |
| `protein_grams` | FLOAT | Protein content in grams. |
| `lipids_grams` | FLOAT | Total lipids content in grams. |
| `carbohidrates_grams` | FLOAT | Total carbohydrates content in grams. |
| `fiber_grams` | FLOAT | Dietary fiber content in grams. |
| `processed_at` | TIMESTAMP | Timestamp when Gemini extracted the data (UTC). |
| `ingestion_at` | TIMESTAMP | Timestamp of BQ insertion (Partition Key). |
| `is_active` | BOOLEAN | SCD Type 2 flag for version control. |
| `source_uri` | STRING | GCS URI of the source PDF. |
| `page_number` | INTEGER | Page number within the source PDF. |

## Recovery Strategy
If a page fails extraction:
1. It is logged to the `dead_letter` table.
2. Operators can re-run the engine using the `specific_pages` parameter to target only those failures.
