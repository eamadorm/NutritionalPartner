provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Service Account — dedicated identity for the SMAE Engine function
# ---------------------------------------------------------------------------
module "smae_engine_sa" {
  source       = "../../../infra/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.sa_name
  display_name = "SMAE Engine SA"
  description  = "Service account for the SMAE Engine Cloud Function"

  iam_project_roles = {
    (var.project_id) = var.sa_roles
  }
}

# ---------------------------------------------------------------------------
# Cloud Function v2 — HTTP-triggered, source-based SMAE extraction pipeline
# ---------------------------------------------------------------------------
module "smae_engine_function" {
  source     = "../../../infra/modules/cloud-function-v2"
  project_id = var.project_id
  region     = var.region
  name       = var.function_name

  bucket_name = "${var.project_id}-gcf-source"
  bucket_config = {
    location = var.region
  }

  bundle_config = {
    path = "../source_code"
  }

  function_config = {
    entry_point     = "smae_handler"
    runtime         = var.runtime
    instance_count  = var.instance_count
    memory_mb       = var.memory_mb
    timeout_seconds = var.timeout_seconds
  }

  docker_repository_id = "projects/${var.project_id}/locations/${var.region}/repositories/${var.artifact_registry_name}"

  iam = {
    "roles/cloudfunctions.invoker" = ["allUsers"]
  }

  service_account = module.smae_engine_sa.email

  depends_on = [module.smae_engine_sa]
}
