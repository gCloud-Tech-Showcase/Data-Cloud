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
#   gs://{project}-video-search/manifests/    — Provenance and mapping metadata
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

# Function SA: trigger Dataform workflows after segmentation
resource "google_project_iam_member" "segmenter_dataform_editor" {
  project = var.project_id
  role    = "roles/dataform.editor"
  member  = "serviceAccount:${google_service_account.video_segmenter.email}"
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
    max_instance_count    = 5
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
