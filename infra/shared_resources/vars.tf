variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for regional resources"
  type        = string
}

variable "artifact_registry_name" {
  description = "Name of the Docker Artifact Registry repository"
  type        = string
}

variable "data_sources_bucket_name" {
  description = "Name of the GCS bucket for nutritional source files"
  type        = string
}

variable "bq_dataset_id" {
  description = "BigQuery dataset ID for nutritional information"
  type        = string
}

variable "bq_dataset_location" {
  description = "BigQuery dataset location (multi-region or regional, e.g. US)"
  type        = string
  default     = null
}
