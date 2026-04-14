# BQ Graph Demo Guide

Step-by-step walkthrough to deploy and explore the BQ Graph demo.

## Prerequisites

- GCP project with billing enabled
- Terraform installed
- Python 3.9+ with virtual environment
- `gcloud` CLI authenticated

## 1. Deploy Infrastructure

Enable the BQ Graph demo in Terraform:

```bash
cd infra

# Preview changes
terraform plan -var="enable_bq_graph_demo=true"

# Apply
terraform apply -var="enable_bq_graph_demo=true"
```

This creates:
- Enterprise reservation: `graph-queries` (QUERY type, 0 baseline, autoscale to 50 slots)
- BigQuery dataset: `data_center_topology`
- Reservation assignment at project level

## 2. Load Sample Data

Generate and load the data center topology:

```bash
cd scripts

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Generate and load data to BigQuery
python generate_datacenter_topology.py \
  --project YOUR_PROJECT_ID \
  --target bigquery
```

Expected output (approximate):
```
============================================================
Generation Statistics
============================================================
  Locations:           48
  Racks:               480
  Hardware Assets:     ~4,700
  NIC Interfaces:      ~18,800
  Applications:        200
  Network Connections:  ~900
  App Deployments:     ~850
  App Dependencies:    ~430
  Maintenance Events:  ~1,500
============================================================
```

## 3. Create the Property Graph

Create the property graph via Dataform:

1. Open [Cloud Console > Dataform](https://console.cloud.google.com/bigquery/dataform)
2. Select repository: `data-cloud`
3. Click **Start Execution** > select tag: `graph`
4. Execute

This runs `CREATE OR REPLACE PROPERTY GRAPH` on the 9 bronze tables, creating a graph with 6 node types and 8 edge relationships. The graph is a metadata overlay — no data is copied.

## 4. Explore in BigQuery Console

1. Open [BigQuery Console](https://console.cloud.google.com/bigquery)
2. Run queries from the [Quick Reference](quick.md)

### Verify Data Loaded

```sql
SELECT 'locations' as table_name, COUNT(*) as row_count FROM `data_center_topology.locations`
UNION ALL SELECT 'racks', COUNT(*) FROM `data_center_topology.racks`
UNION ALL SELECT 'hardware_assets', COUNT(*) FROM `data_center_topology.hardware_assets`
UNION ALL SELECT 'applications', COUNT(*) FROM `data_center_topology.applications`
ORDER BY row_count DESC;
```

### Run Graph Queries

See [Quick Reference](quick.md) for copy-paste queries.

## 5. Example Use Cases

### Impact Analysis

*"What applications are affected by critical maintenance events?"*

Uses a 3-hop graph traversal: apps → servers → maintenance events. In SQL, this would require 3 JOINs including a junction table.

### Dependency Tracing

*"Show all upstream dependencies for our finance apps."*

Traces the DEPENDS_ON edges up to 2 hops deep using quantified path patterns.

### Blast Radius

*"What's the blast radius if rack `US-West-1-R01-01` loses power?"*

Traverses from rack → servers → apps to find all affected applications.

### Shortest Path

*"What's the shortest dependency chain between Finance and Security apps?"*

Uses `ANY SHORTEST` with quantified paths — a BQ Graph exclusive feature.

## 6. Cleanup

Destroy the reservation when done:

```bash
cd infra
terraform apply -var="enable_bq_graph_demo=false"
```

The property graph and dataset can remain (no ongoing cost). The reservation is the only resource with potential cost implications.

---

[Back to README](README.md) | [Architecture](architecture.md) | [Quick Reference](quick.md)
