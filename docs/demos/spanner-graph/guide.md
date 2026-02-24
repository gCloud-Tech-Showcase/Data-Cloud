# Spanner Graph Demo Guide

Step-by-step walkthrough to deploy and explore the Spanner Graph demo.

## Prerequisites

- GCP project with billing enabled
- Terraform installed
- Python 3.9+ with virtual environment
- `gcloud` CLI authenticated

## 1. Deploy Infrastructure

Enable the Spanner Graph demo in Terraform:

```bash
cd infra

# Preview changes
terraform plan -var="enable_spanner_graph_demo=true"

# Apply
terraform apply -var="enable_spanner_graph_demo=true"
```

This creates:
- Spanner instance: `data-center-graph`
- Spanner database: `topology` with 9 tables + property graph

## 2. Load Sample Data

Generate and load the data center topology:

```bash
cd scripts

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Generate and load data to Spanner
python generate_datacenter_topology.py \
  --project YOUR_PROJECT_ID \
  --target spanner \
  --spanner-instance data-center-graph \
  --spanner-database topology
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
  Network Connections: ~900
  App Deployments:     ~850
  App Dependencies:    ~430
  Maintenance Events:  ~1,500
============================================================
```

## 3. Explore in Spanner Studio

1. Open [Cloud Console > Spanner](https://console.cloud.google.com/spanner)
2. Select instance: `data-center-graph`
3. Select database: `topology`
4. Click **Spanner Studio** tab

### Verify Data Loaded

```sql
-- Check row counts
SELECT 'locations' as table_name, COUNT(*) as rows FROM locations
UNION ALL SELECT 'racks', COUNT(*) FROM racks
UNION ALL SELECT 'hardware_assets', COUNT(*) FROM hardware_assets
UNION ALL SELECT 'applications', COUNT(*) FROM applications;
```

### Run Graph Queries

See [Quick Reference](quick.md) for copy-paste queries.

## 4. Example Use Cases

### Impact Analysis

*"What applications are affected if server `uswest1-srv-0001` fails?"*

This query finds all apps deployed on the server, plus apps that depend on those apps (cascade effect).

### Dependency Tracing

*"Show all upstream dependencies for the finance dashboard app."*

Traces the DEPENDS_ON edges to find all services the app relies on.

### Blast Radius

*"What's the blast radius if rack `US-West-1-R01-01` loses power?"*

Traverses from rack -> servers -> apps to find all affected applications.

## 5. Cleanup

Destroy the Spanner resources when done to avoid ongoing costs:

```bash
cd infra
terraform destroy -var="enable_spanner_graph_demo=true"
```

**Important:** Spanner incurs costs while running. See [Spanner pricing](https://cloud.google.com/spanner/pricing) for current rates.

---

[Back to README](README.md) | [Architecture](architecture.md) | [Quick Reference](quick.md)
