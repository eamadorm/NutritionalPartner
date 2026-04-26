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
- Shared resources (Artifact Registry, GCS bucket, BQ dataset+tables) live in `infra/shared_resources/main.tf`
- SMAE-specific resources (SA + Cloud Function v2) live in `backend/smae_engine/deployment/main.tf`
- CI trigger: `smae-engine-ci` (PR to main, `backend/smae_engine/**`, runs tests + local docker build)
- CD trigger: `smae-engine-cd` (push to main, `backend/smae_engine/**`, tests + push image + deploy)
- Docker build context is `backend/` (not the smae_engine subdirectory) — Dockerfile is at `backend/smae_engine/source_code/Dockerfile`
- Image registry path: `us-central1-docker.pkg.dev/<project-id>/nutritional-partner-images/smae-engine`
- Cloud Function entry point: `smae_handler`
- State bucket: `nutritional-partner-tf-states`; smae_engine state path: `tfstates/smae_engine/tf.state`; shared state path: `tfstates/shared_resources/tf.state`
