# =============================================================================
# SECURITY LOGS REAL-TIME ALERTS (Optional)
# Enterprise reservation for continuous queries
#
# Enable this to explore the real-time alerting portion of the Security Logs demo.
#
# COST WARNING: Creates an Enterprise reservation that incurs charges even when
# idle (~1 slot while listening).
#
# Enable with: enable_realtime_alerts = true in terraform.tfvars
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Enterprise Reservation
# Required for continuous queries
# -----------------------------------------------------------------------------

resource "google_bigquery_reservation" "continuous_queries" {
  count = var.enable_realtime_alerts ? 1 : 0

  name          = "continuous-queries"
  location      = var.dataset_location
  edition       = "ENTERPRISE"
  slot_capacity = 0 # No baseline slots - use autoscaling only

  autoscale {
    max_slots = var.realtime_alerts_max_slots
  }
}

# -----------------------------------------------------------------------------
# Reservation Assignment
# Assigns the CONTINUOUS job type to this project
#
# IMPORTANT: job_type = "CONTINUOUS" means this reservation is ONLY used for
# continuous queries. Regular queries (SELECT, INSERT, etc.) continue to use
# on-demand billing or other QUERY-type reservations. The two are isolated.
# -----------------------------------------------------------------------------

resource "google_bigquery_reservation_assignment" "continuous_assignment" {
  count = var.enable_realtime_alerts ? 1 : 0

  assignee    = "projects/${var.project_id}"
  job_type    = "CONTINUOUS"
  reservation = google_bigquery_reservation.continuous_queries[0].id
}

# -----------------------------------------------------------------------------
# Service Account for Continuous Queries
# Required for Pub/Sub export (user accounts can't export to Pub/Sub)
# -----------------------------------------------------------------------------

resource "google_service_account" "continuous_queries" {
  count = var.enable_realtime_alerts ? 1 : 0

  account_id   = "bq-continuous-queries"
  display_name = "BigQuery Continuous Queries"
  description  = "Service account for running continuous queries with Pub/Sub export"
}

# Grant the SA permission to run BigQuery jobs
resource "google_project_iam_member" "continuous_queries_bq_user" {
  count = var.enable_realtime_alerts ? 1 : 0

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.continuous_queries[0].email}"
}

# Grant the SA permission to read from BigQuery tables
resource "google_project_iam_member" "continuous_queries_bq_data_viewer" {
  count = var.enable_realtime_alerts ? 1 : 0

  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.continuous_queries[0].email}"
}

# -----------------------------------------------------------------------------
# Pub/Sub Topic for Real-Time Alerts
# Used by continuous queries to publish high-severity events
# -----------------------------------------------------------------------------

resource "google_pubsub_topic" "security_alerts" {
  count = var.enable_realtime_alerts ? 1 : 0

  name = "security-alerts"

  labels = {
    project = "data-cloud"
    purpose = "security-alerting"
    demo    = "security-logs"
  }

  depends_on = [google_project_service.pubsub]
}

# Subscription for testing/viewing alerts
resource "google_pubsub_subscription" "security_alerts_sub" {
  count = var.enable_realtime_alerts ? 1 : 0

  name  = "security-alerts-sub"
  topic = google_pubsub_topic.security_alerts[0].id

  message_retention_duration = "604800s" # 7 days
  ack_deadline_seconds       = 20

  labels = {
    project = "data-cloud"
    purpose = "security-alerting"
    demo    = "security-logs"
  }
}

# Grant the continuous queries SA permission to publish to the topic
resource "google_pubsub_topic_iam_member" "continuous_queries_publisher" {
  count = var.enable_realtime_alerts ? 1 : 0

  topic  = google_pubsub_topic.security_alerts[0].name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.continuous_queries[0].email}"
}

# Grant the continuous queries SA permission to view topic (needed for schema access)
resource "google_pubsub_topic_iam_member" "continuous_queries_viewer" {
  count = var.enable_realtime_alerts ? 1 : 0

  topic  = google_pubsub_topic.security_alerts[0].name
  role   = "roles/pubsub.viewer"
  member = "serviceAccount:${google_service_account.continuous_queries[0].email}"
}
