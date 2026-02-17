-- =============================================================================
-- DEMO 03: Vector Search for Semantic Log Analysis
-- =============================================================================
--
-- Vector search enables SEMANTIC similarity - finding logs that are
-- conceptually similar even if the exact text doesn't match.
--
-- Use cases:
--   1. "Find events similar to this known attack pattern"
--   2. "Show me logs like this suspicious activity"
--   3. "Detect anomalies by finding outliers in embedding space"
--
-- Key insight: Similar events cluster together in 768-dimensional space
--
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXAMPLE 1: Find Similar Events to a Text Description
-- "Find logs similar to: unauthorized access attempt"
-- -----------------------------------------------------------------------------

WITH search_query AS (
  SELECT ml_generate_embedding_result AS query_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (SELECT 'A failed authentication attempt or unauthorized access to a resource' AS content),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
)

SELECT
  logs.event_timestamp,
  logs.principal_email,
  logs.method_name,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, search_query.query_embedding, 'COSINE') AS similarity_distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     search_query
ORDER BY similarity_distance ASC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- EXAMPLE 2: Find Events Similar to a Known Threat Pattern
-- "Show me events that look like privilege escalation"
-- -----------------------------------------------------------------------------

WITH threat_pattern AS (
  SELECT ml_generate_embedding_result AS pattern_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (SELECT 'Service account key creation or IAM policy change granting elevated permissions' AS content),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
)

SELECT
  logs.event_timestamp,
  logs.principal_email,
  logs.method_name,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, threat_pattern.pattern_embedding, 'COSINE') AS distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     threat_pattern
WHERE ML.DISTANCE(logs.embedding, threat_pattern.pattern_embedding, 'COSINE') < 0.5
ORDER BY distance ASC
LIMIT 20;


-- -----------------------------------------------------------------------------
-- EXAMPLE 3: Find Destructive Operations
-- "Show me logs about resource deletion"
-- -----------------------------------------------------------------------------

WITH search_query AS (
  SELECT ml_generate_embedding_result AS query_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (SELECT 'Resource deletion or data destruction operation' AS content),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
)

SELECT
  logs.event_timestamp,
  logs.principal_email,
  logs.method_name,
  logs.service_name,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, search_query.query_embedding, 'COSINE') AS distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     search_query
ORDER BY distance ASC
LIMIT 20;


-- -----------------------------------------------------------------------------
-- EXAMPLE 4: Find Similar Events to an Existing Log Entry
-- "This event looks suspicious - find more like it"
-- -----------------------------------------------------------------------------

WITH suspicious_event AS (
  SELECT embedding
  FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings`
  WHERE method_name LIKE '%Delete%'
  ORDER BY event_timestamp DESC
  LIMIT 1
)

SELECT
  logs.event_timestamp,
  logs.principal_email,
  logs.method_name,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, suspicious_event.embedding, 'COSINE') AS distance
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     suspicious_event
ORDER BY distance ASC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- EXAMPLE 5: Anomaly Detection via Embedding Distance
-- "Find events that don't cluster with normal activity"
-- -----------------------------------------------------------------------------

WITH normal_centroid AS (
  SELECT
    ARRAY(
      SELECT AVG(val)
      FROM UNNEST(embedding) AS val WITH OFFSET pos
      GROUP BY pos
      ORDER BY pos
    ) AS centroid_embedding
  FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings`
  WHERE status_code = 0  -- Successful operations = "normal"
)

SELECT
  logs.event_timestamp,
  logs.principal_email,
  logs.method_name,
  logs.status_code,
  logs.event_summary,
  ML.DISTANCE(logs.embedding, normal_centroid.centroid_embedding, 'COSINE') AS anomaly_score
FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` AS logs,
     normal_centroid
ORDER BY anomaly_score DESC
LIMIT 20;


-- -----------------------------------------------------------------------------
-- EXAMPLE 6: Security Pattern Library
-- Pre-define known threat patterns and match against them
-- -----------------------------------------------------------------------------

WITH threat_patterns AS (
  SELECT pattern_name, ml_generate_embedding_result AS pattern_embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `gcloud-tech-showcase.security_logs.text_embedding_model`,
    (
      SELECT 'credential_theft' AS pattern_name, 'Service account key download or secret access' AS content
      UNION ALL
      SELECT 'data_exfiltration', 'Large data export or copy to external destination'
      UNION ALL
      SELECT 'privilege_escalation', 'IAM role binding or permission grant to user'
      UNION ALL
      SELECT 'resource_destruction', 'Delete operation on production resource'
      UNION ALL
      SELECT 'reconnaissance', 'List or describe operation across multiple services'
    ),
    STRUCT('SEMANTIC_SIMILARITY' AS task_type)
  )
),

matched_events AS (
  SELECT
    logs.event_id,
    logs.event_timestamp,
    logs.principal_email,
    logs.method_name,
    logs.event_summary,
    patterns.pattern_name,
    ML.DISTANCE(logs.embedding, patterns.pattern_embedding, 'COSINE') AS distance,
    ROW_NUMBER() OVER (PARTITION BY logs.event_id ORDER BY ML.DISTANCE(logs.embedding, patterns.pattern_embedding, 'COSINE')) AS rank
  FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings` logs
  CROSS JOIN threat_patterns patterns
)

SELECT
  event_timestamp,
  principal_email,
  method_name,
  pattern_name AS matched_threat_pattern,
  distance AS pattern_distance,
  event_summary
FROM matched_events
WHERE rank = 1
  AND distance < 0.5  -- Only confident matches
ORDER BY distance ASC
LIMIT 30;
