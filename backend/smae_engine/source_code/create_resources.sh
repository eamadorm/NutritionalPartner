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
echo "Checking GCS bucket: gs://${BUCKET_NAME}..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating GCS bucket: gs://${BUCKET_NAME}..."
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}"
else
  echo "Bucket already exists, skipping."
fi

# --- BigQuery dataset ---
echo "Checking BQ dataset: ${BQ_DATASET}..."
if ! bq --project_id="${PROJECT_ID}" show "${BQ_DATASET}" >/dev/null 2>&1; then
  echo "Creating BQ dataset: ${BQ_DATASET}..."
  bq --project_id="${PROJECT_ID}" mk \
    --dataset \
    --location="${LOCATION}" \
    --description="Nutritional information extracted from SMAE PDFs" \
    "${PROJECT_ID}:${BQ_DATASET}"
else
  echo "Dataset already exists, skipping."
fi

# --- BigQuery main table ---
echo "Checking BQ table: ${BQ_DATASET}.${BQ_TABLE}..."
if ! bq --project_id="${PROJECT_ID}" show "${BQ_DATASET}.${BQ_TABLE}" >/dev/null 2>&1; then
  echo "Creating BQ table: ${BQ_DATASET}.${BQ_TABLE}..."
  bq --project_id="${PROJECT_ID}" mk \
    --table \
    --time_partitioning_field=ingested_at \
    --time_partitioning_type=DAY \
    --clustering_fields=food_uuid,food_group \
    --description="Food equivalents extracted from SMAE PDFs (SCD Type 2)" \
    "${PROJECT_ID}:${BQ_DATASET}.${BQ_TABLE}" \
    'food_uuid:STRING,food_group:STRING,food:STRING,suggested_quantity:STRING,unit:STRING,net_weight_g:INTEGER,energy_kcal:INTEGER,protein_g:FLOAT,lipids_g:FLOAT,carbohydrates_g:FLOAT,ingested_at:TIMESTAMP,source_uri:STRING,active:BOOLEAN'
else
  echo "Table already exists, skipping."
fi

# --- BigQuery dead-letter table ---
echo "Checking BQ dead-letter table: ${BQ_DATASET}.${BQ_DLT_TABLE}..."
if ! bq --project_id="${PROJECT_ID}" show "${BQ_DATASET}.${BQ_DLT_TABLE}" >/dev/null 2>&1; then
  echo "Creating BQ dead-letter table: ${BQ_DATASET}.${BQ_DLT_TABLE}..."
  bq --project_id="${PROJECT_ID}" mk \
    --table \
    --description="Dead-letter table for failed food_equivalents row inserts" \
    "${PROJECT_ID}:${BQ_DATASET}.${BQ_DLT_TABLE}" \
    'source_uri:STRING,food_uuid:STRING,raw_row:STRING,error_message:STRING,failed_at:TIMESTAMP'
else
  echo "Dead-letter table already exists, skipping."
fi

echo "Done."
