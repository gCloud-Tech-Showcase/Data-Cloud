# Security Logs - Quick Reference

SQL queries with expected outputs. Run these in BigQuery Console.

---

## 1. Basic Log Exploration (Pipe Syntax)

```sql
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.methodName AS action,
     protopayload_auditlog.resourceName AS resource
|> ORDER BY timestamp DESC
|> LIMIT 10;
```

**Output:**
```
timestamp                  | user_email                | action                              | resource
---------------------------|---------------------------|-------------------------------------|------------------
2026-02-17 16:10:37 UTC    | admin@example.com         | storage.buckets.delete              | projects/_/buckets/demo-bucket
2026-02-17 16:10:34 UTC    | admin@example.com         | DeleteServiceAccount                | projects/my-project/serviceAccounts/...
```

---

## 2. Find Destructive Operations

```sql
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
|> WHERE LOWER(protopayload_auditlog.methodName) LIKE '%delete%'
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.serviceName AS service,
     protopayload_auditlog.methodName AS action
|> ORDER BY timestamp DESC;
```

**Output:**
```
timestamp                  | user_email        | service                  | action
---------------------------|-------------------|--------------------------|---------------------------
2026-02-17 16:10:37 UTC    | admin@example.com | storage.googleapis.com   | storage.buckets.delete
2026-02-17 16:07:37 UTC    | admin@example.com | logging.googleapis.com   | DeleteSink
```

---

## 3. Top Talkers Analysis

```sql
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> AGGREGATE
     COUNT(*) AS action_count,
     COUNT(DISTINCT protopayload_auditlog.methodName) AS unique_actions
   GROUP BY protopayload_auditlog.authenticationInfo.principalEmail
|> ORDER BY action_count DESC
|> LIMIT 10;
```

**Output:**
```
principalEmail                                    | action_count | unique_actions
--------------------------------------------------|--------------|---------------
service-123@gcp-sa-logging.iam.gserviceaccount.com| 45           | 3
admin@example.com                                 | 28           | 12
```

---

## 4. AI Threat Classification (Pre-Built)

```sql
SELECT
  event_timestamp,
  principal_email,
  method_name,
  threat_level,
  threat_category,
  explanation
FROM `gcloud-tech-showcase.security_logs.gold_threat_classifications`
WHERE threat_level IN ('CRITICAL', 'HIGH')
ORDER BY event_timestamp DESC
LIMIT 10;
```

**Output:**
```
event_timestamp         | principal_email   | method_name              | threat_level | threat_category    | explanation
------------------------|-------------------|--------------------------|--------------|--------------------|---------------------------------
2026-02-17 16:10:34 UTC | admin@example.com | DeleteServiceAccount     | HIGH         | resource_deletion  | Service account deleted...
2026-02-17 16:07:28 UTC | admin@example.com | CreateServiceAccount     | CRITICAL     | iam_change         | New service account created...
```

---

## 5. Threat Level Distribution

```sql
SELECT
  threat_level,
  threat_category,
  COUNT(*) AS event_count
FROM `gcloud-tech-showcase.security_logs.gold_threat_classifications`
GROUP BY threat_level, threat_category
ORDER BY
  CASE threat_level
    WHEN 'CRITICAL' THEN 1
    WHEN 'HIGH' THEN 2
    WHEN 'MEDIUM' THEN 3
    WHEN 'LOW' THEN 4
    ELSE 5
  END;
```

**Output:**
```
threat_level | threat_category    | event_count
-------------|--------------------|--------------
CRITICAL     | iam_change         | 2
HIGH         | resource_deletion  | 5
MEDIUM       | config_change      | 38
INFO         | normal             | 25
```

---

## 6. Semantic Search (Vector)

```sql
WITH search_query AS (
  SELECT ml_generate_embedding_result AS query_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (SELECT 'service account deletion or cleanup operation' AS content),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
)

SELECT
  logs.event_timestamp,
  logs.principal_email,
  logs.method_name,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, search_query.query_embedding, 'COSINE') AS distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     search_query
ORDER BY distance ASC
LIMIT 5;
```

**Output:**
```
event_timestamp         | principal_email   | method_name              | event_summary                           | distance
------------------------|-------------------|--------------------------|------------------------------------------|---------
2026-02-17 16:10:34 UTC | admin@example.com | DeleteServiceAccount     | A successful DeleteServiceAccount...    | 0.26
2026-02-17 16:02:10 UTC | admin@example.com | DeleteServiceAccount     | A successful DeleteServiceAccount...    | 0.26
2026-02-17 16:10:37 UTC | admin@example.com | storage.buckets.delete   | A successful storage.buckets.delete...  | 0.37
```

---

## Navigation

- [Overview](./)
- [Full Guide](guide.md)
- [Back to Demos](../README.md)
