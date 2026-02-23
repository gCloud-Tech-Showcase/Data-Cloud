# Spanner Graph Quick Reference

Copy-paste GQL queries for Spanner Studio.

## Basic Queries

### List All Node Types

```sql
-- Count nodes by type
SELECT 'locations' as node_type, COUNT(*) as count FROM locations
UNION ALL SELECT 'racks', COUNT(*) FROM racks
UNION ALL SELECT 'hardware_assets', COUNT(*) FROM hardware_assets
UNION ALL SELECT 'nic_interfaces', COUNT(*) FROM nic_interfaces
UNION ALL SELECT 'applications', COUNT(*) FROM applications
UNION ALL SELECT 'maintenance_events', COUNT(*) FROM maintenance_events
ORDER BY count DESC;
```

### Sample Applications

```sql
SELECT app_name, app_type, business_domain, criticality_tier, status
FROM applications
WHERE status = 'active'
LIMIT 10;
```

## Graph Traversal Queries

### Find Apps Deployed on Failed Servers

```sql
GRAPH DataCenterGraph
MATCH (app:applications)-[:DEPLOYED_ON]->(server:hardware_assets)
WHERE server.status = 'failed'
RETURN app.app_name, app.criticality_tier, server.hostname, server.status
ORDER BY app.criticality_tier;
```

### Trace App Dependencies (2 hops)

```sql
GRAPH DataCenterGraph
MATCH (app:applications)-[:DEPENDS_ON]->{1,2}(dep:applications)
WHERE app.app_code = 'FIN001'
RETURN app.app_name AS source_app,
       dep.app_name AS dependency,
       dep.app_type,
       dep.criticality_tier
ORDER BY dep.criticality_tier;
```

### Find All Apps in a Data Center

```sql
GRAPH DataCenterGraph
MATCH (dc:locations {location_type: 'data_center'})
      <-[:CHILD_OF]-(row:locations)
      <-[:LOCATED_IN]-(rack:racks)
      <-[:MOUNTED_IN]-(server:hardware_assets)
      <-[:DEPLOYED_ON]-(app:applications)
WHERE dc.name = 'US-West-1'
RETURN DISTINCT app.app_name, app.business_domain, app.criticality_tier
ORDER BY app.criticality_tier, app.app_name;
```

### Blast Radius: Rack Failure Impact

```sql
GRAPH DataCenterGraph
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
GRAPH DataCenterGraph
MATCH (asset:hardware_assets)<-[:MAINTAINED]-(event:maintenance_events)
WHERE asset.criticality_tier = 1
  AND event.severity = 'critical'
RETURN asset.hostname,
       asset.environment,
       event.event_type,
       event.started_at,
       event.downtime_minutes
ORDER BY event.started_at DESC
LIMIT 20;
```

### Location Hierarchy

```sql
GRAPH DataCenterGraph
MATCH (child:locations)-[:CHILD_OF]->(parent:locations)
RETURN child.name AS child_location,
       child.location_type AS child_type,
       parent.name AS parent_location,
       parent.location_type AS parent_type
ORDER BY parent.location_type, parent.name, child.name;
```

## Hybrid SQL + GQL

### Join Graph Results with SQL

```sql
-- Use GRAPH_TABLE to embed graph query in SQL
SELECT gt.app_name, gt.server_hostname, a.technology_stack, a.owner_team
FROM GRAPH_TABLE(
  DataCenterGraph
  MATCH (app:applications)-[:DEPLOYED_ON]->(server:hardware_assets)
  WHERE server.status = 'maintenance'
  RETURN app.app_name, server.hostname AS server_hostname, app.app_id
) AS gt
JOIN applications a ON gt.app_id = a.app_id
ORDER BY a.owner_team, gt.app_name;
```

---

[Back to README](README.md) | [Architecture](architecture.md) | [Full Guide](guide.md)
