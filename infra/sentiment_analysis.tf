# =============================================================================
# SENTIMENT ANALYSIS DEMO
# Gemini-powered review analysis via BigLake
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "sentiment_analysis" {
  dataset_id  = "sentiment_analysis"
  location    = var.dataset_location
  description = "Gemini-powered sentiment analysis of user reviews"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "sentiment-analysis"
  }

  depends_on = [google_project_service.bigquery]
}

# -----------------------------------------------------------------------------
# Cloud Storage Bucket for Unstructured Data
# Stores scraped Play Store reviews as JSON files
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "multimodal_data" {
  name          = "${var.project_id}-multimodal-data"
  location      = var.region
  force_destroy = false # Protect scraped data from accidental deletion

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  labels = {
    project = "data-cloud"
    purpose = "unstructured-data"
    demo    = "sentiment-analysis"
  }

  depends_on = [google_project_service.storage]
}

# Grant BigQuery connection read access to GCS bucket for BigLake Object Tables
resource "google_storage_bucket_iam_member" "bq_connection_gcs_reader" {
  bucket = google_storage_bucket.multimodal_data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"

  depends_on = [
    google_bigquery_connection.vertex_ai,
    google_storage_bucket.multimodal_data
  ]
}
