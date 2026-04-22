# GEMINI.md

Follow this execution pipeline for every task. This document acts as the master anchor for repository-specific standards and mandatory development protocols.

---

### 1. Discovery Phase (Mandatory)
* **Context Gathering**: Use the `gh CLI` to check assigned issues. Review the current repository structure to prevent redundant logic.
* **Deep Research**: Perform web searches for the latest documentation if the implementation involves new libraries or APIs.
* **Architectural Blueprint**: Read `@.agents/rules/architecture-guide.md`. 
  - **Planning & Issues**: You MUST trigger the `@.agents/skills/architecture-planning/SKILL.md` skill to generate plans and manage GitHub entities.
  - **Q&A Session**: Conduct the mandatory back-and-forth Q&A session with the user, generate the folder structure, and create/link the necessary GitHub Issues and Milestones before writing any code.

---

### 2. Implementation Pipeline
All feature development must strictly follow the **`@.agents/rules/development-guide.md`**. 

#### **Stage 1 (Part A): Prototyping (Notebook-First)**
- **Workflow**: For all prototyping, resource management, and notebook verification, you MUST trigger the specialized skill:
  - **Skill**: `@.agents/skills/prototyping-logic/SKILL.md`
- **Security**: Always trigger `@.agents/skills/security-audit/SKILL.md` before finalizing logic.

#### **Stage 2 (Part B): Deployment (Terraform & CI/CD)**
- **Workflow**: For executing the deployment phase, applying Terraform (CFF), and updating CI/CD triggers, you MUST trigger the specialized skill:
  - **Skill**: `@.agents/skills/deployment/SKILL.md`

---

### 3. Standards & Domain Specifics
*   **Coding Standards**: Follow `@.agents/rules/coding-guide.md`.
*   **Backend**: Reference `@.agents/rules/backend-guide.md`.
*   **Frontend**: Reference `@.agents/rules/frontend-guide.md`.
*   **Infrastructure**: Reference `@.agents/rules/devops-guide.md`.
*   **Quality Assurance**: Use `@.agents/rules/tests-guide.md`.
*   **Security**: Follow `@.agents/rules/cybersecurity-guide.md`.

---

> **Golden Rule**: Keep it simple. Follow the `@.agents/rules/development-guide.md` lifecycle without exceptions. Stage 2 (Part B) never begins until Stage 1 (Part A) is fully merged.
