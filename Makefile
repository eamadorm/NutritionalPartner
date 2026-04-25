PROJECT_ID ?= nutritional-partner
REGION ?= us-central1
REPO_NAME ?= NutritionalPartner
REPO_OWNER ?= eamadorm
CONNECTION_NAME ?= github-connection

### General Commands ###

gcloud-auth:
	@echo "Authenticating gcloud and setting project..."
	gcloud auth login
	gcloud auth application-default login
	gcloud config set project $(PROJECT_ID)
	gcloud auth application-default set-quota-project $(PROJECT_ID)

bootstrap:
	@echo "Bootstrapping project foundations..."
	./infra/scripts/bootstrap.sh $(PROJECT_ID) $(REGION) $(REPO_NAME) $(REPO_OWNER) $(CONNECTION_NAME)

cleanup:
	@echo "Tearing down project foundations..."
	@chmod +x ./infra/scripts/cleanup.sh
	./infra/scripts/cleanup.sh $(PROJECT_ID) $(REGION) $(REPO_NAME) $(REPO_OWNER) $(CONNECTION_NAME)

create-triggers:
	@echo "Creating CI/CD triggers..."
	./infra/scripts/create_cicd_triggers.sh $(PROJECT_ID) $(REGION) $(REPO_NAME) $(REPO_OWNER) $(CONNECTION_NAME)

install-precommit:
	uvx pre-commit install

run-precommit:
	uvx pre-commit run --all-files

run-smae-engine:
	@echo "Running SMAE Engine locally..."
	cd backend && uv run --group smae python -m smae_engine.source_code.main