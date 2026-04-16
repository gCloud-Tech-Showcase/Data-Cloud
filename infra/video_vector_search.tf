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
