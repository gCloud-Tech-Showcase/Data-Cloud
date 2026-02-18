# =============================================================================
# CHURN PREDICTION DEMO
# BigQuery ML user retention model with rolling 7-day windows
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Datasets
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "propensity_modeling" {
  dataset_id  = var.dataset_id
  location    = var.dataset_location
  description = "Data Cloud showcase dataset for BQML propensity modeling"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "churn-prediction"
  }

  depends_on = [google_project_service.bigquery]
}

resource "google_bigquery_dataset" "ga4_source" {
  dataset_id  = "ga4_source"
  location    = var.dataset_location
  description = "Source views over GA4/Firebase public datasets"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "churn-prediction"
  }

  depends_on = [google_project_service.bigquery]
}

# -----------------------------------------------------------------------------
# Vertex AI Endpoint
# For deploying the trained retention model
# -----------------------------------------------------------------------------

resource "google_vertex_ai_endpoint" "retention_endpoint" {
  name         = var.retention_model_endpoint_name
  display_name = "User Retention Prediction"
  location     = var.region

  depends_on = [google_project_service.vertex_ai]
}
