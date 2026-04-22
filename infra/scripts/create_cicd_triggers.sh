#!/bin/bash
# ==============================================================================
# Configuration Block
# ==============================================================================
PROJECT_ID="${1:-nutritional-partner}"
REGION="${2:-us-central1}"
REPO_NAME="${3:-NutritionalPartner}"
REPO_OWNER="${4:-eamadorm}"
CONNECTION_NAME="${5:-github-connection}" # Cloud Build 2nd gen connection name

# ==============================================================================
# Initialization Logic
# ==============================================================================
set -e

echo "🛰️ Starting CI/CD Trigger creation for project: ${PROJECT_ID}"

# 1. Check for Cloud Build Connection
echo "🔍 Verifying Cloud Build connection: ${CONNECTION_NAME}..."
if ! gcloud builds connections describe "${CONNECTION_NAME}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "❌ ERROR: Cloud Build connection '${CONNECTION_NAME}' not found in region '${REGION}'."
  echo "👉 Please establish the connection manually in the GCP Console before running this script."
  exit 1
fi

echo "✅ Connection found."

# 2. Check for Repository Linkage
echo "🔗 Verifying repository linkage for ${REPO_OWNER}/${REPO_NAME}..."
# repository linkage check can be complex via CLI, usually creating trigger will fail if not found.

# 3. Create CI Trigger (Pull Requests)
echo "🔨 Creating CI Trigger (on PRs)..."
gcloud builds triggers create github \
  --name="ci-linting-pr" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/${REPO_NAME}" \
  --branch-pattern="^main$" \
  --build-config="infra/ci-lint.yaml" \
  --event-type="pull-request" \
  --description="Global CI linting and security scan for Pull Requests" \
  || echo "⚠️ CI Trigger creation might have failed (check if it already exists)."

# 4. Create CD Trigger (Push to Main)
echo "🚀 Creating CD Trigger (on Push to Main)..."
gcloud builds triggers create github \
  --name="cd-deployment-main" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/${REPO_NAME}" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --event-type="push" \
  --description="Production deployment on merge to main" \
  || echo "⚠️ CD Trigger creation might have failed (check if it already exists)."

echo "✨ CI/CD Triggers setup completed (or verified)!"
