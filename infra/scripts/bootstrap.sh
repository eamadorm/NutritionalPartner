#!/bin/bash
# ==============================================================================
# Configuration Block
# ==============================================================================
PROJECT_ID="${1:-nutritional-partner}"
REGION="${2:-us-central1}"
SA_NAME="cicd-pipeline-sa"
BUCKET_NAME="${PROJECT_ID}-tf-states"

# Roles for least privilege CI/CD (Stage 1 & 2)
ROLES=(
  "roles/storage.admin"
  "roles/artifactregistry.admin"
  "roles/cloudbuild.builds.builder"
  "roles/run.admin"
  "roles/iam.serviceAccountUser"
  "roles/iam.securityAdmin"
  "roles/cloudresourcemanager.projectIamAdmin"
)

# ==============================================================================
# Initialization Logic
# ==============================================================================
set -e

echo "🚀 Starting bootstrap for project: ${PROJECT_ID} in region: ${REGION}"

# 1. Enable Required APIs
echo "📡 Enabling strictly necessary APIs..."
gcloud services enable \
  serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  storage-api.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"

# 2. Create GCS Bucket for Terraform States
echo "🪣 Creating GCS bucket for Terraform states: ${BUCKET_NAME}..."
if ! gsutil ls -p "${PROJECT_ID}" "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_NAME}"
  echo "✅ Bucket created."
else
  echo "ℹ️ Bucket already exists."
fi

echo "🔄 Enabling versioning on bucket..."
gsutil versioning set on "gs://${BUCKET_NAME}"

# 3. Create CI/CD Service Account
echo "👤 Creating Service Account: ${SA_NAME}..."
if ! gcloud iam service-accounts describe "${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="CI/CD Pipeline Service Account" \
    --project="${PROJECT_ID}"
  echo "✅ Service Account created."
else
  echo "ℹ️ Service Account already exists."
fi

# 4. Bind Roles (Least Privilege)
echo "🔐 Binding foundational roles to SA..."
for ROLE in "${ROLES[@]}"; do
  echo "   - Binding ${ROLE}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="${ROLE}" >/dev/null
done

echo "✨ Bootstrap completed successfully!"
