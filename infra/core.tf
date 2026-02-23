# =============================================================================
# CORE INFRASTRUCTURE
# APIs, networking, and shared resources used by all demos
# =============================================================================

# -----------------------------------------------------------------------------
# Enable Required APIs
# -----------------------------------------------------------------------------

resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "bigquery" {
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vertex_ai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "dataform" {
  service            = "dataform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "datalineage" {
  service            = "datalineage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "gemini_data_analytics" {
  service            = "geminidataanalytics.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "logging" {
  service            = "logging.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub" {
  service            = "pubsub.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "dataproc" {
  service            = "dataproc.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudscheduler" {
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

# -----------------------------------------------------------------------------
# VPC Network
# -----------------------------------------------------------------------------

resource "google_compute_network" "main" {
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.compute]
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.network_name}-${var.region}"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.main.id

  private_ip_google_access = true
}

# -----------------------------------------------------------------------------
# Cloud NAT (for VMs without external IPs)
# Required when Vertica demo is enabled (VMs use internal IPs only)
# -----------------------------------------------------------------------------

resource "google_compute_router" "main" {
  count = var.enable_vertica_demo ? 1 : 0

  name    = "data-cloud-router"
  region  = var.region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  count = var.enable_vertica_demo ? 1 : 0

  name                               = "data-cloud-nat"
  router                             = google_compute_router.main[0].name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = false
    filter = "ERRORS_ONLY"
  }
}

# -----------------------------------------------------------------------------
# BigQuery Connection for Vertex AI (Gemini Models)
# Shared by all demos that use Gemini
# -----------------------------------------------------------------------------

resource "google_bigquery_connection" "vertex_ai" {
  connection_id = "vertex-ai-connection"
  location      = var.dataset_location
  friendly_name = "Vertex AI Connection for Gemini"
  description   = "Connection for accessing Gemini models from BigQuery"

  cloud_resource {}

  depends_on = [
    google_project_service.bigquery,
    google_project_service.vertex_ai
  ]
}

resource "google_project_iam_member" "bq_connection_vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"

  depends_on = [
    google_bigquery_connection.vertex_ai,
    google_project_service.vertex_ai
  ]
}

# -----------------------------------------------------------------------------
# Python Scripts Configuration
# Generate .env file for data collection scripts
# -----------------------------------------------------------------------------

resource "local_file" "python_env" {
  content = <<-EOT
    GCP_PROJECT_ID=${var.project_id}
    GCP_REGION=${var.region}
  EOT

  filename = "${path.module}/../scripts/.env"

  file_permission = "0600"
}

# -----------------------------------------------------------------------------
# Project Data (used by multiple resources)
# -----------------------------------------------------------------------------

data "google_project" "current" {}
