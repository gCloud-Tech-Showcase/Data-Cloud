# Data-Cloud Project Context

## Project Identity

Google Cloud Tech Showcase demonstrating **multimodal analytics** with BigQuery, Gemini AI, and Vertex AI. Two domains:

1. **Sentiment Analysis** - Analyze user reviews using Gemini 2.0 Flash in BigQuery
2. **Propensity Modeling** - Predict user retention (7-day return) using BigQuery ML

## Architecture

```
Sentiment Analysis:
  GCS JSON → BigLake Object Table → Gemini AI (BigQuery) → Enriched Reviews

Propensity Modeling:
  GA4 Public Dataset → Dataform (SQL ETL) → BigQuery → BQML Model → Vertex AI
```

**Medallion Architecture (Bronze → Silver → Gold):**

- **Bronze** - Raw, immutable data (BigLake Object Tables, external declarations)
- **Silver** - Cleansed, validated (flattened events, Gemini-enriched reviews)
- **Gold** - Feature-engineered (ML training datasets, models)

**Data Pipeline Layers:**

- `sources/` - Bronze layer (external declarations, BigLake Object Tables)
- `staging/` - Silver layer (cleansed, enriched data)
- `marts/` - Gold layer (feature engineering)
- `ml/` - Gold layer (model training)

## Technology Stack

- **Infrastructure**: Terraform >= 1.6.0
- **Data Warehouse**: BigQuery
- **Object Storage**: Cloud Storage (GCS)
- **Unstructured Data**: BigLake Object Tables
- **Transformation**: Dataform 3.0.0
- **AI Models**: Gemini 2.0 Flash (sentiment analysis), BigQuery ML (propensity modeling)
- **Model Registry**: Vertex AI
- **Secrets**: Secret Manager
- **Scraping**: Python with google-play-scraper library

## Directory Structure

```
Data-Cloud/
├── definitions/
│   ├── sentiment_analysis/                    # Sentiment analysis domain
│   │   ├── sources/bronze_user_reviews.sqlx   # BigLake Object Table (GCS JSON)
│   │   └── staging/silver_review_sentiment.sqlx # Gemini-enriched reviews
│   └── propensity_modeling/                   # User retention domain
│       ├── sources/ga4_events.sqlx            # Firebase dataset reference
│       ├── staging/silver_events_flattened.sqlx # Unnest GA4 nested params
│       ├── marts/gold_training_features.sqlx  # Rolling 7-day window features
│       └── ml/gold_user_retention_model.sqlx  # BQML model definition
├── scripts/                                   # Python tools
│   └── scrape_play_store_reviews.py           # Play Store scraper
├── infra/                                     # Terraform IaC
│   ├── main.tf                                # GCP resources
│   ├── variables.tf                           # Input parameters
│   └── terraform.tfvars.example               # Config template
├── package.json                               # Dataform dependencies
├── workflow_settings.yaml.example             # Dataform config template
└── CLAUDE.md / GEMINI.md                      # AI assistant context
```

## Coding Conventions

### Dataform (.sqlx files)

Always start with a config block:

```javascript
config {
  type: "table",          // declaration, view, table, incremental, or operations
  schema: "dataset_name", // target BigQuery dataset
  description: "...",     // Include BRONZE/SILVER/GOLD prefix
  tags: ["domain", "layer", "category"]  // e.g., ["sentiment_analysis", "silver", "staging"]
}
```

Use `${ref("table_name")}` for dependencies. Use `${self()}` in model definitions.

**Naming Conventions:**

- Bronze layer: `bronze_*` prefix (e.g., `bronze_user_reviews`)
- Silver layer: `silver_*` prefix (e.g., `silver_review_sentiment`, `silver_events_flattened`)
- Gold layer: `gold_*` prefix (e.g., `gold_training_features`, `gold_user_retention_model`)

**Datasets:**

- `sentiment_analysis` - Bronze and Silver layers for review analysis
- `ga4_source` - Silver layer for GA4 events
- `propensity_modeling` - Gold layer for ML models and features

**Tags:**

- Domain: `sentiment_analysis` or `propensity_modeling`
- Layer: `bronze`, `silver`, or `gold`
- Category: `sources`, `staging`, `marts`, `ml`, `examples`

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

1. Edit `definitions/propensity_modeling/marts/gold_training_features.sqlx`
2. Add calculation in `user_training_features` CTE
3. Include in final SELECT with `COALESCE` for nulls

**Modify the model:**

1. Edit `definitions/propensity_modeling/ml/gold_user_retention_model.sqlx`
2. Add feature to SELECT clause
3. Add preprocessing in TRANSFORM if needed (scaling, bucketing)

**Scrape more reviews:**

1. Edit `scripts/scrape_play_store_reviews.py` to add new apps
2. Run: `cd scripts && python scrape_play_store_reviews.py`
3. JSON files are automatically uploaded to GCS

**Query sentiment analysis:**

1. Use BigQuery Console
2. Query `sentiment_analysis.silver_review_sentiment` table
3. Filter by sentiment, category, date range

**Update infrastructure:**

1. Edit files in `infra/`
2. Run `terraform plan` to validate
3. Run `terraform apply` to deploy

## Important Files

**Sentiment Analysis:**
| File | Purpose |
| --------------------------------- | ------------------------------------------------ |
| `sentiment_analysis/sources/bronze_user_reviews.sqlx` | BigLake Object Table for JSON files in GCS |
| `sentiment_analysis/staging/silver_review_sentiment.sqlx` | Gemini AI sentiment enrichment (incremental) |
| `scripts/scrape_play_store_reviews.py` | Python scraper for Play Store reviews |

**Propensity Modeling:**
| File | Purpose |
| --------------------------------- | ------------------------------------------------ |
| `propensity_modeling/staging/silver_events_flattened.sqlx` | GA4 data flattening |
| `propensity_modeling/marts/gold_training_features.sqlx` | Core feature engineering (rolling 7-day windows) |
| `propensity_modeling/ml/gold_user_retention_model.sqlx` | BQML logistic regression model |

**Infrastructure:**
| File | Purpose |
| --------------------------------- | ------------------------------------------------ |
| `infra/main.tf` | All GCP resource definitions (GCS, BigQuery, Vertex AI) |
| `workflow_settings.yaml` | Dataform configuration (project, dataset, location) |

## Source Data

**GA4 Events (Propensity Modeling):**
- Dataset: `firebase-public-project.analytics_153293282.events_*`
- Date range: June 12, 2018 - October 3, 2018
- App: Flood-It! (gaming app)
- ~5.7M events, ~15K users

**User Reviews (Sentiment Analysis):**
- Source: Google Play Store (scraped via Python)
- Storage: GCS bucket `gs://gcloud-tech-showcase-multimodal-data/user-reviews/play-store/flood-it/`
- Format: JSON files with review metadata and text

## Security

Never commit:

- `terraform.tfvars` (contains project ID and GitHub token)
- `workflow_settings.yaml` (contains project-specific config)
- `.terraform/` directory
- `*.tfstate` files
- `scripts/.env` (auto-generated by Terraform)
- `scripts/service-account-key.json` (auto-generated by Terraform)

Credentials are stored in Secret Manager, not in code.

## Guidelines

1. Read files before editing - understand existing patterns
2. Follow existing config block and SQL conventions
3. Ensure `${ref()}` targets exist before referencing
4. Use correct schema for each layer
5. Run `terraform plan` before `terraform apply`
6. Never output or log secrets/tokens
