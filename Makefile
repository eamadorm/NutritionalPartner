PROJECT_ID ?= nutritional-partner
REGION ?= us-central1
REPO_NAME ?= NutritionalPartner
REPO_OWNER ?= eamadorm
CONNECTION_NAME ?= github-connection

### General Commands ###

gcloud-auth:
	gcloud auth application-default login --project=$(PROJECT_ID)
	gcloud config set project $(PROJECT_ID)

bootstrap:
	@echo "🎬 Bootstrapping project foundations..."
	./infra/scripts/bootstrap.sh $(PROJECT_ID) $(REGION)

create-triggers:
	@echo "🛰️ Creating CI/CD triggers..."
	./infra/scripts/create_cicd_triggers.sh $(PROJECT_ID) $(REGION) $(REPO_NAME) $(REPO_OWNER) $(CONNECTION_NAME)

install-precommit:
	uvx pre-commit install

run-precommit:
	uvx pre-commit run --all-files