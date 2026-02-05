# Usage Guide

This guide provides SQL query examples and usage patterns for analyzing sentiment and propensity data.

---

## Table of Contents

- [Sentiment Analysis Queries](#sentiment-analysis-queries)
- [Propensity Modeling Queries](#propensity-modeling-queries)
- [Model Evaluation](#model-evaluation)
- [Making Predictions](#making-predictions)
- [Cross-Domain Analytics](#cross-domain-analytics)
- [Vertex AI Deployment](#vertex-ai-deployment)

---

## Sentiment Analysis Queries

### Query Bronze Layer (Raw Reviews)

View raw review JSON from GCS via BigLake Object Table:

```sql
SELECT
  uri,
  SAFE_CONVERT_BYTES_TO_STRING(data) AS review_json
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 5;
```

**Output:**
```
uri                                              | review_json
------------------------------------------------|----------------------------------------
gs://.../review_abc123.json                      | {"platform": "play-store", ...}
gs://.../review_def456.json                      | {"platform": "play-store", ...}
```

---

### Query Silver Layer (Gemini-Enriched Reviews)

Get sentiment-enriched reviews:

```sql
SELECT
  review_date,
  rating,
  review_text,
  sentiment,        -- positive, neutral, negative
  category,         -- performance, ads, difficulty, bugs, praise, other
  sentiment_score   -- Range: -1 (negative) to +1 (positive)
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 10;
```

---

### Sentiment Distribution

Aggregate sentiment counts and scores:

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

**Sample output:**
```
sentiment | review_count | avg_rating | avg_sentiment_score
----------|--------------|------------|--------------------
positive  | 327          | 4.8        | 0.856
neutral   | 98           | 3.2        | 0.012
negative  | 75           | 1.6        | -0.742
```

---

### Category Breakdown

Analyze sentiment by review category:

```sql
SELECT
  category,
  sentiment,
  COUNT(*) AS count,
  ROUND(AVG(rating), 1) AS avg_rating
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY category, sentiment
ORDER BY category, count DESC;
```

**Sample output:**
```
category     | sentiment | count | avg_rating
-------------|-----------|-------|------------
ads          | negative  | 42    | 1.8
ads          | neutral   | 15    | 3.0
difficulty   | positive  | 38    | 4.5
difficulty   | neutral   | 22    | 3.5
performance  | negative  | 18    | 2.1
praise       | positive  | 156   | 5.0
```

---

### Time Series Analysis

Track sentiment trends over time:

```sql
SELECT
  DATE_TRUNC(review_date, MONTH) AS month,
  sentiment,
  COUNT(*) AS review_count,
  ROUND(AVG(sentiment_score), 3) AS avg_score
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY month, sentiment
ORDER BY month, sentiment;
```

---

### Find Emoji Usage

Extract reviews with emojis (Unicode preserved):

```sql
SELECT
  review_date,
  rating,
  review_text,
  sentiment
FROM `sentiment_analysis.silver_review_sentiment`
WHERE REGEXP_CONTAINS(review_text, r'[\x{1F600}-\x{1F64F}]')  -- Emoticons
   OR REGEXP_CONTAINS(review_text, r'[\x{1F300}-\x{1F5FF}]')  -- Misc symbols
ORDER BY review_date DESC
LIMIT 20;
```

---

### Most Helpful Reviews

Find reviews with high engagement:

```sql
SELECT
  user_name,
  review_date,
  rating,
  LEFT(review_text, 100) AS review_snippet,
  thumbs_up_count,
  sentiment,
  category
FROM `sentiment_analysis.silver_review_sentiment`
WHERE thumbs_up_count > 10
ORDER BY thumbs_up_count DESC
LIMIT 10;
```

---

## Propensity Modeling Queries

### Explore Training Features

View raw training data with features and labels:

```sql
SELECT
  user_pseudo_id,
  observation_date,
  days_active,
  total_events,
  events_per_day,
  level_completion_rate,
  engagement_minutes_per_day,
  days_since_last_activity,
  will_return  -- Label: 1 = returned, 0 = churned
FROM `propensity_modeling.gold_training_features`
ORDER BY observation_date, user_pseudo_id
LIMIT 10;
```

---

### Check Class Balance

Verify label distribution (important for model quality):

```sql
SELECT
  will_return,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `propensity_modeling.gold_training_features`
GROUP BY will_return
ORDER BY will_return;
```

**Expected output:**
```
will_return | count | percentage
------------|-------|------------
0           | 7234  | 39.8
1           | 10932 | 60.2
```

**Note:** Ideally, aim for 30-70% split. Severe imbalance may require rebalancing techniques.

---

### Feature Statistics

Get summary statistics for numerical features:

```sql
SELECT
  ROUND(AVG(days_active), 2) AS avg_days_active,
  ROUND(AVG(total_events), 2) AS avg_total_events,
  ROUND(AVG(level_completion_rate), 3) AS avg_completion_rate,
  ROUND(AVG(engagement_minutes_per_day), 2) AS avg_engagement_minutes,
  ROUND(AVG(events_per_day), 2) AS avg_events_per_day
FROM `propensity_modeling.gold_training_features`;
```

---

### User Lifecycle Segments

Segment users by engagement level:

```sql
SELECT
  CASE
    WHEN days_active >= 6 THEN 'Highly Active'
    WHEN days_active >= 4 THEN 'Moderately Active'
    WHEN days_active >= 2 THEN 'Lightly Active'
    ELSE 'Very Inactive'
  END AS activity_segment,
  COUNT(*) AS user_count,
  ROUND(AVG(will_return) * 100, 1) AS retention_rate_pct,
  ROUND(AVG(level_completion_rate), 3) AS avg_completion_rate
FROM `propensity_modeling.gold_training_features`
GROUP BY activity_segment
ORDER BY retention_rate_pct DESC;
```

---

### Cohort Analysis

Compare retention by observation period:

```sql
SELECT
  observation_date,
  COUNT(*) AS users_observed,
  SUM(will_return) AS users_returned,
  ROUND(AVG(will_return) * 100, 1) AS retention_rate_pct
FROM `propensity_modeling.gold_training_features`
GROUP BY observation_date
ORDER BY observation_date;
```

---

## Model Evaluation

### Overall Model Metrics

Get precision, recall, accuracy, and AUC-ROC:

```sql
SELECT *
FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);
```

**Key metrics:**
- **Precision**: Of predicted churners, what % actually churned?
- **Recall**: Of actual churners, what % did we identify?
- **Accuracy**: Overall correctness of predictions
- **AUC-ROC**: Discrimination ability (0.5 = random, 1.0 = perfect)

**Example output:**
```
precision | recall | accuracy | f1_score | log_loss | roc_auc
----------|--------|----------|----------|----------|--------
0.72      | 0.68   | 0.74     | 0.70     | 0.52     | 0.79
```

**Interpretation:**
- **AUC 0.79**: Good discrimination (much better than random)
- **Precision 0.72**: 72% of predicted churners actually churned
- **Recall 0.68**: Caught 68% of actual churners

---

### Feature Importance

Identify which features drive predictions (via global explainability):

```sql
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY attribution DESC
LIMIT 10;
```

**Sample output:**
```
feature                      | attribution
-----------------------------|------------
days_active                  | 0.234
level_completion_rate        | 0.189
days_since_last_activity     | 0.156
engagement_minutes_per_day   | 0.142
events_per_day               | 0.098
total_events                 | 0.087
...
```

**Interpretation:** Higher attribution = more important for predictions.

---

### Confusion Matrix

See true positives, false positives, etc.:

```sql
SELECT *
FROM ML.CONFUSION_MATRIX(MODEL `propensity_modeling.gold_user_retention_model`);
```

**Sample output:**
```
actual_label | predicted_label | count
-------------|-----------------|-------
0            | 0               | 4821   (True Negatives)
0            | 1               | 2413   (False Positives)
1            | 0               | 3498   (False Negatives)
1            | 1               | 7434   (True Positives)
```

---

### Precision-Recall Curve Data

Analyze trade-offs at different thresholds:

```sql
SELECT
  threshold,
  precision,
  recall,
  f1_score,
  true_positives,
  false_positives,
  false_negatives
FROM ML.ROC_CURVE(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY threshold;
```

---

## Making Predictions

### Batch Predictions with Risk Segmentation

Score a batch of users and segment by churn risk:

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

**Sample output:**
```
user_pseudo_id     | predicted_will_return | return_probability | risk_category
-------------------|----------------------|--------------------|-----------------
1234567890.1234567 | 0                    | 0.18               | HIGH CHURN RISK
2345678901.2345678 | 0                    | 0.24               | HIGH CHURN RISK
3456789012.3456789 | 0                    | 0.42               | MEDIUM RISK
4567890123.4567890 | 1                    | 0.68               | LOW RISK
5678901234.5678901 | 1                    | 0.85               | LOW RISK
```

---

### Score a Single User (Simulated Data)

Test the model with hypothetical user features:

```sql
SELECT
  predicted_will_return,
  (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 0) AS churn_probability,
  (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability
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

**Sample output:**
```
predicted_will_return | churn_probability | return_probability
----------------------|-------------------|--------------------
1                     | 0.35              | 0.65
```

**Interpretation:** 65% likely to return (moderate retention).

---

### Explain Individual Predictions

Use local explainability to understand why a specific prediction was made:

```sql
SELECT *
FROM ML.EXPLAIN_PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`
   WHERE user_pseudo_id = '1234567890.1234567' LIMIT 1)
);
```

**Output:** Feature attributions for that specific user's prediction.

---

### Bulk Export Predictions

Save predictions to a new table for downstream use:

```sql
CREATE OR REPLACE TABLE `propensity_modeling.predictions_latest` AS
SELECT
  user_pseudo_id,
  observation_date,
  predicted_will_return,
  (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability,
  CASE
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.3 THEN 'HIGH'
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.6 THEN 'MEDIUM'
    ELSE 'LOW'
  END AS churn_risk,
  CURRENT_TIMESTAMP() AS scored_at
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`)
);
```

---

## Cross-Domain Analytics

Combine sentiment analysis with propensity predictions for actionable insights.

### High-Risk Users with Negative Sentiment (Future)

**Note:** This requires building `gold_user_sentiment_summary` in the sentiment_analysis domain.

```sql
-- Example query (requires additional aggregation tables)
SELECT
  p.user_pseudo_id,
  p.return_probability,
  p.risk_category,
  s.avg_sentiment_score,
  s.negative_review_count,
  s.last_review_date,
  s.last_review_text
FROM `propensity_modeling.predictions_latest` p
LEFT JOIN `sentiment_analysis.gold_user_sentiment_summary` s
  ON p.user_pseudo_id = s.user_pseudo_id
WHERE p.risk_category = 'HIGH CHURN RISK'
  AND s.avg_sentiment_score < -0.5
ORDER BY p.return_probability ASC, s.avg_sentiment_score ASC
LIMIT 20;
```

**Business insight:** Target these users for personalized retention campaigns addressing their specific complaints.

---

### Sentiment-Driven Churn Drivers

Identify common complaints among churners:

```sql
-- Aggregate sentiment categories for churned vs retained users
WITH user_outcomes AS (
  SELECT
    user_pseudo_id,
    AVG(will_return) AS retention_rate
  FROM `propensity_modeling.gold_training_features`
  GROUP BY user_pseudo_id
),
user_sentiments AS (
  SELECT
    user_name,  -- Note: May not have user_pseudo_id linkage
    category,
    sentiment,
    sentiment_score
  FROM `sentiment_analysis.silver_review_sentiment`
)
SELECT
  us.category,
  us.sentiment,
  COUNT(*) AS review_count,
  ROUND(AVG(us.sentiment_score), 3) AS avg_score
FROM user_sentiments us
-- JOIN logic would depend on having a user linkage field
GROUP BY us.category, us.sentiment
ORDER BY review_count DESC;
```

---

## Vertex AI Deployment

### Deploy Model to Endpoint (via Console)

1. Go to **Vertex AI** → **Model Registry**
2. Find `gold_user_retention_model`
3. Click **Deploy to Endpoint**
4. Configure:
   - **Endpoint name**: `user-retention-endpoint`
   - **Machine type**: `n1-standard-2` (or higher for better latency)
   - **Min replicas**: 1
   - **Max replicas**: 3 (autoscaling)
5. Click **Deploy**

**Deployment time:** ~10-15 minutes

---

### Call Endpoint via REST API

After deployment, get predictions via HTTP:

```bash
#!/bin/bash

PROJECT_ID="your-project-id"
ENDPOINT_ID="1234567890123456789"  # From Vertex AI console
LOCATION="us-central1"

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/endpoints/${ENDPOINT_ID}:predict" \
  -d '{
    "instances": [
      {
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
        "max_score": 150.0,
        "avg_score": 75.0,
        "events_per_active_day": 15.0,
        "days_since_last_activity": 2,
        "device_category": "mobile",
        "operating_system": "Android",
        "country": "United States"
      }
    ]
  }'
```

**Response:**
```json
{
  "predictions": [{
    "predicted_will_return": [1],
    "predicted_will_return_probs": [
      {"label": "0", "prob": 0.35},
      {"label": "1", "prob": 0.65}
    ]
  }],
  "deployedModelId": "1234567890123456789"
}
```

---

### Call Endpoint via Python

```python
from google.cloud import aiplatform

aiplatform.init(project="your-project-id", location="us-central1")

endpoint = aiplatform.Endpoint("projects/PROJECT_NUM/locations/us-central1/endpoints/ENDPOINT_ID")

instances = [{
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
    "max_score": 150.0,
    "avg_score": 75.0,
    "events_per_active_day": 15.0,
    "days_since_last_activity": 2,
    "device_category": "mobile",
    "operating_system": "Android",
    "country": "United States"
}]

response = endpoint.predict(instances=instances)
print(response.predictions)
```

---

## Performance Tips

### Optimize BigQuery Costs

1. **Use clustering on frequently filtered columns:**
```sql
-- Add to gold_training_features.sqlx config
config {
  type: "table",
  cluster_by: ["observation_date", "will_return"]
}
```

2. **Partition large tables by date:**
```sql
config {
  type: "table",
  partition_by: "observation_date"
}
```

3. **Use `LIMIT` for exploratory queries:**
```sql
SELECT * FROM large_table LIMIT 100;
```

4. **Check query cost before running:**
   - Use "Query Validator" in BigQuery UI (shows bytes to be processed)
   - Set daily spending limits in BigQuery console

---

### Speed Up Model Training

1. **Reduce training data size (for iteration):**
```sql
-- In gold_user_retention_model.sqlx
AS SELECT * FROM ${ref("gold_training_features")}
WHERE observation_date >= '2018-08-01'  -- Reduce date range
```

2. **Use sampling for experimentation:**
```sql
AS SELECT * FROM ${ref("gold_training_features")}
WHERE RAND() < 0.5  -- 50% sample
```

3. **Enable early stopping (BQML automatic):**
   - BigQuery ML stops training when loss plateaus

---

## Next Steps

- **[Setup Guide](setup.md)** - Installation and configuration
- **[Architecture Guide](architecture.md)** - Technical design deep dive
- **[README.md](../README.md)** - Project overview
- **[CLAUDE.md](../CLAUDE.md)** - Development guide

---

## Additional Resources

- **BigQuery ML Docs:** https://cloud.google.com/bigquery/docs/bqml-introduction
- **Gemini API Docs:** https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini
- **BigLake Docs:** https://cloud.google.com/bigquery/docs/biglake-intro
- **Dataform Docs:** https://cloud.google.com/dataform/docs
- **Vertex AI Docs:** https://cloud.google.com/vertex-ai/docs
