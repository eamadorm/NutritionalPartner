# Bootstrap & Developer Onboarding

This document describes the foundational setup for the Nutritional Partner monorepo and the automated GCP environment initialization.

## 1. Quick Start

To set up your local environment and initialize GCP foundations:

```bash
# 1. Authenticate with GCP
make gcloud-auth PROJECT_ID=your-project-id

# 2. Run the bootstrap script
make bootstrap PROJECT_ID=your-project-id REGION=us-central1
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

## 3. CI/CD Triggers

After the initial bootstrap, you can automate trigger creation:

```bash
make create-triggers PROJECT_ID=... CONNECTION_NAME=...
```

> [!IMPORTANT]
> **Prerequisite**: You must manually connect your GitHub repository to Cloud Build 2nd Gen in the GCP Console before running this command. The script will fail gracefully if the connection is missing.

## 4. Security Scanning

The global CI pipeline (`infra/ci-lint.yaml`) includes:

- **Bandit**: Python security scanning (High severity only).
- **Gitleaks**: Secrets detection.
- **Semgrep**: Multi-language static analysis for security patterns.
- **Ruff/ESLint**: Standard linting for Python and Frontend.
