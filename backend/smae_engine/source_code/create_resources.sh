#!/bin/bash
# create_resources.sh
# Creates the temporary GCS bucket for manual prototyping of SMAE Engine.

PROJECT_ID=$(gcloud config get-value project)
BUCKET_NAME="nutritional-data-sources"

echo "Creating GCS bucket: gs://${BUCKET_NAME} in project ${PROJECT_ID}..."
gcloud storage buckets create "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" --location="us-central1"

echo "Done."
