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
# Cloud Function v2 — HTTP-triggered, containerised SMAE extraction pipeline
# ---------------------------------------------------------------------------
module "smae_engine_function" {
  source     = "../../../infra/modules/cloud-function-v2"
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


  trigger_config = null

  iam = {
    "roles/cloudfunctions.invoker" = []
  }

  service_account = module.smae_engine_sa.email

  depends_on = [module.smae_engine_sa]
}
