---
trigger: always_on
glob: "**/*.{yaml,yml,tf,tfvars,Makefile}"
description: "DevOps standards for GCP: Cloud Build pipelines, Terraform (CFF), and state management."
---

# devops-guide.md

Follow these protocols for Infrastructure as Code (IaC) and CI/CD orchestration:

### Provider & Infrastructure
- **Cloud Provider**: Exclusively use **Google Cloud Platform (GCP)**.
- **Terraform Standard**: 
  - Use [Cloud Foundation Fabric (CFF)](https://github.com/GoogleCloudPlatform/cloud-foundation-fabric) modules for all resources.
  - Create custom modules only if a CFF module does not exist.
  - Prioritize Terraform over `gcloud` commands for resource provisioning.
- **State Management**:
  - Store state in a GCS bucket named: `<gcp-project-id>-tf-states`.
  - **Structure**:
    - `/tfstates/shared_resources/tf.state`: For foundation resources (Registries, Buckets, Networking).
    - `/tfstates/<deployment_name>/tf.state`: For application-specific resources.
  - **Single Environment**: Use a single-environment strategy for the MVP. No environment-specific bucket prefixes are required at this stage.

### CI/CD Pipelines (Cloud Build)
- **Tooling**: Use **Cloud Build** with pipeline files located within each deployable's `/deployment` directory. Triggers must be created/managed via the centralized `infra/scripts/cicd_triggers.sh` script, **never** via Terraform.

### Bootstrap & Global CI
- **Bootstrap Protocol**: The root `infra/scripts/bootstrap.sh` must be used for the Initial Setup of the GCP project. 
  - It MUST use `gcloud` terminal commands ONLY (no Terraform for bootstrap).
  - It creates the GCS bucket for Terraform state.
  - It creates the Service Account (SA) for CI/CD with necessary IAM roles.
  - It creates a single `ci-lint` trigger in Cloud Build using the root `infra/ci-lint.yaml` definition.
- **Global CI**: The `infra/ci-lint.yaml` pipeline iterates and lints all files (TF, YAML, Python, TS) across the entire repository.
- **Stage 2 Triggers**: For all application deployments, triggers must be added to `infra/scripts/cicd_triggers.sh`. These must be functional and validated before any branch is merged to `main`.
- **Trigger Strategy**: Every deployable must have two path-based triggers (triggered only when files in that folder change):
  1. **CI (Pull Request)**:
     - Execute `make lint` (Code and Terraform linting).
     - Run `terraform plan`.
     - Build Docker image (Verify build, **do not push**).
  2. **CD (Merge to Main)**:
     - Build and **Push** Docker image to Artifact Registry.
     - Run `terraform apply` (using the plan from CI if possible).
     - Deploy to target service (Cloud Run, GKE, etc.).

### Automation & UI
- **Makefile**: There must be **ONLY ONE Makefile** at the root of the repository to orchestrate all local and CI/CD tasks.
  - `make lint`: Run all linters (Ruff, TFLint, etc.).
  - `make test`: Execute the test suite via `uv`.
  - Standardize all common activities (deploy, plan, init) as root Make targets.
- **Docker Context**: For deployables, the Docker Context should typically be set to the deployable's root (e.g., `backend/name/`) even if the `Dockerfile` resides in `/deployment`.

### Implementation Example
**Folder Structure:**
```text
/backend/nutritional_api
  ├── source_code/
  │     └── main.py
  └── deployment/
        ├── main.tf        # Consumes CFF modules
        ├── Dockerfile
        └── pipeline.yaml
/frontend/dashboard
  ├── source_code/
  └── deployment/
/infra
  ├── shared_resources/    # CFF-based foundation
  ├── scripts/
  │     └── bootstrap.sh
  └── ci-lint.yaml
Makefile
```
