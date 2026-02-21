-- =============================================================================
-- DEMO 04: Network Topology Analysis
-- =============================================================================
-- These queries demonstrate network infrastructure analysis:
-- Connection mapping, bandwidth analysis, and network segmentation.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Network Connection Map
-- Show how servers connect to switches and to each other
-- -----------------------------------------------------------------------------
SELECT
  src_asset.hostname AS source_host,
  src_asset.asset_type AS source_type,
  src_if.interface_name AS source_interface,
  src_if.ip_address AS source_ip,
  nc.connection_type,
  nc.bandwidth_gbps,
  nc.status AS connection_status,
  tgt_if.ip_address AS target_ip,
  tgt_if.interface_name AS target_interface,
  tgt_asset.hostname AS target_host,
  tgt_asset.asset_type AS target_type
FROM `data_center_topology.network_connections` nc
JOIN `data_center_topology.nic_interfaces` src_if ON nc.source_interface_id = src_if.interface_id
JOIN `data_center_topology.nic_interfaces` tgt_if ON nc.target_interface_id = tgt_if.interface_id
JOIN `data_center_topology.hardware_assets` src_asset ON src_if.asset_id = src_asset.asset_id
JOIN `data_center_topology.hardware_assets` tgt_asset ON tgt_if.asset_id = tgt_asset.asset_id
WHERE nc.status = 'ACTIVE'
ORDER BY src_asset.hostname, src_if.interface_name
LIMIT 100;

-- -----------------------------------------------------------------------------
-- 2. Switch Port Utilization
-- Show how many connections each network switch handles
-- -----------------------------------------------------------------------------
SELECT
  sw.hostname AS switch_name,
  sw.model,
  r.rack_name,
  COUNT(DISTINCT ni.interface_id) AS total_interfaces,
  COUNT(DISTINCT nc.connection_id) AS active_connections,
  ROUND(COUNT(DISTINCT nc.connection_id) * 100.0 / NULLIF(COUNT(DISTINCT ni.interface_id), 0), 1) AS utilization_pct,
  SUM(nc.bandwidth_gbps) AS total_bandwidth_gbps
FROM `data_center_topology.hardware_assets` sw
JOIN `data_center_topology.racks` r ON sw.rack_id = r.rack_id
LEFT JOIN `data_center_topology.nic_interfaces` ni ON sw.asset_id = ni.asset_id
LEFT JOIN `data_center_topology.network_connections` nc ON ni.interface_id = nc.source_interface_id
WHERE sw.asset_type = 'SWITCH'
  AND sw.status = 'ACTIVE'
GROUP BY sw.asset_id, sw.hostname, sw.model, r.rack_name
ORDER BY utilization_pct DESC;

-- -----------------------------------------------------------------------------
-- 3. Network Path Between Two Servers (2-hop via switch)
-- Find how two servers are connected through the network
-- -----------------------------------------------------------------------------
WITH server_connections AS (
  SELECT
    ha.hostname,
    ha.asset_id,
    ni.interface_id,
    ni.ip_address,
    nc.connection_id,
    CASE
      WHEN nc.source_interface_id = ni.interface_id THEN nc.target_interface_id
      ELSE nc.source_interface_id
    END AS connected_to
  FROM `data_center_topology.hardware_assets` ha
  JOIN `data_center_topology.nic_interfaces` ni ON ha.asset_id = ni.asset_id
  JOIN `data_center_topology.network_connections` nc
    ON ni.interface_id = nc.source_interface_id
    OR ni.interface_id = nc.target_interface_id
  WHERE nc.status = 'ACTIVE'
)
SELECT
  s1.hostname AS server_a,
  s1.ip_address AS server_a_ip,
  sw.hostname AS via_switch,
  s2.ip_address AS server_b_ip,
  s2.hostname AS server_b
FROM server_connections s1
-- Server A connects to Switch
JOIN `data_center_topology.nic_interfaces` sw_if1 ON s1.connected_to = sw_if1.interface_id
JOIN `data_center_topology.hardware_assets` sw ON sw_if1.asset_id = sw.asset_id AND sw.asset_type = 'SWITCH'
-- Switch connects to Server B
JOIN `data_center_topology.nic_interfaces` sw_if2 ON sw.asset_id = sw_if2.asset_id AND sw_if2.interface_id != sw_if1.interface_id
JOIN server_connections s2 ON sw_if2.interface_id = s2.connected_to
WHERE s1.hostname = 'srv-001-us-central1-dc1'  -- Replace with actual hostname
  AND s2.hostname != s1.hostname
LIMIT 20;

-- -----------------------------------------------------------------------------
-- 4. Bandwidth Bottleneck Analysis
-- Find connections with lower bandwidth connecting to high-bandwidth servers
-- -----------------------------------------------------------------------------
WITH server_bandwidth AS (
  SELECT
    ha.asset_id,
    ha.hostname,
    ha.cpu_cores,
    -- Expected bandwidth based on server size
    CASE
      WHEN ha.cpu_cores >= 64 THEN 100  -- Large servers expect 100G
      WHEN ha.cpu_cores >= 32 THEN 50   -- Medium servers expect 50G
      WHEN ha.cpu_cores >= 16 THEN 25   -- Small servers expect 25G
      ELSE 10
    END AS expected_bandwidth_gbps
  FROM `data_center_topology.hardware_assets` ha
  WHERE ha.asset_type = 'SERVER'
    AND ha.status = 'ACTIVE'
)
SELECT
  sb.hostname,
  sb.cpu_cores,
  sb.expected_bandwidth_gbps,
  MAX(nc.bandwidth_gbps) AS actual_max_bandwidth_gbps,
  CASE
    WHEN MAX(nc.bandwidth_gbps) < sb.expected_bandwidth_gbps THEN 'BOTTLENECK'
    ELSE 'OK'
  END AS status
FROM server_bandwidth sb
JOIN `data_center_topology.nic_interfaces` ni ON sb.asset_id = ni.asset_id
JOIN `data_center_topology.network_connections` nc
  ON ni.interface_id = nc.source_interface_id
  OR ni.interface_id = nc.target_interface_id
WHERE nc.status = 'ACTIVE'
GROUP BY sb.asset_id, sb.hostname, sb.cpu_cores, sb.expected_bandwidth_gbps
HAVING MAX(nc.bandwidth_gbps) < sb.expected_bandwidth_gbps
ORDER BY sb.expected_bandwidth_gbps - MAX(nc.bandwidth_gbps) DESC;

-- -----------------------------------------------------------------------------
-- 5. VLAN Segmentation Analysis
-- Show application distribution across VLANs
-- -----------------------------------------------------------------------------
SELECT
  ni.vlan_id,
  COUNT(DISTINCT ha.asset_id) AS server_count,
  COUNT(DISTINCT a.app_id) AS application_count,
  STRING_AGG(DISTINCT a.criticality_tier, ', ') AS criticality_tiers,
  STRING_AGG(DISTINCT a.app_type, ', ') AS app_types
FROM `data_center_topology.nic_interfaces` ni
JOIN `data_center_topology.hardware_assets` ha ON ni.asset_id = ha.asset_id
JOIN `data_center_topology.app_deployments` ad ON ha.asset_id = ad.asset_id
JOIN `data_center_topology.applications` a ON ad.app_id = a.app_id
WHERE ha.asset_type = 'SERVER'
  AND ha.status = 'ACTIVE'
  AND ad.status = 'RUNNING'
  AND ni.vlan_id IS NOT NULL
GROUP BY ni.vlan_id
ORDER BY application_count DESC;
