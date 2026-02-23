# =============================================================================
# REQUIRED VARIABLES
# =============================================================================

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "github_token" {
  description = "GitHub personal access token for Dataform"
  type        = string
  sensitive   = true
}

# =============================================================================
# OPTIONAL VARIABLES - General
# =============================================================================

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "dataset_location" {
  description = "BigQuery dataset location (multi-region)"
  type        = string
  default     = "US"
}

# =============================================================================
# NETWORK
# =============================================================================

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

# =============================================================================
# BIGQUERY
# =============================================================================

variable "dataset_id" {
  description = "BigQuery dataset ID for the propensity modeling use case"
  type        = string
  default     = "propensity_modeling"
}

# =============================================================================
# DATAFORM
# =============================================================================

variable "git_repo_url" {
  description = "GitHub repository URL for Dataform"
  type        = string
  default     = "https://github.com/gCloud-Tech-Showcase/Data-Cloud.git"
}

# =============================================================================
# VERTEX AI
# =============================================================================

variable "retention_model_endpoint_name" {
  description = "Name of endpoint used for user retention model inference"
  type        = string
  default     = "retention-prediction"
}

# =============================================================================
# FEATURE FLAGS - Premium Features
# These features incur additional costs beyond standard usage
# =============================================================================

variable "enable_realtime_alerts" {
  description = <<-EOT
    Enable Enterprise reservation for continuous queries.

    Set to true to explore the real-time alerting portion of the Security Logs demo.

    WARNING: Creates an Enterprise reservation that incurs charges even when idle
    (~1 slot while listening for events).
  EOT
  type        = bool
  default     = false
}

variable "realtime_alerts_max_slots" {
  description = <<-EOT
    Maximum slots for the continuous queries reservation (autoscaling ceiling).
    Only used when enable_realtime_alerts = true.

    Must be a multiple of 50. Minimum: 50, maximum: 500 per CONTINUOUS reservation.
    With 0 baseline + autoscale, you only pay for slots actually used (~1 slot when idle).
  EOT
  type        = number
  default     = 50
}

# =============================================================================
# FEATURE FLAGS - Data Center Topology Demo
# =============================================================================

variable "enable_vertica_demo" {
  description = <<-EOT
    Enable the Vertica-to-BigQuery ingestion demo.

    Creates:
    - BigQuery dataset: data_center_topology
    - Vertica VM (single node Community Edition)
    - Dataproc workflow template for ingestion
    - Cloud Scheduler job (paused by default)
    - GCS buckets for staging

    WARNING: Vertica VM runs continuously when enabled (~$0.13/hr for e2-standard-4).
    Run 'terraform destroy -var="enable_vertica_demo=true"' when not in use.
  EOT
  type        = bool
  default     = false
}

