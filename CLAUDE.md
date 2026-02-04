# CLAUDE.md - Data-Cloud Project

## WHAT: Project Overview

Google Cloud Tech Showcase demonstrating **propensity modeling** with BigQuery ML and Vertex AI. Predicts user retention (7-day return probability) using GA4/Firebase gaming app data.

**Data Pipeline:**
```
GA4 events_* → v_events_flattened (staging) → training_data (mart) → user_retention_model (BQML) → Vertex AI
```

**Key Directories:**
- `definitions/propensity_modeling/` - Dataform SQL pipeline (sources → staging → marts → ml)
- `infra/` - Terraform IaC for GCP resources

## WHY: Architecture Decisions

**Rolling 7-day windows**: Training data uses sliding observation windows, not just "first 7 days". This creates multiple training rows per user and enables continuous churn prediction.

**Feature engineering in `training_data.sqlx`**:
- Features: 7 days prior to observation_date
- Label: Did user return in 7 days after observation_date?
- Filter: `days_active >= 1 AND total_events >= 3`

**Schemas:**
- `ga4_source` - staging views
- `propensity_modeling` - marts and ML models

## HOW: Development Commands

```bash
# Infrastructure
cd infra && terraform init && terraform plan && terraform apply

# Dataform (via Cloud Console)
# Dataform → data-cloud repo → Start Compilation → Start Execution
```

## Dataform Conventions

Every `.sqlx` file needs a config block:
```javascript
config {
  type: "table",           // declaration, view, table, or operations
  schema: "dataset_name",
  description: "..."
}
```

Use `${ref("table_name")}` for dependencies. Use `${self()}` in model definitions.

**Naming:** Staging views use `v_` prefix. Mart tables use descriptive names.

## SQL Patterns

- Use `COALESCE()` for null handling
- Use `SAFE_DIVIDE()` to avoid division errors
- GA4 dates are `YYYYMMDD` strings - use `PARSE_DATE('%Y%m%d', col)`

## Terraform Patterns

- Group resources with comment headers
- Use explicit `depends_on` for ordering
- Mark secrets with `sensitive = true`

## Common Tasks

**Add a training feature:**
1. Edit `definitions/propensity_modeling/marts/training_data.sqlx`
2. Add calculation in `user_training_features` CTE
3. Include in final SELECT with `COALESCE`
4. Add to model's SELECT and TRANSFORM if needed

**Modify the model:**
1. Edit `definitions/propensity_modeling/ml/user_retention_model.sqlx`
2. Add feature to SELECT clause
3. Add preprocessing in TRANSFORM if needed (scaling, bucketing)

## Important Files

| File | Purpose |
|------|---------|
| `marts/training_data.sqlx` | Rolling 7-day window feature engineering |
| `ml/user_retention_model.sqlx` | BQML logistic regression with Vertex AI registration |
| `staging/v_events_flattened.sqlx` | Flattens nested GA4 event_params |
| `infra/main.tf` | All GCP resource definitions |

## Source Data

- Dataset: `firebase-public-project.analytics_153293282.events_*`
- Date range: June 12, 2018 - October 3, 2018

## Security

Never commit: `terraform.tfvars`, `.terraform/`, `*.tfstate`

## Guidelines

1. Read files before editing - understand existing patterns
2. Ensure `${ref()}` targets exist before referencing
3. Run `terraform plan` before `terraform apply`
4. Never output or log secrets/tokens
