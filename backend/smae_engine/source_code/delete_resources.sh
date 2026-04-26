#!/bin/bash
# delete_resources.sh
# Tears down the temporary GCS bucket and BigQuery resources used for manual prototyping.

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project)
BUCKET_NAME="nutritional-data-sources"
BQ_DATASET="nutrimental_information"
BQ_TABLE="food_equivalents"
BQ_DLT_TABLE="food_equivalents_dead_letter"

# --- GCS ---
echo "Deleting GCS bucket: gs://${BUCKET_NAME}..."
gcloud storage rm -r "gs://${BUCKET_NAME}"

# --- BigQuery tables (must be deleted before dataset) ---
echo "Deleting BQ table: ${BQ_DATASET}.${BQ_DLT_TABLE}..."
bq --project_id="${PROJECT_ID}" rm -f \
  "${PROJECT_ID}:${BQ_DATASET}.${BQ_DLT_TABLE}" || echo "Table not found, skipping."

echo "Deleting BQ table: ${BQ_DATASET}.${BQ_TABLE}..."
bq --project_id="${PROJECT_ID}" rm -f \
  "${PROJECT_ID}:${BQ_DATASET}.${BQ_TABLE}" || echo "Table not found, skipping."

# --- BigQuery dataset ---
echo "Deleting BQ dataset: ${BQ_DATASET}..."
bq --project_id="${PROJECT_ID}" rm -f \
  --dataset "${PROJECT_ID}:${BQ_DATASET}" || echo "Dataset not found, skipping."

echo "Done."
