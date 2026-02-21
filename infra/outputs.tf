# =============================================================================
# OUTPUTS
# =============================================================================

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
# BigQuery - Churn Prediction
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
# Vertex AI - Churn Prediction
# -----------------------------------------------------------------------------

output "vertex_endpoint_id" {
  description = "The Vertex AI endpoint ID for retention model"
  value       = google_vertex_ai_endpoint.retention_endpoint.name
}

output "vertex_endpoint_predict_url" {
  description = "The Vertex AI endpoint prediction URL"
  value       = "https://${var.region}-aiplatform.googleapis.com/v1/${google_vertex_ai_endpoint.retention_endpoint.id}:predict"
}

# -----------------------------------------------------------------------------
# Sentiment Analysis
# -----------------------------------------------------------------------------

output "sentiment_analysis_dataset_id" {
  description = "The sentiment analysis BigQuery dataset ID"
  value       = google_bigquery_dataset.sentiment_analysis.dataset_id
}

output "multimodal_data_bucket" {
  description = "GCS bucket for unstructured review data"
  value       = google_storage_bucket.multimodal_data.name
}

# -----------------------------------------------------------------------------
# Campaign Intelligence
# -----------------------------------------------------------------------------

output "campaign_intelligence_dataset_id" {
  description = "The campaign intelligence BigQuery dataset ID"
  value       = google_bigquery_dataset.campaign_intelligence.dataset_id
}

# -----------------------------------------------------------------------------
# Security Logs
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
  description = "Pub/Sub topic for security alerts from continuous queries (if enabled)"
  value       = var.enable_realtime_alerts ? google_pubsub_topic.security_alerts[0].id : null
}

output "security_logs_iceberg_bucket" {
  description = "GCS bucket for BigLake Iceberg security logs"
  value       = google_storage_bucket.security_logs_iceberg.name
}

# -----------------------------------------------------------------------------
# Security Logs - Real-Time (Conditional)
# -----------------------------------------------------------------------------

output "continuous_queries_reservation" {
  description = "BigQuery Enterprise reservation for continuous queries (if enabled)"
  value       = var.enable_realtime_alerts ? google_bigquery_reservation.continuous_queries[0].name : null
}

output "continuous_queries_service_account" {
  description = "Service account email for running continuous queries with Pub/Sub export"
  value       = var.enable_realtime_alerts ? google_service_account.continuous_queries[0].email : null
}

output "realtime_alerts_enabled" {
  description = "Whether real-time alerts (continuous queries) are enabled"
  value       = var.enable_realtime_alerts
}

# -----------------------------------------------------------------------------
# Data Center Topology (Knowledge Graph)
# -----------------------------------------------------------------------------

output "data_center_topology_dataset_id" {
  description = "The data center topology BigQuery dataset ID (if enabled)"
  value       = var.enable_knowledge_graph_demo ? google_bigquery_dataset.data_center_topology[0].dataset_id : null
}

output "knowledge_graph_demo_enabled" {
  description = "Whether the Knowledge Graph demo is enabled"
  value       = var.enable_knowledge_graph_demo
}

# -----------------------------------------------------------------------------
# Vertica Ingestion (Conditional)
# -----------------------------------------------------------------------------

output "vertica_demo_enabled" {
  description = "Whether the Vertica ingestion demo is enabled"
  value       = var.enable_vertica_demo
}

output "vertica_vm_internal_ip" {
  description = "Vertica VM internal IP address (for Spark connector)"
  value       = var.enable_vertica_demo ? google_compute_instance.vertica[0].network_interface[0].network_ip : null
}

# No external IP output - VM uses internal IP only (secure by default)
# Access via IAP: gcloud compute ssh vertica-demo --tunnel-through-iap

output "vertica_staging_bucket" {
  description = "GCS bucket for Vertica Spark connector staging"
  value       = var.enable_vertica_demo ? google_storage_bucket.vertica_staging[0].name : null
}

output "spark_scripts_bucket" {
  description = "GCS bucket containing PySpark jobs"
  value       = var.enable_vertica_demo ? google_storage_bucket.spark_scripts[0].name : null
}

output "dataproc_workflow_template" {
  description = "Dataproc workflow template for Vertica to BigQuery ingestion"
  value       = var.enable_vertica_demo ? google_dataproc_workflow_template.vertica_to_bq[0].name : null
}

output "scheduler_job_name" {
  description = "Cloud Scheduler job for weekly sync (paused by default)"
  value       = var.enable_vertica_demo ? google_cloud_scheduler_job.vertica_sync[0].name : null
}
