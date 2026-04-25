#!/bin/bash
# delete_resources.sh
# Tears down the temporary GCS bucket used for manual prototyping.

BUCKET_NAME="nutritional-data-sources"

echo "Deleting GCS bucket: gs://${BUCKET_NAME}..."
gcloud storage rm -r "gs://${BUCKET_NAME}"

echo "Done."
