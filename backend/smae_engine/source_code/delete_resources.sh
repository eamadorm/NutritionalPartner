#!/bin/bash
# delete_resources.sh: Teardown manual infrastructure for SMAE Engine Stage 1

PROJECT_ID="nutritional-partner"
BUCKET_NAME="nutritional-data-sources"
DATASET_ID="nutrimental_information"

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 1. Delete GCS Bucket
echo "Deleting GCS bucket $BUCKET_NAME..."
gcloud storage buckets delete gs://$BUCKET_NAME --recursive

# 2. Delete BQ Dataset
echo "Deleting BQ dataset $DATASET_ID..."
bq rm -r -f $DATASET_ID

echo "Cleanup complete."
