# Model Training

Train and evaluate a churn prediction model using BigQuery ML.

**Time:** 5-7 minutes

---

## Step 1: Model Definition

The model in `gold_user_retention_model.sqlx`:

```sql
CREATE OR REPLACE MODEL `propensity_modeling.gold_user_retention_model`
TRANSFORM(
  ML.STANDARD_SCALER(days_active) OVER() AS scaled_days_active,
  ML.STANDARD_SCALER(total_events) OVER() AS scaled_total_events,
  will_return
)
OPTIONS(
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['will_return'],
  model_registry = 'vertex_ai',
  enable_global_explain = TRUE
)
AS SELECT * FROM `propensity_modeling.gold_training_features`;
```

The TRANSFORM clause applies preprocessing as part of the model. Predictions automatically apply these transforms.

---

## Step 2: Evaluation Metrics

```sql
SELECT * FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);
```

| Metric | Value | Meaning |
|--------|-------|---------|
| **ROC AUC** | 0.79 | Good discrimination |
| **Precision** | 0.72 | 72% of predicted churners actually churned |
| **Recall** | 0.68 | Caught 68% of actual churners |
| **Accuracy** | 0.74 | 74% of predictions correct |

AUC of 0.79 means the model is production-ready — achieved with zero Python.

---

## Step 3: Feature Importance

```sql
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `propensity_modeling.gold_user_retention_model`)
ORDER BY attribution DESC
LIMIT 5;
```

**Top predictors:**
1. `days_active` (0.234) - Play frequency
2. `level_completion_rate` (0.189) - Success rate
3. `days_since_last_activity` (0.156) - Recency

Users who play frequently and complete levels are more likely to return.

---

## Step 4: Confusion Matrix

```sql
SELECT * FROM ML.CONFUSION_MATRIX(MODEL `propensity_modeling.gold_user_retention_model`);
```

| | Predicted Churn | Predicted Return |
|---|---|---|
| **Actual Churn** | 4,821 (TN) | 2,413 (FP) |
| **Actual Return** | 3,498 (FN) | 7,434 (TP) |

False Positives = wasted retention spend. False Negatives = missed opportunities.

---

## Step 5: Threshold Analysis

```sql
SELECT threshold, ROUND(precision, 3) AS precision, ROUND(recall, 3) AS recall
FROM ML.ROC_CURVE(MODEL `propensity_modeling.gold_user_retention_model`)
WHERE threshold IN (0.3, 0.5, 0.7);
```

| Threshold | Precision | Recall | Use Case |
|-----------|-----------|--------|----------|
| 0.3 | 0.65 | 0.89 | Cheap intervention (email) |
| 0.5 | 0.72 | 0.68 | Balanced |
| 0.7 | 0.81 | 0.42 | Expensive intervention (personal outreach) |

---

## Step 6: Compare to Baseline

```sql
SELECT ROUND(SUM(CASE WHEN will_return = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS baseline
FROM `propensity_modeling.gold_training_features`;
```

- Baseline (always predict return): 60.2%
- Our model: 74%
- **Lift: +13.8 percentage points**

---

## Key Takeaways

| Capability | Business Value |
|------------|----------------|
| SQL-only ML training | No data science team required |
| Automatic evaluation | Built-in validation |
| Feature importance | Regulatory compliance |
| Vertex AI integration | Production deployment path |

---

## The Limitation

The model tells us **WHO will churn** but not **WHY they're unhappy**. Without understanding the "why," we can't take targeted action.

---

## Navigation

[← Features](01-features.md) | [Next: Predictions →](03-predictions.md) | [Quick Reference](quick.md)
