# CLAUDE.md - Data-Cloud Project

## WHAT: Project Overview

Google Cloud Tech Showcase demonstrating **multimodal analytics** with BigQuery, Gemini AI, and Vertex AI. Three domains:

1. **Sentiment Analysis** - Analyze user reviews using Gemini 2.0 Flash in BigQuery
2. **Propensity Modeling** - Predict user retention (7-day return) using BigQuery ML
3. **Campaign Intelligence** - AI-powered campaign recommendations using public Census + theLook eCommerce data

**Medallion Architecture (Bronze → Silver → Gold):**
```
Sentiment Analysis:
  GCS JSON files → bronze_user_reviews (BigLake) → silver_review_sentiment (Gemini)

Propensity Modeling:
  GA4 events_* → silver_events_flattened → gold_training_features → gold_user_retention_model (BQML)

Campaign Intelligence:
  theLook users + Census tracts → silver_users_with_census (ST_CONTAINS) → gold_tract_campaign_features → gold_campaign_recommendations (Gemini)
```

**Key Directories:**
- `definitions/sentiment_analysis/` - Review analysis with Gemini
- `definitions/propensity_modeling/` - User retention ML pipeline
- `definitions/campaign_intelligence/` - Campaign recommendations with Census + eCommerce data
- `infra/` - Terraform IaC for GCP resources
- `scripts/` - Python scraper for Play Store reviews

## WHY: Architecture Decisions

**Medallion Architecture (Bronze/Silver/Gold)**: Industry-standard data lakehouse pattern for progressive refinement:
- **Bronze** - Raw, immutable data (BigLake Object Tables, external declarations)
- **Silver** - Cleansed, validated, business-ready (flattened events, Gemini-enriched reviews)
- **Gold** - Feature-engineered, analytics-ready (ML training datasets, models)

**Data Mesh with Domains**: Domain-driven organization for business alignment:
- `sentiment_analysis/` - User review analysis with Gemini
- `propensity_modeling/` - User retention prediction with BQML
- `campaign_intelligence/` - Campaign targeting using public Census housing data + theLook digital signals

**Rolling 7-day windows**: Training data uses sliding observation windows, not just "first 7 days". This creates multiple training rows per user and enables continuous churn prediction.

**Feature engineering in `gold_training_features.sqlx`**:
- Features: 7 days prior to observation_date
- Label: Did user return in 7 days after observation_date?
- Filter: `days_active >= 1 AND total_events >= 3`

**BigLake + Gemini**: Query unstructured data (JSON files in GCS) directly without ETL, enrich with AI in a single SQL query.

**Datasets:**
- `sentiment_analysis` - Bronze and Silver layers for review analysis
- `ga4_source` - Silver layer for GA4 events
- `propensity_modeling` - Gold layer for ML models and features
- `campaign_intelligence` - All layers for campaign targeting (Census + theLook)

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
  type: "table",           // declaration, view, table, incremental, or operations
  schema: "dataset_name",
  description: "...",      // Include BRONZE/SILVER/GOLD prefix
  tags: ["domain", "layer", "category"]  // e.g., ["sentiment_analysis", "silver", "staging"]
}
```

Use `${ref("table_name")}` for dependencies. Use `${self()}` in model definitions.

**Naming Conventions:**
- Bronze layer: `bronze_*` prefix (e.g., `bronze_user_reviews`)
- Silver layer: `silver_*` prefix (e.g., `silver_review_sentiment`, `silver_events_flattened`)
- Gold layer: `gold_*` prefix (e.g., `gold_training_features`, `gold_user_retention_model`)

**Tags:**
- Domain: `sentiment_analysis`, `propensity_modeling`, or `campaign_intelligence`
- Layer: `bronze`, `silver`, or `gold`
- Category: `sources`, `staging`, `marts`, `ml`, `models`, `examples`

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
1. Edit `definitions/propensity_modeling/marts/gold_training_features.sqlx`
2. Add calculation in `user_training_features` CTE
3. Include in final SELECT with `COALESCE`
4. Add to model's SELECT and TRANSFORM if needed

**Modify the model:**
1. Edit `definitions/propensity_modeling/ml/gold_user_retention_model.sqlx`
2. Add feature to SELECT clause
3. Add preprocessing in TRANSFORM if needed (scaling, bucketing)

**Scrape more reviews:**
1. Edit `scripts/scrape_play_store_reviews.py` to add new apps
2. Run: `cd scripts && python scrape_play_store_reviews.py`
3. JSON files are automatically uploaded to GCS via Terraform-generated .env

**Query sentiment analysis:**
1. Use BigQuery Console
2. Query `sentiment_analysis.silver_review_sentiment` table
3. Filter by sentiment, category, date range, etc.

## Important Files

**Sentiment Analysis:**
| File | Purpose |
|------|---------|
| `sentiment_analysis/sources/bronze_user_reviews.sqlx` | BigLake Object Table for JSON files in GCS |
| `sentiment_analysis/staging/silver_review_sentiment.sqlx` | Gemini AI sentiment enrichment (incremental) |
| `scripts/scrape_play_store_reviews.py` | Python scraper for Play Store reviews |

**Propensity Modeling:**
| File | Purpose |
|------|---------|
| `propensity_modeling/staging/silver_events_flattened.sqlx` | Flattens nested GA4 event_params |
| `propensity_modeling/marts/gold_training_features.sqlx` | Rolling 7-day window feature engineering |
| `propensity_modeling/ml/gold_user_retention_model.sqlx` | BQML logistic regression with Vertex AI |

**Campaign Intelligence:**
| File | Purpose |
|------|---------|
| `campaign_intelligence/sources/thelook_*.sqlx` | theLook eCommerce public dataset declarations |
| `campaign_intelligence/sources/census_*.sqlx` | Census tracts and ACS housing data declarations |
| `campaign_intelligence/staging/silver_users_with_census.sqlx` | Users joined to census tracts via ST_CONTAINS |
| `campaign_intelligence/staging/silver_engagement_signals.sqlx` | Aggregated digital engagement by user |
| `campaign_intelligence/staging/silver_tract_demographics.sqlx` | Housing tenure and income by tract |
| `campaign_intelligence/marts/gold_tract_campaign_features.sqlx` | Campaign scoring by census tract |
| `campaign_intelligence/marts/gold_user_segments.sqlx` | User segments with propensity scores |
| `campaign_intelligence/models/gemini_campaign_agent.sqlx` | Remote Gemini model for recommendations |
| `campaign_intelligence/models/gold_campaign_recommendations.sqlx` | AI-generated campaign recommendations |

**Infrastructure:**
| File | Purpose |
|------|---------|
| `infra/main.tf` | All GCP resource definitions (GCS, BigQuery, Vertex AI) |
| `workflow_settings.yaml` | Dataform configuration (project, dataset, location) |

## Source Data

**GA4 Events (Propensity Modeling):**
- Dataset: `firebase-public-project.analytics_153293282.events_*`
- Date range: June 12, 2018 - October 3, 2018
- App: Flood-It! (gaming app)

**User Reviews (Sentiment Analysis):**
- Source: Google Play Store (scraped via Python)
- Storage: GCS bucket `gs://gcloud-tech-showcase-multimodal-data/user-reviews/play-store/flood-it/`
- Format: JSON files with review metadata and text

**theLook eCommerce (Campaign Intelligence):**
- Dataset: `bigquery-public-data.thelook_ecommerce`
- Tables: `users`, `events`, `orders`
- Contains: User demographics with lat/long, web events, purchase transactions

**Census Data (Campaign Intelligence):**
- Tracts: `bigquery-public-data.geo_census_tracts.us_census_tracts_national`
- ACS: `bigquery-public-data.census_bureau_acs.censustract_2018_5yr`
- Contains: Geographic boundaries, housing tenure, income demographics

## Security

Never commit:
- `terraform.tfvars` (contains project ID and GitHub token)
- `workflow_settings.yaml` (contains project-specific config)
- `.terraform/` directory
- `*.tfstate` files
- `scripts/.env` (auto-generated by Terraform)
- `scripts/service-account-key.json` (auto-generated by Terraform)

## Guidelines

1. Read files before editing - understand existing patterns
2. Ensure `${ref()}` targets exist before referencing
3. Run `terraform plan` before `terraform apply`
4. Never output or log secrets/tokens
