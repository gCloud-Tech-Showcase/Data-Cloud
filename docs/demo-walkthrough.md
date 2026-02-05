# Demo Walkthrough

This guide walks through the key features of the multimodal analytics showcase, demonstrating each capability with actual commands and expected outputs.

**Time:** 20-30 minutes
**Prerequisites:** Infrastructure deployed via [Getting Started](getting-started.md)

---

## Overview

You'll demonstrate:
1. **BigLake** - Query unstructured JSON without ETL
2. **Gemini AI** - Sentiment analysis via SQL
3. **BigQuery ML** - Train and evaluate a churn model
4. **Vertex AI** - Model registry and explainability
5. **Cross-domain analytics** - Combine sentiment + churn predictions

---

## Step 1: Query Raw Reviews with BigLake

BigLake Object Tables let you query GCS files directly without loading data into BigQuery.

### Run This Query

```sql
SELECT
  uri,
  SAFE_CONVERT_BYTES_TO_STRING(data) AS review_json
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 5;
```

### Expected Output

```
uri                                                          | review_json
-------------------------------------------------------------|----------------------------------------
gs://.../user-reviews/play-store/flood-it/review_abc.json    | {"platform": "play-store", "review_id": ...}
gs://.../user-reviews/play-store/flood-it/review_def.json    | {"platform": "play-store", "review_id": ...}
...
```

**💡 Key Point:** Data stays in GCS — no ETL pipeline, no data duplication. BigQuery queries it in place.

---

## Step 2: See Gemini AI Sentiment Analysis

The `silver_review_sentiment` table enriches raw reviews with Gemini 2.0 Flash analysis.

### Run This Query

```sql
SELECT
  review_date,
  rating,
  LEFT(review_text, 80) AS review_snippet,
  sentiment,
  category,
  sentiment_score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 10;
```

### Expected Output

```
review_date | rating | review_snippet                                  | sentiment | category    | sentiment_score
------------|--------|-------------------------------------------------|-----------|-------------|----------------
2018-07-15  | 1      | "This game crashes every time I reach level 3..." | negative  | bugs        | -0.92
2018-08-03  | 2      | "Too many ads! Can't even play anymore"          | negative  | ads         | -0.85
2018-06-22  | 1      | "Waste of time, levels are impossible"           | negative  | difficulty  | -0.78
...
```

**💡 Key Point:** Gemini extracts:
- **Sentiment:** positive, neutral, negative
- **Category:** bugs, ads, difficulty, performance, praise, other
- **Score:** -1 (very negative) to +1 (very positive)

All via `ML.GENERATE_TEXT()` in SQL — no external API calls.

---

## Step 3: Analyze Sentiment Distribution

See how reviews break down by sentiment and category.

### Run This Query

```sql
SELECT
  sentiment,
  category,
  COUNT(*) AS review_count,
  ROUND(AVG(rating), 1) AS avg_rating,
  ROUND(AVG(sentiment_score), 3) AS avg_sentiment_score
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY sentiment, category
ORDER BY sentiment, review_count DESC;
```

### Expected Output

```
sentiment | category    | review_count | avg_rating | avg_sentiment_score
----------|-------------|--------------|------------|--------------------
positive  | praise      | 187          | 5.0        | 0.89
positive  | difficulty  | 52           | 4.6        | 0.72
neutral   | performance | 38           | 3.4        | 0.05
negative  | ads         | 48           | 1.8        | -0.81
negative  | bugs        | 32           | 1.5        | -0.87
```

**💡 Key Point:** Most complaints are about ads and bugs — actionable product feedback from unstructured text.

---

## Step 4: Explore Training Features

The `gold_training_features` table uses rolling 7-day windows to create ML-ready data.

### Run This Query

```sql
SELECT
  user_pseudo_id,
  observation_date,
  days_active,
  total_events,
  level_completion_rate,
  engagement_minutes_per_day,
  will_return  -- Label: 1 = returned, 0 = churned
FROM `propensity_modeling.gold_training_features`
ORDER BY observation_date, user_pseudo_id
LIMIT 10;
```

### Expected Output

```
user_pseudo_id      | observation_date | days_active | total_events | level_completion_rate | engagement_minutes_per_day | will_return
--------------------|------------------|-------------|--------------|----------------------|---------------------------|-------------
1234567890.1234567  | 2018-07-01       | 5           | 78           | 0.72                 | 4.3                       | 1
2345678901.2345678  | 2018-07-01       | 2           | 18           | 0.33                 | 1.1                       | 0
...
```

**💡 Key Point:** Each row is a user snapshot at a point in time. The model learns which behaviors predict return vs. churn.

---

## Step 5: Check Model Performance

Evaluate the BigQuery ML model registered in Vertex AI.

### Run This Query

```sql
SELECT *
FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);
```

### Expected Output

```
precision | recall | accuracy | f1_score | log_loss | roc_auc
----------|--------|----------|----------|----------|--------
0.72      | 0.68   | 0.74     | 0.70     | 0.52     | 0.79
```

**Interpretation:**
- **ROC AUC 0.79:** Good discrimination (much better than random 0.5)
- **Precision 72%:** Of predicted churners, 72% actually churned
- **Recall 68%:** Caught 68% of actual churners

**💡 Key Point:** Production-ready model trained entirely in SQL, no Python/notebooks required.

---

## Step 6: See Feature Importance

Understand which features drive churn predictions.

### Run This Query

```sql
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY attribution DESC
LIMIT 10;
```

### Expected Output

```
feature                      | attribution
-----------------------------|------------
days_active                  | 0.234
level_completion_rate        | 0.189
days_since_last_activity     | 0.156
engagement_minutes_per_day   | 0.142
events_per_day               | 0.098
...
```

**💡 Key Point:** Days active and completion rate are the strongest predictors. Users who play frequently and complete levels are more likely to return.

---

## Step 7: Make Churn Predictions

Score a batch of users and segment by risk.

### Run This Query

```sql
SELECT
  user_pseudo_id,
  predicted_will_return,
  ROUND((SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1), 3) AS return_probability,
  CASE
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.3 THEN 'HIGH CHURN RISK'
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.6 THEN 'MEDIUM RISK'
    ELSE 'LOW RISK'
  END AS risk_category
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features` LIMIT 100)
)
ORDER BY return_probability ASC
LIMIT 10;
```

### Expected Output

```
user_pseudo_id      | predicted_will_return | return_probability | risk_category
--------------------|----------------------|--------------------|-----------------
1234567890.1234567  | 0                    | 0.18               | HIGH CHURN RISK
2345678901.2345678  | 0                    | 0.24               | HIGH CHURN RISK
3456789012.3456789  | 0                    | 0.42               | MEDIUM RISK
4567890123.4567890  | 1                    | 0.68               | LOW RISK
5678901234.5678901  | 1                    | 0.85               | LOW RISK
...
```

**💡 Key Point:** Real-time scoring via SQL. Deploy to Vertex AI endpoint for sub-second predictions via REST API.

---

## Step 8: Cross-Domain Insight (Concept)

Combine sentiment analysis with churn predictions to prioritize interventions.

### Conceptual Query

```sql
-- This requires building gold_user_sentiment_summary first
-- Shown here as a demonstration of the cross-domain value
SELECT
  p.user_pseudo_id,
  p.return_probability,
  p.risk_category,
  s.avg_sentiment_score,
  s.negative_review_count,
  s.most_recent_complaint
FROM predictions_table p
LEFT JOIN sentiment_summary_table s
  ON p.user_pseudo_id = s.user_pseudo_id
WHERE p.risk_category = 'HIGH CHURN RISK'
  AND s.avg_sentiment_score < -0.5
ORDER BY p.return_probability ASC, s.avg_sentiment_score ASC
LIMIT 20;
```

### Business Value

**Without multimodal analytics:**
- "User X has 18% probability of returning" → Generic re-engagement campaign

**With multimodal analytics:**
- "User X has 18% probability of returning AND recent reviews complain about ads" → Targeted offer: "Try premium ad-free for 7 days"

**💡 Key Point:** Combining structured (behavior) + unstructured (sentiment) data enables **contextualized** interventions, not just predictions.

---

## Step 9: Verify Vertex AI Integration

Check that the model is registered in Vertex AI.

### Via Console

1. Navigate to **Vertex AI → Model Registry**
2. Look for `gold_user_retention_model`
3. Click on it to see:
   - Model version
   - Training date
   - Feature schema
   - Explainability enabled

### Via gcloud CLI

```bash
gcloud ai models list \
  --region=us-central1 \
  --filter="displayName:gold_user_retention_model"
```

### Expected Output

```
MODEL_ID                      DISPLAY_NAME                    CONTAINER_IMAGE_URI
1234567890123456789          gold_user_retention_model        gcr.io/cloud-aiplatform/...
```

**💡 Key Point:** BQML models automatically register to Vertex AI with `model_registry='vertex_ai'` option. No manual export required.

---

## Step 10: Review Incremental Processing

The sentiment pipeline uses incremental processing to avoid reprocessing reviews.

### Check Execution Logs

In **Dataform → Executions → silver_review_sentiment**:

**First run:**
```
Processed 523 reviews
BigQuery ML.GENERATE_TEXT() called 523 times
Duration: ~45 seconds
```

**Second run (no new data):**
```
Processed 0 reviews (no new data)
Duration: ~2 seconds
```

**Third run (50 new reviews added to GCS):**
```
Processed 50 reviews
BigQuery ML.GENERATE_TEXT() called 50 times
Duration: ~8 seconds
```

**💡 Key Point:** Incremental table with `uniqueKey: ["review_id"]` ensures we only call Gemini API for new reviews — cost optimization built in.

---

## Demo Summary

You've demonstrated:

| Capability | Technology | Business Value |
|------------|------------|----------------|
| **Query unstructured data without ETL** | BigLake Object Tables | Faster time-to-insight, lower cost |
| **AI enrichment via SQL** | Gemini 2.0 Flash | No external APIs, native integration |
| **In-database ML training** | BigQuery ML | Train where data lives, no data movement |
| **Model explainability** | Vertex AI | Understand predictions for regulatory compliance |
| **Cost-efficient pipelines** | Dataform incremental processing | Only process new data |
| **Multimodal analytics** | Combining structured + unstructured | Contextualized insights, not just predictions |

---

## Next Steps for Prospects

1. **Extend the model:** Add more features (e.g., in-app purchase behavior)
2. **Deploy to production:** Vertex AI endpoint for real-time predictions
3. **Build dashboards:** Looker Studio for business users
4. **Add monitoring:** Cloud Monitoring alerts for data quality
5. **Scale:** This architecture handles billions of rows and petabytes of data

---

## Additional Demo Ideas

### For Data Engineers
- Show Dataform dependency graph (visual pipeline)
- Demonstrate tag-based execution (`sentiment_analysis` vs `propensity_modeling`)
- Show Git integration (version control for SQL)

### For Data Scientists
- Show `ML.EXPLAIN_PREDICT()` for local explanations
- Demonstrate hyperparameter tuning options in BQML
- Show integration with Vertex AI Workbench for notebooks

### For Business Stakeholders
- Focus on Step 8 (cross-domain insights)
- Show sentiment trend over time
- Demonstrate ROI: cost of Gemini API vs. value of insights

---

## Resources

- **[Getting Started](getting-started.md)** - Full deployment guide
- **[SQL Examples](examples.md)** - More query patterns
- **[Architecture](architecture.md)** - Technical deep dive
- **[BigQuery ML Docs](https://cloud.google.com/bigquery/docs/bqml-introduction)** - BQML reference
- **[Gemini in BigQuery](https://cloud.google.com/bigquery/docs/generate-text)** - ML.GENERATE_TEXT() guide
