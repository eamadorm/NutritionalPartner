#!/bin/bash
# ==============================================================================
# Configuration Block
# ==============================================================================
PROJECT_ID="${1:-nutritional-partner}"
REGION="${2:-us-central1}"
REPO_NAME="${3:-NutritionalPartner}"
REPO_OWNER="${4:-eamadorm}"
CONNECTION_NAME="${5:-github-connection}"

USER_EMAIL="eamadorm11@gmail.com"
SA_NAME="cicd-pipeline-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
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

echo "Starting bootstrap for project: ${PROJECT_ID} in region: ${REGION}"

# 1. Enable Required APIs
echo "Enabling strictly necessary APIs..."
gcloud services enable \
  serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  storage-api.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"

# 2. Create GCS Bucket for Terraform States
echo "Creating GCS bucket for Terraform states: ${BUCKET_NAME}..."
if ! gsutil ls -p "${PROJECT_ID}" "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_NAME}"
  echo "SUCCESS: Bucket created."
else
  echo "INFO: Bucket already exists."
fi

echo "Enabling versioning on bucket..."
gsutil versioning set on "gs://${BUCKET_NAME}"

# 3. Create CI/CD Service Account
echo "Creating Service Account: ${SA_NAME}..."
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="CI/CD Pipeline Service Account" \
    --project="${PROJECT_ID}"
  echo "SUCCESS: Service Account created."
else
  echo "INFO: Service Account already exists."
fi

# 4. Bind Roles (Least Privilege)
echo "Binding foundational roles to SA..."
for ROLE in "${ROLES[@]}"; do
  echo "   - Binding ${ROLE}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" >/dev/null
done

# 5. Grant Impersonation to Owner
echo "Granting Token Creator role to ${USER_EMAIL}..."
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --member="user:${USER_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" >/dev/null

# 6. Initialize CI/CD Triggers
echo "Initializing CI/CD Triggers..."
./infra/scripts/create_cicd_triggers.sh \
  "${PROJECT_ID}" \
  "${REGION}" \
  "${REPO_NAME}" \
  "${REPO_OWNER}" \
  "${CONNECTION_NAME}" \
  "${SA_EMAIL}"

echo "Bootstrap completed successfully!"
