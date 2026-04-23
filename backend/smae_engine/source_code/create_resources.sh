#!/bin/bash
# create_resources.sh: Setup manual infrastructure for SMAE Engine Stage 1

PROJECT_ID="nutritional-partner"
BUCKET_NAME="nutritional-data-sources"
DATASET_ID="nutrimental_information"
TABLE_FOOD="food_equivalents"
TABLE_DLQ="extraction_dead_letter"
LOCATION="us-central1"

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 1. Create GCS Bucket
echo "Creating GCS bucket $BUCKET_NAME..."
gcloud storage buckets create gs://$BUCKET_NAME --location=$LOCATION

# 2. Create BQ Dataset
echo "Creating BQ dataset $DATASET_ID..."
bq --location=$LOCATION mk -d $DATASET_ID

# 3. Create BQ Nutritional Info Table
echo "Creating BQ table nutritional_info..."
bq mk --table \
    --schema "food_uuid:STRING,family_group:STRING,food:STRING,suggested_quantity:STRING,unit:STRING,gross_weight_grams:FLOAT,net_weight_grams:FLOAT,energy_kcal:FLOAT,protein_grams:FLOAT,lipids_grams:FLOAT,carbohidrates_grams:FLOAT,fiber_grams:FLOAT,processed_at:TIMESTAMP,ingestion_at:TIMESTAMP,is_active:BOOLEAN,source_uri:STRING,page_number:INTEGER" \
    --time_partitioning_field ingestion_at \
    --time_partitioning_type DAY \
    --clustering_fields family_group,food \
    $DATASET_ID.$TABLE_FOOD

# Update descriptions for food_equivalents
echo "Updating column descriptions for $TABLE_FOOD..."
bq update --description "Nutritional food equivalents data extracted via Gemini" $DATASET_ID.$TABLE_FOOD

# 4. Create BQ Dead Letter Table
echo "Creating BQ table $TABLE_DLQ..."
bq mk --table \
    --schema "source_uri:STRING,page_number:INTEGER,error_message:STRING,processed_at:TIMESTAMP,ingestion_at:TIMESTAMP" \
    --time_partitioning_field ingestion_at \
    --time_partitioning_type DAY \
    --clustering_fields source_uri \
    $DATASET_ID.$TABLE_DLQ

echo "Setup complete."
