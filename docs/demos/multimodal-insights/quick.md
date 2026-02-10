# Multimodal Insights - Quick Reference

SQL queries with expected outputs. Run these in BigQuery Console.

---

## 1. High-Risk Users (Churn Predictions)

```sql
SELECT
  user_pseudo_id,
  ROUND((SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1), 3) AS return_probability,
  CASE
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.3 THEN 'HIGH RISK'
    WHEN (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.6 THEN 'MEDIUM RISK'
    ELSE 'LOW RISK'
  END AS risk_category
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`)
)
WHERE (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) < 0.3
ORDER BY return_probability ASC
LIMIT 10;
```

---

## 2. Complaint Categories (Sentiment)

```sql
SELECT
  category,
  COUNT(*) AS count,
  ROUND(AVG(sentiment_score), 3) AS avg_score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
GROUP BY category
ORDER BY count DESC;
```

**Output:**
```
category    | count | avg_score
------------|-------|----------
ads         | 42    | -0.810
bugs        | 32    | -0.872
difficulty  | 15    | -0.687
```

---

## 3. Intervention Matrix

| Churn Risk | Complaint | Intervention |
|------------|-----------|--------------|
| HIGH | Ads | Offer 7-day premium ad-free trial |
| HIGH | Bugs | Priority support + update notification |
| HIGH | Difficulty | Suggest easier levels + tutorial |
| HIGH | No complaints | Generic engagement email |

---

## 4. Model Registry Check

```sql
SELECT
  model_name,
  model_type,
  creation_time
FROM `propensity_modeling.INFORMATION_SCHEMA.MODELS`
WHERE model_name = 'gold_user_retention_model';
```

---

## 5. Batch Scoring Query

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

---

## Navigation

- [Overview](./)
- [Full Guide](guide.md)
- [Back to Demos](../README.md)
