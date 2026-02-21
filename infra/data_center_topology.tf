# =============================================================================
# DATA CENTER TOPOLOGY DEMO
# Knowledge Graph analytics on data center hardware inventory
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Dataset (Shared)
# Used by both Knowledge Graph demo and Vertica ingestion demo
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "data_center_topology" {
  count = var.enable_knowledge_graph_demo ? 1 : 0

  dataset_id  = "data_center_topology"
  location    = var.dataset_location
  description = "Data center hardware topology - Knowledge Graph ready schema with entities (locations, racks, servers, applications) and relationships (connections, deployments, dependencies)"

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "data-center-topology"
  }

  depends_on = [google_project_service.bigquery]
}
