# Implementation Plan: SMAE Engine Stage 2 Deployment

Promote the SMAE document extraction pipeline from a manual prototyping script to a codified, containerized, and secure Cloud Function (v2).

## User Review Required

> [!IMPORTANT]
> **Shared Data Architecture**: The BigQuery dataset `nutrimental_information` and its tables are managed as **Shared Infrastructure** in `infra/shared_resources/`.
> **Cloud Function v2 Architecture**: Deployed as a containerized Cloud Function (Cloud Run based).
> **CI/CD Triggers**: Two separate triggers will be created: one for **Pull Request validation** (Test + Build) and one for **Production Deployment** (Push + Deploy) upon merging to `main`.

## Proposed Changes

### 1. Shared Infrastructure
Codify global resources used across the entire Nutritional Partner project.

#### [NEW] [infra/shared_resources/main.tf](file:///workspaces/NutritionalPartner/infra/shared_resources/main.tf)
- **Artifact Registry**: Create a repository named `nutritional-partner-images` to host Docker images.
- **GCS Bucket**: Manage the `nutritional-data-sources` bucket.
- **BigQuery Dataset**: `nutrimental_information`.
- **BigQuery Tables**: `food_equivalents` and `food_equivalents_dead_letter`.

---

### 2. SMAE Engine Infrastructure (Terraform)
Codify the specific logic and access controls for the SMAE engine.

#### [NEW] [backend/smae_engine/deployment/main.tf](file:///workspaces/NutritionalPartner/backend/smae_engine/deployment/main.tf)
- **Service Account**: `smae-engine-sa` with `roles/storage.objectUser`, `roles/bigquery.dataEditor`, and `roles/aiplatform.user`.
- **Cloud Function v2**: HTTP triggered, containerized runtime.
- **GCS Backend**: State stored in `gs://nutritional-partner-tf-states/tfstates/smae_engine/tf.state`.

---

### 3. Application Logic & Containerization

#### [NEW] [backend/smae_engine/source_code/Dockerfile](file:///workspaces/NutritionalPartner/backend/smae_engine/source_code/Dockerfile)
- Standardized multi-stage Python build with `uv`.

#### [MODIFY] [backend/smae_engine/source_code/main.py](file:///workspaces/NutritionalPartner/backend/smae_engine/source_code/main.py)
- Implement `smae_handler(request)` for the Functions Framework.

---

### 4. CI/CD Orchestration (Best Practices)

#### [MODIFY] [Makefile](file:///workspaces/NutritionalPartner/Makefile)
Add standardized targets for the SMAE engine deployment:
- `test-smae-engine`: Runs `uv run pytest`.
- `build-smae-engine-local`: Executes `docker build` only (for CI validation).
- `build-smae-engine`: Executes `docker build` and `docker push` to Artifact Registry.
- `deploy-smae-engine`: Executes `gcloud functions deploy`.

#### [MODIFY] [infra/scripts/create_cicd_triggers.sh](file:///workspaces/NutritionalPartner/infra/scripts/create_cicd_triggers.sh)
Provision two distinct triggers for the `smae_engine`:

1.  **CI Trigger (PR Validation)**:
    - **Event**: Pull Request targeting `main`.
    - **Included Files**: `backend/smae_engine/**`.
    - **Build Step**: Executes `make test-smae-engine build-smae-engine-local`.
2.  **CD Trigger (Production Deployment)**:
    - **Event**: Push to `main` branch.
    - **Included Files**: `backend/smae_engine/**`.
    - **Build Step**: Executes `make test-smae-engine build-smae-engine deploy-smae-engine`.

#### [DELETE] [backend/smae_engine/source_code/create_resources.sh](file:///workspaces/NutritionalPartner/backend/smae_engine/source_code/create_resources.sh)
- Remove manual setup scripts once Terraform and CI/CD are functional.

## Verification Plan

### Automated Tests
- Trigger PR validation by creating a test branch.
- Trigger Production deployment by merging a PR.
- Integration test: `curl` call to the production Cloud Function URL.

### Manual Verification
- Inspect Artifact Registry for the new image version.
- Verify Cloud Function IAM permissions and BQ table clustering.
