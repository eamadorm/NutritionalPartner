# Bootstrap & Developer Onboarding

This document describes the foundational setup for the Nutritional Partner monorepo and the automated GCP environment initialization.

## 1. Quick Start

To set up your local environment and initialize GCP foundations:

```bash
# 2. Run the bootstrap script
make bootstrap PROJECT_ID=your-project-id REGION=us-central1

# 3. (Optional) Teardown the environment
make cleanup PROJECT_ID=your-project-id
```

## 2. Infrastructure Foundations

The `make bootstrap` command executes `infra/scripts/bootstrap.sh`, which performs the following:

- **APIs**: Enables Cloud Build, Artifact Registry, IAM, and Storage.
- **State Management**: Creates a GCS bucket `{PROJECT_ID}-tf-states` with versioning enabled for Terraform state files.
- **Service Account**: Creates `cicd-pipeline-sa` with least privilege roles:
    - `roles/storage.admin`
    - `roles/artifactregistry.admin`
    - `roles/cloudbuild.builds.builder`
    - `roles/run.admin`
    - `roles/iam.serviceAccountUser`
    - `roles/iam.securityAdmin`
    - `roles/resourcemanager.projectIamAdmin`

## 3. CI/CD Lifecycle Utility

Foundational infrastructure is managed via two core scripts that ensure idempotency and safety.

### Bootstrap & Triggers
`make bootstrap` orchestrates the creation of all foundational resources. It calls `create_cicd_triggers.sh`, which automatically:
- **Detects Repository Naming**: Identifies whether the repo is linked as `RepoName` or the 2nd Gen standard `Owner-RepoName`.
- **Aligns Event Flags**: Uses API-specific flags (`--pull-request-pattern`) for 2nd Gen compatibility.
- **Handles SA Impersonation**: Configures triggers using the full canonical resource name of the service account.

### Cleanup & Reset
`make cleanup` executes `infra/scripts/cleanup.sh` to safely teardown triggers, service accounts, and state buckets.

> [!CAUTION]
> **Data Loss**: Cleanup permanently deletes the Terraform state bucket. Backup your states if you intend to restore the environment later.

## 4. Security Scanning

The global CI pipeline (`infra/ci-lint.yaml`) includes:

- **Bandit**: Python security scanning (High severity only).
- **Gitleaks**: Secrets detection.
- **Semgrep**: Multi-language static analysis for security patterns.
- **Ruff/ESLint**: Standard linting for Python and Frontend.
