-- =============================================================================
-- DEMO 03: AI.SEARCH for Semantic Log Analysis
-- =============================================================================
--
-- AI.SEARCH enables SEMANTIC similarity search with zero embedding management.
-- BigQuery automatically handles embedding generation and similarity matching.
--
-- Use cases:
--   1. "Find events similar to this known attack pattern"
--   2. "Show me logs like this suspicious activity"
--   3. Natural language search across log events
--
-- Key insight: Just describe what you're looking for in plain English!
--
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXAMPLE 1: Natural Language Search
-- "Find logs about unauthorized access or authentication failures"
-- -----------------------------------------------------------------------------

-- AI.SEARCH takes your query, embeds it, and finds similar events
SELECT
  base.event_timestamp,
  base.principal_email,
  base.method_name,
  base.event_summary,
  distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'failed authentication attempt or unauthorized access to a resource',
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 2: Find Privilege Escalation Patterns
-- "Show me events that look like privilege escalation"
-- -----------------------------------------------------------------------------

SELECT
  base.event_timestamp,
  base.principal_email,
  base.method_name,
  base.event_summary,
  distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'service account key creation or IAM policy change granting elevated permissions',
  top_k => 15,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 3: Find Destructive Operations
-- "Show me logs about resource deletion or data destruction"
-- -----------------------------------------------------------------------------

SELECT
  base.event_timestamp,
  base.principal_email,
  base.method_name,
  base.service_name,
  base.event_summary,
  distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'resource deletion or data destruction operation',
  top_k => 20,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 4: Find Reconnaissance Activity
-- "Show me scanning or enumeration behavior"
-- -----------------------------------------------------------------------------

SELECT
  base.event_timestamp,
  base.principal_email,
  base.method_name,
  base.event_summary,
  distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'listing resources or enumerating services for reconnaissance',
  top_k => 15,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 5: Search with Pre-Filtering
-- "Find IAM-related events similar to a threat pattern"
-- -----------------------------------------------------------------------------

-- You can pre-filter the table before searching
SELECT
  base.event_timestamp,
  base.principal_email,
  base.method_name,
  base.event_summary,
  distance
FROM AI.SEARCH(
  (
    SELECT * FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings`
    WHERE service_name = 'iam.googleapis.com'
  ),
  'event_summary',
  'creating or modifying service accounts',
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 6: Find Events by Specific User Pattern
-- Filter to a user, then search semantically
-- -----------------------------------------------------------------------------

SELECT
  base.event_timestamp,
  base.principal_email,
  base.method_name,
  base.event_summary,
  distance
FROM AI.SEARCH(
  (
    SELECT * FROM `gcloud-tech-showcase.security_logs.silver_log_embeddings`
    WHERE principal_email LIKE '%@%.com'
      AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  ),
  'event_summary',
  'configuration changes or administrative actions',
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 7: Threat Pattern Library (Multiple Searches)
-- Search for multiple known threat patterns
-- -----------------------------------------------------------------------------

-- Credential theft pattern
SELECT 'credential_theft' AS threat_pattern, base.*, distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'service account key download or secret access',
  top_k => 5
)
WHERE distance < 0.5

UNION ALL

-- Data exfiltration pattern
SELECT 'data_exfiltration' AS threat_pattern, base.*, distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'large data export or copy to external destination',
  top_k => 5
)
WHERE distance < 0.5

UNION ALL

-- Defense evasion pattern
SELECT 'defense_evasion' AS threat_pattern, base.*, distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'disabling logging or deleting audit trails',
  top_k => 5
)
WHERE distance < 0.5

ORDER BY threat_pattern, distance ASC;


-- -----------------------------------------------------------------------------
-- COMPARISON: Old Way vs New Way
-- -----------------------------------------------------------------------------

-- OLD WAY (manual embedding + distance calculation):
-- WITH search_query AS (
--   SELECT ml_generate_embedding_result AS query_embedding
--   FROM ML.GENERATE_EMBEDDING(
--     MODEL `security_logs.text_embedding_model`,
--     (SELECT 'unauthorized access' AS content),
--     STRUCT('RETRIEVAL_QUERY' AS task_type)
--   )
-- )
-- SELECT logs.*, ML.DISTANCE(logs.embedding, search_query.query_embedding, 'COSINE') AS distance
-- FROM `security_logs.silver_log_embeddings` logs, search_query
-- ORDER BY distance ASC
-- LIMIT 10;

-- NEW WAY (AI.SEARCH - one line!):
SELECT base.*, distance
FROM AI.SEARCH(
  TABLE `gcloud-tech-showcase.security_logs.silver_log_embeddings`,
  'event_summary',
  'unauthorized access',
  top_k => 10
)
ORDER BY distance ASC;
