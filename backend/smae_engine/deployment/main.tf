provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Service Account — dedicated identity for the SMAE Engine function
# ---------------------------------------------------------------------------
module "smae_engine_sa" {
  source       = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/iam-service-account?ref=v34.1.0"
  project_id   = var.project_id
  name         = var.sa_name
  display_name = "SMAE Engine SA"
  description  = "Service account for the SMAE Engine Cloud Function"

  iam_project_roles = {
    (var.project_id) = var.sa_roles
  }
}

# ---------------------------------------------------------------------------
# Cloud Function v2 — HTTP-triggered, containerised SMAE extraction pipeline
# ---------------------------------------------------------------------------
module "smae_engine_function" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/cloud-function-v2?ref=v34.1.0"
  project_id = var.project_id
  region     = var.region
  name       = var.function_name

  function_config = {
    entry_point     = "smae_handler"
    runtime         = var.runtime
    instance_count  = var.instance_count
    memory_mb       = var.memory_mb
    timeout_seconds = var.timeout_seconds
  }

  container = {
    image = "us-central1-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/${var.image_name}:${var.image_tag}"
  }

  trigger_config = null

  iam = {
    "roles/cloudfunctions.invoker" = []
  }

  service_account = module.smae_engine_sa.email

  depends_on = [module.smae_engine_sa]
}
