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

# Explicitly create the Dataform service identity (service account)
resource "google_project_service_identity" "dataform" {
  provider = google-beta
  project  = var.project_id
  service  = "dataform.googleapis.com"

  depends_on = [google_project_service.dataform]
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
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
# BigQuery Datasets
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "propensity_modeling" {
  dataset_id = var.dataset_id
  location   = var.dataset_location

  description = "Data Cloud showcase dataset for BQML propensity modeling"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
  }

  depends_on = [google_project_service.bigquery]
}

resource "google_bigquery_dataset" "ga4_source" {
  dataset_id = "ga4_source"
  location   = var.dataset_location

  description = "Source views over GA4/Firebase public datasets"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
  }

  depends_on = [google_project_service.bigquery]
}

# -----------------------------------------------------------------------------
# Secret Manager (for GitHub token)
# -----------------------------------------------------------------------------

data "google_project" "current" {}

resource "google_secret_manager_secret" "github_token" {
  secret_id = "dataform-github-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
}

resource "google_secret_manager_secret_iam_member" "dataform_access" {
  secret_id = google_secret_manager_secret.github_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_project_service_identity.dataform.email}"

  depends_on = [google_project_service_identity.dataform]
}


resource "google_project_iam_member" "dataform_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_project_service_identity.dataform.email}"

  depends_on = [google_project_service_identity.dataform]
}

resource "google_project_iam_member" "dataform_bq_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_project_service_identity.dataform.email}"

  depends_on = [google_project_service_identity.dataform]
}

resource "google_project_iam_member" "dataform_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_project_service_identity.dataform.email}"

  depends_on = [google_project_service_identity.dataform]
}

resource "google_project_iam_member" "dataform_vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_project_service_identity.dataform.email}"

  depends_on = [google_project_service_identity.dataform]
}

# -----------------------------------------------------------------------------
# Dataform Repository
# -----------------------------------------------------------------------------

resource "google_dataform_repository" "main" {
  provider = google-beta
  name     = "data-cloud"
  region   = var.region

  git_remote_settings {
    url                                 = var.git_repo_url
    default_branch                      = "main"
    authentication_token_secret_version = google_secret_manager_secret_version.github_token.id
  }

  depends_on = [
    google_project_service.dataform,
    google_secret_manager_secret_iam_member.dataform_access
  ]
}

# -----------------------------------------------------------------------------
# Dataform Release Configuration
# Compiles the code from the dev branch
# -----------------------------------------------------------------------------

resource "google_dataform_repository_release_config" "main" {
  provider   = google-beta
  project    = var.project_id
  region     = var.region
  repository = google_dataform_repository.main.name

  name          = "production"
  git_commitish = "main"

  # Compile every hour (and immediately on creation)
  cron_schedule = "0 * * * *"
  time_zone     = "America/Los_Angeles"

  code_compilation_config {
    default_database = var.project_id
    default_location = var.dataset_location
  }
}

# -----------------------------------------------------------------------------
# Dataform Workflow Configuration
# Defines how to execute the compiled workflow (manual trigger)
# -----------------------------------------------------------------------------

resource "google_dataform_repository_workflow_config" "main" {
  provider       = google-beta
  project        = var.project_id
  region         = var.region
  repository     = google_dataform_repository.main.name
  release_config = google_dataform_repository_release_config.main.id

  name = "full-workflow"

  invocation_config {
    fully_refresh_incremental_tables_enabled = true
    transitive_dependencies_included         = true
    transitive_dependents_included           = false
  }
}


# -----------------------------------------------------------------------------
# Vertex AI Configuration
# Endpoint to deploy user retention model manually after created and registered
# -----------------------------------------------------------------------------


resource "google_vertex_ai_endpoint" "retention_endpoint" {
  name         = var.retention_model_endpoint_name
  display_name = "User Retention Prediction"
  location     = var.region

  depends_on = [google_project_service.vertex_ai]
}
