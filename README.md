# Google Cloud Tech Showcase: Multimodal Analytics with BigQuery, Gemini & Vertex AI

This demo showcases Google Cloud's **open lakehouse architecture** for multimodal analytics, combining structured GA4 data with unstructured Play Store reviews using BigQuery, Gemini AI, and Vertex AI.

**What you'll build:**

- **Bronze/Silver/Gold medallion architecture** on BigQuery's open lakehouse
- **Sentiment analysis pipeline** using Gemini AI and BigLake Object Tables
- **User retention ML model** with BigQuery ML and Vertex AI
- **Domain-driven data mesh** with two use cases: sentiment analysis + propensity modeling

**Business context:** Predict which users are likely to churn AND understand why through sentiment analysis of their reviews, enabling targeted retention campaigns with context.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Google Cloud Open Lakehouse                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BRONZE LAYER (Raw, Immutable)                                             │
│  ┌───────────────────┐           ┌─────────────────────────────────┐      │
│  │  Firebase GA4     │           │  Cloud Storage (GCS)            │      │
│  │  Public Dataset   │           │  ┌──────────────────────────┐   │      │
│  │  (Structured)     │           │  │ Play Store Reviews       │   │      │
│  └─────────┬─────────┘           │  │ (JSON - Multimodal)      │   │      │
│            │                      │  └──────────┬───────────────┘   │      │
│            │                      └─────────────┼───────────────────┘      │
│            ▼                                    ▼                          │
│  ┌────────────────────────────────────────────────────────────┐           │
│  │              BigQuery + BigLake + Dataform                  │           │
│  ├────────────────────────────────────────────────────────────┤           │
│  │                                                             │           │
│  │  SILVER LAYER (Cleansed, Enriched)                         │           │
│  │  ┌──────────────────────┐  ┌─────────────────────────┐    │           │
│  │  │ silver_events_       │  │ silver_review_          │    │           │
│  │  │   flattened          │  │   sentiment             │◀───Gemini AI   │
│  │  │ (GA4 unnested)       │  │ (Gemini enriched)       │    │           │
│  │  └──────────────────────┘  └─────────────────────────┘    │           │
│  │                                                             │           │
│  │  GOLD LAYER (Feature-Engineered, ML-Ready)                 │           │
│  │  ┌──────────────────────┐  ┌─────────────────────────┐    │           │
│  │  │ gold_training_       │  │ gold_user_              │    │           │
│  │  │   features           │  │   retention_model       │    │           │
│  │  │ (7-day windows)      │  │ (BQML Logistic Reg)     │    │           │
│  │  └──────────────────────┘  └──────────┬──────────────┘    │           │
│  │                                       │                    │           │
│  └───────────────────────────────────────┼────────────────────┘           │
│                                          │                                │
│  ┌───────────────────────────────────────▼─────────────────────────────┐ │
│  │                     Vertex AI Platform                               │ │
│  │  ┌──────────────────────┐         ┌─────────────────────────────┐   │ │
│  │  │  Model Registry      │         │  Gemini Models              │   │ │
│  │  │  (Versioning)        │         │  (gemini-2.0-flash-001)     │   │ │
│  │  └──────────────────────┘         └─────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Mesh Domains:**
- `sentiment_analysis/` - Multimodal review analysis with Gemini
- `propensity_modeling/` - User retention prediction with BQML
- `analytics/` (future) - Cross-domain user 360° insights

---

## Prerequisites

Before starting, ensure you have:

- [ ] Google Cloud Project with billing enabled
- [ ] `gcloud` CLI installed and authenticated (`gcloud auth login`)
- [ ] Terraform >= 1.6.0 installed
- [ ] GitHub personal access token (for Dataform)
- [ ] Python 3.9+ (for optional review scraping)

---

## Step 1: Configure Your Project

Before deploying, configure your project ID in two places:

### A. Terraform Configuration

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
project_id   = "your-project-id"
github_token = "ghp_your_token_here"
```

### B. Dataform Configuration

```bash
cd ..  # Back to project root
cp workflow_settings.yaml.example workflow_settings.yaml
```

Edit `workflow_settings.yaml`:

```yaml
defaultProject: your-project-id  # ← Change this to match your GCP project
defaultLocation: US
defaultDataset: propensity_modeling

vars:
  region: US
```

---

## Step 2: Deploy the Infrastructure

Terraform provisions all GCP resources following Google Cloud best practices.

```bash
cd infra  # If not already there
```

Deploy:

```bash
terraform init
terraform plan    # Review what will be created
terraform apply   # Type 'yes' to confirm
```

**What gets created:**

| Resource | Purpose |
|----------|---------|
| **BigQuery datasets** | `sentiment_analysis`, `propensity_modeling`, `ga4_source` |
| **GCS bucket** | `{project}-multimodal-data` for review JSON files |
| **BigQuery connection** | `vertex-ai-connection` (US multi-region) for Gemini access |
| **Dataform repository** | Connected to this GitHub repo |
| **IAM bindings** | Service account permissions for BigLake, Vertex AI, GCS |
| **Secret Manager** | Secure GitHub token storage |

---

## Step 2A: Collect Play Store Reviews (Optional)

If you want fresh review data, run the Python scraper:

```bash
cd scripts
pip install -r requirements.txt
python scrape_play_store_reviews.py
```

**What it does:**
- Scrapes Google Play Store reviews for "Flood It!" game
- Uploads each review as a JSON file to GCS: `gs://{project}-multimodal-data/user-reviews/play-store/flood-it/`
- Checkpoint/resume capability for long-running scrapes
- Preserves Unicode (emojis) in review text

**Sample review JSON:**
```json
{
  "platform": "play-store",
  "review_id": "abc123",
  "user_name": "John Doe",
  "review_text": "🎮 Love this game!",
  "rating": 5,
  "review_date": "2018-06-20",
  "app_version": "2.98",
  "thumbs_up_count": 12,
  "scraped_at": "2026-02-04T21:41:05Z"
}
```

**Note:** Pre-scraped reviews are already in GCS if you skip this step.

---

## Step 2B: Run the Data Pipeline

The Dataform pipeline builds the medallion architecture (bronze → silver → gold).

1. Open **Google Cloud Console → Dataform**
2. Select the `data-cloud` repository
3. Create a **Development Workspace** (name must match branch: `claude/gemini-bigquery-unstructured-data-OuNWR`)
4. Click **Start Compilation** → **Create**
5. Click **Start Execution** → Select workflow by tags:
   - Run `sentiment_analysis` tag for sentiment pipeline
   - Run `propensity_modeling` tag for retention model
   - Or run all

**What gets built:**

### Sentiment Analysis Domain

| Object | Layer | Type | Description |
|--------|-------|------|-------------|
| `bronze_user_reviews` | Bronze | BigLake Object Table | Raw review JSON from GCS |
| `gemini_sentiment_model` | - | Remote Model | Gemini 2.0 Flash endpoint |
| `silver_review_sentiment` | Silver | Incremental Table | Gemini-enriched sentiment analysis |

### Propensity Modeling Domain

| Object | Layer | Type | Description |
|--------|-------|------|-------------|
| `events_*` (external) | Bronze | Declaration | Firebase GA4 public dataset |
| `silver_events_flattened` | Silver | View | Unnested GA4 event parameters |
| `silver_user_sessions` | Silver | View | Session-level aggregations |
| `gold_training_features` | Gold | Table | 7-day rolling window features (~18K rows) |
| `gold_user_retention_model` | Gold | BQML Model | Logistic regression, registered in Vertex AI |

---

## Step 3: Explore Sentiment Analysis

### Query the Bronze Layer (Raw Reviews)

```sql
SELECT
  uri,
  SAFE_CONVERT_BYTES_TO_STRING(data) AS review_json
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 5;
```

### Query the Silver Layer (Gemini-Enriched)

```sql
SELECT
  review_date,
  rating,
  review_text,
  sentiment,        -- positive/neutral/negative
  category,         -- performance/ads/difficulty/bugs/praise/other
  sentiment_score   -- -1 to +1
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 10;
```

**Sentiment distribution:**

```sql
SELECT
  sentiment,
  COUNT(*) AS review_count,
  ROUND(AVG(rating), 2) AS avg_rating,
  ROUND(AVG(sentiment_score), 3) AS avg_sentiment_score
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY sentiment
ORDER BY avg_sentiment_score DESC;
```

**Category breakdown:**

```sql
SELECT
  category,
  sentiment,
  COUNT(*) AS count
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY category, sentiment
ORDER BY category, count DESC;
```

---

## Step 4: Explore Propensity Modeling

### Query the Gold Training Features

```sql
SELECT
  user_pseudo_id,
  observation_date,
  days_active,
  total_events,
  level_completion_rate,
  will_return  -- Label: did user return in next 7 days?
FROM `propensity_modeling.gold_training_features`
LIMIT 10;
```

### Check Class Balance

```sql
SELECT
  will_return,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `propensity_modeling.gold_training_features`
GROUP BY will_return;
```

### Feature Engineering Approach

The model uses **rolling 7-day windows**:
- **Features**: User behavior from 7 days prior to observation_date
- **Label**: Did user return in 7 days after observation_date?
- **Result**: Multiple training rows per user (weekly snapshots)

| Category | Features |
|----------|----------|
| **Activity** | `days_active`, `total_events`, `events_per_day` |
| **Engagement** | `total_engagement_minutes`, `engagement_minutes_per_day`, `days_since_last_activity` |
| **Gameplay** | `levels_started`, `levels_completed`, `level_completion_rate` |
| **Scoring** | `max_score`, `avg_score` |
| **Device** | `device_category`, `operating_system`, `country` |

---

## Step 5: Analyze the Retention Model

### Model Evaluation Metrics

```sql
SELECT *
FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);
```

Key metrics:
- **Precision**: Of predicted churners, what % actually churned?
- **Recall**: Of actual churners, what % did we identify?
- **AUC-ROC**: Model discrimination ability (0.5 = random, 1.0 = perfect)

### Feature Importance

```sql
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY attribution DESC
LIMIT 10;
```

### Confusion Matrix

```sql
SELECT *
FROM ML.CONFUSION_MATRIX(MODEL `propensity_modeling.gold_user_retention_model`);
```

---

## Step 6: Run Predictions

### Batch Predictions with Risk Segmentation

```sql
SELECT
  user_pseudo_id,
  predicted_will_return,
  (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability,
  CASE
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.3 THEN 'HIGH CHURN RISK'
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.6 THEN 'MEDIUM RISK'
    ELSE 'LOW RISK'
  END AS risk_category
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features` LIMIT 100)
)
ORDER BY return_probability ASC;
```

### Score a New User (Simulated)

```sql
SELECT
  predicted_will_return,
  predicted_will_return_probs
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT
    7 AS days_in_window,
    3 AS days_active,
    45 AS total_events,
    6.4 AS events_per_day,
    2.5 AS engagement_minutes_per_day,
    5 AS levels_started,
    3 AS levels_completed,
    0 AS levels_failed,
    0.6 AS level_completion_rate,
    17.5 AS total_engagement_minutes,
    150 AS max_score,
    75.0 AS avg_score,
    15.0 AS events_per_active_day,
    2 AS days_since_last_activity,
    'mobile' AS device_category,
    'Android' AS operating_system,
    'United States' AS country
  )
);
```

---

## Step 7: Cross-Domain Analytics (Future)

**Combine sentiment + propensity for user 360°:**

```sql
-- Future: Join sentiment aggregates with churn predictions
SELECT
  p.user_pseudo_id,
  p.return_probability,
  p.risk_category,
  s.avg_sentiment_score,
  s.negative_review_count,
  s.last_review_date
FROM propensity_predictions p
LEFT JOIN user_sentiment_summary s
  ON p.user_pseudo_id = s.user_pseudo_id
WHERE p.risk_category = 'HIGH CHURN RISK'
  AND s.avg_sentiment_score < -0.5
ORDER BY p.return_probability ASC;
```

**Insight:** Target high-risk churners with recent negative sentiment for personalized retention campaigns.

---

## Step 8: (Optional) Deploy to Vertex AI Endpoint

For real-time inference:

1. Go to **Vertex AI → Model Registry**
2. Find `gold_user_retention_model` (auto-registered)
3. Click **Deploy to Endpoint**
4. Configure machine type and deploy

**Call the endpoint:**

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT/locations/us-central1/endpoints/ENDPOINT_ID:predict" \
  -d '{
    "instances": [{
      "days_in_window": 7,
      "days_active": 3,
      "total_events": 45,
      "events_per_day": 6.4,
      ...
    }]
  }'
```

---

## Medallion Architecture Explained

This project follows the **bronze/silver/gold pattern** popularized by modern lakehouses:

### 🥉 Bronze Layer - Raw, Immutable
- **Purpose**: Landing zone for raw data as-is
- **Examples**: BigLake Object Tables, external declarations
- **Naming**: `bronze_*` prefix
- **Characteristics**: No transformations, append-only, full audit trail

### 🥈 Silver Layer - Cleansed, Validated
- **Purpose**: Business-ready data with quality checks
- **Examples**: Flattened events, Gemini-enriched reviews
- **Naming**: `silver_*` prefix
- **Characteristics**: Type conversions, unnesting, enrichment, deduplication

### 🥇 Gold Layer - Feature-Engineered, Analytics-Ready
- **Purpose**: ML-ready features and business aggregations
- **Examples**: Training datasets, BQML models, aggregated marts
- **Naming**: `gold_*` prefix
- **Characteristics**: Feature engineering, aggregations, ML models

**Why medallion + data mesh?**
- **Medallion**: Clear data quality layers (bronze → silver → gold)
- **Data Mesh**: Domain ownership (sentiment_analysis, propensity_modeling)
- **Result**: Scalable, governed, domain-driven lakehouse

---

## Project Structure

```
.
├── infra/                              # Terraform IaC
│   ├── main.tf                         # All GCP resources
│   ├── variables.tf                    # Input variables
│   └── terraform.tfvars.example        # Config template
│
├── scripts/                            # Data collection
│   ├── scrape_play_store_reviews.py    # Review scraper with checkpointing
│   └── requirements.txt                # Python dependencies
│
├── definitions/                        # Dataform SQL pipeline
│   ├── sentiment_analysis/
│   │   ├── sources/
│   │   │   └── bronze_user_reviews.sqlx          # BigLake Object Table
│   │   ├── models/
│   │   │   └── gemini_sentiment_model.sqlx       # Remote Gemini model
│   │   └── staging/
│   │       └── silver_review_sentiment.sqlx      # Gemini-enriched (incremental)
│   │
│   └── propensity_modeling/
│       ├── sources/
│       │   └── ga4_events.sqlx                   # External GA4 declaration
│       ├── staging/
│       │   ├── silver_events_flattened.sqlx      # Unnested GA4 events
│       │   └── silver_user_sessions.sqlx         # Session aggregations
│       ├── marts/
│       │   └── gold_training_features.sqlx       # 7-day rolling windows
│       └── ml/
│           ├── gold_user_retention_model.sqlx    # BQML logistic regression
│           ├── predictions.sqlx                  # Example prediction queries
│           └── model_evaluation.sqlx             # Model evaluation queries
│
├── package.json                        # Dataform dependencies
├── workflow_settings.yaml              # Dataform project config
├── CLAUDE.md                           # Project development guide
└── README.md
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Infrastructure** | Terraform 1.6+ | One-click deployment of GCP resources |
| **Data Warehouse** | BigQuery | Storage, transformation, SQL analytics |
| **Multimodal Data** | BigLake Object Tables | Unstructured data in GCS queryable via SQL |
| **AI/ML** | Gemini 2.0 Flash | Multimodal sentiment analysis |
| **ML Training** | BigQuery ML | In-database logistic regression |
| **Model Management** | Vertex AI | Model registry, versioning, deployment |
| **Data Transformation** | Dataform 3.0 | SQL-based ETL with Git integration |
| **Orchestration** | Dataform Workflows | Scheduled execution with tags |
| **Secrets** | Secret Manager | Secure GitHub token storage |
| **Review Collection** | Python + google-play-scraper | Automated review scraping |

---

## Source Data

### Sentiment Analysis
- **Source**: Google Play Store (Flood It! game)
- **Collection**: Python scraper with checkpoint/resume
- **Format**: JSON files in GCS (one per review)
- **Date Range**: Configurable (defaults to all available)
- **Volume**: ~500+ reviews with emojis and Unicode preserved

### Propensity Modeling
- **Source**: `firebase-public-project.analytics_153293282.events_*`
- **Date Range**: June 12, 2018 – October 3, 2018
- **Events**: ~5.7M raw GA4 events
- **Users**: ~15K unique users

---

## Key Features

✅ **Medallion architecture** with bronze/silver/gold layers
✅ **Domain-driven data mesh** with clear ownership
✅ **Multimodal analytics** - structured + unstructured data
✅ **Gemini AI integration** via BigQuery remote models
✅ **BigLake Object Tables** for GCS data without movement
✅ **Incremental pipelines** to minimize cost and reprocessing
✅ **Feature engineering** with rolling time windows
✅ **BigQuery ML** with Vertex AI model registry
✅ **Tag-based workflows** for selective execution
✅ **Google Cloud native** - follows official best practices

---

## Cleanup

To remove all deployed resources:

```bash
cd infra
terraform destroy
```

**Note:** This preserves GCS data (multimodal bucket has `force_destroy = false`). Delete manually if needed.

---

## Next Steps

1. **Build gold-layer aggregations**: Create `sentiment_analysis/marts/gold_user_sentiment_summary.sqlx`
2. **Cross-domain joins**: Join sentiment with propensity predictions
3. **Vertex AI Feature Store**: Register gold tables as online features
4. **Looker Studio dashboard**: Visualize sentiment trends + churn risk
5. **Productionize**: Add data quality assertions, monitoring, alerting

---

## License

This project is provided for educational and demonstration purposes.
