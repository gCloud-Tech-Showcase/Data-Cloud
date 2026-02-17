output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

# -----------------------------------------------------------------------------
# Network
# -----------------------------------------------------------------------------

output "network_name" {
  description = "The VPC network name"
  value       = google_compute_network.main.name
}

output "network_self_link" {
  description = "The VPC network self link"
  value       = google_compute_network.main.self_link
}

output "subnet_name" {
  description = "The subnet name"
  value       = google_compute_subnetwork.main.name
}

output "subnet_self_link" {
  description = "The subnet self link"
  value       = google_compute_subnetwork.main.self_link
}

# -----------------------------------------------------------------------------
# BigQuery
# -----------------------------------------------------------------------------

output "propensity_modeling_dataset_id" {
  description = "The propensity modeling BigQuery dataset ID"
  value       = google_bigquery_dataset.propensity_modeling.dataset_id
}

output "ga4_source_dataset_id" {
  description = "The GA4 source BigQuery dataset ID"
  value       = google_bigquery_dataset.ga4_source.dataset_id
}

# -----------------------------------------------------------------------------
# Dataform
# -----------------------------------------------------------------------------

output "dataform_repository_name" {
  description = "The Dataform repository name"
  value       = google_dataform_repository.main.name
}

output "dataform_release_config_name" {
  description = "The Dataform release configuration name"
  value       = google_dataform_repository_release_config.main.name
}

output "dataform_workflow_config_name" {
  description = "The Dataform workflow configuration name"
  value       = google_dataform_repository_workflow_config.main.name
}

# -----------------------------------------------------------------------------
# Vertex AI
# -----------------------------------------------------------------------------

output "vertex_endpoint_id" {
  value = google_vertex_ai_endpoint.retention_endpoint.name
}

output "vertex_endpoint_predict_url" {
  value = "https://${var.region}-aiplatform.googleapis.com/v1/${google_vertex_ai_endpoint.retention_endpoint.id}:predict"
}

# -----------------------------------------------------------------------------
# Security Logs Demo
# -----------------------------------------------------------------------------

output "security_logs_dataset_id" {
  description = "The security logs BigQuery dataset ID"
  value       = google_bigquery_dataset.security_logs.dataset_id
}

output "audit_log_sink_name" {
  description = "The Cloud Audit Log sink name"
  value       = google_logging_project_sink.audit_to_bigquery.name
}

output "audit_log_sink_writer_identity" {
  description = "The service account identity used by the log sink"
  value       = google_logging_project_sink.audit_to_bigquery.writer_identity
}

output "security_alerts_topic" {
  description = "Pub/Sub topic for security alerts from continuous queries"
  value       = google_pubsub_topic.security_alerts.id
}

output "security_logs_iceberg_bucket" {
  description = "GCS bucket for BigLake Iceberg security logs"
  value       = google_storage_bucket.security_logs_iceberg.name
}
