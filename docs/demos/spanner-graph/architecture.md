# Spanner Graph Architecture

## Overview

This demo uses Spanner Graph to model data center infrastructure as a property graph, enabling intuitive queries for impact analysis and dependency tracing.

## Data Flow

```mermaid
graph LR
    subgraph "Data Generator"
        GEN[generate_datacenter_topology.py<br/>--target spanner]
    end

    subgraph "Generated Data"
        NODES[6 Node Tables<br/>~25K rows]
        EDGES[3 Edge Tables<br/>~2K rows]
    end

    subgraph "Spanner Database: topology"
        TABLES[Relational Tables<br/>SQL access]
        GRAPH[Property Graph<br/>DataCenterGraph<br/>GQL access]
    end

    GEN --> NODES
    GEN --> EDGES
    NODES -->|batch mutations| TABLES
    EDGES -->|batch mutations| TABLES
    TABLES -.->|mapped via DDL| GRAPH
```

## Graph Schema

```mermaid
graph TB
    subgraph "Location Hierarchy"
        REGION[locations<br/>region]
        DC[locations<br/>datacenter]
        ROW[locations<br/>row]
    end

    subgraph "Physical Infrastructure"
        RACK[racks]
        SERVER[hardware_assets<br/>server]
        SWITCH[hardware_assets<br/>switch]
        STORAGE[hardware_assets<br/>storage]
        NIC[nic_interfaces]
    end

    subgraph "Applications"
        APP[applications]
        MAINT[maintenance_events]
    end

    REGION -->|CHILD_OF| DC
    DC -->|CHILD_OF| ROW
    ROW -->|LOCATED_IN| RACK
    RACK -->|MOUNTED_IN| SERVER
    RACK -->|MOUNTED_IN| SWITCH
    RACK -->|MOUNTED_IN| STORAGE
    SERVER -->|BELONGS_TO| NIC
    NIC <-->|CONNECTS_TO| NIC
    APP -->|DEPLOYED_ON| SERVER
    APP <-->|DEPENDS_ON| APP
    MAINT -->|MAINTAINED| SERVER
```

## Node Tables

| Table | Primary Key | Description | Sample Size |
|-------|-------------|-------------|-------------|
| `locations` | `location_id` | Hierarchical locations (regions, DCs, rows) | ~50 |
| `racks` | `rack_id` | Physical rack units | ~500 |
| `hardware_assets` | `asset_id` | Servers, switches, storage | ~4,700 |
| `nic_interfaces` | `interface_id` | Network interfaces/ports | ~19,000 |
| `applications` | `app_id` | Deployed software | ~200 |
| `maintenance_events` | `event_id` | Historical maintenance | ~1,500 |

## Graph Edge Definitions

Some node tables double as edges via their foreign keys. The graph DDL defines 8 edge relationships:

| Table | Source Column | Destination Column | Label | Description |
|-------|--------------|-------------------|-------|-------------|
| `locations` | `location_id` | `parent_location_id` | CHILD_OF | Location hierarchy |
| `racks` | `rack_id` | `location_id` | LOCATED_IN | Rack placement |
| `hardware_assets` | `asset_id` | `rack_id` | MOUNTED_IN | Asset in rack |
| `nic_interfaces` | `interface_id` | `asset_id` | BELONGS_TO | NIC on asset |
| `network_connections` | `source_interface_id` | `target_interface_id` | CONNECTS_TO | Network links |
| `app_deployments` | `app_id` | `asset_id` | DEPLOYED_ON | App on server |
| `app_dependencies` | `app_id` | `depends_on_app_id` | DEPENDS_ON | App dependencies |
| `maintenance_events` | `event_id` | `asset_id` | MAINTAINED | Maintenance history |

## Infrastructure Components

| Component | Resource | Purpose |
|-----------|----------|---------|
| Spanner Instance | `data-center-graph` | Regional instance (100 PU minimum) |
| Spanner Database | `topology` | Contains tables and property graph |
| Property Graph | `DataCenterGraph` | Graph view over relational tables |

## Key Files

| File | Purpose |
|------|---------|
| `infra/spanner_graph.tf` | Terraform for Spanner instance, database, DDL |
| `infra/variables.tf` | Feature flag `enable_spanner_graph_demo` |
| `scripts/generate_datacenter_topology.py` | Data generator with `--target spanner` |

---

[Back to README](README.md) | [Quick Reference](quick.md) | [Full Guide](guide.md)
