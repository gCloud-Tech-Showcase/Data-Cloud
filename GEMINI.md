# Data-Cloud Project Context

## Project Identity

Google Cloud Tech Showcase demonstrating **propensity modeling** with BigQuery ML and Vertex AI. Predicts user retention (7-day return probability) using GA4/Firebase gaming app data.

## Architecture

```
GA4 Public Dataset → Dataform (SQL ETL) → BigQuery → BQML Model → Vertex AI Registry
```

**Data Pipeline Layers:**

- `sources/` - External data declarations (Firebase `events_*`)
- `staging/` - Flattening and cleaning (`v_events_flattened`)
- `marts/` - Feature engineering (`training_data`)
- `ml/` - Model training (`user_retention_model`)

## Technology Stack

- **Infrastructure**: Terraform >= 1.6.0
- **Data Warehouse**: BigQuery
- **Transformation**: Dataform 3.0.0
- **ML**: BigQuery ML (logistic regression)
- **Model Registry**: Vertex AI
- **Secrets**: Secret Manager

## Directory Structure

```
Data-Cloud/
├── definitions/propensity_modeling/    # Dataform SQL pipeline
│   ├── sources/ga4_events.sqlx         # Firebase dataset reference
│   ├── staging/v_events_flattened.sqlx # Unnest GA4 nested params
│   ├── marts/training_data.sqlx        # Rolling 7-day window features
│   └── ml/user_retention_model.sqlx    # BQML model definition
├── infra/                              # Terraform IaC
│   ├── main.tf                         # GCP resources
│   ├── variables.tf                    # Input parameters
│   └── terraform.tfvars.example        # Config template
├── package.json                        # Dataform dependencies
└── workflow_settings.yaml              # Dataform config
```

## Coding Conventions

### Dataform (.sqlx files)

Always start with a config block:

```javascript
config {
  type: "table",          // declaration, view, table, or operations
  schema: "dataset_name", // target BigQuery dataset
  description: "..."      // always include
}
```

Use `${ref("table_name")}` for dependencies. Use `${self()}` in model definitions.

**Naming:**

- Staging views: prefix with `v_` (e.g., `v_events_flattened`)
- Mart tables: descriptive names (e.g., `training_data`)

**Schemas:**

- `ga4_source` - staging views
- `propensity_modeling` - marts and ML models

### SQL Patterns

- Use `COALESCE()` for null handling
- Use `SAFE_DIVIDE()` to avoid division errors
- GA4 dates are `YYYYMMDD` strings - use `PARSE_DATE('%Y%m%d', date_column)`

### Terraform

- Group resources with comment headers
- Use explicit `depends_on` for ordering
- Mark secrets with `sensitive = true`
- Enable APIs before creating dependent resources

## Key Commands

```bash
# Infrastructure
cd infra && terraform init && terraform plan && terraform apply

# Dataform (via Cloud Console)
# 1. Dataform → data-cloud repo → Start Compilation → Start Execution
```

## Common Tasks

**Add a feature to training data:**

1. Edit `definitions/propensity_modeling/marts/training_data.sqlx`
2. Add calculation in `user_training_features` CTE
3. Include in final SELECT with `COALESCE` for nulls

**Modify the model:**

1. Edit `definitions/propensity_modeling/ml/user_retention_model.sqlx`
2. Add feature to SELECT clause
3. Add preprocessing in TRANSFORM if needed (scaling, bucketing)

**Update infrastructure:**

1. Edit files in `infra/`
2. Run `terraform plan` to validate
3. Run `terraform apply` to deploy

## Important Files

| File                              | Purpose                                          |
| --------------------------------- | ------------------------------------------------ |
| `marts/training_data.sqlx`        | Core feature engineering (rolling 7-day windows) |
| `ml/user_retention_model.sqlx`    | BQML logistic regression model                   |
| `staging/v_events_flattened.sqlx` | GA4 data flattening                              |
| `infra/main.tf`                   | All GCP resource definitions                     |

## Source Data

- Dataset: `firebase-public-project.analytics_153293282.events_*`
- Date range: June 12, 2018 - October 3, 2018
- ~5.7M events, ~15K users

## Security

Never commit:

- `terraform.tfvars` (contains secrets)
- `.terraform/` directory
- `*.tfstate` files

Credentials are stored in Secret Manager, not in code.

## Guidelines

1. Read files before editing - understand existing patterns
2. Follow existing config block and SQL conventions
3. Ensure `${ref()}` targets exist before referencing
4. Use correct schema for each layer
5. Run `terraform plan` before `terraform apply`
6. Never output or log secrets/tokens
