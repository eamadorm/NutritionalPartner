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
    - `/tfstates/shared_resources/tf.state` (Registries, Buckets, Networking).
    - `/tfstates/<deployable_name>/tf.state` (Specific app resources).

### CI/CD Pipelines (Cloud Build)
- **Tooling**: Use **Cloud Build** with pipeline files located within each deployable's directory (e.g., `api/ci-pipeline.yaml`).
- **Trigger Strategy**: Every deployable must have two path-based triggers (triggered only when files in that folder change):
  1. **CI (Pull Request)**:
     - Execute `make lint` (Code and Terraform linting).
     - Run `terraform plan`.
     - Build Docker image (Verify build, **do not push**).
  2. **CD (Merge to Main)**:
     - Build and **Push** Docker image to Artifact Registry.
     - Run `terraform apply` (using the plan from CI if possible).
     - Deploy to target service (Cloud Run, GKE, etc.).

### Automation & Scripting
- **Makefiles**: Use `make` commands to encapsulate complex logic.
  - `make lint`: Run all linters (Ruff, TFLint, etc.).
  - `make test`: Execute the test suite via `uv`.
  - Use `make` for any deployment steps that fall outside of standard Terraform scope.

### Implementation Example
**Folder Structure:**
```text
/api
  ├── ci-pipeline.yaml
  ├── cd-pipeline.yaml
  ├── Makefile
  └── main.tf  # Uses CFF modules
