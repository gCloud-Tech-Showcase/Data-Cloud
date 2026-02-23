# Vertica-to-BigQuery Ingestion

Migrate data from a Vertica warehouse to BigQuery using Dataproc and Spark.

## What You'll Build

Demonstrate a complete data migration pipeline from legacy Vertica to BigQuery:
1. **Vertica CE VM** — Single-node Community Edition running in Docker
2. **PySpark Ingestion** — JDBC-based extraction with Spark on Dataproc
3. **Ephemeral Clusters** — Workflow template spins up cluster, runs job, tears down
4. **Scheduled Sync** — Cloud Scheduler for automated weekly ingestion (paused by default)

## Technologies

| Service | Purpose |
|---------|---------|
| Vertica CE | Source database (Docker on Compute Engine) |
| Dataproc | Managed Spark cluster for ETL |
| PySpark + JDBC | Data extraction and transformation |
| BigQuery | Target data warehouse |
| Cloud Scheduler | Automated pipeline triggers |
| IAP | Secure SSH access (no external IPs) |

## Data Model

Data center hardware topology with ~27K rows across 9 tables:

| Category | Tables |
|----------|--------|
| **Entities** | locations, racks, hardware_assets, nic_interfaces, applications |
| **Relationships** | network_connections, app_deployments, app_dependencies, maintenance_events |

## Results

- **Full table migration** from Vertica to BigQuery
- **Secure by default** — internal IPs only, IAP for SSH access
- **Ephemeral compute** — Dataproc cluster exists only during job execution
- **Reproducible** — Infrastructure as Code with Terraform

## Guides

- [Quick Reference](quick.md) — Commands with expected outputs
- [Architecture](architecture.md) — Pipeline diagram and data flow
- [Full Guide](guide.md) — Step-by-step walkthrough

## Standalone

This demo is independent from other demos. Requires `enable_vertica_demo = true` in Terraform.

**Cost warning:** Vertica VM runs continuously when enabled (~$0.13/hr for e2-standard-4). Destroy when not in use.
