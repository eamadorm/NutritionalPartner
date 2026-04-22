---
trigger: always_on
glob: "**/*"
description: "Development lifecycle protocols: Stage 1 (Prototyping/Notebooks) vs Stage 2 (Deployment/Terraform)."
---

# development-guide.md

This guide defines the mandatory lifecycle for developing, verifying, and promoting deployable components in the Nutritional Partner project.

## The Two-Issue Strategy
Every deployable feature must be split into **two distinct GitHub issues**:
1. **Issue Part A**: Stage 1 - Prototyping & Scripting.
2. **Issue Part B**: Stage 2 - Infrastructure Deployment.

### Issue Requirements
- **Mandatory Isolation**: Each GitHub issue must represent ONLY ONE stage.
- **Sequential Dependency**: A Stage 2 (Part B) issue can **ONLY** begin once **all** associated Stage 1 (Part A) issues are merged.

---

## Stage 1: Prototyping (Mandatory)
The goal of Stage 1 is to prove the logic works using manual infrastructure and verification notebooks.
- **Workflow**: For all prototyping tasks, implementing the iterative cycle, building verification notebooks, and managing manual resources, you MUST trigger the specialized skill:
  - **Skill**: `@.agents/skills/prototyping-logic/SKILL.md`

## Stage 2: Infrastructure Deployment
Stage 2 begins only after Stage 1 is fully merged. This stage covers Terraform codification and CI/CD trigger management.
- **Workflow**: For executing the deployment phase, applying Terraform modules (CFF), and updating CI/CD triggers, you MUST trigger the specialized skill:
  - **Skill**: `@.agents/skills/deployment/SKILL.md`

