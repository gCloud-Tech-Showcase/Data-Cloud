# =============================================================================
# VIDEO VECTOR SEARCH DEMO
# Multimodal video embeddings + BigQuery Vector Search
#
# Enables semantic search over a collection of video files using Gemini
# multimodal embeddings and BigQuery VECTOR_SEARCH — all in SQL.
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "video_vector_search" {
  dataset_id  = "video_vector_search"
  location    = var.dataset_location
  description = "Multimodal video vector search — semantic video discovery using Gemini embeddings"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "video-vector-search"
  }

  depends_on = [google_project_service.bigquery]
}

# -----------------------------------------------------------------------------
# Cloud Storage Bucket for Video Data
# Stores raw videos and 2-minute segments for embedding generation
#
# Structure:
#   gs://{project}-video-search/raw/          — Original full videos
#   gs://{project}-video-search/segments/     — 2-min segments per video
#   gs://{project}-video-search/thumbnails/   — Thumbnail per video
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "video_search" {
  name          = "${var.project_id}-video-search"
  location      = var.region
  force_destroy = false # Protect downloaded video data

  uniform_bucket_level_access = true

  versioning {
    enabled = false # Videos are large; versioning would be expensive
  }

  labels = {
    project = "data-cloud"
    purpose = "video-data"
    demo    = "video-vector-search"
  }

  depends_on = [google_project_service.storage]
}

# Grant BigQuery connection read access to video bucket for Object Tables
resource "google_storage_bucket_iam_member" "bq_connection_video_reader" {
  bucket = google_storage_bucket.video_search.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"

  depends_on = [
    google_bigquery_connection.vertex_ai,
    google_storage_bucket.video_search
  ]
}

# -----------------------------------------------------------------------------
# Dataform Release Config for feature branch
# Compiles from video-vector-search branch during development.
# TODO: Remove after merging to main.
# -----------------------------------------------------------------------------

resource "google_dataform_repository_release_config" "video_search_dev" {
  provider   = google-beta
  project    = var.project_id
  region     = var.region
  repository = google_dataform_repository.main.name

  name          = "video-search-dev"
  git_commitish = "video-vector-search"

  cron_schedule = "0 * * * *"
  time_zone     = "America/Los_Angeles"

  code_compilation_config {
    default_database = var.project_id
    default_location = var.dataset_location
  }
}

# Scheduled workflow for video vector search pipeline
# Runs hourly — incremental, so near-zero cost when no new videos
resource "google_dataform_repository_workflow_config" "video_search" {
  provider       = google-beta
  project        = var.project_id
  region         = var.region
  repository     = google_dataform_repository.main.name
  release_config = google_dataform_repository_release_config.video_search_dev.id

  name = "video-search-pipeline"

  cron_schedule = "0 * * * *"
  time_zone     = "America/Los_Angeles"

  invocation_config {
    included_tags                           = ["video_vector_search"]
    transitive_dependencies_included        = true
    fully_refresh_incremental_tables_enabled = false
    service_account                         = google_service_account.video_segmenter.email
  }
}

# -----------------------------------------------------------------------------
# Cloud Function: Automatic Video Segmentation
# Triggered when a video is uploaded to raw/*.mp4
# Splits into 2-minute segments for embedding generation
# -----------------------------------------------------------------------------

# Source bucket for Cloud Function code
resource "google_storage_bucket" "function_source" {
  name          = "${var.project_id}-function-source"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  labels = {
    project = "data-cloud"
    purpose = "function-source"
  }

  depends_on = [google_project_service.storage]
}

# Package function source as zip
data "archive_file" "segment_video_source" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/segment_video"
  output_path = "${path.module}/../functions/segment_video.zip"
}

resource "google_storage_bucket_object" "function_source_zip" {
  name   = "segment-video-${data.archive_file.segment_video_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.segment_video_source.output_path
}

# Service account for the segmentation function
resource "google_service_account" "video_segmenter" {
  account_id   = "video-segmenter"
  display_name = "Video Segmentation Cloud Function"

  depends_on = [google_project_service.cloudfunctions]
}

# Function SA: read/write access to the video bucket (runtime)
resource "google_storage_bucket_iam_member" "segmenter_bucket_admin" {
  bucket = google_storage_bucket.video_search.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Function SA: read function source from source bucket (build)
resource "google_storage_bucket_iam_member" "segmenter_source_reader" {
  bucket = google_storage_bucket.function_source.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Function SA: read/write to Cloud Functions internal staging bucket (build)
resource "google_storage_bucket_iam_member" "segmenter_gcf_sources" {
  bucket = "gcf-v2-sources-${data.google_project.current.number}-${var.region}"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Function SA: receive Eventarc events (trigger)
resource "google_project_iam_member" "segmenter_eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Function SA: invoke the Cloud Run service backing the function (trigger)
resource "google_project_iam_member" "segmenter_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Function SA: write build logs (build)
resource "google_project_iam_member" "segmenter_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Function SA: push container images (build)
resource "google_project_iam_member" "segmenter_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}


# Function SA also serves as Dataform execution SA (strict act-as mode)
# These roles are for scheduled Dataform workflow execution, not the Cloud Function
resource "google_project_iam_member" "segmenter_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}

resource "google_project_iam_member" "segmenter_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}

resource "google_project_iam_member" "segmenter_bq_connection_user" {
  project = var.project_id
  role    = "roles/bigquery.connectionAdmin"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
}

# Dataform service agent needs Token Creator + SA User to impersonate the SA
resource "google_service_account_iam_member" "dataform_token_creator" {
  service_account_id = google_service_account.video_segmenter.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_project_service_identity.dataform.email}"
}

resource "google_service_account_iam_member" "dataform_sa_user" {
  service_account_id = google_service_account.video_segmenter.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_project_service_identity.dataform.email}"
}

# Eventarc service agent needs its own role to route events
resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-eventarc.iam.gserviceaccount.com"

  depends_on = [google_project_service.eventarc]
}

# Ensure GCS service agent exists (lazily created, may not exist in fresh projects)
data "google_storage_project_service_account" "gcs_account" {
  project = var.project_id
}

# GCS service agent needs Pub/Sub publisher to emit object events
resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"

  depends_on = [google_project_service.pubsub]
}

# Cloud Function (2nd gen)
resource "google_cloudfunctions2_function" "segment_video" {
  name     = "segment-video"
  location = var.region

  build_config {
    runtime               = "python312"
    entry_point           = "segment_video"
    service_account       = google_service_account.video_segmenter.id

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_source_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = var.video_search_max_instances
    available_memory      = "1Gi"
    timeout_seconds       = 540
    service_account_email = google_service_account.video_segmenter.email
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.video_search.name
    }

    service_account_email = google_service_account.video_segmenter.email
  }

  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.cloudbuild,
    google_project_service.run,
    google_project_service.eventarc,
    google_storage_bucket_iam_member.segmenter_bucket_admin,
    google_storage_bucket_iam_member.segmenter_source_reader,
    google_storage_bucket_iam_member.segmenter_gcf_sources,
    google_project_iam_member.segmenter_eventarc_receiver,
    google_project_iam_member.segmenter_log_writer,
    google_project_iam_member.segmenter_artifact_registry,
    google_project_iam_member.eventarc_service_agent,
    google_project_iam_member.gcs_pubsub_publisher,
  ]
}

# -----------------------------------------------------------------------------
# Build Pipeline: Artifact Registry + Cloud Build (Optional)
# Creates an AR repo and Cloud Build trigger for auto-building the UI image.
# Only needed by repo maintainers who publish pre-built images.
#
# Enable with: enable_video_search_build = true in terraform.tfvars
# -----------------------------------------------------------------------------

resource "google_artifact_registry_repository" "public" {
  count = var.enable_video_search_build ? 1 : 0

  repository_id = "public"
  location      = var.region
  format        = "DOCKER"
  description   = "Pre-built container images for demo UIs"

  labels = {
    project = "data-cloud"
    purpose = "container-images"
  }

  depends_on = [google_project_service.cloudbuild]
}

# Service account for Cloud Build (org policy requires BYOSA)
resource "google_service_account" "ui_builder" {
  count        = var.enable_video_search_build ? 1 : 0
  account_id   = "video-search-ui-builder"
  display_name = "Video Search UI Builder (Cloud Build)"

  depends_on = [google_project_service.cloudbuild]
}

resource "google_project_iam_member" "ui_builder_builds" {
  count   = var.enable_video_search_build ? 1 : 0
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.ui_builder[0].email}"
}

resource "google_project_iam_member" "ui_builder_ar_writer" {
  count   = var.enable_video_search_build ? 1 : 0
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.ui_builder[0].email}"
}

resource "google_project_iam_member" "ui_builder_logs" {
  count   = var.enable_video_search_build ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ui_builder[0].email}"
}

# Builder SA: read/write Cloud Build source bucket
resource "google_project_iam_member" "ui_builder_storage" {
  count   = var.enable_video_search_build ? 1 : 0
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.ui_builder[0].email}"
}

# Cloud Build trigger: auto-build UI image on push to main
resource "google_cloudbuild_trigger" "video_search_ui" {
  count    = var.enable_video_search_build ? 1 : 0
  name     = "video-search-ui"
  location = var.region

  service_account = google_service_account.ui_builder[0].id

  github {
    owner = "gCloud-Tech-Showcase"
    name  = "Data-Cloud"
    push {
      branch = "^main$"
    }
  }

  included_files = ["ui/video-search/**"]

  build {
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "build",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/public/video-search-ui:$COMMIT_SHA",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/public/video-search-ui:latest",
        "ui/video-search",
      ]
    }
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push", "--all-tags",
        "${var.region}-docker.pkg.dev/${var.project_id}/public/video-search-ui",
      ]
    }
    images = ["${var.region}-docker.pkg.dev/${var.project_id}/public/video-search-ui:latest"]

    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
  }

  depends_on = [
    google_artifact_registry_repository.public,
    google_project_iam_member.ui_builder_builds,
    google_project_iam_member.ui_builder_ar_writer,
    google_project_iam_member.ui_builder_logs,
  ]
}

# -----------------------------------------------------------------------------
# Generated .env for local API development
# Terraform is the single source of truth for project config.
# -----------------------------------------------------------------------------

resource "local_file" "video_search_api_env" {
  filename        = "${path.module}/../ui/video-search/api/.env"
  file_permission = "0600"
  content         = "GCP_PROJECT_ID=${var.project_id}\nGCS_BUCKET=${google_storage_bucket.video_search.name}\n"
}

# -----------------------------------------------------------------------------
# Cloud Run: Video Search UI (Optional)
# Deploy the React + FastAPI UI to a public Cloud Run endpoint.
# Uses pre-built container image — no build step required.
#
# Enable with: enable_video_search_ui = true in terraform.tfvars
# -----------------------------------------------------------------------------

resource "google_service_account" "video_search_ui" {
  count        = var.enable_video_search_ui ? 1 : 0
  account_id   = "video-search-ui"
  display_name = "Video Search UI (Cloud Run)"

  depends_on = [google_project_service.run]
}

# Cloud Run SA: read BQ data
resource "google_project_iam_member" "ui_bq_data_viewer" {
  count   = var.enable_video_search_ui ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

# Cloud Run SA: run BQ queries
resource "google_project_iam_member" "ui_bq_job_user" {
  count   = var.enable_video_search_ui ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

# Cloud Run SA: use BQ connection for AI.GENERATE_EMBEDDING in search
resource "google_project_iam_member" "ui_bq_connection" {
  count   = var.enable_video_search_ui ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.connectionUser"
  member  = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

# Cloud Run SA: read videos and thumbnails from GCS
resource "google_storage_bucket_iam_member" "ui_bucket_reader" {
  count  = var.enable_video_search_ui ? 1 : 0
  bucket = google_storage_bucket.video_search.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

# Cloud Run SA: write to GCS for video ingestion (Add Videos feature)
resource "google_storage_bucket_iam_member" "ui_bucket_writer" {
  count  = var.enable_video_search_ui ? 1 : 0
  bucket = google_storage_bucket.video_search.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

resource "google_cloud_run_v2_service" "video_search_ui" {
  count    = var.enable_video_search_ui ? 1 : 0
  name     = "video-search-ui"
  location = var.region

  template {
    service_account = google_service_account.video_search_ui[0].email

    containers {
      image = var.enable_video_search_build ? "${var.region}-docker.pkg.dev/${var.project_id}/public/video-search-ui:latest" : var.video_search_ui_image

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.video_search.name
      }

      resources {
        limits = {
          memory = "1Gi"
          cpu    = "1"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }

  depends_on = [
    google_project_service.run,
    google_project_iam_member.ui_bq_data_viewer,
    google_project_iam_member.ui_bq_job_user,
    google_project_iam_member.ui_bq_connection,
    google_storage_bucket_iam_member.ui_bucket_reader,
    google_storage_bucket_iam_member.ui_bucket_writer,
  ]
}

