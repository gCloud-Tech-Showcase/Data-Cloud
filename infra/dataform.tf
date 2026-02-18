# =============================================================================
# DATAFORM
# Repository, release configuration, workflow, and IAM
# =============================================================================

# -----------------------------------------------------------------------------
# Dataform Service Identity
# -----------------------------------------------------------------------------

resource "google_project_service_identity" "dataform" {
  provider = google-beta
  project  = var.project_id
  service  = "dataform.googleapis.com"

  depends_on = [google_project_service.dataform]
}

# -----------------------------------------------------------------------------
# Secret Manager (GitHub token for Dataform)
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Dataform IAM
# -----------------------------------------------------------------------------

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
# -----------------------------------------------------------------------------

resource "google_dataform_repository_release_config" "main" {
  provider   = google-beta
  project    = var.project_id
  region     = var.region
  repository = google_dataform_repository.main.name

  name          = "production"
  git_commitish = "main"

  cron_schedule = "0 * * * *"
  time_zone     = "America/Los_Angeles"

  code_compilation_config {
    default_database = var.project_id
    default_location = var.dataset_location
  }
}

# -----------------------------------------------------------------------------
# Dataform Workflow Configuration
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
