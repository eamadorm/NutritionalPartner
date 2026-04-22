# GEMINI.md

Follow this execution pipeline for every task. This document acts as the master anchor for repository-specific standards and mandatory development protocols.

---

### 1. Discovery & Planning
* **Context Gathering**: Use the `gh CLI` to check assigned issues. Review the current repository structure to prevent redundant logic.
* **Deep Research**: Perform web searches for the latest documentation if the implementation involves new libraries or APIs.
* **Architectural Blueprint**: Read `architecture-guide.md`. Conduct the Q&A session with the user and generate a plan before writing code.

---

### 2. Implementation Pipeline
All feature development must strictly follow the **[development-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/development-guide.md)**. 

#### **Stage 1: Prototyping (Notebook-First)**
1.  Develop logic in `/source_code`.
2.  Manage manual infrastructure via `create_resources.sh` and `delete_resources.sh`.
3.  Verify functionality via a **Jupyter Notebook** (located in `notebooks/`).
4.  **Wait for User Approval** of the notebook before cleanup.

#### **Stage 2: Promotion (Terraform & CI/CD)**
1.  Codification in `/deployment` using **Terraform (CFF)**.
2.  Centralized CI/CD trigger management via **`infra/scripts/cicd_triggers.sh`**.

---

### 3. Standards & Domain Specifics
*   **Backend**: Reference [backend-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/backend-guide.md) (Python/uv, Pydantic AI).
*   **Frontend**: Reference [frontend-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/frontend-guide.md) (TypeScript, Next.js).
*   **Infrastructure**: Reference [devops-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/devops-guide.md) (GCP, Cloud Foundation Fabric).
*   **Quality Assurance**: Use [tests-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/tests-guide.md).
*   **Security**: Follow [cybersecurity-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/cybersecurity-guide.md) and generate `cybersec_report.md`.

---

> **Golden Rule**: Keep it simple. Follow the `development-guide.md` lifecycle without exceptions. If it isn't in a notebook first, it isn't ready for Terraform.
