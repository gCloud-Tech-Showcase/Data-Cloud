# Example Queries

This folder contains example SQL queries organized by use case.

## Structure

```
examples/
├── propensity_modeling/     # User retention ML pipeline
│   ├── batch_inference.sql
│   ├── model_evaluation.sql
│   ├── predictions.sql
│   └── real_time_inference_payload.json
├── security_logs/           # Security log analytics demo
│   ├── demo_01_pipe_syntax.sql      # 10 pipe syntax examples
│   ├── demo_02_gemini_log_triage.sql # AI classification
│   └── demo_03_vector_search.sql     # Semantic search
└── campaign_intelligence/   # Campaign targeting (future)
```

## Security Logs Demo

For the OpenText security demo, use the queries in `security_logs/`:

1. **Pipe Syntax** (`demo_01_pipe_syntax.sql`) - Intuitive log queries familiar to Splunk/KQL users
2. **Gemini Triage** (`demo_02_gemini_log_triage.sql`) - AI-powered threat classification
3. **Vector Search** (`demo_03_vector_search.sql`) - Semantic similarity for threat hunting

### Quick Start

```sql
-- Run in BigQuery Console
-- Basic log exploration with pipe syntax
FROM `gcloud-tech-showcase.security_logs.cloudaudit_googleapis_com_activity`
|> WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
|> SELECT timestamp, protopayload_auditlog.methodName, protopayload_auditlog.serviceName
|> ORDER BY timestamp DESC
|> LIMIT 20
```

## Propensity Modeling

Queries for the user retention ML model:

- `batch_inference.sql` - Run predictions on user cohorts
- `model_evaluation.sql` - Evaluate model performance
- `predictions.sql` - Score individual users
