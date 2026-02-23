# Vertica Ingestion - Quick Reference

Commands and expected outputs for the Vertica-to-BigQuery ingestion demo.

---

## 1. Deploy Infrastructure

```bash
cd infra
terraform apply -var="enable_vertica_demo=true"
```

**Key outputs:**
```
vertica_vm_internal_ip = "10.0.0.x"
dataproc_workflow_template = "vertica-to-bigquery"
scheduler_job_name = "vertica-to-bigquery-weekly"
```

---

## 2. SSH to Vertica VM

```bash
gcloud compute ssh vertica-demo --zone=us-central1-a --tunnel-through-iap
```

---

## 3. Check Vertica Status

```bash
sudo docker ps
```

**Output:**
```
CONTAINER ID   IMAGE                         STATUS          NAMES
abc123...      jbfavre/vertica:9.2.0-7...    Up 10 minutes   vertica-ce
```

```bash
sudo docker exec vertica-ce /opt/vertica/bin/vsql -U dbadmin -d demo -c 'SELECT version()'
```

**Output:**
```
Vertica Analytic Database v9.2.0-7
```

---

## 4. IAP Tunnel for Local Access

```bash
gcloud compute ssh vertica-demo --zone=us-central1-a --tunnel-through-iap -- -L 5433:localhost:5433
```

Keep this terminal open while loading data.

---

## 5. Load Data to Vertica

```bash
cd scripts
source .venv/bin/activate

export VERTICA_HOST=localhost VERTICA_PORT=5433 VERTICA_USER=dbadmin VERTICA_PASSWORD="" VERTICA_DATABASE=demo

python generate_datacenter_topology.py --project gcloud-tech-showcase --target vertica
```

**Output:**
```
Loading data to Vertica at localhost:5433/demo
Created table: locations (6 rows)
Created table: racks (20 rows)
...
Successfully loaded 9 tables to Vertica
```

---

## 6. Trigger Dataproc Ingestion

```bash
gcloud dataproc workflow-templates instantiate vertica-to-bigquery --region=us-central1
```

**Output:**
```
Waiting for workflow template instantiation to complete...
WorkflowTemplate [vertica-to-bigquery] instantiated.
```

---

## 7. Monitor Workflow

```bash
gcloud dataproc operations list --region=us-central1 --filter="labels.goog-dataproc-workflow-template-id=vertica-to-bigquery" --limit=1
```

**Output:**
```
NAME                                      DONE
projects/.../operations/abc123...          True
```

---

## 8. Verify BigQuery Tables

```bash
bq ls data_center_topology
```

**Output:**
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

---

## 9. Query Sample Data

```sql
-- Location hierarchy
SELECT location_type, COUNT(*) as count
FROM `data_center_topology.locations`
GROUP BY location_type;
```

**Output:**
```
location_type  | count
---------------|------
REGION         | 1
DATA_CENTER    | 1
FLOOR          | 2
ROOM           | 4
```

```sql
-- Hardware asset summary
SELECT asset_type, status, COUNT(*) as count
FROM `data_center_topology.hardware_assets`
GROUP BY asset_type, status
ORDER BY count DESC;
```

**Output:**
```
asset_type | status     | count
-----------|------------|------
SERVER     | ACTIVE     | 150
NETWORK    | ACTIVE     | 30
STORAGE    | ACTIVE     | 20
```

---

## 10. Cleanup

Destroy Vertica VM only:
```bash
cd infra
terraform destroy -var="enable_vertica_demo=true" -target=google_compute_instance.vertica
```

Destroy all Vertica resources:
```bash
terraform destroy -var="enable_vertica_demo=true"
```

---

## Navigation

- [Overview](./)
- [Full Guide](guide.md)
- [Architecture](architecture.md)
- [Back to Demos](../README.md)
