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

### SMAE Engine ###

IMAGE_TAG ?= latest
SMAE_IMAGE = us-central1-docker.pkg.dev/$(PROJECT_ID)/nutritional-partner-images/smae-engine

test-smae-engine:
	@echo "Running SMAE Engine tests..."
	cd backend && uv run pytest ../tests/backend/smae_engine/

build-smae-engine-local:
	@echo "Building SMAE Engine image (local validation only)..."
	docker build \
		-t smae-engine:local \
		-f backend/smae_engine/deployment/Dockerfile \
		backend/

build-smae-engine:
	@echo "Building and pushing SMAE Engine image..."
	docker build \
		-t $(SMAE_IMAGE):$(IMAGE_TAG) \
		-f backend/smae_engine/deployment/Dockerfile \
		backend/
	docker push $(SMAE_IMAGE):$(IMAGE_TAG)

deploy-smae-engine:
	@echo "Deploying SMAE Engine to Cloud Functions v2..."
	gcloud functions deploy smae-engine \
		--gen2 \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--image=$(SMAE_IMAGE):$(IMAGE_TAG) \
		--service-account=smae-engine-sa@$(PROJECT_ID).iam.gserviceaccount.com \
		--trigger-http \
		--no-allow-unauthenticated