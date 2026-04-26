project_id             = "nutritional-partner"
region                 = "us-central1"
image_tag              = "latest"
sa_name                = "smae-engine-sa"
function_name          = "smae-engine"
artifact_registry_name = "nutritional-partner-images"
image_name             = "smae-engine"
runtime                = "python313"
instance_count         = 1
memory_mb              = 512
timeout_seconds        = 300
sa_roles = [
  "roles/storage.objectUser",
  "roles/bigquery.dataEditor",
  "roles/aiplatform.user",
]
