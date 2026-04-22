#!/bin/bash
# ==============================================================================
# Configuration Block
# ==============================================================================
PROJECT_ID="${1:-nutritional-partner}"
REGION="${2:-us-central1}"
REPO_NAME="${3:-NutritionalPartner}"
REPO_OWNER="${4:-eamadorm}" # Github account name
CONNECTION_NAME="${5:-github-connection}" # Cloud Build 2nd gen connection name
DEFAULT_SA="${6}" # Default Service Account for triggers

# ==============================================================================
# Initialization Logic
# ==============================================================================
set -e

echo "Starting CI/CD Trigger creation for project: ${PROJECT_ID}"

# 1. Check for Cloud Build Connection
echo "Verifying Cloud Build connection: ${CONNECTION_NAME}..."
if ! gcloud builds connections describe "${CONNECTION_NAME}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "ERROR: Cloud Build connection '${CONNECTION_NAME}' not found in region '${REGION}'."
  echo "ACTION REQUIRED: Please establish the connection manually in the GCP Console before running this script."
  echo "Visit: https://console.cloud.google.com/cloud-build/repositories/2nd-gen"
  exit 1
fi
echo "SUCCESS: Connection found."

# 2. Check for Repository Linkage
echo "Verifying repository linkage: ${REPO_NAME}..."
if ! gcloud builds repositories describe "${REPO_NAME}" --connection="${CONNECTION_NAME}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "ERROR: Repository '${REPO_NAME}' is not linked to connection '${CONNECTION_NAME}' in region '${REGION}'."
  echo "ACTION REQUIRED: Please link the repository manually in the GCP Console under the '${CONNECTION_NAME}' connection."
  echo "Visit: https://console.cloud.google.com/cloud-build/repositories/2nd-gen"
  exit 1
fi
echo "SUCCESS: Repository linkage verified."

# ==============================================================================
# Functional Logic
# ==============================================================================

# Function to create a Cloud Build trigger if it doesn't already exist.
# Usage: create_cloudbuild_trigger NAME EVENT_TYPE INCLUDED_FILES IGNORED_FILES SERVICE_ACCOUNT YAML_CONFIG_FILE
create_cloudbuild_trigger() {
  local NAME="$1"
  local EVENT_TYPE="$2"
  local INCLUDED_FILES="$3"
  local IGNORED_FILES="$4"
  local SERVICE_ACCOUNT="$5"
  local YAML_CONFIG_FILE="$6"

  echo "Processing trigger: ${NAME}..."

  # Check for existence
  if gcloud builds triggers describe "${NAME}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "INFO: Trigger '${NAME}' already exists. Skipping creation."
    return 0
  fi

  # Prepare create command
  local COMMAND=(
    "gcloud" "builds" "triggers" "create" "github"
    "--name=${NAME}"
    "--region=${REGION}"
    "--project=${PROJECT_ID}"
    "--repository=projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/${REPO_NAME}"
    "--branch-pattern=^main$"
    "--build-config=${YAML_CONFIG_FILE}"
    "--event-type=${EVENT_TYPE}"
    "--service-account=${SERVICE_ACCOUNT}"
  )

  # Add optional file filters
  if [[ -n "${INCLUDED_FILES}" ]]; then
    COMMAND+=("--included-files=${INCLUDED_FILES}")
  fi
  if [[ -n "${IGNORED_FILES}" ]]; then
    COMMAND+=("--ignored-files=${IGNORED_FILES}")
  fi

  # Execute command
  if "${COMMAND[@]}" >/dev/null 2>&1; then
    echo "SUCCESS: Trigger '${NAME}' created."
  else
    echo "ERROR: Failed to create trigger '${NAME}'."
    return 1
  fi
}

# ==============================================================================
# Trigger Definitions
# ==============================================================================

# CI Triggers (Pull Request focus)
# Patterns: Name|Event|Included|Ignored|SA|ConfigFile
CI_TRIGGERS=(
  "ci-linting|pull-request||**/*.md,.gitignore,LICENSE|${DEFAULT_SA}|infra/ci-lint.yaml"
)

# CD Triggers (Merge to Main focus)
CD_TRIGGERS=()

# ==============================================================================
# Execution Loop
# ==============================================================================

echo "Initializing CI Triggers..."
for trigger in "${CI_TRIGGERS[@]}"; do
  IFS='|' read -r name type inc ign sa config <<< "$trigger"
  create_cloudbuild_trigger "$name" "$type" "$inc" "$ign" "$sa" "$config"
done

echo "Initializing CD Triggers..."
for trigger in "${CD_TRIGGERS[@]}"; do
  IFS='|' read -r name type inc ign sa config <<< "$trigger"
  create_cloudbuild_trigger "$name" "$type" "$inc" "$ign" "$sa" "$config"
done

echo "CI/CD Triggers setup completed (or verified)!"
