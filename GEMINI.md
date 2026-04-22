# GEMINI.md

Follow this execution pipeline for every task. This document acts as the master anchor for repository-specific standards and mandatory development protocols.

---

### 1. Discovery Phase (Mandatory)
* **Context Gathering**: Use the `gh CLI` to check assigned issues. Review the current repository structure to prevent redundant logic.
* **Deep Research**: Perform web searches for the latest documentation if the implementation involves new libraries or APIs.
* **Architectural Blueprint**: Read `architecture-guide.md`. Planning must follow the **Part A/Part B** issue creation standard. Conduct the Q&A session with the user and generate a plan before writing code.

---

### 2. Implementation Pipeline
All feature development must strictly follow the **[development-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/development-guide.md)**. 

#### **Stage 1 (Part A): Prototyping (Notebook-First)**
1.  Develop logic in `/source_code`.
2.  Manage manual infrastructure via `create_resources.sh` and `delete_resources.sh`.
3.  Pass **Cybersecurity** (0 High) and **Testing** hurdles.
4.  Verify functionality via a **Jupyter Notebook** (located in `notebooks/`).
5.  **Wait for User Approval** of the notebook before cleanup and merging.

#### **Stage 2 (Part B): Deployment (Terraform & CI/CD)**
1.  Triggers ONLY after all associated Part A issues are merged.
2.  Codification in `/deployment` using **Terraform (CFF)**.
3.  Centralized CI/CD trigger management via **`infra/scripts/cicd_triggers.sh`**.

---

### 3. Standards & Domain Specifics
*   **Backend**: Reference [backend-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/backend-guide.md).
*   **Frontend**: Reference [frontend-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/frontend-guide.md).
*   **Infrastructure**: Reference [devops-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/devops-guide.md).
*   **Quality Assurance**: Use [tests-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/tests-guide.md).
*   **Security**: Follow [cybersecurity-guide.md](file:///workspaces/NutritionalPartner/.agents/rules/cybersecurity-guide.md).

---

> **Golden Rule**: Keep it simple. Follow the `development-guide.md` lifecycle without exceptions. Stage 2 (Part B) never begins until Stage 1 (Part A) is fully merged.
