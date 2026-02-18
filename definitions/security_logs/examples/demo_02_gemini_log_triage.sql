-- =============================================================================
-- DEMO 02: Gemini AI for Security Log Triage
-- =============================================================================
--
-- This demo shows how to use Gemini AI directly in BigQuery to:
--   1. Classify security events by threat level
--   2. Categorize events (IAM changes, data exfil, etc.)
--   3. Generate human-readable explanations
--   4. Recommend next steps for the security team
--
-- No data movement required - AI inference happens in-place on your log data.
--
-- =============================================================================

-- -----------------------------------------------------------------------------
-- OPTION A: Query Pre-Classified Events
-- (Requires running Dataform to populate gold_threat_classifications)
-- -----------------------------------------------------------------------------

-- Show high-priority threats
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
  CASE threat_level
    WHEN 'CRITICAL' THEN 1
    WHEN 'HIGH' THEN 2
    ELSE 3
  END,
  event_timestamp DESC;


-- Threat level distribution
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


-- -----------------------------------------------------------------------------
-- OPTION B: Ad-Hoc AI Analysis (No Pre-Built Tables Required)
-- Great for live demos - runs directly on audit logs
-- -----------------------------------------------------------------------------

-- Classify a sample of recent events on-the-fly
WITH classified AS (
  SELECT
    timestamp AS event_timestamp,
    protopayload_auditlog.authenticationInfo.principalEmail AS principal_email,
    protopayload_auditlog.methodName AS method_name,
    protopayload_auditlog.resourceName AS resource_name,
    -- Extract JSON from response, stripping markdown code fences if present
    REGEXP_EXTRACT(ml_generate_text_llm_result, r'\{[^{}]*"threat_level"[^{}]*\}') AS json_response
  FROM
    ML.GENERATE_TEXT(
      MODEL `gcloud-tech-showcase.security_logs.gemini_log_analyst`,
      (
        SELECT
          timestamp,
          protopayload_auditlog,
          CONCAT(
            'Return ONLY a raw JSON object. No markdown, no code fences, no explanation.\n',
            'Format: {"threat_level": "<CRITICAL|HIGH|MEDIUM|LOW|INFO>", ',
            '"category": "<iam_change|data_exfil|resource_deletion|config_change|normal>", ',
            '"explanation": "<one sentence>"}\n\n',
            'Classify this audit log:\n',
            'User: ', COALESCE(protopayload_auditlog.authenticationInfo.principalEmail, 'unknown'), '\n',
            'Action: ', COALESCE(protopayload_auditlog.methodName, 'unknown'), '\n',
            'Service: ', COALESCE(protopayload_auditlog.serviceName, 'unknown'), '\n',
            'Status: ', CAST(COALESCE(protopayload_auditlog.status.code, 0) AS STRING)
          ) AS prompt
        FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        ORDER BY timestamp DESC
        LIMIT 20
      ),
      STRUCT(0.1 AS temperature, 256 AS max_output_tokens, TRUE AS flatten_json_output)
    )
)
SELECT
  event_timestamp,
  principal_email,
  method_name,
  resource_name,
  JSON_EXTRACT_SCALAR(json_response, '$.threat_level') AS threat_level,
  JSON_EXTRACT_SCALAR(json_response, '$.category') AS threat_category,
  JSON_EXTRACT_SCALAR(json_response, '$.explanation') AS explanation
FROM classified
ORDER BY
  CASE JSON_EXTRACT_SCALAR(json_response, '$.threat_level')
    WHEN 'CRITICAL' THEN 1
    WHEN 'HIGH' THEN 2
    WHEN 'MEDIUM' THEN 3
    ELSE 4
  END;


-- -----------------------------------------------------------------------------
-- OPTION C: Summarize a Suspicious User's Activity
-- "What has this user been doing?"
-- -----------------------------------------------------------------------------

-- First, find a user with interesting activity
WITH user_activity AS (
  SELECT
    protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
    ARRAY_AGG(
      CONCAT(
        FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', timestamp), ': ',
        protopayload_auditlog.methodName, ' on ', protopayload_auditlog.serviceName
      )
      ORDER BY timestamp DESC
      LIMIT 20
    ) AS recent_actions
  FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND protopayload_auditlog.authenticationInfo.principalEmail IS NOT NULL
  GROUP BY user_email
  ORDER BY COUNT(*) DESC
  LIMIT 1
),

ai_result AS (
  SELECT
    user_email,
    REGEXP_EXTRACT(ml_generate_text_llm_result, r'\{[^{}]*"summary"[^{}]*\}') AS json_response
  FROM
    ML.GENERATE_TEXT(
      MODEL `gcloud-tech-showcase.security_logs.gemini_log_analyst`,
      (
        SELECT
          user_email,
          CONCAT(
            'Return ONLY raw JSON. No markdown, no code fences.\n',
            'Format: {"summary": "<2-3 sentences>", "risk_assessment": "<low|medium|high>", ',
            '"anomalies": "<unusual patterns or null>"}\n\n',
            'Analyze activity for: ', user_email, '\n',
            'Recent actions:\n',
            ARRAY_TO_STRING(recent_actions, '\n')
          ) AS prompt
        FROM user_activity
      ),
      STRUCT(0.2 AS temperature, 512 AS max_output_tokens, TRUE AS flatten_json_output)
    )
)

SELECT
  user_email,
  JSON_EXTRACT_SCALAR(json_response, '$.summary') AS activity_summary,
  JSON_EXTRACT_SCALAR(json_response, '$.risk_assessment') AS risk_assessment,
  JSON_EXTRACT_SCALAR(json_response, '$.anomalies') AS anomalies_detected
FROM ai_result;


-- -----------------------------------------------------------------------------
-- OPTION D: Explain a Specific Suspicious Event
-- "Tell me more about this event"
-- -----------------------------------------------------------------------------

WITH ai_explanations AS (
  SELECT
    timestamp,
    protopayload_auditlog.methodName AS action,
    protopayload_auditlog.resourceName AS resource,
    REGEXP_EXTRACT(ml_generate_text_llm_result, r'\{[^{}]*"what_happened"[^{}]*\}') AS json_response
  FROM
    ML.GENERATE_TEXT(
      MODEL `gcloud-tech-showcase.security_logs.gemini_log_analyst`,
      (
        SELECT
          timestamp,
          protopayload_auditlog,
          CONCAT(
            'Return ONLY raw JSON. No markdown, no code fences.\n',
            'Format: {"what_happened": "<plain English>", ',
            '"why_suspicious": "<reason or null>", ',
            '"investigate": "<next steps>"}\n\n',
            'Explain this GCP audit event:\n',
            'Time: ', CAST(timestamp AS STRING), '\n',
            'User: ', COALESCE(protopayload_auditlog.authenticationInfo.principalEmail, 'unknown'), '\n',
            'Service: ', COALESCE(protopayload_auditlog.serviceName, 'unknown'), '\n',
            'Method: ', COALESCE(protopayload_auditlog.methodName, 'unknown'), '\n',
            'Resource: ', COALESCE(protopayload_auditlog.resourceName, 'unknown'), '\n',
            'Status: ', CAST(COALESCE(protopayload_auditlog.status.code, 0) AS STRING), '\n',
            'IP: ', COALESCE(protopayload_auditlog.requestMetadata.callerIp, 'unknown')
          ) AS prompt
        FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
        WHERE protopayload_auditlog.methodName LIKE '%Delete%'
           OR protopayload_auditlog.methodName LIKE '%SetIamPolicy%'
           OR protopayload_auditlog.methodName LIKE '%CreateServiceAccount%'
        ORDER BY timestamp DESC
        LIMIT 5
      ),
      STRUCT(0.2 AS temperature, 512 AS max_output_tokens, TRUE AS flatten_json_output)
    )
)

SELECT
  timestamp,
  action,
  resource,
  JSON_EXTRACT_SCALAR(json_response, '$.what_happened') AS what_happened,
  JSON_EXTRACT_SCALAR(json_response, '$.why_suspicious') AS why_suspicious,
  JSON_EXTRACT_SCALAR(json_response, '$.investigate') AS what_to_investigate
FROM ai_explanations;
