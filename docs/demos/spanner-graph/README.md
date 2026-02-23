# Spanner Graph: Data Center Topology

Analyze data center infrastructure using graph queries for impact analysis, dependency tracing, and network topology exploration.

## What You'll Build

1. **Spanner Graph Database** - Property graph over relational tables
2. **GQL Queries** - Path traversals, impact analysis, dependency mapping
3. **Unified Data Model** - Same data accessible via SQL and GQL

## Technologies

| Service | Purpose |
|---------|---------|
| Cloud Spanner | Globally-consistent database with graph support |
| Spanner Graph | Property graph layer over Spanner tables |
| GQL | ISO-standard graph query language |

## Data Model

Reuses the data center topology from the Vertica Ingestion demo:

| Node Type | Examples |
|-----------|----------|
| locations | Regions, data centers, rows |
| racks | Physical rack units |
| hardware_assets | Servers, switches, storage |
| nic_interfaces | Network interfaces |
| applications | Deployed software |
| maintenance_events | Historical maintenance records |

| Edge Type | Relationship |
|-----------|--------------|
| CHILD_OF | Location hierarchy |
| LOCATED_IN | Rack placement |
| MOUNTED_IN | Server in rack |
| BELONGS_TO | NIC on asset |
| CONNECTS_TO | Network topology |
| DEPLOYED_ON | App on server |
| DEPENDS_ON | App dependencies |
| MAINTAINED | Maintenance history |

## Results

- **Graph traversals** express multi-hop queries naturally
- **Impact analysis** in single queries vs. multiple JOINs
- **ISO GQL** syntax familiar to graph database users

## Guides

- [Quick Reference](quick.md) - GQL queries with outputs
- [Architecture](architecture.md) - Graph schema and data model
- [Full Guide](guide.md) - Step-by-step walkthrough

## Standalone

This demo is independent from other demos. Requires `enable_spanner_graph_demo = true` in Terraform.

**Cost warning:** Spanner incurs costs while running. Destroy when not in use. See [Spanner pricing](https://cloud.google.com/spanner/pricing) for current rates.
