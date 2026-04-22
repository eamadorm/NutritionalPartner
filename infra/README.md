# Infrastructure Foundations (Bootstrap)

This directory contains the foundational automation scripts required to bootstrap the Nutritional Partner project on Google Cloud Platform (GCP).

## Prerequisites

Before running the bootstrap process, ensure the operator has the following:

1. **GCP Project**: A valid project ID with billing enabled.
2. **Permissions**: The executing user must have the following roles:
    - `roles/owner` (or a combination of the roles below).
    - `roles/resourcemanager.projectIamAdmin` (to manage SA roles).
    - `roles/serviceusage.serviceUsageAdmin` (to enable Required APIs).
    - `roles/cloudbuild.connectionAdmin` (Required to establish the **Run-Once** GitHub connection).
    - `roles/secretmanager.admin` (Required as Cloud Build stores 2nd gen connection secrets in Secret Manager).
3. **gcloud CLI Setup**:
    - **Recommended**: Run `make gcloud-auth` from the root of the repository.
    - **Manual Alternative**:
        1. Authenticate your session: `gcloud auth login`
        2. Configure application default credentials: `gcloud auth application-default login`
        3. Set your active project: `gcloud config set project your-project-id`

## Run-Once: GitHub to Cloud Build Connection

Cloud Build 2nd Gen connections **must be established manually** once before the triggers can be managed via script.

1. Go to the [Cloud Build Repositories page](https://console.cloud.google.com/cloud-build/repositories/2nd-gen).
2. Click **Create Connection**.
3. Select **GitHub** as the provider.
4. Follow the authentication flow and select the `<your-repo-name>` repository.
    - **Troubleshooting**: If the repository does not appear in the options:
        1. In the GitHub authentication popup, click **"Manage Installations"**.
        2. Alternatively, go to GitHub **Settings** > **Applications** > **Installed GitHub Apps**.
        3. Find **Google Cloud Build** and click **Configure**.
        4. Scroll down to **Repository access** and ensure the `<your-repo-name>` repository is selected (either via "All repositories" or manually added to "Only select repositories").
        5. Return to the GCP Console and refresh the repository list.
5. Name the connection `github-connection` (or match the name you intend to use in the bootstrap).

> [!NOTE]
> The `create_cicd_triggers.sh` script (called by bootstrap) will automatically verify that the connection and repository linkage exist before attempting to create triggers.

## Trigger Configuration

Trigger definitions are managed in lists within `infra/scripts/create_cicd_triggers.sh`. When adding new triggers, follow these rules:

1. **Pathing**: The `YAML_CONFIG_FILE` must be the **relative path from the repository root** (e.g., `infra/ci-lint.yaml`).
2. **File Filtering**: You can specify `included-files` and `ignored-files` patterns using glob syntax. 
    - **Advantage**: You can pass multiple patterns by separating them with commas (e.g., `infra/**,frontend/**`).
    - The `ci-linting` trigger is configured by default to ignore documentation (`**/*.md`), `.gitignore`, and `LICENSE` files across the entire repo.
3. **Idempotency**: The script checks for the trigger name before creation. If a trigger already exists, it will log its existence and skip creation.

## Execution

You can bootstrap the project foundations using either the project `Makefile` (recommended) or by calling the script directly.

### Method 1: Using Makefile
From the root of the repository, run:
```bash
make bootstrap PROJECT_ID=your-project-id [REGION=us-central1] [REPO_NAME=<your-repo-name>] [REPO_OWNER=<your-github-handle>] [CONNECTION_NAME=github-connection]
```

### Method 2: Direct Execution
Run the script from the root of the repository:
```bash
./infra/scripts/bootstrap.sh \
  "your-project-id" \
  "us-central1" \
  "<your-repo-name>" \
  "<your-github-handle>" \
  "github-connection"
```

## Cleanup

If you need to teardown the foundational infrastructure, you can use the cleanup utility. 

> [!CAUTION]
> **Data Loss Warning**: The cleanup process will permanently delete the Terraform state bucket and all its contents. Make sure you have backed up any necessary state files if you intend to restore the environment later.

### Method 1: Using Makefile (Recommended)
```bash
make cleanup PROJECT_ID=your-project-id [REGION=us-central1]
```

### Method 2: Direct Execution
```bash
./infra/scripts/cleanup.sh "your-project-id" "us-central1"
```

## What Bootstrap Does
1. **Enables APIs**: Strictly necessary services (IAM, Cloud Build, Artifact Registry, etc.).
2. **State Management**: Creates a GCS bucket named `<project-id>-tf-states` with versioning enabled.
3. **CI/CD Identity**: Creates the `cicd-pipeline-sa` service account with foundational permissions.
4. **Impersonation**: Grants `roles/iam.serviceAccountTokenCreator` to `eamadorm11@gmail.com` on the Service Account.
5. **Triggers**: Calls `create_cicd_triggers.sh` to initialize PR (linting) and Push (deployment) triggers.
