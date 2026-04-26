provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Artifact Registry — Docker repository for all deployable images
# ---------------------------------------------------------------------------
module "artifact_registry" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/artifact-registry?ref=v34.1.0"
  project_id = var.project_id
  location   = var.region
  name       = var.artifact_registry_name
  format = {
    docker = {}
  }
  description = "Docker images for NutritionalPartner deployables"
}

# ---------------------------------------------------------------------------
# GCS Bucket — source PDF uploads and raw nutritional data files
# ---------------------------------------------------------------------------
module "nutritional_data_sources_bucket" {
  source     = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/gcs?ref=v34.1.0"
  project_id = var.project_id
  name       = var.data_sources_bucket_name
  location   = var.region
  versioning = false
}

# ---------------------------------------------------------------------------
# BigQuery Dataset + Tables — nutritional information warehouse
# ---------------------------------------------------------------------------
module "nutrimental_information_dataset" {
  source      = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/bigquery-dataset?ref=v34.1.0"
  project_id  = var.project_id
  id          = var.bq_dataset_id
  location    = var.bq_dataset_location
  description = "Nutritional information extracted from SMAE PDFs"

  tables = {
    food_equivalents = {
      friendly_name = "Food Equivalents"
      description   = "Food equivalents extracted from SMAE PDFs (SCD Type 2)"
      schema = jsonencode([
        { name = "food_uuid", type = "STRING", mode = "REQUIRED" },
        { name = "food_group", type = "STRING", mode = "NULLABLE" },
        { name = "food", type = "STRING", mode = "NULLABLE" },
        { name = "suggested_quantity", type = "STRING", mode = "NULLABLE" },
        { name = "unit", type = "STRING", mode = "NULLABLE" },
        { name = "net_weight_g", type = "INTEGER", mode = "NULLABLE" },
        { name = "energy_kcal", type = "INTEGER", mode = "NULLABLE" },
        { name = "protein_g", type = "FLOAT", mode = "NULLABLE" },
        { name = "lipids_g", type = "FLOAT", mode = "NULLABLE" },
        { name = "carbohydrates_g", type = "FLOAT", mode = "NULLABLE" },
        { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
        { name = "source_uri", type = "STRING", mode = "REQUIRED" },
        { name = "active", type = "BOOLEAN", mode = "REQUIRED" }
      ])
      partitioning = {
        field = "ingested_at"
        type  = "DAY"
      }
      clustering = ["food_uuid", "food_group"]
      labels     = {}
    }

    food_equivalents_dead_letter = {
      friendly_name = "Food Equivalents Dead Letter"
      description   = "Dead-letter table for failed food_equivalents row inserts"
      schema = jsonencode([
        { name = "source_uri", type = "STRING", mode = "NULLABLE" },
        { name = "food_uuid", type = "STRING", mode = "NULLABLE" },
        { name = "raw_row", type = "STRING", mode = "NULLABLE" },
        { name = "error_message", type = "STRING", mode = "NULLABLE" },
        { name = "failed_at", type = "TIMESTAMP", mode = "REQUIRED" }
      ])
      labels = {}
    }
  }
}
