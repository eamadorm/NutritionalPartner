---
trigger: always_on
description: "DevOps standards for GCP: Cloud Build pipelines, Terraform (CFF), and state management."
---

# devops-guide.md

Follow these protocols for Infrastructure as Code (IaC) and CI/CD orchestration:

### Provider & Infrastructure
- **Cloud Provider**: Exclusively use **Google Cloud Platform (GCP)**.
- **Terraform Standard**:
  - Use [Cloud Foundation Fabric (CFF)](https://github.com/GoogleCloudPlatform/cloud-foundation-fabric) modules for all resources.
  - Always pin CFF modules to an explicit version tag (e.g. `?ref=v34.1.0`). **Never use a floating `main` ref.**
  - **Provider Versioning**: Ensure that `required_providers` blocks in the root configuration are always compatible with the version constraints of the vendored CFF modules. This compatibility must be verified during the planning and development of any DevOps component to prevent initialization conflicts.
  - **Module Vendoring**: To ensure maximum stability and bypass download issues, foundational modules from the Cloud Foundation Fabric (CFF) repository must be downloaded and stored locally in `infra/modules/`. Use the latest stable version (e.g., `v34.1.0`). Specific deployables must reference these local modules. **Cloud Run v2 is preferred for all containerized architectures.**
  - Prioritize Terraform over `gcloud` commands for resource provisioning.
- **State Management**:
  - Store state in a GCS bucket named: `<gcp-project-id>-tf-states`.
  - **Structure**: `/tfstates/<deployment_name>/tf.state`.

### Regional Deployment Strategy
- **Project Main Region**: `us-central1` is the mandatory default region for all resources.
- **Overridability**: Every deployable must support regional overrides for specific services (e.g. `bq_location`, `ar_region`).
- **Fallback Logic**: If a service-specific region is not provided, it must always default to the `region` variable (which itself defaults to `us-central1`).
- **Implementation Pattern**:
  ```hcl
  variable "region" {
    type    = string
    default = "us-central1"
  }
  variable "specific_service_region" {
    type    = string
    default = null
  }
  locals {
    effective_region = coalesce(var.specific_service_region, var.region)
  }
  ```

### Deployable Folder Structure
Every deployable under `backend/<name>/` must follow this exact layout:

```
backend/<name>/
  source_code/          # Python logic only — no deployment artifacts of any kind
  deployment/
    backend.tf          # terraform{} block, empty backend "gcs" {}, required_providers
    vars.tf             # variable declarations only
    terraform.tfvars    # concrete values — committed to source control
    main.tf             # provider + module blocks only
    Dockerfile          # container image definition — lives here, NOT in source_code/
    cloudbuild-ci.yaml  # CI pipeline (lint, test, build)
    cloudbuild-cd.yaml  # CD pipeline (terraform init + apply)
```

**`source_code/` must never contain**: Dockerfiles, shell scripts for GCP provisioning, or any other deployment artifact.

**Stage 1 shell scripts** (`create_resources.sh`, `delete_resources.sh`) belong at the root of `backend/<name>/` during Stage 1 only. Both files must be **deleted before Stage 2 begins** — they must not be present once Terraform owns the resources.

### Dockerfile Best Practices
All Dockerfiles must adhere to these standards:
- **Security**: Never run as `root`. Define a non-privileged `USER`.
- **Optimization**: Use multi-stage builds to keep production images lean.

### Terraform File Structure
Every Terraform deployment must be split across exactly four files — no exceptions:
- **`backend.tf`**: `terraform {}` block with an **empty** `backend "gcs" {}` and `required_providers`. No values inside the backend block — neither `bucket` nor `prefix` are hardcoded. Both are always injected at runtime.
- **`vars.tf`**: All `variable` declarations. No hardcoded defaults for environment-specific values (project_id, region).
- **`terraform.tfvars`**: Concrete values for every declared variable. Committed to source control (values are not secret).
- **`main.tf`**: `provider` block and all `module` blocks only — no variable declarations, no backend config.

**Parametrization rule**: Every operationally meaningful value in `main.tf` must be a variable — no hardcoded strings or numbers. This includes: resource names, service account name, IAM roles (`list(string)`), runtime identifier, memory, timeout, instance count, image/registry names, dataset IDs, dataset location, and bucket names. Structural values that are not configuration (BQ table schemas, partition definitions, entry point names tied to code) may remain inline.

Initialization command pattern (Makefile and Cloud Build) — **both `bucket` and `prefix` must always be passed**:
```
terraform init \
  -backend-config="bucket=<project-id>-tf-states" \
  -backend-config="prefix=tfstates/<deployment_name>/tf.state"
```

### CI/CD Pipelines (Cloud Build)
- **Tooling**: Use **Cloud Build**. Triggers must be created/managed via the centralized `infra/scripts/cicd_triggers.sh` script, **never** via Terraform.

#### CI/CD Responsibility Separation

| Pipeline | Steps | Must NOT contain |
|----------|-------|-----------------|
| `cloudbuild-ci.yaml` (PR gate) | Run tests · Docker build (local, no push) · `terraform validate` | Docker push, `terraform apply` |
| `cloudbuild-cd.yaml` (push-to-main) | Docker build + push · `terraform init` + `terraform apply` | Tests — already validated by CI |

Tests **must never appear in the CD pipeline**. CI is the correctness gate; CD executes a pre-validated artifact. The `terraform validate` step in CI (run with `-backend=false`) is the CD pre-flight check — it confirms the Terraform config is syntactically valid and all referenced variables exist before any merge reaches CD.

#### Service Account Permissions Validation

When writing or reviewing any CI/CD pipeline, verify the executing SA has all required IAM permissions for every step. Required permissions for `cicd-pipeline-sa` typically include:

- GCS read/write for Terraform state bucket
- Artifact Registry push (Docker image publication)
- Cloud Run / Cloud Functions deploy and update
- IAM role bindings (to create/update per-function/service SAs)
- Service account impersonation (`roles/iam.serviceAccountUser`)
- Service account management (`roles/iam.serviceAccountAdmin`)

**Mandatory Check**: Whenever creating a new deployable with its own Service Account and IAM roles, you MUST verify that the CI/CD SA (`cicd-pipeline-sa`) has the necessary permissions (e.g., `iam.serviceAccounts.create`, `iam.serviceAccounts.actAs`) to fully provision and configure the new service.

**If any permission is missing**: add the role to the `ROLES` array in `infra/scripts/bootstrap.sh` — **never in Terraform**. `bootstrap.sh` is the single source of truth for CI/CD SA permissions; the SA (`cicd-pipeline-sa`) is defined and granted roles there exclusively.

#### Shared Resources vs. Local Deployment
Before adding any resource to a deployable's `deployment/` folder, perform a **Global Context Check**:
- **Shared Resources**: If a resource (GCS bucket, BigQuery dataset, Artifact Registry) is intended to be used by **multiple deployables** or represents **foundational infrastructure**, it MUST be defined in `infra/shared_resources/`.
- **Local Resources**: Only resources strictly dedicated to a single deployable (e.g., the specific Cloud Run service, its dedicated SA, and its IAM bindings) should reside in the deployable's `deployment/` folder.

#### CD Pipeline — Terraform deploy pattern
The CD pipeline (`cloudbuild-cd.yaml`) must deploy via `terraform init` + `terraform apply`. **Never use `gcloud functions deploy` or equivalent imperative deploy commands in the CD pipeline.**

Key rules:
- **Substitutions Placement**: All `substitutions` must be defined at the **top** of the Cloud Build YAML file for easier discovery and replacement.
- Pass the image tag as a Terraform variable: `-var="image_tag=$SHORT_SHA"`.
- Use the `_REGION` substitution variable (a user-defined substitution) — not `$REGION`, which is not a Cloud Build built-in.
- Do **not** set `substitution_option: ALLOW_LOOSE`. All referenced substitution variables must be explicitly declared.

Minimal CD step pattern:
```yaml
substitutions:
  _REGION: us-central1

steps:
  - name: 'hashicorp/terraform:1.9'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        terraform init \
          -backend-config="bucket=$$_PROJECT_ID-tf-states" \
          -backend-config="prefix=tfstates/<deployment_name>/tf.state" && \
        terraform apply -auto-approve \
          -var="image_tag=$SHORT_SHA" \
          -var="region=$_REGION"

```

### Automation & Execution
- **Makefile**: There must be **ONLY ONE Makefile** at the root of the repository to orchestrate all local and CI/CD tasks.
- **Workflow**: For all Stage 2 deployment tasks, Terraform codification, and CI/CD trigger management, you MUST trigger the specialized skill:
  - **Skill**: `@.agents/skills/deployment/SKILL.md`