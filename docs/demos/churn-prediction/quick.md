# Churn Prediction - Quick Reference

SQL queries with expected outputs. Run these in BigQuery Console.

---

## 1. Explore Raw GA4 Data

```sql
SELECT
  event_date,
  event_name,
  user_pseudo_id,
  device.category AS device_category,
  geo.country AS country
FROM `firebase-public-project.analytics_153293282.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20180612' AND '20180620'
LIMIT 10;
```

**Output:**
```
event_date | event_name      | user_pseudo_id     | device_category | country
-----------|-----------------|--------------------| ----------------|---------------
20180612   | user_engagement | 1234567890.123...  | mobile          | United States
20180612   | level_start     | 1234567890.123...  | mobile          | United States
```

---

## 2. View Training Features

```sql
SELECT
  user_pseudo_id,
  observation_date,
  days_active,
  total_events,
  level_completion_rate,
  will_return
FROM `propensity_modeling.gold_training_features`
LIMIT 10;
```

**Output:**
```
user_pseudo_id    | observation_date | days_active | total_events | level_completion_rate | will_return
------------------|------------------|-------------|--------------|----------------------|------------
1234567890.123... | 2018-07-01       | 5           | 78           | 0.72                 | 1
2345678901.234... | 2018-07-01       | 2           | 18           | 0.33                 | 0
```

---

## 3. Check Class Balance

```sql
SELECT
  will_return,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `propensity_modeling.gold_training_features`
GROUP BY will_return;
```

**Output:**
```
will_return | count | percentage
------------|-------|------------
0           | 7234  | 39.8
1           | 10932 | 60.2
```

---

## 4. Evaluate Model

```sql
SELECT * FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);
```

**Output:**
```
precision | recall | accuracy | f1_score | roc_auc
----------|--------|----------|----------|--------
0.72      | 0.68   | 0.74     | 0.70     | 0.79
```

---

## 5. Feature Importance

```sql
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY attribution DESC
LIMIT 5;
```

**Output:**
```
feature                    | attribution
---------------------------|------------
days_active                | 0.234
level_completion_rate      | 0.189
days_since_last_activity   | 0.156
engagement_minutes_per_day | 0.142
events_per_day             | 0.098
```

---

## 6. Make Predictions

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
  (SELECT * FROM `propensity_modeling.gold_training_features` LIMIT 100)
)
ORDER BY return_probability ASC
LIMIT 10;
```

**Output:**
```
user_pseudo_id     | return_probability | risk_category
-------------------|--------------------|---------------
1234567890.123...  | 0.182              | HIGH RISK
2345678901.234...  | 0.237              | HIGH RISK
3456789012.345...  | 0.547              | MEDIUM RISK
```

---

## 7. Risk Distribution

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
  COUNT(*) AS user_count
FROM predictions
GROUP BY risk_category;
```

**Output:**
```
risk_category | user_count
--------------|------------
HIGH RISK     | 3872
MEDIUM RISK   | 6845
LOW RISK      | 7449
```

---

## Navigation

- [Overview](./)
- [Full Guides](01-features.md)
- [Back to Demos](../README.md)
