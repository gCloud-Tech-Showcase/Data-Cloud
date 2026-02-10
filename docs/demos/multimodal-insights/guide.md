# Multimodal Analytics Guide

Combine churn predictions with sentiment analysis for targeted interventions.

**Time:** 5-7 minutes

---

## The Business Problem

**From Churn Prediction:** We identified high-risk users but didn't know why they were unhappy.
**From Sentiment Analysis:** We identified complaints (ads, bugs) but didn't know which users complained.

**Generic approach:**
```
High churn risk → Send generic discount to everyone
Result: 30-40% conversion, wasted spend on 60-70%
```

**Multimodal approach:**
```
High churn risk + Specific complaint → Targeted intervention
Result: 60-70% conversion, efficient spend
```

---

## Step 1: Conceptual Cross-Domain Query

This demonstrates the value of combining both datasets.

**Note:** This is a conceptual query since we don't have user_pseudo_id in review data. In production, you'd link via email, device ID, or customer ID.

```sql
-- CONCEPTUAL: Assumes user linkage exists
SELECT
  p.user_pseudo_id,
  ROUND(p.return_probability, 3) AS return_probability,
  p.risk_category,
  s.avg_sentiment_score,
  s.primary_complaint_category
FROM (
  SELECT
    user_pseudo_id,
    (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability,
    CASE
      WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.3 THEN 'HIGH CHURN RISK'
      WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.6 THEN 'MEDIUM RISK'
      ELSE 'LOW RISK'
    END AS risk_category
  FROM ML.PREDICT(
    MODEL `propensity_modeling.gold_user_retention_model`,
    (SELECT * FROM `propensity_modeling.gold_training_features`)
  )
) p
LEFT JOIN (
  SELECT
    user_pseudo_id,
    AVG(sentiment_score) AS avg_sentiment_score,
    ARRAY_AGG(category ORDER BY review_date DESC LIMIT 1)[OFFSET(0)] AS primary_complaint_category
  FROM `sentiment_analysis.silver_review_sentiment`
  GROUP BY user_pseudo_id
) s ON p.user_pseudo_id = s.user_pseudo_id
WHERE p.risk_category = 'HIGH CHURN RISK'
  AND s.avg_sentiment_score < -0.5;
```

---

## Step 2: Targeted Intervention Matrix

With both datasets combined, we can create precise interventions.

| Churn Risk | Complaint Category | Intervention |
|------------|-------------------|--------------|
| **HIGH** | Ads | Offer 7-day premium ad-free trial |
| **HIGH** | Bugs | Priority support + update notification |
| **HIGH** | Difficulty | Suggest easier levels + tutorial |
| **HIGH** | No complaints | Generic engagement email |
| **MEDIUM** | Ads | Show fewer ads for 30 days |
| **MEDIUM** | Any | Monitor, light engagement |
| **LOW** | Any | Standard communication |

---

## Step 3: Example Targeted Campaigns

### Campaign 1: Ad-Frustrated Users

**Target:** HIGH churn risk + ads complaint

```sql
SELECT user_pseudo_id, return_probability, most_recent_review_text
FROM combined_multimodal_table
WHERE risk_category = 'HIGH CHURN RISK'
  AND primary_complaint_category = 'ads'
ORDER BY return_probability ASC
LIMIT 100;
```

**Action:** Email with subject "Enjoy [Game] ad-free for 7 days"

### Campaign 2: Bug-Affected Users

**Target:** HIGH churn risk + bugs complaint

**Action:**
1. Prioritize their specific crash in next update
2. Email: "We fixed the bug you reported!"
3. Offer in-app currency as apology

---

## Step 4: Vertex AI Integration

Confirm the BQML model is registered in Vertex AI.

```sql
SELECT model_name, model_type, creation_time
FROM `propensity_modeling.INFORMATION_SCHEMA.MODELS`
WHERE model_name = 'gold_user_retention_model';
```

**Via gcloud:**
```bash
gcloud ai models list \
  --region=us-central1 \
  --filter="displayName:gold_user_retention_model"
```

---

## Step 5: Production Deployment

### Option A: Scheduled BigQuery Jobs (Batch)

```sql
CREATE OR REPLACE TABLE `propensity_modeling.daily_risk_scores` AS
SELECT
  user_pseudo_id,
  CURRENT_DATE() AS score_date,
  (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`)
);
```

### Option B: Vertex AI Endpoint (Real-Time)

```bash
gcloud ai endpoints deploy-model ENDPOINT_ID \
  --region=us-central1 \
  --model=gold_user_retention_model \
  --display-name=user-retention-v1 \
  --machine-type=n1-standard-2
```

---

## Key Takeaways

| Capability | Technology Stack | Business Value |
|------------|------------------|----------------|
| Multimodal analytics | BigQuery + BigLake + Gemini + BQML | WHO + WHY insights |
| No data movement | BigLake Object Tables | Faster time-to-insight |
| Unified platform | Everything in BigQuery | No tool sprawl |
| Production-ready | Vertex AI integration | Real-time deployment |

---

## Demo Summary

**Part 1: Churn Prediction**
- Processed 5.7M GA4 events
- Trained BQML model (79% AUC)
- Scored 18K users for churn risk

**Part 2: Sentiment Analysis**
- Queried 500+ JSON reviews from Cloud Storage
- Enriched with Gemini AI via SQL
- Identified complaint categories

**Part 3: Multimodal Analytics**
- Combined both datasets
- Created targeted intervention matrix
- Demonstrated production deployment paths

---

## Navigation

[← Sentiment Insights](../sentiment-analysis/02-insights.md) | [Campaign Intelligence →](../campaign-intelligence/) | [Quick Reference](quick.md)
