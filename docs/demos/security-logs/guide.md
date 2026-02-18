# Security Logs Analytics Guide

Analyze Cloud Audit Logs with AI-powered threat detection and semantic search.

**Time:** 15-20 minutes

---

## The Use Case

Security teams drown in log data. Cloud Audit Logs capture every API call, but finding threats requires:
- **Familiar query syntax** — analysts know Splunk SPL and Azure KQL
- **AI assistance** — classify threats automatically, explain anomalies
- **Semantic search** — find threats you don't know how to search for

This demo shows how BigQuery addresses all three with pipe syntax, Gemini AI, and vector embeddings.

---

## Step 1: Explore with Pipe Syntax

Pipe syntax reads top-to-bottom, like Splunk or KQL. Start with the data source, chain operations.

```sql
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.methodName AS action,
     protopayload_auditlog.serviceName AS service
|> ORDER BY timestamp DESC
|> LIMIT 20;
```

**Key Point:** No subqueries, no inside-out reading. Each pipe adds a transformation.

---

## Step 2: Chain Filters Iteratively

Add filters one at a time to narrow down. Find delete operations:

```sql
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
|> WHERE LOWER(protopayload_auditlog.methodName) LIKE '%delete%'
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.serviceName AS service,
     protopayload_auditlog.methodName AS action,
     protopayload_auditlog.resourceName AS deleted_resource
|> ORDER BY timestamp DESC;
```

**Pattern:** Start broad, add `|> WHERE` clauses to refine. Each pipe narrows the dataset.

---

## Step 3: Aggregate with AGGREGATE

Find top talkers — users with the most activity:

```sql
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> AGGREGATE
     COUNT(*) AS action_count,
     COUNT(DISTINCT protopayload_auditlog.methodName) AS unique_actions,
     COUNT(DISTINCT protopayload_auditlog.serviceName) AS services_touched
   GROUP BY protopayload_auditlog.authenticationInfo.principalEmail
|> WHERE services_touched >= 2
|> ORDER BY action_count DESC
|> LIMIT 10;
```

**Pattern:** `AGGREGATE ... GROUP BY` replaces the traditional `SELECT ... GROUP BY` pattern.

---

## Step 4: AI Threat Classification

The `gold_threat_classifications` table contains AI-classified events. Gemini analyzes each log entry and assigns:
- **Threat level:** CRITICAL, HIGH, MEDIUM, LOW, INFO
- **Category:** iam_change, resource_deletion, config_change, recon, normal
- **Explanation:** Human-readable reason for the classification

```sql
SELECT
  event_timestamp,
  principal_email,
  method_name,
  threat_level,
  threat_category,
  explanation,
  recommended_action
FROM `gcloud-tech-showcase.security_logs.gold_threat_classifications`
WHERE threat_level IN ('CRITICAL', 'HIGH')
ORDER BY
  CASE threat_level WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 ELSE 3 END,
  event_timestamp DESC;
```

**How it works:** Each event is sent to Gemini with a prompt asking for JSON classification. The model returns threat level, category, and explanation.

---

## Step 5: Ad-Hoc AI Analysis

Run AI classification on any log event without pre-built tables:

```sql
WITH classified AS (
  SELECT
    timestamp,
    protopayload_auditlog.methodName AS method_name,
    REGEXP_EXTRACT(ml_generate_text_llm_result, r'\{[^{}]*"threat_level"[^{}]*\}') AS json_response
  FROM ML.GENERATE_TEXT(
    MODEL `gcloud-tech-showcase.security_logs.gemini_log_analyst`,
    (
      SELECT timestamp, protopayload_auditlog,
        CONCAT(
          'Return ONLY raw JSON: {"threat_level": "<CRITICAL|HIGH|MEDIUM|LOW|INFO>", ',
          '"category": "<iam_change|resource_deletion|config_change|normal>", ',
          '"explanation": "<one sentence>"}\n\n',
          'Classify: ', protopayload_auditlog.methodName, ' on ', protopayload_auditlog.serviceName
        ) AS prompt
      FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
      WHERE protopayload_auditlog.methodName LIKE '%Delete%'
      LIMIT 5
    ),
    STRUCT(0.1 AS temperature, 256 AS max_output_tokens, TRUE AS flatten_json_output)
  )
)
SELECT
  timestamp, method_name,
  JSON_EXTRACT_SCALAR(json_response, '$.threat_level') AS threat_level,
  JSON_EXTRACT_SCALAR(json_response, '$.explanation') AS explanation
FROM classified;
```

---

## Step 6: Semantic Vector Search

Find events similar to a natural language description:

```sql
WITH search_query AS (
  SELECT ml_generate_embedding_result AS query_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (SELECT 'privilege escalation or IAM policy change' AS content),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
)

SELECT
  logs.event_timestamp,
  logs.method_name,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, search_query.query_embedding, 'COSINE') AS distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     search_query
ORDER BY distance ASC
LIMIT 10;
```

**Key insight:** Lower distance = more similar. Events cluster by semantic meaning, not just keywords.

---

## Step 7: Threat Pattern Library

Match events against pre-defined threat patterns:

```sql
WITH threat_patterns AS (
  SELECT pattern_name, ml_generate_embedding_result AS pattern_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (
      SELECT 'credential_theft' AS pattern_name, 'Service account key download or secret access' AS content
      UNION ALL SELECT 'privilege_escalation', 'IAM role binding or permission grant'
      UNION ALL SELECT 'resource_destruction', 'Delete operation on production resource'
      UNION ALL SELECT 'reconnaissance', 'List or describe operation across services'
    ),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
)

SELECT
  logs.method_name,
  patterns.pattern_name AS matched_pattern,
  ML.DISTANCE(logs.embedding, patterns.pattern_embedding, 'COSINE') AS distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` logs
CROSS JOIN threat_patterns patterns
WHERE ML.DISTANCE(logs.embedding, patterns.pattern_embedding, 'COSINE') < 0.4
ORDER BY distance ASC
LIMIT 20;
```

---

## Key Takeaways

| Capability | Technology | Business Value |
|------------|------------|----------------|
| Intuitive queries | Pipe Syntax | Analysts productive immediately |
| Auto-classification | Gemini AI | Focus on real threats, not noise |
| Semantic search | Vector Embeddings | Find threats you can't keyword-search |
| No data movement | BigQuery + Log Sink | Analyze logs where they land |

---

---

## Step 8: Real-Time Alerts (Optional)

Enable continuous queries for instant threat detection with Pub/Sub export.

**Requirements:** Enterprise reservation (`enable_realtime_alerts = true`)

[Continue to Real-Time Alerts →](08-realtime-alerts.md)

---

## Navigation

[← Demos](../README.md) | [Quick Reference](quick.md)
