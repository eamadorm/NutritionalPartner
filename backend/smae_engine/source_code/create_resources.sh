#!/bin/bash
# create_resources.sh
# Creates the temporary GCS bucket and BigQuery resources for manual prototyping of SMAE Engine.

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project)
BUCKET_NAME="nutritional-data-sources"
BQ_DATASET="nutrimental_information"
BQ_TABLE="food_equivalents"
BQ_DLT_TABLE="food_equivalents_dead_letter"
LOCATION="us-central1"

# --- GCS ---
echo "Creating GCS bucket: gs://${BUCKET_NAME} in project ${PROJECT_ID}..."
gcloud storage buckets create "gs://${BUCKET_NAME}" \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}"

# --- BigQuery dataset ---
echo "Creating BQ dataset: ${BQ_DATASET}..."
bq --project_id="${PROJECT_ID}" mk \
  --dataset \
  --location="${LOCATION}" \
  --description="Nutritional information extracted from SMAE PDFs" \
  "${PROJECT_ID}:${BQ_DATASET}" || echo "Dataset already exists, skipping."

# --- BigQuery main table ---
echo "Creating BQ table: ${BQ_DATASET}.${BQ_TABLE}..."
bq --project_id="${PROJECT_ID}" mk \
  --table \
  --time_partitioning_field=ingested_at \
  --time_partitioning_type=DAY \
  --description="Food equivalents extracted from SMAE PDFs (SCD Type 2)" \
  "${PROJECT_ID}:${BQ_DATASET}.${BQ_TABLE}" \
  'food_uuid:STRING,food_group:STRING,food:STRING,suggested_quantity:STRING,unit:STRING,net_weight_g:INTEGER,energy_kcal:INTEGER,protein_g:FLOAT,lipids_g:FLOAT,carbohydrates_g:FLOAT,ingested_at:TIMESTAMP,source_uri:STRING,active:BOOLEAN' \
  || echo "Table already exists, skipping."

# --- BigQuery dead-letter table ---
echo "Creating BQ dead-letter table: ${BQ_DATASET}.${BQ_DLT_TABLE}..."
bq --project_id="${PROJECT_ID}" mk \
  --table \
  --description="Dead-letter table for failed food_equivalents row inserts" \
  "${PROJECT_ID}:${BQ_DATASET}.${BQ_DLT_TABLE}" \
  'source_uri:STRING,food_uuid:STRING,raw_row:STRING,error_message:STRING,failed_at:TIMESTAMP' \
  || echo "Dead-letter table already exists, skipping."

echo "Done."
