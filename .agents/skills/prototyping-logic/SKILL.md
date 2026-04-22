---
name: prototyping-logic
description: Manages the Stage 1 (Prototyping) workflow, including resource script creation, dependency isolation, and Jupyter Notebook verification. Trigger this skill when building the initial logic for a feature.
---

# Prototyping & Logic Skill

This skill governs the execution of Stage 1 (Prototyping) within the Nutritional Partner project.

## 1. Environment Setup
- **Code Location**: `backend/<name>/source_code/` or `frontend/<name>/source_code/`.
- **Resources**: If manual GCP resources are needed, create:
    - `create_resources.sh`: `gcloud` commands to provision.
    - `delete_resources.sh`: `gcloud` commands to cleanup.

## 2. Implementation Loop
Execute the following iterative cycle:
1. **Develop Logic**: Build the core scripts.
2. **Security Check**: Trigger `@.agents/skills/security-audit/SKILL.md`.
3. **Test Suite**: Create tests in `tests/backend/` or `tests/frontend/`. Ensure Happy Path, Edge Cases, and Failure Modes.
4. **Notebook**: Create a verification notebook in `notebooks/`.

## 3. Jupyter Notebook Standard
Location: `notebooks/<deployable_name>/<notebook_name>.ipynb`
- Use `import sys; sys.path.append("../..")`.
- Demonstrate: Logic success, edge cases, and data schemas.

## 4. Commit & PR Protocol
- **Commits**: Max 5 files per commit. Must be stable/linted.
- **PR Content**: High-level summary of changes + DoD verification.
- **Cleanup**: Delete manual resources via `delete_resources.sh` before merging.

## References
- `@.agents/rules/development-guide.md` for lifecycle definitions.
