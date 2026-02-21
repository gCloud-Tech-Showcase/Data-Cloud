-- =============================================================================
-- DEMO 01: Basic Topology Queries
-- =============================================================================
-- These queries demonstrate the foundational data model for the data center
-- topology. Run these first to understand the schema before moving to graph
-- traversal queries.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Location Hierarchy Overview
-- Shows the hierarchical structure: Region -> Data Center -> Floor -> Room
-- -----------------------------------------------------------------------------
SELECT
  location_type,
  COUNT(*) AS count,
  COUNT(DISTINCT parent_location_id) AS parent_locations
FROM `data_center_topology.locations`
GROUP BY location_type
ORDER BY
  CASE location_type
    WHEN 'REGION' THEN 1
    WHEN 'DATA_CENTER' THEN 2
    WHEN 'FLOOR' THEN 3
    WHEN 'ROOM' THEN 4
  END;

-- -----------------------------------------------------------------------------
-- 2. Hardware Asset Distribution by Type
-- Overview of infrastructure components across the environment
-- -----------------------------------------------------------------------------
SELECT
  asset_type,
  status,
  criticality_tier,
  COUNT(*) AS asset_count,
  SUM(cpu_cores) AS total_cpu_cores,
  SUM(ram_gb) AS total_ram_gb,
  SUM(storage_tb) AS total_storage_tb
FROM `data_center_topology.hardware_assets`
GROUP BY asset_type, status, criticality_tier
ORDER BY asset_type, status, criticality_tier;

-- -----------------------------------------------------------------------------
-- 3. Application Portfolio Summary
-- Business applications deployed across the infrastructure
-- -----------------------------------------------------------------------------
SELECT
  app_type,
  criticality_tier,
  COUNT(*) AS app_count,
  ROUND(AVG(sla_uptime_percent), 2) AS avg_sla_requirement,
  COUNT(DISTINCT owner_team) AS teams_involved
FROM `data_center_topology.applications`
GROUP BY app_type, criticality_tier
ORDER BY
  CASE criticality_tier
    WHEN 'TIER_1' THEN 1
    WHEN 'TIER_2' THEN 2
    WHEN 'TIER_3' THEN 3
  END,
  app_type;

-- -----------------------------------------------------------------------------
-- 4. Rack Capacity Utilization
-- Shows how many assets are deployed per rack and power status
-- -----------------------------------------------------------------------------
SELECT
  r.rack_name,
  r.status AS rack_status,
  r.power_capacity_kw,
  COUNT(ha.asset_id) AS assets_deployed,
  COUNTIF(ha.asset_type = 'SERVER') AS servers,
  COUNTIF(ha.asset_type = 'SWITCH') AS switches,
  COUNTIF(ha.asset_type = 'STORAGE') AS storage_arrays
FROM `data_center_topology.racks` r
LEFT JOIN `data_center_topology.hardware_assets` ha ON r.rack_id = ha.rack_id
GROUP BY r.rack_id, r.rack_name, r.status, r.power_capacity_kw
ORDER BY assets_deployed DESC
LIMIT 20;

-- -----------------------------------------------------------------------------
-- 5. Network Connectivity Overview
-- Shows the network connection distribution
-- -----------------------------------------------------------------------------
SELECT
  connection_type,
  status,
  COUNT(*) AS connection_count,
  ROUND(AVG(bandwidth_gbps), 1) AS avg_bandwidth_gbps,
  ROUND(AVG(latency_ms), 2) AS avg_latency_ms
FROM `data_center_topology.network_connections`
GROUP BY connection_type, status
ORDER BY connection_type, status;
