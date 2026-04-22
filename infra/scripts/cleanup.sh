#!/bin/bash
# ==============================================================================
# Configuration Block
# ==============================================================================
PROJECT_ID="${1:-nutritional-partner}"
REGION="${2:-us-central1}"
REPO_NAME="${3:-NutritionalPartner}"
REPO_OWNER="${4:-eamadorm}"
CONNECTION_NAME="${5:-github-connection}"
SA_NAME="cicd-pipeline-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET_NAME="${PROJECT_ID}-tf-states"

# ==============================================================================
# Initialization Logic
# ==============================================================================
set -e

echo "Starting cleanup for project: ${PROJECT_ID} in region: ${REGION}"

# 1. Delete CI/CD Triggers
echo "Deleting CI/CD Triggers..."
# We try to delete known triggers. Add more here as they are created.
KNOWN_TRIGGERS=("ci-linting")

for trigger in "${KNOWN_TRIGGERS[@]}"; do
  echo "   - Deleting trigger: ${trigger}..."
  gcloud builds triggers delete "${trigger}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet || echo "      (Trigger '${trigger}' not found or already deleted)"
done

# 2. Delete Service Account
echo "Deleting Service Account: ${SA_NAME}..."
if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts delete "${SA_EMAIL}" --project="${PROJECT_ID}" --quiet
  echo "SUCCESS: Service Account deleted."
else
  echo "INFO: Service Account not found or already deleted."
fi

# 3. Delete GCS Bucket for Terraform States
echo "Deleting GCS bucket: ${BUCKET_NAME}..."
if gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  # Note: Use -r to recursively delete all contents (state files)
  gcloud storage rm -r "gs://${BUCKET_NAME}" --project="${PROJECT_ID}"
  echo "SUCCESS: Bucket deleted."
else
  echo "INFO: Bucket not found or already deleted."
fi

# ==============================================================================
# Summary
# ==============================================================================
echo "Cleanup completed successfully!"
echo "NOTE: External resources like GitHub connections or manually enabled APIs were NOT affected."
