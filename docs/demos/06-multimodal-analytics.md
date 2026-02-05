# Demo Guide 06: Multimodal Analytics

**Objective:** Combine churn predictions with sentiment analysis for targeted interventions.

**Time:** 5-7 minutes

**What you'll demonstrate:**
- Cross-domain analytics (behavioral + sentiment)
- Targeted interventions based on both WHO and WHY
- Vertex AI model registry integration
- Incremental processing (only new data is processed)
- **The payoff:** Complete multimodal analytics solution

---

## Step 1: The Business Problem (Recap)

**From Guide 03:** We identified high-risk users but didn't know why they were unhappy.
**From Guide 05:** We identified complaints (ads, bugs) but didn't know which users complained.

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

## Step 2: Conceptual Cross-Domain Query

This demonstrates the value of combining both datasets.

**Note:** This is a conceptual query since we don't have user_pseudo_id in review data. In production, you'd link via email, device ID, or customer ID.

### Conceptual SQL

```sql
-- CONCEPTUAL: Assumes we have user linkage
SELECT
  p.user_pseudo_id,
  ROUND(p.return_probability, 3) AS return_probability,
  p.risk_category,
  s.avg_sentiment_score,
  s.negative_review_count,
  s.primary_complaint_category,
  s.most_recent_review_text
FROM (
  -- Churn predictions
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
  -- Sentiment aggregates per user
  SELECT
    user_pseudo_id,
    AVG(sentiment_score) AS avg_sentiment_score,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_review_count,
    ARRAY_AGG(category ORDER BY review_date DESC LIMIT 1)[OFFSET(0)] AS primary_complaint_category,
    ARRAY_AGG(review_text ORDER BY review_date DESC LIMIT 1)[OFFSET(0)] AS most_recent_review_text
  FROM `sentiment_analysis.silver_review_sentiment`
  GROUP BY user_pseudo_id
) s
  ON p.user_pseudo_id = s.user_pseudo_id
WHERE p.risk_category = 'HIGH CHURN RISK'
  AND s.avg_sentiment_score < -0.5
ORDER BY p.return_probability ASC, s.avg_sentiment_score ASC;
```

### Expected Output (Conceptual)

```
user_pseudo_id  | return_probability | risk_category   | avg_sentiment_score | negative_review_count | primary_complaint_category | most_recent_review_text
----------------|--------------------| ----------------|---------------------|----------------------|----------------------------|---------------------------
1234567890.12...| 0.182              | HIGH CHURN RISK | -0.85               | 3                    | ads                        | "Too many ads, can't play"
2345678901.23...| 0.215              | HIGH CHURN RISK | -0.78               | 2                    | bugs                       | "Crashes on level 5"
3456789012.34...| 0.247              | HIGH CHURN RISK | -0.71               | 2                    | difficulty                 | "Levels are impossible"
```

---

## Step 3: Targeted Intervention Matrix

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

**Key insight:** Targeted interventions based on complaint category convert better than generic campaigns.

---

## Step 4: Example Targeted Campaigns

### Campaign 1: Ad-Frustrated Users

**Target:** HIGH churn risk + ads complaint

```sql
-- Identify users for premium trial offer
SELECT
  user_pseudo_id,
  return_probability,
  most_recent_review_text
FROM combined_multimodal_table
WHERE risk_category = 'HIGH CHURN RISK'
  AND primary_complaint_category = 'ads'
ORDER BY return_probability ASC
LIMIT 100;
```

**Action:** Email with subject "Enjoy [Game] ad-free for 7 days" + offer for premium upgrade

---

### Campaign 2: Bug-Affected Users

**Target:** HIGH churn risk + bugs complaint

```sql
-- Identify users experiencing crashes
SELECT
  user_pseudo_id,
  return_probability,
  most_recent_review_text
FROM combined_multimodal_table
WHERE risk_category = 'HIGH CHURN RISK'
  AND primary_complaint_category = 'bugs'
ORDER BY return_probability ASC;
```

**Action:**
1. Prioritize their specific crash in next update
2. Email: "We fixed the bug you reported! Try again now"
3. Offer in-app currency as apology

---

## Step 5: Verify Vertex AI Integration

Confirm the BQML model is registered in Vertex AI for production deployment.

### Via BigQuery

```sql
SELECT
  model_name,
  model_type,
  creation_time,
  last_modified_time
FROM `propensity_modeling.INFORMATION_SCHEMA.MODELS`
WHERE model_name = 'gold_user_retention_model';
```

### Via Cloud Console

1. Navigate to **Vertex AI** → **Model Registry**
2. Look for `gold_user_retention_model`
3. Verify:
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

**Key Point:** BQML models with `model_registry='vertex_ai'` automatically register. No manual export needed.

---

## Step 6: Production Deployment Path

### Option A: Scheduled BigQuery Jobs

**For batch scoring:**
1. Create scheduled query in BigQuery
2. Run predictions daily/weekly
3. Write results to a table
4. Export to CRM or marketing automation tool

```sql
-- Scheduled query runs daily
CREATE OR REPLACE TABLE `propensity_modeling.daily_risk_scores` AS
SELECT
  user_pseudo_id,
  CURRENT_DATE() AS score_date,
  (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability,
  -- ... risk category and other fields
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`)
);
```

---

### Option B: Vertex AI Endpoint (Real-Time)

**For real-time scoring:**
1. Deploy model to Vertex AI endpoint
2. Call via REST API
3. Get predictions in <100ms

**Deployment:**
```bash
# Via gcloud CLI
gcloud ai endpoints deploy-model ENDPOINT_ID \
  --region=us-central1 \
  --model=gold_user_retention_model \
  --display-name=user-retention-v1 \
  --machine-type=n1-standard-2
```

**API call:**
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
      ...
    }]
  }'
```

---

## Key Takeaways

| Capability | Technology Stack | Business Value |
|------------|------------------|----------------|
| **Multimodal analytics** | BigQuery + BigLake + Gemini + BQML | Contextualized insights (WHO + WHY) |
| **No data movement** | BigLake Object Tables | Faster time-to-insight, simpler architecture |
| **Unified platform** | Everything in BigQuery | No tool sprawl, easier maintenance |
| **Production-ready** | Vertex AI integration | Deploy to real-time endpoints |
| **Incremental processing** | Dataform incremental tables | Process only new data |
| **SQL-first** | No Python required | Accessible to SQL analysts |

---

## Demo Summary

### What We Built

**Part 1: Churn Prediction**
- Processed 5.7M GA4 events
- Engineered features with rolling windows
- Trained BQML model (79% AUC)
- Scored 18K users for churn risk

**Part 2: Sentiment Analysis**
- Queried 500+ JSON reviews from Cloud Storage
- Enriched with Gemini AI via SQL
- Identified complaint categories (ads, bugs)
- Analyzed sentiment trends

**Part 3: Multimodal Analytics**
- Combined both datasets
- Created targeted intervention matrix
- Demonstrated improved retention efficiency through targeting
- Showed production deployment paths

---

### Business Impact

**Before multimodal analytics:**
- Know WHO will churn
- Send generic campaigns
- Low conversion rates
- Wasted spend on wrong interventions

**After multimodal analytics:**
- Know WHO will churn AND WHY
- Send targeted interventions
- Higher conversion rates
- More efficient retention spend

---

### Google Cloud Differentiators

What makes this possible on Google Cloud:

1. **BigLake:** Query unstructured data without ETL
2. **Gemini in BigQuery:** AI enrichment via SQL, no external APIs
3. **BigQuery ML:** Train models where data lives
4. **Vertex AI:** Production model registry and deployment
5. **Dataform:** Incremental processing, only new data is processed
6. **Unified platform:** No tool sprawl, everything in BigQuery

**Traditional approach would require:**
- Separate sentiment analysis tool
- ETL pipelines to move data
- Python/notebook environment for ML
- Manual model deployment
- Multiple teams and skillsets

**Google Cloud approach:**
- Single platform (BigQuery)
- SQL-based (accessible to analysts)
- Fully integrated (no glue code)
- Production-ready (Vertex AI)

---

## Next Steps

1. **Try it yourself:** Deploy via [Getting Started Guide](../getting-started.md)
2. **Customize:** Add your own review sources (App Store, support tickets)
3. **Extend:** Build gold-layer aggregations for deeper insights
4. **Productionize:** Deploy to Vertex AI endpoints for real-time scoring
5. **Scale:** Architecture handles billions of rows, petabytes of data

---

## Navigation

**Previous:** [05 - Sentiment Insights](05-sentiment-insights.md)
**Start Over:** [Demo Walkthrough](../demo-walkthrough.md) (Overview)
**Home:** [README](../../README.md)
