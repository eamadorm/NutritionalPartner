#!/bin/bash
# ==============================================================================
# Configuration Block
# ==============================================================================
PROJECT_ID="${1:-nutritional-partner}"
REGION="${2:-us-central1}"
REPO_NAME="${3:-NutritionalPartner}"
REPO_OWNER="${4:-eamadorm}"
CONNECTION_NAME="${5:-eamadorm-github}"

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
  "roles/resourcemanager.projectIamAdmin"
)

# ==============================================================================
# Bootstrap Execution
# ==============================================================================
set -e

echo "Starting bootstrap for project: ${PROJECT_ID} in region: ${REGION}"

# 1. Enable strictly necessary APIs
echo "Enabling strictly necessary APIs..."
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  --project="${PROJECT_ID}"

# 2. Create GCS bucket for Terraform states
echo "Creating GCS bucket for Terraform states: ${BUCKET_NAME}..."
if gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "INFO: Bucket already exists."
else
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}"
fi

echo "Enabling versioning on bucket..."
gcloud storage buckets update "gs://${BUCKET_NAME}" --versioning

# 3. Create CI/CD Service Account
echo "Creating Service Account: ${SA_NAME}..."
if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "INFO: Service Account already exists."
else
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="CI/CD Pipeline Service Account" \
    --project="${PROJECT_ID}"
fi

# 4. Bind foundational roles to the SA
echo "Binding foundational roles to SA..."
for ROLE in "${ROLES[@]}"; do
  echo "   - Binding ${ROLE}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None >/dev/null
done

# 5. Allow current user to impersonate the SA (for local Terraform runs)
echo "Granting Token Creator role to ${USER_EMAIL}..."
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --member="user:${USER_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --condition=None >/dev/null

# 6. Deploy Shared Resources
echo "Deploying Shared Resources (BigQuery, Artifact Registry, GCS)..."
cd infra/shared_resources
terraform init \
  -backend-config="bucket=${BUCKET_NAME}" \
  -backend-config="prefix=tfstates/shared_resources/tf.state"
terraform apply -auto-approve \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}"
cd ../..

# 7. Initialize CI/CD Triggers
echo "Initializing CI/CD Triggers..."
bash ./infra/scripts/create_cicd_triggers.sh \
  "${PROJECT_ID}" \
  "${REGION}" \
  "${REPO_NAME}" \
  "${REPO_OWNER}" \
  "${CONNECTION_NAME}" \
  "${SA_EMAIL}"

echo "Bootstrap completed successfully!"
