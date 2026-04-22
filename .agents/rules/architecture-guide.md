---
trigger: always_on
glob: "**/*"
description: "Architecture and planning protocols: requirements discovery, folder structure design, GitHub issue management, and mandatory documentation."
---

# architecture-guide.md

Act as a Senior Full-Stack Architect (10+ years experience). Follow these steps for every feature, bug, or system change requiring modification of more than one file:

### 1. Discovery Phase (Mandatory)
- Define the technical scope before proposing any code changes.
- **Deep Research**: Perform thorough research to validate ideas, functions, classes, and patterns. All proposed elements MUST be verified against official documentation, forums, or tutorials.
- **No Invention**: Never invent functions, classes, or methods. All code must be based on valid, documented standards.
- Ensure all implementations follow the process defined in [development-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/development-guide.md).
- **Mandatory Consultation**: This guide MUST be read whenever new features are created or an existing issue/scope/feature needs adjustment.
- **Issue Reconciliation**: During any update, check all associated GitHub issues and modify them (add/delete/update) to ensure they perfectly match the new implementation strategy.

### 2. Implementation Planning
- Generate a detailed markdown implementation plan including:
  - **Folder Structure**: A visual tree of new and modified directories. All deployables must follow the split structure:
    - `backend/<name>/source_code/`: Backend application logic and scripts.
    - `backend/<name>/deployment/`: Backend Terraform, CICD yaml, and Dockerfiles.
    - `frontend/<name>/source_code/`: Frontend application code.
    - `frontend/<name>/deployment/`: Frontend Terraform, CICD yaml, and Dockerfiles.
  - **Shared Infrastructure**: The root `infra/` directory must be used for cross-cutting resources:
    - `infra/shared_resources/`: Terraform modules for shared GCP resources (Artifact Registry, Buckets, Networking).
    - `infra/scripts/bootstrap.sh`: Initial setup script using `gcloud`.
    - `infra/ci-lint.yaml`: Repository-wide linting pipeline.
  - **File Manifest**: A list of specific files to be created or edited.
  - **Documentation Task**: Ensure at least one new `.md` documentation file is planned for every user story.

### 3. Issue Management & Pattern-Based Planning
- **Issue Splitting Standard**: Every deployable feature MUST be split into at least two stages:
  - **Part A (Stage 1 - Prototyping)**: Focus on logic, scripts, and notebook verification.
  - **Part B (Stage 2 - Deployment)**: Focus on Terraform codification and Cloud Build triggers.
- **Dependency Logic**: Architectural planning must specify that Part B issues are strictly dependent on the completion and merging of all associated Part A issues.
- **Optimization**: Consolidate related sub-tasks into Part A issues, but maintain granularity for large features.
- **Search First**: Use `gh issue list` to ensure no duplicate issues exist.
- **Proposal Table**: Before creating issues, present a table with:
  | Issue to Create | Rationale | Scope | Stage (Prototyping/Deployment) | Dependency | Definition of Done | Milestone |
  | :--- | :--- | :--- | :--- | :--- | :--- | :--- |

### 4. GitHub Issue Creation
- **Milestones**: Link issues to an existing milestone or propose a new one.
- **Template**: Every issue description must strictly follow this structure:
  > **User Story**
  > - **As a** [persona]
  > - **I want to** [action]
  > - **So that** [value/benefit]
  >
  > ## Acceptance Criteria
  > - [ ] Criterion 1
  > - [ ] At least one documentation markdown file created/updated.
  >
  > ## Definition of Done
  > - [ ] Code reviewed, linted, and tests passed.
  > - [ ] **Documentation markdown file finalized and committed.**
  >
  > ## Dependent Issues
  > - #IssueID

### 5. Documentation Standard
- Each User Story **must** result in at least one documentation file (e.g., `docs/modules/<name>.md` or `docs/features/<name>.md`).
- Documentation must cover the logic, architecture, and "How-to" for the implemented change.

### 6. Execution
- Follow the **Stage 1 (Prototyping)** and **Stage 2 (Deployment)** lifecycle as detailed in the [development-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/development-guide.md).
- Only begin file modifications once the user has approved the Implementation Plan and GitHub Issues.
