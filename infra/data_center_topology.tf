# =============================================================================
# DATA CENTER TOPOLOGY - SHARED DATASET
# Used by: Vertica Ingestion, Spanner Graph (and future BQ Knowledge Graph)
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset
# Shared dataset for data center topology demos
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "data_center_topology" {
  # Create if any topology-based demo is enabled
  count = (var.enable_vertica_demo || var.enable_spanner_graph_demo) ? 1 : 0

  dataset_id  = "data_center_topology"
  location    = var.dataset_location
  description = "Data center hardware topology - entities (locations, racks, servers, applications) and relationships (connections, deployments, dependencies)"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "data-center-topology"
  }

  depends_on = [google_project_service.bigquery]
}
