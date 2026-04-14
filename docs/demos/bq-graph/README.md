# BQ Graph: Data Center Topology

Analyze data center infrastructure using BigQuery property graph and GQL — the same ISO-standard graph query language used by Spanner Graph, running on BigQuery's serverless analytics engine.

## What You'll Build

1. **BigQuery Property Graph** - Graph overlay on relational tables (zero data duplication)
2. **GQL Queries** - Path traversals, impact analysis, dependency mapping
3. **BQ-Specific Features** - GRAPH_TABLE, ANY SHORTEST, NEXT chaining

## Technologies

| Service | Purpose |
|---------|---------|
| BigQuery | Serverless data warehouse with graph support |
| BQ Graph | Property graph layer over BigQuery tables |
| GQL | ISO-standard graph query language |
| Enterprise Reservation | Dedicated capacity for graph queries |

## Data Model

Same data center topology as the [Spanner Graph](../spanner-graph/) demo:

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

- **Same GQL syntax** as Spanner Graph — write once, run on either engine
- **BQ-exclusive features** like GRAPH_TABLE hybrid queries, ANY SHORTEST, NEXT chaining
- **5-JOIN SQL queries** reduced to single-line graph patterns

## Guides

- [Quick Reference](quick.md) - GQL queries with outputs
- [Architecture](architecture.md) - Graph schema and data model
- [Full Guide](guide.md) - Step-by-step walkthrough

## What's Next

This demo uses the same data and GQL syntax as [Spanner Graph](../spanner-graph/). Compare them side-by-side: use Spanner for real-time operational queries, BigQuery for deep analytics at scale.

**Cost note:** The Enterprise reservation uses autoscale (0 baseline). Destroy when not in use: `terraform apply -var="enable_bq_graph_demo=false"`.
