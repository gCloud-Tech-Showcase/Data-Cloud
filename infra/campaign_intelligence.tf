# =============================================================================
# CAMPAIGN INTELLIGENCE DEMO (Proof of Concept)
# Census geospatial + theLook eCommerce targeting
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "campaign_intelligence" {
  dataset_id  = "campaign_intelligence"
  location    = var.dataset_location
  description = "Campaign intelligence combining public housing/census data with digital engagement signals"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "campaign-intelligence"
  }

  depends_on = [google_project_service.bigquery]
}
