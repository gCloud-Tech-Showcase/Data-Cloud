# Vertica-to-BigQuery Ingestion Guide

Migrate data from a Vertica warehouse to BigQuery using Dataproc and Spark.

---

## The Use Case

Organizations running legacy Vertica warehouses need to migrate to BigQuery. This demo shows:
- **JDBC-based extraction** — Standard approach compatible with any Vertica version
- **Ephemeral compute** — Dataproc cluster exists only during job execution
- **Scheduled sync** — Automated weekly ingestion with Cloud Scheduler
- **Secure by default** — No external IPs, IAP for SSH access

---

## Prerequisites

1. Deploy infrastructure with Vertica demo enabled:

```bash
cd infra
terraform apply -var="enable_vertica_demo=true"
```

2. Wait for Vertica VM to start (~3-5 minutes for Docker container initialization)

---

## Step 1: Verify Vertica is Running

SSH to the Vertica VM via IAP tunnel:

```bash
gcloud compute ssh vertica-demo --zone=us-central1-a --tunnel-through-iap
```

Check the Vertica container status:

```bash
sudo docker ps
sudo docker logs vertica-ce
```

Verify Vertica is responding:

```bash
sudo docker exec vertica-ce /opt/vertica/bin/vsql -U dbadmin -d demo -c 'SELECT version()'
```

**Expected output:**
```
                               version
----------------------------------------------------------------------
 Vertica Analytic Database v9.2.0-7
```

---

## Step 2: Load Sample Data to Vertica

Open an IAP tunnel for local Vertica access (in a separate terminal):

```bash
gcloud compute ssh vertica-demo --zone=us-central1-a --tunnel-through-iap -- -L 5433:localhost:5433
```

In your original terminal, activate the Python environment and load data:

```bash
cd scripts
source .venv/bin/activate

export VERTICA_HOST=localhost
export VERTICA_PORT=5433
export VERTICA_USER=dbadmin
export VERTICA_PASSWORD=""
export VERTICA_DATABASE=demo

python generate_datacenter_topology.py --project gcloud-tech-showcase --target vertica
```

**Expected output:**
```
Loading data to Vertica at localhost:5433/demo
Created table: locations (6 rows)
Created table: racks (20 rows)
Created table: hardware_assets (200 rows)
...
Successfully loaded 9 tables to Vertica
```

---

## Step 3: Run the Dataproc Ingestion

Trigger the workflow template via Cloud Console or CLI:

**Console:**
1. Go to Dataproc > Workflow Templates
2. Select `vertica-to-bigquery`
3. Click **Run**

**CLI:**
```bash
gcloud dataproc workflow-templates instantiate vertica-to-bigquery --region=us-central1
```

The workflow will:
1. Create an ephemeral Dataproc cluster (internal IPs only)
2. Submit the PySpark job
3. Extract all 9 tables from Vertica via JDBC
4. Write each table to BigQuery (WRITE_TRUNCATE mode)
5. Delete the cluster

**Monitor progress:**
```bash
gcloud dataproc operations list --region=us-central1 --filter="labels.goog-dataproc-workflow-template-id=vertica-to-bigquery"
```

---

## Step 4: Verify Data in BigQuery

Check that all tables were created:

```bash
bq ls data_center_topology
```

**Expected output:**
```
         tableId          Type
 ----------------------- -------
  app_dependencies        TABLE
  app_deployments         TABLE
  applications            TABLE
  hardware_assets         TABLE
  locations               TABLE
  maintenance_events      TABLE
  network_connections     TABLE
  nic_interfaces          TABLE
  racks                   TABLE
```

Query the data:

```sql
SELECT location_type, COUNT(*) as count
FROM `data_center_topology.locations`
GROUP BY location_type
ORDER BY count DESC;
```

---

## Step 5: Optional - Enable Scheduled Sync

The Cloud Scheduler job is created but paused by default. To enable weekly sync:

```bash
gcloud scheduler jobs resume vertica-weekly-sync --location=us-central1
```

To pause it again:

```bash
gcloud scheduler jobs pause vertica-weekly-sync --location=us-central1
```

---

## Cleanup

Destroy the Vertica VM to avoid ongoing costs:

```bash
cd infra
terraform destroy -var="enable_vertica_demo=true" -target=google_compute_instance.vertica
```

Or destroy all Vertica-related resources:

```bash
terraform destroy -var="enable_vertica_demo=true"
```

---

## Key Takeaways

| Capability | Technology | Business Value |
|------------|------------|----------------|
| JDBC extraction | Standard driver | Works with any Vertica version |
| Ephemeral clusters | Dataproc workflow templates | Pay only for compute during ingestion |
| Automated sync | Cloud Scheduler | Hands-off weekly refresh |
| Secure by default | Internal IPs + IAP | No public exposure |

---

## Troubleshooting

### Dataproc cluster creation timeout

**Symptom:** Workflow fails with "Cluster creation timed out"

**Cause:** Missing firewall rules for internal communication

**Solution:** Verify `allow-dataproc-internal` firewall rule exists:
```bash
gcloud compute firewall-rules describe allow-dataproc-internal
```

### Vertica connection refused

**Symptom:** PySpark job fails with "Connection refused"

**Cause:** Vertica container not running or not ready

**Solution:** SSH to VM and check container status:
```bash
sudo docker ps
sudo docker logs vertica-ce
```

### Permission denied on BigQuery write

**Symptom:** Job fails with "Access Denied" on BigQuery

**Cause:** Dataproc service account lacks BigQuery permissions

**Solution:** Verify IAM bindings in Terraform output

---

## Navigation

[← Demos](../README.md) | [Quick Reference](quick.md) | [Architecture](architecture.md)
