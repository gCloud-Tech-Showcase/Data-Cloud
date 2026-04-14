# BQ Graph Demo

BigQuery property graph for data center topology analysis using GQL.

Same data center topology as the [Spanner Graph](../spanner-graph/) demo, but running on BigQuery with Enterprise edition. Demonstrates that BQ Graph and Spanner Graph share the same GQL query language — use Spanner for real-time operational queries, BigQuery for deep analytics at scale.

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
- Enterprise reservation for QUERY jobs (0 baseline, autoscale to 50 slots)
- BigQuery dataset: `data_center_topology`

## 2. Load Sample Data

Generate and load the data center topology to BigQuery:

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

## 3. Create the Property Graph

Create the property graph via Dataform:

1. Open [Cloud Console > Dataform](https://console.cloud.google.com/bigquery/dataform)
2. Select repository: `data-cloud`
3. Click **Start Execution** > select tag: `graph`
4. Execute

This runs `CREATE OR REPLACE PROPERTY GRAPH` on the 9 bronze tables, creating a graph with 6 node types and 8 edge relationships.

## 4. Run Graph Queries

Open [BigQuery Console](https://console.cloud.google.com/bigquery) and run the queries below.

> **Note:** BQ Graph uses the same GQL syntax as Spanner Graph. Key differences from the Spanner demo:
> - Enum values are uppercase: `'FAILED'` not `'failed'`, `'DATA_CENTER'` not `'data_center'`
> - `criticality_tier` is a string (`'TIER_1'`) not an integer (`1`)
> - Graph name is fully qualified: `` `data_center_topology.data_center_graph` ``

### Verify Data Loaded

```sql
-- Check row counts
SELECT 'locations' as table_name, COUNT(*) as rows FROM `data_center_topology.locations`
UNION ALL SELECT 'racks', COUNT(*) FROM `data_center_topology.racks`
UNION ALL SELECT 'hardware_assets', COUNT(*) FROM `data_center_topology.hardware_assets`
UNION ALL SELECT 'applications', COUNT(*) FROM `data_center_topology.applications`
ORDER BY rows DESC;
```

### Find Apps Deployed on Failed Servers

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (app:applications)-[:DEPLOYED_ON]->(server:hardware_assets)
WHERE server.status = 'FAILED'
RETURN app.app_name, app.criticality_tier, server.hostname, server.status
ORDER BY app.criticality_tier;
```

### Trace App Dependencies (2 hops)

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (app:applications)-[:DEPENDS_ON]->{1,2}(dep:applications)
WHERE app.app_name LIKE 'Finance%'
RETURN app.app_name AS source_app,
       dep.app_name AS dependency,
       dep.app_type,
       dep.criticality_tier
ORDER BY dep.criticality_tier;
```

### Find All Apps in a Data Center

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (dc:locations {location_type: 'DATA_CENTER'})
      <-[:CHILD_OF]-(row:locations)
      <-[:LOCATED_IN]-(rack:racks)
      <-[:MOUNTED_IN]-(server:hardware_assets)
      <-[:DEPLOYED_ON]-(app:applications)
WHERE dc.name = 'US-West-1'
RETURN DISTINCT app.app_name, app.criticality_tier
ORDER BY app.criticality_tier, app.app_name;
```

### Blast Radius: Rack Failure Impact

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (rack:racks)
      <-[:MOUNTED_IN]-(server:hardware_assets)
      <-[:DEPLOYED_ON]-(app:applications)
WHERE rack.rack_name LIKE 'US-West-1-R01%'
RETURN rack.rack_name,
       COUNT(DISTINCT server.asset_id) AS servers_affected,
       COUNT(DISTINCT app.app_id) AS apps_affected
GROUP BY rack.rack_name
ORDER BY apps_affected DESC;
```

### Critical Assets with Recent Maintenance

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (asset:hardware_assets)<-[:MAINTAINED]-(event:maintenance_events)
WHERE asset.criticality_tier = 'TIER_1'
  AND event.severity = 'CRITICAL'
RETURN asset.hostname,
       event.event_type,
       event.started_at,
       event.downtime_minutes
ORDER BY event.started_at DESC
LIMIT 20;
```

### Location Hierarchy

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (child:locations)-[:CHILD_OF]->(parent:locations)
RETURN child.name AS child_location,
       child.location_type AS child_type,
       parent.name AS parent_location,
       parent.location_type AS parent_type
ORDER BY parent.location_type, parent.name, child.name;
```

## BQ-Specific Features

These features are available in BQ Graph but not in Spanner Graph.

### GRAPH_TABLE: Hybrid SQL + GQL

Embed graph queries in standard SQL using `GRAPH_TABLE`:

```sql
SELECT gt.app_name, gt.server_hostname, a.owner_team
FROM GRAPH_TABLE(
  `data_center_topology.data_center_graph`
  MATCH (app:applications)-[:DEPLOYED_ON]->(server:hardware_assets)
  WHERE server.status = 'MAINTENANCE'
  RETURN app.app_name, server.hostname AS server_hostname, app.app_id
) AS gt
JOIN `data_center_topology.applications` a ON gt.app_id = a.app_id
ORDER BY a.owner_team, gt.app_name;
```

### ANY SHORTEST: Shortest Path

Find the shortest path between two nodes:

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH ANY SHORTEST
  (src:applications)-[:DEPENDS_ON]->{1,5}(dst:applications)
WHERE src.app_name LIKE 'Finance%' AND dst.app_name LIKE 'Auth%'
RETURN src.app_name AS source,
       dst.app_name AS destination,
       ARRAY_LENGTH(dst) AS hops;
```

### NEXT: Chained Graph Queries

Chain multiple graph operations:

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (rack:racks)<-[:MOUNTED_IN]-(server:hardware_assets)
WHERE rack.rack_name LIKE 'US-West-1-R01%'
RETURN server, COUNT(*) AS server_count
GROUP BY server
ORDER BY server_count DESC
LIMIT 5

NEXT

MATCH (server:hardware_assets)<-[:DEPLOYED_ON]-(app:applications)
RETURN server.hostname, app.app_name, app.criticality_tier
ORDER BY app.criticality_tier;
```

## Graph Visualization

BQ Graph supports visualization in the BigQuery console. Use `TO_JSON()` to return graph elements:

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (app:applications)-[d:DEPLOYED_ON]->(server:hardware_assets)-[m:MOUNTED_IN]->(rack:racks)
WHERE rack.rack_name LIKE 'US-West-1-R01%'
RETURN TO_JSON(app) AS app_node,
       TO_JSON(d) AS deployed_edge,
       TO_JSON(server) AS server_node,
       TO_JSON(m) AS mounted_edge,
       TO_JSON(rack) AS rack_node
LIMIT 50;
```

## 5. Cleanup

Destroy the reservation when done:

```bash
cd infra
terraform apply -var="enable_bq_graph_demo=false"
```

The property graph and dataset can remain (no ongoing cost). The reservation is the only resource with potential cost implications.

---

[Back to Demos](../README.md)
