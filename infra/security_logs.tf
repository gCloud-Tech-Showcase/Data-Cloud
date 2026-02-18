# =============================================================================
# SECURITY LOGS DEMO
# AI-powered threat detection with log embeddings and semantic search
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "security_logs" {
  dataset_id  = "security_logs"
  location    = var.dataset_location
  description = "Security log analytics demo - Cloud Audit Logs with AI enrichment, vector search, and real-time alerting"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "security-logs"
  }

  depends_on = [google_project_service.bigquery]
}

# -----------------------------------------------------------------------------
# Cloud Logging Sink to BigQuery
# Routes Cloud Audit Logs to BigQuery for analysis
# -----------------------------------------------------------------------------

resource "google_logging_project_sink" "audit_to_bigquery" {
  name        = "audit-logs-to-bigquery"
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.security_logs.dataset_id}"

  # Capture all Cloud Audit Logs (Admin Activity, Data Access, System Events)
  filter = <<-EOT
    logName:"cloudaudit.googleapis.com"
  EOT

  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }

  depends_on = [
    google_project_service.logging,
    google_bigquery_dataset.security_logs
  ]
}

# Grant the log sink's service account permission to write to BigQuery
resource "google_bigquery_dataset_iam_member" "log_sink_writer" {
  dataset_id = google_bigquery_dataset.security_logs.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.audit_to_bigquery.writer_identity

  depends_on = [google_logging_project_sink.audit_to_bigquery]
}

# -----------------------------------------------------------------------------
# BigLake Iceberg Storage
# For managed table format demo
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "security_logs_iceberg" {
  name          = "${var.project_id}-security-logs-iceberg"
  location      = var.region
  force_destroy = true # Demo bucket - OK to destroy

  uniform_bucket_level_access = true

  labels = {
    project = "data-cloud"
    purpose = "security-logs-iceberg"
    demo    = "security-logs"
  }

  depends_on = [google_project_service.storage]
}

# Grant BigQuery connection access to Iceberg bucket
resource "google_storage_bucket_iam_member" "bq_connection_iceberg_reader" {
  bucket = google_storage_bucket.security_logs_iceberg.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"

  depends_on = [
    google_bigquery_connection.vertex_ai,
    google_storage_bucket.security_logs_iceberg
  ]
}
