---
name: deployment
description: Manages Stage 2 (Deployment), including Terraform codification via CFF, CI/CD trigger management, and Cloud Build orchestration. Trigger this skill when promoting logic from prototyping to production.
---

# Deployment Skill

This skill governs the infrastructure codification and pipeline automation for the Nutritional Partner project.

## 1. Terraform Codification (CFF)
Implement infrastructure requirements in `backend/<name>/deployment/` or `frontend/<name>/deployment/`:
- **Modules**: Exclusively use CFF modules.
- **Shared Infrastructure**: Use `infra/shared_resources/` for global foundation resources (Networking, Registries, Buckets).
- **Resources**: Ensure they match the logic approved in the Stage 1 Notebook.
- **State**: Use the `<gcp-project-id>-tf-states` bucket.

## 2. CI/CD Orchestration
Manage triggers via `infra/scripts/cicd_triggers.sh`:
- **PR Trigger (CI)**: `make lint`, `terraform plan`, verify Docker build.
- **Merge Trigger (CD)**: Push to Artifact Registry, `terraform apply`, and deploy to Cloud Run/GKE.
- **Constraint**: Triggers must NEVER be managed via Terraform.

## 3. Automation (Makefile)
- Ensure all common activities (plan, deploy, lint) are wrapped in the root `Makefile`.
- Context: Docker context should be the deployable root (e.g., `backend/name/`).

## 4. Project Bootstrap
When performing an initial setup, use `infra/scripts/bootstrap.sh`:
- Create GCS state bucket.
- Create CI/CD Service Account and IAM roles.
- Initialize the `ci-lint` trigger.

## References
- `@.agents/rules/devops-guide.md` for GCP and state management standards.
