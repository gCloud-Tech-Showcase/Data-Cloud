variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

# -----------------------------------------------------------------------------
# Network
# -----------------------------------------------------------------------------

variable "network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "data-cloud-vpc"
}

variable "subnet_cidr" {
  description = "CIDR range for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

# -----------------------------------------------------------------------------
# BigQuery
# -----------------------------------------------------------------------------

variable "dataset_id" {
  description = "BigQuery dataset ID for the propensity modeling use case"
  type        = string
  default     = "propensity_modeling"
}

variable "dataset_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

# -----------------------------------------------------------------------------
# Dataform
# -----------------------------------------------------------------------------

variable "git_repo_url" {
  description = "GitLab repository URL for Dataform"
  type        = string
  default     = "https://gitlab.com/google-cloud-tech-showcase/data-cloud.git"
}

variable "gitlab_token" {
  description = "GitLab personal access token for Dataform"
  type        = string
  sensitive   = true
}
