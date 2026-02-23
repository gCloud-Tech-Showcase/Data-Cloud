# =============================================================================
# SPANNER GRAPH DEMO
# Property graph database for data center topology analysis
# =============================================================================

# -----------------------------------------------------------------------------
# Spanner Instance
# -----------------------------------------------------------------------------

resource "google_spanner_instance" "data_center_graph" {
  provider = google-beta
  count    = var.enable_spanner_graph_demo ? 1 : 0

  name             = "data-center-graph"
  config           = "regional-${var.region}"
  display_name     = "Data Center Topology Graph"
  processing_units = 100 # Minimum capacity
  edition          = "ENTERPRISE" # Required for Spanner Graph

  labels = {
    project = "data-cloud"
    purpose = "showcase"
    demo    = "spanner-graph"
  }

  depends_on = [google_project_service.spanner]
}

# -----------------------------------------------------------------------------
# Spanner Database with Schema DDL
# -----------------------------------------------------------------------------

resource "google_spanner_database" "topology" {
  count = var.enable_spanner_graph_demo ? 1 : 0

  instance = google_spanner_instance.data_center_graph[0].name
  name     = "topology"

  database_dialect     = "GOOGLE_STANDARD_SQL"
  deletion_protection  = false
  version_retention_period = "1h"

  ddl = [
    # =========================================================================
    # NODE TABLES
    # =========================================================================

    # Locations: regions, data centers, rows
    <<-EOT
      CREATE TABLE locations (
        location_id STRING(36) NOT NULL,
        location_type STRING(50),
        name STRING(255),
        parent_location_id STRING(36),
        geo_latitude FLOAT64,
        geo_longitude FLOAT64,
        address STRING(500),
        timezone STRING(50),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (location_id)
    EOT
    ,

    # Racks: physical rack units
    <<-EOT
      CREATE TABLE racks (
        rack_id STRING(36) NOT NULL,
        location_id STRING(36),
        rack_name STRING(100),
        rack_units INT64,
        power_capacity_kw FLOAT64,
        cooling_zone STRING(50),
        install_date DATE,
        status STRING(50),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (rack_id)
    EOT
    ,

    # Hardware assets: servers, switches, storage
    <<-EOT
      CREATE TABLE hardware_assets (
        asset_id STRING(36) NOT NULL,
        asset_type STRING(50),
        rack_id STRING(36),
        rack_position_start INT64,
        rack_position_end INT64,
        hostname STRING(100),
        serial_number STRING(50),
        asset_tag STRING(50),
        manufacturer STRING(100),
        model STRING(100),
        cpu_model STRING(100),
        cpu_cores INT64,
        ram_gb INT64,
        storage_tb INT64,
        purchase_date DATE,
        warranty_expiry DATE,
        end_of_life_date DATE,
        status STRING(50),
        environment STRING(50),
        criticality_tier INT64,
        owner_team STRING(100),
        cost_center STRING(50),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (asset_id)
    EOT
    ,

    # NIC interfaces: network interfaces and ports
    <<-EOT
      CREATE TABLE nic_interfaces (
        interface_id STRING(36) NOT NULL,
        asset_id STRING(36),
        interface_name STRING(50),
        mac_address STRING(20),
        ip_address STRING(50),
        subnet_mask STRING(20),
        vlan_id INT64,
        speed_gbps FLOAT64,
        interface_type STRING(50),
        status STRING(20),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (interface_id)
    EOT
    ,

    # Applications: deployed software
    <<-EOT
      CREATE TABLE applications (
        app_id STRING(36) NOT NULL,
        app_name STRING(255),
        app_code STRING(20),
        description STRING(500),
        app_type STRING(50),
        technology_stack STRING(100),
        business_domain STRING(50),
        criticality_tier INT64,
        data_classification STRING(50),
        owner_team STRING(100),
        technical_contact STRING(255),
        business_contact STRING(255),
        status STRING(50),
        go_live_date DATE,
        sunset_date DATE,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (app_id)
    EOT
    ,

    # Maintenance events: historical maintenance records
    <<-EOT
      CREATE TABLE maintenance_events (
        event_id STRING(36) NOT NULL,
        asset_id STRING(36),
        event_type STRING(50),
        severity STRING(20),
        description STRING(500),
        started_at TIMESTAMP,
        resolved_at TIMESTAMP,
        downtime_minutes INT64,
        root_cause STRING(50),
        technician STRING(100),
        ticket_number STRING(50),
        created_at TIMESTAMP
      ) PRIMARY KEY (event_id)
    EOT
    ,

    # =========================================================================
    # EDGE TABLES
    # =========================================================================

    # Network connections: physical network links
    <<-EOT
      CREATE TABLE network_connections (
        connection_id STRING(36) NOT NULL,
        source_interface_id STRING(36),
        target_interface_id STRING(36),
        connection_type STRING(50),
        bandwidth_gbps FLOAT64,
        cable_type STRING(50),
        status STRING(20),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (connection_id)
    EOT
    ,

    # App deployments: application-to-server mappings
    <<-EOT
      CREATE TABLE app_deployments (
        deployment_id STRING(36) NOT NULL,
        app_id STRING(36),
        asset_id STRING(36),
        deployment_role STRING(50),
        instance_count INT64,
        port_number INT64,
        resource_cpu_cores INT64,
        resource_ram_gb INT64,
        deployment_date DATE,
        status STRING(50),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (deployment_id)
    EOT
    ,

    # App dependencies: application-to-application dependencies
    <<-EOT
      CREATE TABLE app_dependencies (
        dependency_id STRING(36) NOT NULL,
        app_id STRING(36),
        depends_on_app_id STRING(36),
        dependency_type STRING(50),
        protocol STRING(20),
        port_number INT64,
        is_critical BOOL,
        data_flow_direction STRING(20),
        created_at TIMESTAMP,
        updated_at TIMESTAMP
      ) PRIMARY KEY (dependency_id)
    EOT
    ,

    # =========================================================================
    # PROPERTY GRAPH DEFINITION
    # =========================================================================

    <<-EOT
      CREATE OR REPLACE PROPERTY GRAPH DataCenterGraph
        NODE TABLES (
          locations,
          racks,
          hardware_assets,
          nic_interfaces,
          applications,
          maintenance_events
        )
        EDGE TABLES (
          -- Location hierarchy (parent-child)
          locations AS location_hierarchy
            SOURCE KEY (location_id) REFERENCES locations (location_id)
            DESTINATION KEY (parent_location_id) REFERENCES locations (location_id)
            LABEL CHILD_OF,

          -- Rack placement in location
          racks AS rack_placement
            SOURCE KEY (rack_id) REFERENCES racks (rack_id)
            DESTINATION KEY (location_id) REFERENCES locations (location_id)
            LABEL LOCATED_IN,

          -- Asset placement in rack
          hardware_assets AS asset_placement
            SOURCE KEY (asset_id) REFERENCES hardware_assets (asset_id)
            DESTINATION KEY (rack_id) REFERENCES racks (rack_id)
            LABEL MOUNTED_IN,

          -- NIC belongs to asset
          nic_interfaces AS nic_ownership
            SOURCE KEY (interface_id) REFERENCES nic_interfaces (interface_id)
            DESTINATION KEY (asset_id) REFERENCES hardware_assets (asset_id)
            LABEL BELONGS_TO,

          -- Network connections between NICs
          network_connections
            SOURCE KEY (source_interface_id) REFERENCES nic_interfaces (interface_id)
            DESTINATION KEY (target_interface_id) REFERENCES nic_interfaces (interface_id)
            LABEL CONNECTS_TO,

          -- App deployments on assets
          app_deployments
            SOURCE KEY (app_id) REFERENCES applications (app_id)
            DESTINATION KEY (asset_id) REFERENCES hardware_assets (asset_id)
            LABEL DEPLOYED_ON,

          -- App dependencies
          app_dependencies
            SOURCE KEY (app_id) REFERENCES applications (app_id)
            DESTINATION KEY (depends_on_app_id) REFERENCES applications (app_id)
            LABEL DEPENDS_ON,

          -- Maintenance events on assets
          maintenance_events AS maintenance_history
            SOURCE KEY (event_id) REFERENCES maintenance_events (event_id)
            DESTINATION KEY (asset_id) REFERENCES hardware_assets (asset_id)
            LABEL MAINTAINED
        )
    EOT
  ]

  depends_on = [google_spanner_instance.data_center_graph]
}
