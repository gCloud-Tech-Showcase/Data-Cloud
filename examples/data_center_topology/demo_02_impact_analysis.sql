-- =============================================================================
-- DEMO 02: Infrastructure Impact Analysis
-- =============================================================================
-- These queries demonstrate impact analysis scenarios:
-- "What happens if X fails?" - Critical for change management and incident response
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Applications Affected by Server Failure
-- Given a server hostname, find all applications that would be impacted
-- -----------------------------------------------------------------------------
WITH failed_server AS (
  SELECT asset_id, hostname
  FROM `data_center_topology.hardware_assets`
  WHERE hostname = 'srv-001-us-central1-dc1'  -- Replace with actual hostname
)
SELECT
  a.app_name,
  a.app_type,
  a.criticality_tier,
  a.owner_team,
  a.sla_uptime_percent,
  d.deployment_role,
  -- Check if there are other healthy deployments
  EXISTS(
    SELECT 1
    FROM `data_center_topology.app_deployments` d2
    JOIN `data_center_topology.hardware_assets` ha2 ON d2.asset_id = ha2.asset_id
    WHERE d2.app_id = a.app_id
      AND d2.deployment_id != d.deployment_id
      AND ha2.status = 'ACTIVE'
      AND d2.status = 'RUNNING'
  ) AS has_redundancy
FROM failed_server fs
JOIN `data_center_topology.app_deployments` d ON fs.asset_id = d.asset_id
JOIN `data_center_topology.applications` a ON d.app_id = a.app_id
WHERE d.status = 'RUNNING'
ORDER BY a.criticality_tier, a.app_name;

-- -----------------------------------------------------------------------------
-- 2. Rack Power Failure Impact
-- Find all applications affected if a rack loses power
-- -----------------------------------------------------------------------------
WITH rack_failure AS (
  SELECT rack_id, rack_name
  FROM `data_center_topology.racks`
  WHERE rack_name = 'RACK-A01'  -- Replace with actual rack name
)
SELECT
  rf.rack_name,
  COUNT(DISTINCT ha.asset_id) AS affected_servers,
  COUNT(DISTINCT d.app_id) AS affected_applications,
  STRING_AGG(DISTINCT a.app_name, ', ' ORDER BY a.app_name) AS application_list,
  COUNTIF(a.criticality_tier = 'TIER_1') AS tier1_apps_affected
FROM rack_failure rf
JOIN `data_center_topology.hardware_assets` ha ON rf.rack_id = ha.rack_id
JOIN `data_center_topology.app_deployments` d ON ha.asset_id = d.asset_id
JOIN `data_center_topology.applications` a ON d.app_id = a.app_id
WHERE ha.status = 'ACTIVE'
  AND d.status = 'RUNNING'
GROUP BY rf.rack_name;

-- -----------------------------------------------------------------------------
-- 3. Data Center Evacuation Impact
-- Full impact analysis for data center maintenance or disaster
-- -----------------------------------------------------------------------------
WITH dc_assets AS (
  SELECT
    dc.name AS data_center_name,
    ha.asset_id,
    ha.hostname,
    ha.asset_type
  FROM `data_center_topology.locations` dc
  JOIN `data_center_topology.locations` floor ON floor.parent_location_id = dc.location_id
  JOIN `data_center_topology.locations` room ON room.parent_location_id = floor.location_id
  JOIN `data_center_topology.racks` r ON r.location_id = room.location_id
  JOIN `data_center_topology.hardware_assets` ha ON ha.rack_id = r.rack_id
  WHERE dc.location_type = 'DATA_CENTER'
    AND dc.name = 'us-central1-dc1'  -- Replace with actual DC name
    AND ha.status = 'ACTIVE'
)
SELECT
  dca.data_center_name,
  a.criticality_tier,
  COUNT(DISTINCT a.app_id) AS applications_affected,
  COUNT(DISTINCT dca.asset_id) AS servers_in_dc,
  -- Check for apps with no deployment outside this DC
  COUNT(DISTINCT CASE
    WHEN NOT EXISTS (
      SELECT 1
      FROM `data_center_topology.app_deployments` d2
      JOIN `data_center_topology.hardware_assets` ha2 ON d2.asset_id = ha2.asset_id
      WHERE d2.app_id = a.app_id
        AND ha2.asset_id NOT IN (SELECT asset_id FROM dc_assets)
        AND d2.status = 'RUNNING'
    ) THEN a.app_id
  END) AS apps_with_no_redundancy
FROM dc_assets dca
JOIN `data_center_topology.app_deployments` d ON dca.asset_id = d.asset_id
JOIN `data_center_topology.applications` a ON d.app_id = a.app_id
WHERE d.status = 'RUNNING'
GROUP BY dca.data_center_name, a.criticality_tier
ORDER BY a.criticality_tier;

-- -----------------------------------------------------------------------------
-- 4. Warranty Expiration Risk Assessment
-- Find critical applications running on servers with expiring warranties
-- -----------------------------------------------------------------------------
SELECT
  ha.hostname,
  ha.model,
  ha.warranty_expiry,
  DATE_DIFF(ha.warranty_expiry, CURRENT_DATE(), DAY) AS days_until_expiry,
  a.app_name,
  a.criticality_tier,
  a.sla_uptime_percent
FROM `data_center_topology.hardware_assets` ha
JOIN `data_center_topology.app_deployments` d ON ha.asset_id = d.asset_id
JOIN `data_center_topology.applications` a ON d.app_id = a.app_id
WHERE ha.warranty_expiry <= DATE_ADD(CURRENT_DATE(), INTERVAL 90 DAY)
  AND ha.status = 'ACTIVE'
  AND a.criticality_tier = 'TIER_1'
ORDER BY ha.warranty_expiry, a.app_name;

-- -----------------------------------------------------------------------------
-- 5. Single Points of Failure Detection
-- Find TIER_1 applications with only one active deployment
-- -----------------------------------------------------------------------------
SELECT
  a.app_name,
  a.app_type,
  a.owner_team,
  a.sla_uptime_percent,
  COUNT(d.deployment_id) AS deployment_count,
  STRING_AGG(ha.hostname, ', ') AS deployed_on
FROM `data_center_topology.applications` a
JOIN `data_center_topology.app_deployments` d ON a.app_id = d.app_id
JOIN `data_center_topology.hardware_assets` ha ON d.asset_id = ha.asset_id
WHERE a.criticality_tier = 'TIER_1'
  AND d.status = 'RUNNING'
  AND ha.status = 'ACTIVE'
GROUP BY a.app_id, a.app_name, a.app_type, a.owner_team, a.sla_uptime_percent
HAVING COUNT(d.deployment_id) = 1
ORDER BY a.sla_uptime_percent DESC;
