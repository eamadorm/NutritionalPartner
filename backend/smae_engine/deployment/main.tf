provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Service Account — dedicated identity for the SMAE Engine service
# ---------------------------------------------------------------------------
module "smae_engine_sa" {
  source       = "../../../infra/modules/iam-service-account"
  project_id   = var.project_id
  name         = var.sa_name
  display_name = "SMAE Engine SA"
  description  = var.sa_description

  iam_project_roles = {
    (var.project_id) = var.sa_roles
  }
}

# ---------------------------------------------------------------------------
# Cloud Run v2 — HTTP-triggered, containerised SMAE extraction pipeline
# ---------------------------------------------------------------------------
module "smae_engine_service" {
  source     = "../../../infra/modules/cloud-run-v2"
  project_id = var.project_id
  region     = var.region
  name       = var.function_name # Keep the name var for consistency

  service_account = module.smae_engine_sa.email

  containers = {
    smae-engine = {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/${var.image_name}:${var.image_tag}"
      resources = {
        limits = {
          cpu    = var.cpu
          memory = "${var.memory_mb}Mi"
        }
      }
    }
  }

  revision = {
    max_instance_count = var.instance_count
    min_instance_count = var.min_instance_count
    timeout            = "${var.timeout_seconds}s"
  }


  depends_on = [module.smae_engine_sa]
}
