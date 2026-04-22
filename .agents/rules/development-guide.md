---
trigger: always_on
glob: "**/*"
description: "Development lifecycle protocols: Stage 1 (Prototyping/Notebooks) vs Stage 2 (Promotion/Terraform)."
---

# development-guide.md

This guide defines the mandatory lifecycle for developing, verifying, and promoting deployable components in the Nutritional Partner project.

## The Two-Issue Strategy
Every deployable feature (e.g., `smae_engine`, `nutrient_agent`) must be split into **two distinct GitHub issues**:
1. **Issue Part A**: Stage 1 - Prototyping & Scripting.
2. **Issue Part B**: Stage 2 - Infrastructure Promotion.

---

## Stage 1: Prototyping (Mandatory)
The goal of Stage 1 is to prove the logic works using manual infrastructure before codifying it in Terraform.

### 1. Folder Structure
All application logic, scripts, and processing code must reside in:
`backend/<deployable_name>/source_code/` or `frontend/<deployable_name>/source_code/`.

### 2. Manual Infrastructure Scripts
If the scripts require GCP resources (GCS, BigQuery, Secret Manager only), they must be managed via two bash scripts in the deployable root:
- `create_resources.sh`: Contains `gcloud` commands to create the environment.
- `delete_resources.sh`: Contains `gcloud` commands to tear down the environment.

### 3. Verification Protocol (Notebooks)
A Jupyter Notebook must be created to demonstrate the functionality:
- **Location**: `notebooks/<deployable_name>/<notebook_name>.ipynb`.
- **Requirements**:
  - Must use `import sys; sys.path.append("../..")` to correctly import modules from the project root.
  - Must show successful execution, edge case handling, and data validation.

### 4. Stage 1 Definition of Done (DoD)
- Logic implemented in `/source_code`.
- `create_resources.sh` and `delete_resources.sh` functional.
- Notebook approved by the user.
- **Manual infrastructure deleted** via `delete_resources.sh`.

---

## Stage 2: Infrastructure Promotion
Stage 2 begins only after Stage 1 is approved and cleaned up.

### 1. Codification (Terraform)
The infrastructure requirements proven in Stage 1 must be codified in:
`backend/<deployable_name>/deployment/` or `frontend/<deployable_name>/deployment/`.
- Use **Cloud Foundation Fabric (CFF)** modules.
- Ensure all resources (GCS, BQ, etc.) match the logic approved in the Notebook.

### 2. CI/CD Triggers
All Cloud Build triggers must be created/updated via the centralized script:
`infra/scripts/cicd_triggers.sh`.
- **RULE**: Cloud Build triggers must **NEVER** be managed via Terraform. 
- Triggers must be functional and tested before merging.

### 3. Stage 2 Definition of Done (DoD)
- Terraform modules applied successfully.
- CI/CD triggers functional (tested via `cicd_triggers.sh`).
- PR merged into `main`.
