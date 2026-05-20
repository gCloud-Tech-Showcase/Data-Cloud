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
}

# -----------------------------------------------------------------------------
# Dataform Workflow: Video Vector Search Pipeline
# Runs hourly — incremental, so near-zero cost when no new videos.
# Uses the production release config (compiles from main branch).
# Separate from the full-workflow to preserve incremental behavior
# (the main workflow does full refresh, which would re-run Gemini API calls).
# -----------------------------------------------------------------------------

resource "google_dataform_repository_workflow_config" "video_search" {
  provider       = google-beta
  project        = var.project_id
  region         = var.region
  repository     = google_dataform_repository.main.name
  release_config = google_dataform_repository_release_config.main.id

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

resource "google_bigquery_dataset_iam_member" "segmenter_bq_data_editor" {
  dataset_id = google_bigquery_dataset.video_vector_search.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.video_segmenter.email}"
}

resource "google_project_iam_member" "segmenter_bq_connection_user" {
  project = var.project_id
  # connectionAdmin is required (not connectionUser) because Dataform's
  # service-account execution model needs bigquery.connections.delegate,
  # which only connectionAdmin provides among predefined roles.
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
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.video_search.name
    }

    # Note: Eventarc does not support name/prefix filtering for GCS finalized events.
    # The function handles this by checking the object path and exiting early
    # for non-raw/ files (segments, thumbnails, etc.).

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

# Builder SA: deploy new revisions to Cloud Run after building
resource "google_project_iam_member" "ui_builder_run_developer" {
  count   = var.enable_video_search_build ? 1 : 0
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.ui_builder[0].email}"
}

# Builder SA: act as Cloud Run SA when deploying new revisions
resource "google_service_account_iam_member" "ui_builder_acts_as_run_sa" {
  count              = var.enable_video_search_build && var.enable_video_search_ui ? 1 : 0
  service_account_id = google_service_account.video_search_ui[0].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ui_builder[0].email}"
}

# Builder SA: read/write Cloud Build source and staging buckets
resource "google_project_iam_member" "ui_builder_storage" {
  count   = var.enable_video_search_build ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
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
    # Deploy to Cloud Run (if the service exists)
    step {
      name = "gcr.io/google.com/cloudsdktool/cloud-sdk"
      args = [
        "gcloud", "run", "services", "update", "video-search-ui",
        "--region", var.region,
        "--image", "${var.region}-docker.pkg.dev/${var.project_id}/public/video-search-ui:$COMMIT_SHA",
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
    google_project_iam_member.ui_builder_run_developer,
  ]
}

# -----------------------------------------------------------------------------
# Generated .env for local API development
# Terraform is the single source of truth for project config.
# -----------------------------------------------------------------------------

resource "local_file" "video_search_api_env" {
  filename        = "${path.module}/../ui/video-search/api/.env"
  file_permission = "0600"
  content         = "GCP_PROJECT_ID=${var.project_id}\nGCS_BUCKET=${google_storage_bucket.video_search.name}\nGOOGLE_GENAI_USE_VERTEXAI=TRUE\nGOOGLE_CLOUD_LOCATION=${var.region}\n"
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

# Cloud Run SA: call Gemini via Vertex AI (agent + Conversational Analytics)
resource "google_project_iam_member" "ui_vertex_ai_user" {
  count   = var.enable_video_search_ui ? 1 : 0
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

# Cloud Run SA: write to GCS for video ingestion (Add Videos feature)
resource "google_storage_bucket_iam_member" "ui_bucket_writer" {
  count  = var.enable_video_search_ui ? 1 : 0
  bucket = google_storage_bucket.video_search.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

# Cloud Run SA: sign GCS URLs for media playback (signBlob API)
resource "google_service_account_iam_member" "ui_self_token_creator" {
  count              = var.enable_video_search_ui ? 1 : 0
  service_account_id = google_service_account.video_search_ui[0].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.video_search_ui[0].email}"
}

resource "google_cloud_run_v2_service" "video_search_ui" {
  count    = var.enable_video_search_ui ? 1 : 0
  name     = "video-search-ui"
  location = var.region

  # Disable IAM invoker check — makes the service publicly accessible
  # without allUsers binding (compatible with Domain Restricted Sharing)
  invoker_iam_disabled = true

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
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
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
    google_project_iam_member.ui_vertex_ai_user,
    google_storage_bucket_iam_member.ui_bucket_reader,
    google_storage_bucket_iam_member.ui_bucket_writer,
    google_service_account_iam_member.ui_self_token_creator,
  ]
}

# =============================================================================
# AGENT ENGINE (Optional)
# Deploy The Archivist to Vertex AI Agent Engine (Reasoning Engine)
# for use with Gemini Enterprise and external systems.
#
# Enable with: enable_agent_engine = true in terraform.tfvars
# =============================================================================

# App Hub API — required for the Agent Engine dashboard in Cloud Console
resource "google_project_service" "apphub" {
  count              = var.enable_agent_engine ? 1 : 0
  service            = "apphub.googleapis.com"
  disable_on_destroy = false
}

# Telemetry API — required for Agent Engine tracing and observability dashboard
resource "google_project_service" "telemetry" {
  count              = var.enable_agent_engine ? 1 : 0
  service            = "telemetry.googleapis.com"
  disable_on_destroy = false
}

# Discovery Engine API — required for Gemini Enterprise integration
resource "google_project_service" "discoveryengine" {
  count              = var.enable_agent_engine ? 1 : 0
  service            = "discoveryengine.googleapis.com"
  disable_on_destroy = false
}

# GCS bucket for Agent Engine staging artifacts
resource "google_storage_bucket" "agent_staging" {
  count         = var.enable_agent_engine ? 1 : 0
  name          = "${var.project_id}-agent-staging"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  labels = {
    project = "data-cloud"
    purpose = "agent-staging"
    demo    = "video-vector-search"
  }

  depends_on = [google_project_service.storage]
}

# Service account for the deployed agent
resource "google_service_account" "agent_engine" {
  count        = var.enable_agent_engine ? 1 : 0
  account_id   = "video-search-agent"
  display_name = "The Archivist (Agent Engine)"

  depends_on = [google_project_service.vertex_ai]
}

# Agent SA: run BQ queries
resource "google_project_iam_member" "agent_bq_job_user" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: read BQ data
resource "google_project_iam_member" "agent_bq_data_viewer" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: delegate to BQ connection for AI.GENERATE_EMBEDDING
# connectionAdmin is required (not connectionUser) because the agent
# needs bigquery.connections.delegate for embedding generation.
resource "google_project_iam_member" "agent_bq_connection" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.connectionAdmin"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: call Gemini via Vertex AI
resource "google_project_iam_member" "agent_vertex_ai_user" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: write to Cloud Logging. Without this, the OpenTelemetry log
# exporter inside the deployed agent fails with PermissionDenied on
# logging.logEntries.create, hiding the real exceptions from query_metadata
# and other tools.
resource "google_project_iam_member" "agent_log_writer" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: write spans to Cloud Trace. Required by the Agent Engine
# OpenTelemetry exporter when telemetry is enabled (see env vars below).
resource "google_project_iam_member" "agent_trace_agent" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: call Conversational Analytics chat() for the query_metadata tool.
# This role grants geminidataanalytics.locations.chat which the stateless
# chat() endpoint requires. Without it, query_metadata returns 403
# "User does not have permission to chat" when invoked through Agent Engine.
# Locally the developer has the same capability via owner role.
resource "google_project_iam_member" "agent_geminidataanalytics_stateless_chat" {
  count   = var.enable_agent_engine ? 1 : 0
  project = var.project_id
  role    = "roles/geminidataanalytics.dataAgentStatelessUser"
  member  = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Agent SA: read from staging bucket
resource "google_storage_bucket_iam_member" "agent_staging_reader" {
  count  = var.enable_agent_engine ? 1 : 0
  bucket = google_storage_bucket.agent_staging[0].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.agent_engine[0].email}"
}

# Package agent source code for deployment
data "archive_file" "agent_source" {
  count       = var.enable_agent_engine ? 1 : 0
  type        = "tar.gz"
  source_dir  = "${path.module}/../agents/video_search"
  output_path = "${path.module}/../agents/video_search.tar.gz"
}

# Deploy agent to Agent Engine (Reasoning Engine)
resource "google_vertex_ai_reasoning_engine" "the_archivist" {
  count        = var.enable_agent_engine ? 1 : 0
  display_name = "The Archivist"
  description  = "Video Content Analyst — searches, filters, plays, and analyzes a video library through natural language conversation."
  region       = var.region
  project      = var.project_id

  spec {
    agent_framework = "google-adk"
    class_methods = jsonencode([
      {
        name     = "query"
        api_mode = "async"
        parameters = {
          type       = "object"
          required   = ["message"]
          properties = {
            message    = { type = "string", description = "The user's message" }
            user_id    = { type = "string", description = "User identifier" }
            session_id = { type = "string", description = "Session identifier" }
          }
        }
      },
      {
        name     = "stream_query"
        api_mode = "async"
        parameters = {
          type       = "object"
          required   = ["message"]
          properties = {
            message    = { type = "string", description = "The user's message" }
            user_id    = { type = "string", description = "User identifier" }
            session_id = { type = "string", description = "Session identifier" }
          }
        }
      },
    ])

    source_code_spec {
      inline_source {
        source_archive = filebase64(data.archive_file.agent_source[0].output_path)
      }

      python_spec {
        entrypoint_module = "agent"
        entrypoint_object = "app"
        version           = "3.12"
        requirements_file = "requirements.txt"
      }
    }

    deployment_spec {
      min_instances = 1
      max_instances = 2

      # GOOGLE_CLOUD_PROJECT is automatically set by Agent Engine (reserved)
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      # Tracing and observability (required for the Agent Engine dashboard)
      env {
        name  = "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"
        value = "true"
      }
      env {
        name  = "OTEL_SEMCONV_STABILITY_OPT_IN"
        value = "gen_ai_latest_experimental"
      }
      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "EVENT_ONLY"
      }
    }

    service_account = google_service_account.agent_engine[0].email
  }

  labels = {
    project = "data-cloud"
    demo    = "video-vector-search"
    agent   = "the-archivist"
  }

  depends_on = [
    google_project_service.vertex_ai,
    google_project_iam_member.agent_bq_job_user,
    google_project_iam_member.agent_bq_data_viewer,
    google_project_iam_member.agent_bq_connection,
    google_project_iam_member.agent_vertex_ai_user,
    google_project_iam_member.agent_log_writer,
    google_storage_bucket_iam_member.agent_staging_reader,
  ]
}

# =============================================================================
# GEMINI ENTERPRISE (Optional)
# Register The Archivist into a new Gemini Enterprise (formerly Agentspace)
# app so it's reachable from the GE surface. Requires enable_agent_engine.
#
# Enable with: enable_gemini_enterprise = true (and enable_agent_engine = true)
# =============================================================================

# Force-create the Discovery Engine service agent so we can grant it IAM below.
# Without this, the service-{project_number}@gcp-sa-discoveryengine SA may not
# exist on a fresh project until the first Discovery Engine resource is created.
resource "google_project_service_identity" "discoveryengine" {
  count    = var.enable_agent_engine && var.enable_gemini_enterprise ? 1 : 0
  provider = google-beta
  project  = var.project_id
  service  = "discoveryengine.googleapis.com"

  depends_on = [google_project_service.discoveryengine]
}

# Wait briefly after API enablement before creating the search engine,
# to avoid SERVICE_DISABLED on first-time apply.
resource "time_sleep" "discoveryengine_propagation" {
  count           = var.enable_agent_engine && var.enable_gemini_enterprise ? 1 : 0
  create_duration = "30s"

  depends_on = [google_project_service.discoveryengine]
}

# Allow the Discovery Engine service agent to invoke the Reasoning Engine.
# This is what lets the GE app call into The Archivist at query time.
resource "google_project_iam_member" "discoveryengine_sa_aiplatform_user" {
  count   = var.enable_agent_engine && var.enable_gemini_enterprise ? 1 : 0
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-discoveryengine.iam.gserviceaccount.com"

  depends_on = [google_project_service_identity.discoveryengine]
}

# Stub data store for the Agentspace app. A GE search engine schema requires
# at least one data store association even when the user-facing experience is
# driven entirely by a registered agent. NO_CONTENT means nothing is indexed.
resource "google_discovery_engine_data_store" "video_search_stub" {
  count                       = var.enable_agent_engine && var.enable_gemini_enterprise ? 1 : 0
  data_store_id               = "video-search-stub-store-search"
  location                    = "global"
  display_name                = "Video Search (stub data store)"
  industry_vertical           = "GENERIC"
  content_config              = "NO_CONTENT"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  create_advanced_site_search = false

  depends_on = [
    google_project_service.discoveryengine,
    time_sleep.discoveryengine_propagation,
  ]
}

# The Gemini Enterprise / Agentspace app.
# app_type = APP_TYPE_INTRANET is what makes this surface as an Agentspace
# app (with the agent gallery) rather than a generic Vertex AI Search app.
resource "google_discovery_engine_search_engine" "video_search" {
  count             = var.enable_agent_engine && var.enable_gemini_enterprise ? 1 : 0
  engine_id         = "video-search-engine"
  collection_id     = "default_collection"
  location          = "global"
  display_name      = "Video Library Intelligence (Archivist)"
  industry_vertical = "GENERIC"
  app_type          = "APP_TYPE_INTRANET"
  data_store_ids    = [google_discovery_engine_data_store.video_search_stub[0].data_store_id]

  common_config {
    company_name = "Video Library Intelligence (Archivist)"
  }

  search_engine_config {
    search_tier = "SEARCH_TIER_ENTERPRISE"
  }

  depends_on = [
    google_project_service.discoveryengine,
    time_sleep.discoveryengine_propagation,
  ]
}

# Register the deployed Reasoning Engine as an agent inside the GE app.
# Discovery Engine v1alpha agent registration is not yet covered by the
# Terraform provider, so we call the REST API via local-exec.
resource "null_resource" "register_archivist_agent" {
  count = var.enable_agent_engine && var.enable_gemini_enterprise ? 1 : 0

  triggers = {
    chat_engine_name    = google_discovery_engine_search_engine.video_search[0].name
    reasoning_engine    = "projects/${var.project_id}/locations/${var.region}/reasoningEngines/${google_vertex_ai_reasoning_engine.the_archivist[0].name}"
    agent_resource_path = "${google_discovery_engine_search_engine.video_search[0].name}/assistants/default_assistant/agents/the-archivist"
    project_id          = var.project_id
  }

  # Create / update: ensure the default_assistant exists, then register
  # The Archivist as an ADK agent on it. Both calls tolerate 409 (already
  # exists) for idempotency on re-apply.
  provisioner "local-exec" {
    command = <<-EOT
      set -e
      TOKEN=$(gcloud auth application-default print-access-token)

      echo "Ensuring default_assistant exists..."
      GET_CODE=$(curl -sS -o /tmp/ge_assistant.json -w "%%{http_code}" \
        "https://discoveryengine.googleapis.com/v1alpha/${self.triggers.chat_engine_name}/assistants/default_assistant" \
        -H "Authorization: Bearer $TOKEN" \
        -H "X-Goog-User-Project: ${self.triggers.project_id}")
      if [ "$GET_CODE" = "200" ]; then
        echo "default_assistant already exists"
      elif [ "$GET_CODE" = "404" ]; then
        echo "Creating default_assistant..."
        POST_CODE=$(curl -sS -o /tmp/ge_assistant.json -w "%%{http_code}" -X POST \
          "https://discoveryengine.googleapis.com/v1alpha/${self.triggers.chat_engine_name}/assistants?assistantId=default_assistant" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -H "X-Goog-User-Project: ${self.triggers.project_id}" \
          -d '{"displayName": "Video Library Intelligence"}')
        cat /tmp/ge_assistant.json
        if [ "$POST_CODE" != "200" ]; then
          echo "Assistant creation failed (HTTP $POST_CODE)"
          exit 1
        fi
      else
        cat /tmp/ge_assistant.json
        echo "Unexpected status checking assistant (HTTP $GET_CODE)"
        exit 1
      fi

      echo "Registering The Archivist agent..."
      AGENT_CODE=$(curl -sS -o /tmp/ge_register.json -w "%%{http_code}" -X POST \
        "https://discoveryengine.googleapis.com/v1alpha/${self.triggers.chat_engine_name}/assistants/default_assistant/agents?agentId=the-archivist" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${self.triggers.project_id}" \
        -d '{
          "displayName": "The Archivist",
          "description": "Video Content Analyst — searches, filters, plays, and analyzes a video library through natural language conversation.",
          "adkAgentDefinition": {
            "provisionedReasoningEngine": {
              "reasoningEngine": "${self.triggers.reasoning_engine}"
            }
          }
        }')
      cat /tmp/ge_register.json
      if [ "$AGENT_CODE" = "200" ] || [ "$AGENT_CODE" = "409" ]; then
        echo "Registration OK (HTTP $AGENT_CODE)"
      else
        echo "Registration failed (HTTP $AGENT_CODE)"
        exit 1
      fi
    EOT
  }

  # Destroy: deregister the agent. Tolerates 404 in case it was deleted manually.
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      curl -sS -X DELETE \
        "https://discoveryengine.googleapis.com/v1alpha/${self.triggers.agent_resource_path}" \
        -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
        -H "X-Goog-User-Project: ${self.triggers.project_id}" || true
    EOT
  }

  depends_on = [
    google_discovery_engine_search_engine.video_search,
    google_vertex_ai_reasoning_engine.the_archivist,
    google_project_iam_member.discoveryengine_sa_aiplatform_user,
  ]
}

