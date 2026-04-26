# Project-level variables are injected via CI/CD pipelines
# project_id = "..."
# region     = "..."

image_tag              = "latest"
sa_name                = "smae-engine-sa"
function_name          = "smae-engine"
artifact_registry_name = "nutritional-partner-images"
image_name             = "smae-engine"
runtime                = "python313"
instance_count         = 1
min_instance_count     = 0
memory_mb              = 1024
timeout_seconds        = 3600
sa_roles = [
  "roles/storage.objectUser",
  "roles/bigquery.dataEditor",
  "roles/bigquery.jobUser",
  "roles/aiplatform.user",
]
