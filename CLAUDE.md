# CLAUDE.md - AI Assistant Guide for Data-Cloud Repository

## Project Overview

This is a **Google Cloud Tech Showcase** project demonstrating end-to-end **propensity modeling** using BigQuery ML (BQML) and Vertex AI. The project predicts user retention (7-day return probability) using Google Analytics 4 (GA4) data from a Firebase gaming app.

**Primary Use Case**: E-commerce/gaming user retention prediction - identifying which users are likely to return to the application within 7 days based on their first week of activity.

## Architecture & Data Flow

```
GA4 Public Dataset (Firebase analytics_153293282)
    ↓
[Source Declaration] events_* (wildcard table)
    ↓
[Staging] v_events_flattened (unnests nested GA4 JSON)
    ↓
[Staging] v_user_sessions (aggregates events into sessions)
    ↓
[Mart] training_data (feature engineering, 7-day windows)
    ↓
[ML] user_retention_model (BQML logistic regression)
    ↓
Vertex AI Model Registry (automatic registration)
```

## Directory Structure

```
Data-Cloud/
├── definitions/                    # Dataform SQL transformation pipeline
│   └── propensity_modeling/
│       ├── sources/               # External data declarations
│       │   └── ga4_events.sqlx    # Firebase public dataset reference
│       ├── staging/               # Data cleaning layer
│       │   ├── v_events_flattened.sqlx  # Unnest nested GA4 params
│       │   └── v_user_sessions.sqlx     # Session aggregation
│       ├── marts/                 # Business-ready datasets
│       │   └── training_data.sqlx       # ML feature engineering
│       └── ml/                    # Machine learning assets
│           ├── user_retention_model.sqlx    # BQML model definition
│           ├── model_evaluation.sqlx        # Evaluation queries (disabled)
│           └── predictions.sqlx             # Prediction queries (disabled)
├── infra/                         # Terraform Infrastructure as Code
│   ├── main.tf                    # Core GCP resources
│   ├── variables.tf               # Input parameters
│   ├── versions.tf                # Terraform/provider versions
│   ├── providers.tf               # GCP provider config
│   ├── outputs.tf                 # Deployment outputs
│   └── terraform.tfvars.example   # Variable template
├── package.json                   # Dataform dependencies (@dataform/core 3.0.0)
├── workflow_settings.yaml         # Dataform project settings
├── README.md                      # Project documentation
└── .gitignore                     # Excludes sensitive files
```

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Infrastructure as Code | Terraform | >= 1.6.0 |
| Cloud Provider | Google Cloud Platform | - |
| Data Warehouse | BigQuery | - |
| Data Transformation | Dataform | 3.0.0 |
| Machine Learning | BigQuery ML (BQML) | - |
| Model Registry | Vertex AI | - |
| Secret Management | Secret Manager | - |
| Version Control | Git (GitHub) | - |

## Key Conventions

### Dataform SQL Files (.sqlx)

1. **Config Block Required**: Every `.sqlx` file starts with a `config {}` block:
   ```javascript
   config {
     type: "table",           // declaration, view, table, or operations
     schema: "dataset_name",  // target BigQuery dataset
     description: "...",      // always include descriptions
     hasOutput: true          // for operations type only
   }
   ```

2. **Dependency References**: Use `${ref("table_name")}` for dependencies:
   ```sql
   FROM ${ref("v_events_flattened")}
   ```

3. **Self-Reference for Models**: Use `${self()}` in model definitions:
   ```sql
   CREATE OR REPLACE MODEL ${self()}
   ```

4. **Layer Naming Conventions**:
   - Sources: declared external tables (`events_*`)
   - Staging views: prefix with `v_` (e.g., `v_events_flattened`)
   - Mart tables: descriptive names (e.g., `training_data`)
   - ML models: descriptive names (e.g., `user_retention_model`)

5. **Schema Organization**:
   - `ga4_source` - staging views
   - `propensity_modeling` - marts and ML models

### SQL Code Patterns

1. **Null Handling**: Always use `COALESCE` or `SAFE_DIVIDE`:
   ```sql
   COALESCE(f.level_completion_rate, 0) AS level_completion_rate
   SAFE_DIVIDE(numerator, NULLIF(denominator, 0))
   ```

2. **Feature Engineering Windows**:
   - Training window: 7 days of user activity
   - Label window: Days 8-14 (non-overlapping)
   - Minimum activity filter: `total_sessions >= 1 AND total_events >= 3`

3. **BQML Model Options**:
   ```sql
   OPTIONS(
     model_type = 'LOGISTIC_REG',
     input_label_cols = ['will_return'],
     l2_reg = 0.1,
     model_registry = 'vertex_ai',
     vertex_ai_model_id = 'model_name',
     enable_global_explain = TRUE
   )
   ```

### Terraform Conventions

1. **Resource Grouping**: Group by section with comment headers:
   ```hcl
   # -----------------------------------------------------------------------------
   # Section Name
   # -----------------------------------------------------------------------------
   ```

2. **Dependencies**: Use explicit `depends_on` for resource ordering

3. **Sensitive Variables**: Mark with `sensitive = true`:
   ```hcl
   variable "github_token" {
     sensitive = true
   }
   ```

4. **Service Enablement**: Always enable APIs before creating resources

## Development Workflow

### Infrastructure Deployment

```bash
cd infra/

# 1. Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars
# Edit with your project_id and github_token

# 2. Initialize Terraform
terraform init

# 3. Review plan
terraform plan

# 4. Apply infrastructure
terraform apply
```

### Dataform Pipeline Execution

1. **Via Google Cloud Console**:
   - Navigate to Dataform UI
   - Select repository "data-cloud"
   - Trigger workflow execution manually

2. **Automated**: Hourly compilation via cron (`0 * * * *`)

### Model Training

The model trains automatically when the Dataform pipeline runs the `user_retention_model.sqlx` file. It:
1. Trains a logistic regression model
2. Automatically registers to Vertex AI Model Registry
3. Enables global explainability

## Important Files

| File | Purpose |
|------|---------|
| `definitions/.../training_data.sqlx` | Core feature engineering logic |
| `definitions/.../user_retention_model.sqlx` | BQML model definition |
| `definitions/.../v_events_flattened.sqlx` | GA4 data transformation |
| `infra/main.tf` | All GCP resource definitions |
| `infra/variables.tf` | Configuration parameters |
| `workflow_settings.yaml` | Dataform project config |

## BigQuery Datasets

| Dataset | Purpose |
|---------|---------|
| `propensity_modeling` | Production ML models and training data |
| `ga4_source` | Staging views over raw GA4 data |

## Common Tasks for AI Assistants

### Adding a New Feature to Training Data

1. Edit `definitions/propensity_modeling/marts/training_data.sqlx`
2. Add feature calculation in `user_training_features` CTE
3. Include in final SELECT with `COALESCE` for null handling
4. Update model if feature should be used in training

### Adding a New Model Feature

1. Edit `definitions/propensity_modeling/ml/user_retention_model.sqlx`
2. Add to SELECT clause
3. Add preprocessing in TRANSFORM clause if needed (scaling, bucketing)

### Creating New Staging Views

1. Create `.sqlx` file in `definitions/propensity_modeling/staging/`
2. Use `type: "view"` and `schema: "ga4_source"`
3. Reference upstream sources with `${ref()}`

### Modifying Infrastructure

1. Edit appropriate file in `infra/`
2. Run `terraform plan` to validate
3. Run `terraform apply` to deploy

## Testing & Validation

- **Model Evaluation**: Use queries in `model_evaluation.sqlx` (currently disabled)
- **Predictions Testing**: Use queries in `predictions.sqlx` (currently disabled)
- **Enable for execution**: Set `hasOutput: true` in config block

Key evaluation queries available:
- Training statistics
- Classification metrics (accuracy, precision, recall, AUC-ROC)
- Confusion matrix
- Feature importance (Global Explain)

## Security Considerations

1. **Never commit**:
   - `terraform.tfvars` (contains secrets)
   - `.terraform/` directory
   - `*.tfstate` files

2. **Credentials**: Stored in Secret Manager, not in code

3. **IAM**: Dataform uses service account with minimal permissions:
   - `roles/bigquery.jobUser`
   - `roles/bigquery.dataViewer`
   - `roles/secretmanager.secretAccessor`

## Source Data Reference

The project uses Firebase public dataset:
- Project: `firebase-public-project`
- Dataset: `analytics_153293282`
- Tables: `events_*` (date-sharded)
- Date range: `20180612` to `20181003`

## Quick Reference Commands

```bash
# Terraform
terraform init          # Initialize workspace
terraform plan          # Preview changes
terraform apply         # Deploy infrastructure
terraform destroy       # Remove all resources

# Git
git status              # Check current state
git add <file>          # Stage changes
git commit -m "msg"     # Commit changes
git push origin <branch># Push to remote
```

## Notes for AI Assistants

1. **Read before editing**: Always read files completely before making changes
2. **Preserve patterns**: Follow existing config block and SQL patterns
3. **Test references**: Ensure `${ref()}` targets exist
4. **Mind the schemas**: Use correct schema for each layer
5. **Infrastructure changes**: Always run `terraform plan` first
6. **Sensitive data**: Never output or log secrets/tokens
7. **Date handling**: GA4 uses `YYYYMMDD` string format, use `PARSE_DATE`
