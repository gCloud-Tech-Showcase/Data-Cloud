-- =============================================================================
-- DEMO 01: Pipe Syntax for Security Log Analysis
-- =============================================================================
--
-- Pipe syntax is an extension to GoogleSQL designed for intuitive log analysis.
-- It's familiar to users of Splunk SPL, Azure KQL, and other log query languages.
--
-- Key benefits:
--   • Operations flow top-to-bottom (like reading a recipe)
--   • Chain filters, aggregations, and transformations naturally
--   • No performance penalty - same query optimizer as standard SQL
--
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXAMPLE 1: Basic Log Exploration
-- "Show me recent admin activity"
-- -----------------------------------------------------------------------------

-- TRADITIONAL SQL (read inside-out, bottom-to-top)
SELECT
  timestamp,
  protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
  protopayload_auditlog.methodName AS action,
  protopayload_auditlog.resourceName AS resource
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY timestamp DESC
LIMIT 50;

-- PIPE SYNTAX (read top-to-bottom, left-to-right)
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.methodName AS action,
     protopayload_auditlog.resourceName AS resource
|> ORDER BY timestamp DESC
|> LIMIT 50;


-- -----------------------------------------------------------------------------
-- EXAMPLE 2: Investigating Destructive Operations
-- "Find all delete operations in the last week"
-- -----------------------------------------------------------------------------

-- PIPE SYNTAX - Easy to add more filters iteratively
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


-- -----------------------------------------------------------------------------
-- EXAMPLE 3: Top Talkers Analysis
-- "Who are the most active users in the last 24 hours?"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> AGGREGATE
     COUNT(*) AS action_count,
     COUNT(DISTINCT protopayload_auditlog.methodName) AS unique_actions,
     MIN(timestamp) AS first_seen,
     MAX(timestamp) AS last_seen
   GROUP BY protopayload_auditlog.authenticationInfo.principalEmail
|> ORDER BY action_count DESC
|> LIMIT 20;


-- -----------------------------------------------------------------------------
-- EXAMPLE 4: Service Usage Breakdown
-- "What GCP services are being used and by whom?"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
|> AGGREGATE
     COUNT(*) AS call_count,
     COUNT(DISTINCT protopayload_auditlog.authenticationInfo.principalEmail) AS unique_users
   GROUP BY protopayload_auditlog.serviceName
|> ORDER BY call_count DESC
|> LIMIT 15;


-- -----------------------------------------------------------------------------
-- EXAMPLE 5: Failed Operations (Potential Security Issues)
-- "Find operations that failed - could indicate unauthorized access attempts"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> WHERE protopayload_auditlog.status.code != 0  -- Non-zero status = error
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.serviceName AS service,
     protopayload_auditlog.methodName AS attempted_action,
     protopayload_auditlog.status.code AS error_code,
     protopayload_auditlog.status.message AS error_message
|> ORDER BY timestamp DESC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 6: IAM Permission Changes
-- "Track who is modifying IAM policies"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
|> WHERE protopayload_auditlog.methodName LIKE '%SetIamPolicy%'
      OR protopayload_auditlog.methodName LIKE '%CreateServiceAccount%'
      OR protopayload_auditlog.methodName LIKE '%CreateServiceAccountKey%'
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS actor,
     protopayload_auditlog.methodName AS action,
     protopayload_auditlog.resourceName AS target_resource
|> ORDER BY timestamp DESC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 7: Chained Analysis (Power of Pipe Syntax)
-- "Start broad, progressively narrow down"
-- -----------------------------------------------------------------------------

-- This shows the iterative exploration workflow:
-- Start with everything, then add pipes to refine

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
-- Uncomment lines below to progressively filter:
-- |> WHERE protopayload_auditlog.serviceName = 'bigquery.googleapis.com'
-- |> WHERE protopayload_auditlog.methodName LIKE '%Job%'
-- |> WHERE protopayload_auditlog.authenticationInfo.principalEmail LIKE '%@example.com'
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.serviceName AS service,
     protopayload_auditlog.methodName AS action
|> ORDER BY timestamp DESC
|> LIMIT 100;


-- -----------------------------------------------------------------------------
-- EXAMPLE 8: Time-Based Pattern Analysis
-- "Activity patterns by hour of day"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
|> EXTEND EXTRACT(HOUR FROM timestamp) AS hour_of_day
|> AGGREGATE COUNT(*) AS activity_count
   GROUP BY hour_of_day
|> ORDER BY hour_of_day;


-- -----------------------------------------------------------------------------
-- EXAMPLE 9: Cross-Service Activity Correlation
-- "Users active across multiple services (potential lateral movement)"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> AGGREGATE
     COUNT(*) AS total_actions,
     COUNT(DISTINCT protopayload_auditlog.serviceName) AS services_touched,
     ARRAY_AGG(DISTINCT protopayload_auditlog.serviceName) AS service_list
   GROUP BY protopayload_auditlog.authenticationInfo.principalEmail
|> WHERE services_touched >= 3
|> ORDER BY services_touched DESC, total_actions DESC;


-- -----------------------------------------------------------------------------
-- EXAMPLE 10: Semi-Structured Data Exploration
-- "Explore nested JSON fields without pre-defined schema"
-- -----------------------------------------------------------------------------

FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
|> WHERE protopayload_auditlog.requestMetadata.callerIp IS NOT NULL
|> SELECT
     timestamp,
     protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
     protopayload_auditlog.requestMetadata.callerIp AS source_ip,
     protopayload_auditlog.requestMetadata.callerSuppliedUserAgent AS user_agent,
     protopayload_auditlog.methodName AS action
|> ORDER BY timestamp DESC
|> LIMIT 25;
