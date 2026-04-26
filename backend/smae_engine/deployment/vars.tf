variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and supporting resources"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy (short git SHA from Cloud Build)"
  type        = string
  default     = "latest"
}

variable "sa_name" {
  description = "Service account name for the SMAE Engine function"
  type        = string
}

variable "function_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "artifact_registry_name" {
  description = "Artifact Registry repository name containing the function image"
  type        = string
}

variable "image_name" {
  description = "Docker image name within the Artifact Registry repository"
  type        = string
}

variable "runtime" {
  description = "Execution environment (unused in Cloud Run v2 but kept for consistency)"
  type        = string
}

variable "instance_count" {
  description = "Maximum number of Cloud Run instances"
  type        = number
}

variable "min_instance_count" {
  description = "Minimum number of Cloud Run instances (0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "memory_mb" {
  description = "Memory allocated to each Cloud Run instance in MB"
  type        = number
}

variable "timeout_seconds" {
  description = "Cloud Run execution timeout in seconds"
  type        = number
}

variable "sa_roles" {
  description = "IAM roles granted to the service account at project level"
  type        = list(string)
}
