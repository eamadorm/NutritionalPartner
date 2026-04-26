# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nutritional Partner is an AI-driven assistant for health-conscious individuals to manage clinical nutritional plans. Core capabilities: PDF plan ingestion, profile completion agent, dynamic food equivalents (via SMAE nutritional system), and an agentic generative UI dashboard.

## Common Commands

All orchestration goes through the single root `Makefile`. **Never create secondary Makefiles.**

### Backend (Python)

All Python commands use `uv`. Never run `python` directly.

```bash
# Run a script for a specific deployable group
uv run --group <group-name> python -m path.to.script

# Run all tests
cd backend && uv run pytest

# Run a single test file
cd backend && uv run pytest tests/backend/<deployable_name>/test_<name>.py

# Lint and format (via pre-commit)
uvx pre-commit run --all-files

# Install pre-commit hooks
make install-precommit
```

### Frontend (Next.js)

```bash
cd frontend
pnpm install          # Install dependencies
pnpm dev              # Start dev server
pnpm build            # Production build
pnpm lint             # ESLint check
```

### Infrastructure

```bash
make gcloud-auth      # Authenticate gcloud + set project
make bootstrap PROJECT_ID=<id> [REGION=us-central1] [REPO_NAME=NutritionalPartner] [REPO_OWNER=eamadorm] [CONNECTION_NAME=github-connection]
make cleanup PROJECT_ID=<id>
make create-triggers
```

## Architecture

### Monorepo Structure

```
backend/                   # Python 3.13, managed with uv
  <deployable_name>/
    source_code/           # Production logic
    deployment/            # Terraform (Stage 2 only)
    create_resources.sh    # Manual GCP setup for Stage 1
    delete_resources.sh    # Teardown after Stage 1 DoD
frontend/                  # Next.js 16 App Router, TypeScript, Tailwind CSS, pnpm
  src/app/                 # App Router pages
infra/
  scripts/                 # bootstrap.sh, cleanup.sh, create_cicd_triggers.sh
  ci-lint.yaml             # Cloud Build pipeline (Ruff, Bandit, Gitleaks, Semgrep, ESLint)
tests/
  backend/<deployable_name>/   # pytest unit tests
notebooks/<deployable_name>/   # Jupyter verification notebooks
.agents/
  rules/                   # Domain-specific coding standards (always active)
  skills/                  # Procedural skill scripts for agents
docs/system/               # Architecture and protocol documentation
```

### The Two-Stage Development Lifecycle

Every deployable feature follows a mandatory two-issue, two-stage flow. **Stage 2 never begins until Stage 1 is fully merged into `main`.**

- **Stage 1 – Part A (Prototyping)**: Logic lives in `backend/<name>/source_code/`. GCP resources are provisioned via `create_resources.sh` using `gcloud` commands only. Verified via a Jupyter notebook in `notebooks/<name>/`. Manual resources are deleted via `delete_resources.sh` before Stage 1 DoD.
- **Stage 2 – Part B (Deployment)**: Logic is codified in Terraform (Cloud Foundation Fabric modules) at `backend/<name>/deployment/`. CI/CD triggers are managed exclusively via `infra/scripts/create_cicd_triggers.sh` — **never via Terraform**.

### CI/CD Responsibility Separation

| Pipeline | Responsibilities |
|----------|-----------------|
| CI (`cloudbuild-ci.yaml`) | Tests · Docker build (local, no push) · `terraform validate` |
| CD (`cloudbuild-cd.yaml`) | Docker build + push · `terraform init` + `terraform apply` |

Tests must **never** appear in the CD pipeline — CI is the correctness gate. The `terraform validate` step in CI (with `-backend=false`) is the CD pre-flight check. If the CI/CD service account (`cicd-pipeline-sa`) lacks permissions for any step, add the missing role to `infra/scripts/bootstrap.sh` — never to Terraform.

### GCP Infrastructure

- Cloud Provider: GCP exclusively.
- Terraform state: GCS bucket `<project-id>-tf-states`, path `/tfstates/<deployment_name>/tf.state`.
- All Terraform uses [Cloud Foundation Fabric (CFF)](https://github.com/GoogleCloudPlatform/cloud-foundation-fabric) modules.
- **Regional Standard**: Default region is `us-central1`. Resources must use fallback logic: `specific_region` ?? `main_region` (`us-central1`).
- **Module Vendoring**: All CFF modules are vendored locally in `infra/modules/` (v34.1.0).
- Authentication: Application Default Credentials (ADC) only — never JSON credential files.
- CI/CD: Cloud Build. Linting pipeline defined in `infra/ci-lint.yaml` runs Ruff, Bandit, Gitleaks, Semgrep, and ESLint.

### Commit Protocol

- Each commit must represent a linted, stable, logically complete unit of work.
- **Maximum 5 modified files per commit.**

## Backend Standards

- **AI agents**: Pydantic AI library.
- **MCP servers**: MCP Python SDK.
- **Logging**: loguru (`INFO` for public method entries and state changes; `DEBUG` for internal logic).
- **Validation**: Pydantic only. All validation lives in Pydantic models — never spread across layers.
  - Config classes: `BaseSettings`. Data schemas: `BaseModel`.
  - Use `Annotated[type, Field(...)]` for all model attributes.
  - Public methods use distinct `<Action>Request(BaseModel)` / `<Action>Response(BaseModel)` schemas.
  - Public methods return Pydantic `Response` schemas. Private methods return `dict`.
  - Never return tuples from multi-value returns.
- **Type hints**: Strict — `Any` is forbidden. Use lowercase built-ins (`list[]`, `dict[]`). Max two levels of nesting. `Self`, `Optional`, `Union` from `typing`. No string forward references.
- **Function length**: Max 50 lines before mandatory extraction into sub-functions.
- **Pre-commit**: Ruff (linter + formatter), `terraform fmt`. Every commit must pass.

## Frontend Standards

- **Stack**: Next.js App Router, TypeScript, Tailwind CSS (mobile-first), pnpm.
- **Component architecture**: Atomic Design — `atoms` / `molecules` / `organisms`. Max 100 lines per component; extract logic to custom hooks.
- **Schema validation**: Zod for all API responses.
- **State**: Zustand for global state; React Context for low-frequency updates. No prop drilling beyond 3 levels.
- **Token storage**: `HttpOnly` cookies only — never `localStorage`/`sessionStorage`.
- **Auth flow**: Authorization Code Flow with PKCE + Refresh Token Rotation.

## Security Requirements

Every feature must pass a security audit (via `.agents/skills/security-audit/SKILL.md`) before Stage 1 DoD:
- **Gate**: 0 High/Urgent threats; max 2 Medium threats.
- Rate limiting: `slowapi` at the application layer (MVP); Cloud Armor for production scale.
- CORS: explicit origin allowlist — never `*` in production.
- JWT: RS256 or ES256 only; validate `exp`, `aud`, `iss`; no PII in payload.

## Notebooks

Notebooks live at `notebooks/<deployable_name>/<notebook_name>.ipynb`. They must use:
```python
import sys; sys.path.append("<relative_path_to_repo_root>")
```
to import project modules (e.g., `sys.path.append("../..")` for two levels deep). Notebooks must demonstrate successful execution, edge cases, and data validation.

## Mandatory Subagent Protocol

On **every** user prompt, evaluate the available subagents before composing a reply. Launch any that match the task — do not skip:

| Trigger | Agent |
|---------|-------|
| Writing or reviewing backend Python code | `backend-dev-specialist` |
| Writing or reviewing frontend code | `senior-frontend-dev` |
| Any security-sensitive code (auth, input handling, IAM, secrets) | `cybersec-sentinel` |
| Terraform, Cloud Build, Docker, GCP infra | `devops-engineer` |
| Architecture or technology decisions | `software-architect` |
| New or modified code that needs validation | `test-runner` |
| Codebase exploration spanning multiple files | `Explore` |
| Implementation planning before coding | `Plan` |

Multiple agents may run in parallel for independent concerns. Only skip if the prompt is purely conversational with zero technical content.

## Agent Rules Reference

Domain standards are in `.agents/rules/` and apply to all code in this repo:
- `architecture-guide.md` — discovery, Q&A, and issue reconciliation protocol
- `development-guide.md` — the two-stage lifecycle (canonical reference)
- `coding-guide.md` — DRY, SRP, guard clauses, intent-based naming, docstring format
- `backend-guide.md` — Python/uv/Pydantic AI specifics
- `frontend-guide.md` — Next.js/TypeScript/Zod specifics
- `devops-guide.md` — Terraform/Cloud Build/GCP specifics
- `cybersecurity-guide.md` — ADC, JWT, rate limiting, CORS
- `tests-guide.md` — Happy path / Edge cases / Failure modes trinity
