PROJECT_ID=nutritional-partner
REGION=us-central1

### General Commands ###

gcloud-auth:
	gcloud auth application-default login --project=$(PROJECT_ID)
	gcloud config set project $(PROJECT_ID)

install-precommit:
	uvx pre-commit install

run-precommit:
	uvx pre-commit run --all-files