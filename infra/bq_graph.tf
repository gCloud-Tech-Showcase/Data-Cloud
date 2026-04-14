# =============================================================================
# BQ GRAPH DEMO
# BigQuery property graph for data center topology analysis
# Requires Enterprise edition reservation for GQL queries
#
# COST WARNING: Creates an Enterprise reservation. With 0 baseline + autoscale,
# no cost when idle — slots only consumed during query execution. However, the
# QUERY-type assignment applies to ALL queries in the project.
#
# Enable with: enable_bq_graph_demo = true in terraform.tfvars
# =============================================================================

# -----------------------------------------------------------------------------
# BigQuery Enterprise Reservation
# Required for BQ Graph (GQL queries need Enterprise edition)
# -----------------------------------------------------------------------------

resource "google_bigquery_reservation" "graph_queries" {
  count = var.enable_bq_graph_demo ? 1 : 0

  name          = "graph-queries"
  location      = var.dataset_location
  edition       = "ENTERPRISE"
  slot_capacity = 0 # No baseline slots - use autoscaling only

  autoscale {
    max_slots = var.bq_graph_max_slots
  }
}

# -----------------------------------------------------------------------------
# Reservation Assignment
# Assigns the QUERY job type to this project
#
# IMPORTANT: job_type = "QUERY" means ALL regular queries in the project use
# this reservation (not just graph queries). With 0 baseline + autoscale,
# this is equivalent to on-demand but enables Enterprise features like BQ Graph.
# -----------------------------------------------------------------------------

resource "google_bigquery_reservation_assignment" "graph_assignment" {
  count = var.enable_bq_graph_demo ? 1 : 0

  assignee    = "projects/${var.project_id}"
  job_type    = "QUERY"
  reservation = google_bigquery_reservation.graph_queries[0].id
}
