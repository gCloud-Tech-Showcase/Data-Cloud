# =============================================================================
# DATA CENTER TOPOLOGY DEMO
# Vertica-to-BigQuery ingestion with data center hardware inventory
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset
# Target dataset for Vertica ingestion
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "data_center_topology" {
  count = var.enable_vertica_demo ? 1 : 0

  dataset_id  = "data_center_topology"
  location    = var.dataset_location
  description = "Data center hardware topology - entities (locations, racks, servers, applications) and relationships (connections, deployments, dependencies) ingested from Vertica"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "vertica-ingestion"
  }

  depends_on = [google_project_service.bigquery]
}
