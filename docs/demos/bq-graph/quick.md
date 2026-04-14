# BQ Graph Quick Reference

Copy-paste GQL queries for BigQuery Console.

> **Key schema notes:**
> - Enum values are lowercase: `'failed'`, `'data_center'`, `'critical'`
> - `criticality_tier` is an integer (`1`, `2`, `3`, `4`)
> - Location hierarchy: `region` → `data_center` → `row`
> - Graph name is fully qualified: `` `data_center_topology.data_center_graph` ``

## Basic Queries

### List All Node Types

```sql
-- Count nodes by type
SELECT 'locations' as node_type, COUNT(*) as row_count FROM `data_center_topology.locations`
UNION ALL SELECT 'racks', COUNT(*) FROM `data_center_topology.racks`
UNION ALL SELECT 'hardware_assets', COUNT(*) FROM `data_center_topology.hardware_assets`
UNION ALL SELECT 'nic_interfaces', COUNT(*) FROM `data_center_topology.nic_interfaces`
UNION ALL SELECT 'applications', COUNT(*) FROM `data_center_topology.applications`
UNION ALL SELECT 'maintenance_events', COUNT(*) FROM `data_center_topology.maintenance_events`
ORDER BY row_count DESC;
```

### Sample Applications

```sql
SELECT app_name, app_type, criticality_tier, status
FROM `data_center_topology.applications`
WHERE status = 'active'
LIMIT 10;
```

## Graph Traversal Queries

### Find Apps Affected by Critical Maintenance

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (app:applications)-[:DEPLOYED_ON]->(server:hardware_assets)<-[:MAINTAINED]-(event:maintenance_events)
WHERE event.severity = 'critical'
RETURN app.app_name, app.criticality_tier, server.hostname, event.event_type, event.downtime_minutes
ORDER BY app.criticality_tier, event.downtime_minutes DESC
LIMIT 20;
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
MATCH (dc:locations {location_type: 'data_center'})
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

### Critical Tier-1 Assets with Recent Maintenance

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (asset:hardware_assets)<-[:MAINTAINED]-(event:maintenance_events)
WHERE asset.criticality_tier = 1
  AND event.severity = 'critical'
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
  WHERE server.criticality_tier = 1
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
  (src:applications)-[e:DEPENDS_ON]->{1,5}(dst:applications)
WHERE src.app_name LIKE 'Finance%' AND dst.app_name LIKE 'Security%'
RETURN src.app_name AS source,
       dst.app_name AS destination,
       ARRAY_LENGTH(e) AS hops;
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

## Graph Visualization Queries

These queries return graph elements via `TO_JSON()`, enabling visual exploration in the BigQuery console.

### Visualize: Apps on Servers in Racks

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

### Visualize: Critical Maintenance Events

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (asset:hardware_assets)<-[m:MAINTAINED]-(event:maintenance_events)
WHERE asset.criticality_tier = 1
  AND event.severity = 'critical'
RETURN TO_JSON(asset) AS asset_node,
       TO_JSON(m) AS maintained_edge,
       TO_JSON(event) AS event_node
LIMIT 50;
```

### Visualize: Application Dependencies

```sql
GRAPH `data_center_topology.data_center_graph`
MATCH (app:applications)-[d:DEPENDS_ON]->(dep:applications)
WHERE app.criticality_tier = 1
RETURN TO_JSON(app) AS app_node,
       TO_JSON(d) AS depends_edge,
       TO_JSON(dep) AS dep_node
LIMIT 50;
```

---

[Back to README](README.md) | [Architecture](architecture.md) | [Full Guide](guide.md)
