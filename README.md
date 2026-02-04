# Google Cloud Tech Showcase: Propensity Modeling with BQML and Vertex AI

This walkthrough demonstrates how to build an end-to-end **user retention prediction** pipeline using Google Cloud's data and AI tools. You'll deploy infrastructure, transform data, train a machine learning model, and run predictions—all using SQL.

**What you'll build:**

- A data pipeline that transforms raw GA4 events into ML-ready features
- A logistic regression model trained directly in BigQuery
- Batch and real-time inference capabilities

**Business context:** Predict which users are likely to churn so you can target them with retention campaigns before they leave.

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                       Google Cloud Platform                           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │   Firebase   │    │   Dataform   │    │       BigQuery         │  │
│  │  Public Data │───▶│  (SQL ETL)   │───▶│  ┌────────────────┐   │  │
│  │  (GA4 Events)│    │              │    │  │  training_data │   │  │
│  └──────────────┘    └──────────────┘    │  └───────┬────────┘   │  │
│                                          │          │             │  │
│                                          │          ▼             │  │
│                                          │  ┌────────────────┐   │  │
│                                          │  │   BQML Model   │   │  │
│                                          │  │ (Logistic Reg) │   │  │
│                                          │  └───────┬────────┘   │  │
│                                          └──────────┼────────────┘  │
│                                                     │               │
│                            ┌────────────────────────┼─────────────┐ │
│                            │                        ▼             │ │
│                            │  ┌────────────────────────────────┐ │ │
│                            │  │   Vertex AI Model Registry     │ │ │
│                            │  │   (Versioning & Governance)    │ │ │
│                            │  └───────────────┬────────────────┘ │ │
│                            │                  │                   │ │
│                            │                  ▼                   │ │
│                            │  ┌────────────────────────────────┐ │ │
│                            │  │     Vertex AI Endpoint         │ │ │
│                            │  │   (Real-time Predictions)      │ │ │
│                            │  └────────────────────────────────┘ │ │
│                            └─────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

Before starting, ensure you have:

- [ ] Google Cloud Project with billing enabled
- [ ] `gcloud` CLI installed and authenticated (`gcloud auth login`)
- [ ] Terraform >= 1.6.0 installed
- [ ] GitHub personal access token (for Dataform to sync this repo)

---

## Step 1: Deploy the Infrastructure

Terraform provisions all the GCP resources: BigQuery datasets, Dataform repository, IAM permissions, and networking.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
project_id   = "your-project-id"
github_token = "ghp_your_token_here"
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
| BigQuery datasets | `propensity_modeling`, `ga4_source` |
| Dataform repository | Connected to this GitHub repo |
| Secret Manager secret | Stores your GitHub token securely |
| IAM bindings | Dataform service account permissions |
| VPC network | Private networking for GCP services |

---

## Step 2: Run the Data Pipeline

The Dataform pipeline transforms raw GA4 events into ML-ready training data.

1. Open **Google Cloud Console → Dataform**
2. Select the `data-cloud` repository
3. Click **Start Compilation** → **Create** (fetches latest code from GitHub)
4. Click **Start Execution** → **Start** (runs the full workflow)

**What gets built:**

| Object                                     | Type  | Description                          |
| ------------------------------------------ | ----- | ------------------------------------ |
| `ga4_source.v_events_flattened`            | View  | Flattens nested GA4 event parameters |
| `propensity_modeling.training_data`        | Table | ~18K rows of engineered features     |
| `propensity_modeling.user_retention_model` | Model | Trained BQML logistic regression     |

---

## Step 3: Explore the Training Data

Open **BigQuery Console** and run these queries to understand your data.

**Preview the training data:**

```sql
SELECT *
FROM `propensity_modeling.training_data`
LIMIT 10;
```

**Check the class balance (churned vs. returned):**

```sql
SELECT
  will_return,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `propensity_modeling.training_data`
GROUP BY will_return;
```

**How the features are engineered:**

The model uses a **rolling 7-day window** approach:

- **Features**: User behavior from the 7 days prior to each observation date
- **Label**: Did the user return in the 7 days _after_ the observation date?
- **Result**: Multiple training rows per user (one per weekly snapshot)

| Category       | Features                                                                             |
| -------------- | ------------------------------------------------------------------------------------ |
| **Activity**   | `days_active`, `total_events`, `events_per_day`, `events_per_active_day`             |
| **Engagement** | `total_engagement_minutes`, `engagement_minutes_per_day`, `days_since_last_activity` |
| **Gameplay**   | `levels_started`, `levels_completed`, `levels_failed`, `level_completion_rate`       |
| **Scoring**    | `max_score`, `avg_score`                                                             |
| **Device**     | `device_category`, `operating_system`, `country`                                     |

---

## Step 4: Analyze the Model

**View model evaluation metrics:**

```sql
SELECT *
FROM ML.EVALUATE(MODEL `propensity_modeling.user_retention_model`);
```

Key metrics to look for:

- **Precision**: Of users predicted to return, what % actually did?
- **Recall**: Of users who returned, what % did we identify?
- **AUC-ROC**: Model's ability to distinguish churners from returners (0.5 = random, 1.0 = perfect)

**View feature importance (what drives predictions):**

```sql
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.user_retention_model`)
ORDER BY attribution DESC;
```

**View training progress:**

```sql
SELECT *
FROM ML.TRAINING_INFO(MODEL `propensity_modeling.user_retention_model`);
```

**View the confusion matrix:**

```sql
SELECT *
FROM ML.CONFUSION_MATRIX(MODEL `propensity_modeling.user_retention_model`);
```

---

## Step 5: Run Batch Predictions

Score all users in your training data:

```sql
SELECT
  user_pseudo_id,
  observation_date,
  predicted_will_return,
  ROUND(predicted_will_return_probs[OFFSET(1)].prob, 3) AS return_probability,
  ROUND(predicted_will_return_probs[OFFSET(0)].prob, 3) AS churn_probability
FROM ML.PREDICT(
  MODEL `propensity_modeling.user_retention_model`,
  (SELECT * FROM `propensity_modeling.training_data`)
)
ORDER BY churn_probability DESC
LIMIT 20;
```

**Score a hypothetical new user:**

```sql
SELECT
  predicted_will_return,
  ROUND(predicted_will_return_probs[OFFSET(0)].prob, 3) AS churn_probability,
  ROUND(predicted_will_return_probs[OFFSET(1)].prob, 3) AS return_probability
FROM ML.PREDICT(
  MODEL `propensity_modeling.user_retention_model`,
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

## Step 6: Tune the Classification Threshold

The model outputs a probability (0-1). The **threshold** determines when to classify a user as "will return" vs "will churn."

**Default threshold: 0.5**

- Probability >= 0.5 → Predicted to return
- Probability < 0.5 → Predicted to churn

**In BigQuery Console:**

1. Go to your model in the BigQuery explorer
2. Click the **Evaluation** tab
3. Use the **Positive class threshold** slider to see how precision/recall change

**Threshold tradeoffs:**

| Threshold        | Effect                                                             |
| ---------------- | ------------------------------------------------------------------ |
| **Lower (0.3)**  | Higher recall—catches more at-risk users, but more false positives |
| **Higher (0.7)** | Higher precision—fewer but more confident predictions              |

**View the ROC curve data:**

```sql
SELECT *
FROM ML.ROC_CURVE(MODEL `propensity_modeling.user_retention_model`);
```

---

## Step 7: (Optional) Deploy for Real-time Predictions

For real-time inference, deploy the model to a Vertex AI endpoint.

1. Go to **Vertex AI → Model Registry**
2. Find `user_retention_model` (auto-registered during training)
3. Click **Deploy to Endpoint**
4. Configure machine type and deploy

**Call the endpoint via REST API:**

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://REGION-aiplatform.googleapis.com/v1/projects/PROJECT/locations/REGION/endpoints/ENDPOINT_ID:predict" \
  -d '{
    "instances": [{
      "days_in_window": 7,
      "days_active": 3,
      "total_events": 45,
      "events_per_day": 6.4,
      "engagement_minutes_per_day": 2.5,
      "levels_started": 5,
      "levels_completed": 3,
      "levels_failed": 0,
      "level_completion_rate": 0.6,
      "total_engagement_minutes": 17.5,
      "max_score": 150,
      "avg_score": 75.0,
      "events_per_active_day": 15.0,
      "days_since_last_activity": 2,
      "device_category": "mobile",
      "operating_system": "Android",
      "country": "United States"
    }]
  }'
```

---

## Step 8: Explain Individual Predictions

Understand why the model made a specific prediction:

```sql
SELECT *
FROM ML.EXPLAIN_PREDICT(
  MODEL `propensity_modeling.user_retention_model`,
  (SELECT * FROM `propensity_modeling.training_data` LIMIT 5)
);
```

This shows the contribution of each feature to the prediction for each user.

---

## Cleanup

To remove all deployed resources:

```bash
cd infra
terraform destroy
```

---

## Project Structure

```
.
├── infra/                              # Terraform Infrastructure as Code
│   ├── main.tf                         # GCP resources (APIs, BigQuery, Dataform, IAM)
│   ├── variables.tf                    # Input variables
│   ├── outputs.tf                      # Deployment outputs
│   ├── providers.tf                    # Google Cloud provider config
│   ├── versions.tf                     # Version constraints
│   └── terraform.tfvars.example        # Configuration template
│
├── definitions/                        # Dataform SQL pipeline
│   └── propensity_modeling/
│       ├── sources/
│       │   └── ga4_events.sqlx         # Source declaration for Firebase data
│       ├── staging/
│       │   └── v_events_flattened.sqlx # Unnest GA4 nested params → flat columns
│       ├── marts/
│       │   └── training_data.sqlx      # Rolling 7-day window feature engineering
│       └── ml/
│           └── user_retention_model.sqlx   # BQML logistic regression model
│
├── package.json                        # Dataform dependencies
├── workflow_settings.yaml              # Dataform project config
└── README.md
```

---

## Source Data

This demo uses a public Firebase gaming dataset:

| Property   | Value                                                  |
| ---------- | ------------------------------------------------------ |
| Dataset    | `firebase-public-project.analytics_153293282.events_*` |
| Date Range | June 12, 2018 – October 3, 2018                        |
| Events     | ~5.7M raw events                                       |
| Users      | ~15K unique users                                      |

---

## Technology Stack

| Component           | Technology           | Purpose                                   |
| ------------------- | -------------------- | ----------------------------------------- |
| Infrastructure      | Terraform (>= 1.6.0) | One-click deployment of all GCP resources |
| Data Warehouse      | BigQuery             | Storage, transformation, and ML training  |
| Data Transformation | Dataform (3.0.0)     | SQL-based ETL with dependency management  |
| Machine Learning    | BigQuery ML          | In-database model training                |
| Model Management    | Vertex AI            | Model registry, versioning, deployment    |
| Secrets             | Secret Manager       | Secure storage of GitHub token            |

---

## License

This project is provided for educational and demonstration purposes.
