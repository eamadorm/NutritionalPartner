---
name: SMAE Engine Stage 2 Deployment
description: Infrastructure codification and CI/CD setup for the smae_engine deployable (Stage 2 completed)
type: project
---

Stage 2 deployment for smae_engine is implemented. Terraform, Cloud Build pipelines, and Dockerfile are in place.

**Why:** Stage 1 prototyping (gcloud/manual resources via create_resources.sh) was completed and merged. Stage 2 codifies all resources in Terraform and wires CI/CD via Cloud Build.

**How to apply:** When making changes to smae_engine infrastructure, use the Terraform files in `backend/smae_engine/deployment/` and the shared resources in `infra/shared_resources/`. Never re-create manual provisioning scripts — everything is IaC.

Key facts:
- `create_resources.sh` was deleted (replaced by Terraform)
- Both deployments use the 4-file TF structure: `backend.tf` (terraform+backend, prefix only), `vars.tf` (variable declarations, no env-specific defaults), `terraform.tfvars` (concrete values), `main.tf` (provider+modules only)
- The GCS backend bucket is never hardcoded in any `.tf` file; always injected via `-backend-config="bucket=$PROJECT_ID-tf-states"` at init time
- Shared resources (Artifact Registry, GCS bucket, BQ dataset+tables) live in `infra/shared_resources/`
- SMAE-specific resources (SA + Cloud Function v2) live in `backend/smae_engine/deployment/`
- CD pipeline deploys via `terraform init` + `terraform apply` (not `gcloud functions deploy`); image tag passed as `-var="image_tag=$SHORT_SHA"`
- CI trigger: `smae-engine-ci` (PR to main, `backend/smae_engine/**`, runs tests + local docker build)
- CD trigger: `smae-engine-cd` (push to main, `backend/smae_engine/**`, tests + push image + tf-init + tf-apply) — 5 steps total
- Docker build context is `backend/` (not the smae_engine subdirectory) — Dockerfile is at `backend/smae_engine/deployment/Dockerfile`
- Image registry path: `us-central1-docker.pkg.dev/<project-id>/nutritional-partner-images/smae-engine`
- Cloud Function entry point: `smae_handler`
- State bucket: `nutritional-partner-tf-states`; smae_engine state path: `tfstates/smae_engine/tf.state`; shared state path: `tfstates/shared_resources/tf.state`
