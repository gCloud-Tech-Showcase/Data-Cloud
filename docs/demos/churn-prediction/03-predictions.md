# Churn Predictions

Score users for churn risk and segment by priority.

**Time:** 5 minutes

---

## Step 1: Make Predictions

```sql
SELECT
  user_pseudo_id,
  predicted_will_return,
  ROUND((SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1), 3) AS return_probability
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features` LIMIT 100)
)
ORDER BY return_probability ASC
LIMIT 10;
```

The model returns both binary predictions (0/1) and probability scores for risk segmentation.

---

## Step 2: Segment by Risk

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
ORDER BY return_probability ASC;
```

| Risk Level | Threshold | Action |
|------------|-----------|--------|
| HIGH RISK | <30% | Immediate intervention |
| MEDIUM RISK | 30-60% | Monitor closely |
| LOW RISK | >60% | Standard communication |

---

## Step 3: Risk Distribution

```sql
WITH predictions AS (
  SELECT (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability
  FROM ML.PREDICT(MODEL `propensity_modeling.gold_user_retention_model`,
    (SELECT * FROM `propensity_modeling.gold_training_features`))
)
SELECT
  CASE
    WHEN return_probability < 0.3 THEN 'HIGH RISK'
    WHEN return_probability < 0.6 THEN 'MEDIUM RISK'
    ELSE 'LOW RISK'
  END AS risk_category,
  COUNT(*) AS user_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM predictions
GROUP BY risk_category;
```

~21% of users are at high churn risk — your retention campaign target audience.

---

## Step 4: High-Risk User Details

```sql
SELECT
  f.user_pseudo_id,
  ROUND((SELECT prob FROM UNNEST(p.predicted_will_return_probs) WHERE label = 1), 3) AS return_probability,
  f.days_active,
  f.total_events,
  ROUND(f.level_completion_rate, 2) AS completion_rate,
  f.days_since_last_activity
FROM ML.PREDICT(MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`)) p
JOIN `propensity_modeling.gold_training_features` f
  ON p.user_pseudo_id = f.user_pseudo_id AND p.observation_date = f.observation_date
WHERE (SELECT prob FROM UNNEST(p.predicted_will_return_probs) WHERE label = 1) < 0.3
ORDER BY return_probability ASC
LIMIT 10;
```

**Patterns in high-risk users:**
- Low days active (1-2 days)
- Low completion rate (<0.5)
- High recency (3-5 days since last activity)

---

## The Limitation

**"User X has 18% return probability. What should we do?"**

Possible actions:
1. Send generic "we miss you" email
2. Offer discount on premium
3. Push notification about new levels
4. Personal outreach

**The problem:** We don't know WHY they stopped engaging.

| Scenario | Root Cause | Right Action |
|----------|------------|--------------|
| A | Levels too difficult | Suggest easier levels |
| B | Frustrated by ads | Offer ad-free trial |
| C | Experiencing bugs | Prioritize bug fixes |
| D | Lost interest | Accept and move on |

**Without understanding the "why," we're guessing.**

---

## What's Next

To understand WHY users churn, we need to analyze unstructured data:
- User reviews
- Support tickets
- In-app feedback

Continue to [Sentiment Analysis](../sentiment-analysis/overview.md) to add this dimension.

---

## Navigation

[← Training](02-training.md) | [Sentiment Analysis →](../sentiment-analysis/overview.md) | [Quick Reference](quick.md)
