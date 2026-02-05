# Demo Guide 02: Train ML Model

**Objective:** Train and evaluate a churn prediction model using BigQuery ML.

**Time:** 5-7 minutes

**What you'll demonstrate:**
- Train logistic regression model entirely in SQL
- Evaluate model performance (precision, recall, AUC)
- Explore feature importance via explainability
- Understand model without writing Python code

---

## Step 1: Review the Model Definition

The model is defined in `definitions/propensity_modeling/ml/gold_user_retention_model.sqlx`.

**Key features:**
- **Model type:** Logistic regression (binary classification)
- **Input:** Features from `gold_training_features`
- **Label:** `will_return` (0 or 1)
- **Registry:** Automatically registered to Vertex AI
- **Explainability:** Global explain enabled

### Model SQL Pattern

```sql
CREATE OR REPLACE MODEL `propensity_modeling.gold_user_retention_model`
TRANSFORM(
  days_in_window,
  ML.STANDARD_SCALER(days_active) OVER() AS scaled_days_active,
  ML.STANDARD_SCALER(total_events) OVER() AS scaled_total_events,
  -- ... more feature transforms
  will_return
)
OPTIONS(
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['will_return'],
  model_registry = 'vertex_ai',
  vertex_ai_model_id = 'user_retention_model',
  enable_global_explain = TRUE
)
AS SELECT * FROM `propensity_modeling.gold_training_features`;
```

**Key Point:** The TRANSFORM clause applies feature preprocessing (scaling, encoding) as part of the model definition. Predictions automatically apply these transforms.

---

## Step 2: Check Model Training Metrics

After the model trains, BigQuery ML provides automatic evaluation metrics.

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

### Interpretation

| Metric | Value | Meaning |
|--------|-------|---------|
| **ROC AUC** | 0.79 | Good discrimination (much better than random 0.5) |
| **Precision** | 0.72 | Of predicted churners, 72% actually churned |
| **Recall** | 0.68 | Of actual churners, we caught 68% |
| **Accuracy** | 0.74 | 74% of all predictions are correct |
| **F1 Score** | 0.70 | Balanced measure of precision and recall |

**Key Point:** AUC of 0.79 means the model is production-ready. In a sales context, emphasize this is achieved with zero Python code — just SQL.

---

## Step 3: Explore Feature Importance

Use global explainability to see which features drive predictions.

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
total_events                 | 0.087
max_score                    | 0.052
levels_started               | 0.041
device_category              | 0.001
```

### Interpretation

**Top 3 predictors:**
1. **days_active** (0.234) - How many days the user played in the window
2. **level_completion_rate** (0.189) - Success rate on levels
3. **days_since_last_activity** (0.156) - Recency of last session

**Business insight:** Users who play frequently and complete levels are more likely to return. Users who haven't played recently are at risk.

**Key Point:** BigQuery ML provides explainability out of the box — critical for regulatory compliance and stakeholder trust.

---

## Step 4: View the Confusion Matrix

Understand where the model makes mistakes.

### Run This Query

```sql
SELECT *
FROM ML.CONFUSION_MATRIX(MODEL `propensity_modeling.gold_user_retention_model`);
```

### Expected Output

```
actual_label | predicted_label | count
-------------|-----------------|-------
0            | 0               | 4821   (True Negatives - correctly predicted churners)
0            | 1               | 2413   (False Positives - predicted return but churned)
1            | 0               | 3498   (False Negatives - predicted churn but returned)
1            | 1               | 7434   (True Positives - correctly predicted returners)
```

### Interpretation

- **Correctly identified churners:** 4,821 users (True Negatives)
- **Missed churners:** 2,413 users (False Positives) — thought they'd return but didn't
- **Unnecessary interventions:** 3,498 users (False Negatives) — targeted but would have returned anyway
- **Correctly identified returners:** 7,434 users (True Positives)

**Business tradeoff:** False Positives mean wasted retention spend. False Negatives mean missed opportunities.

---

## Step 5: Examine ROC Curve Data

Analyze precision/recall tradeoffs at different thresholds.

### Run This Query

```sql
SELECT
  threshold,
  ROUND(precision, 3) AS precision,
  ROUND(recall, 3) AS recall,
  ROUND(f1_score, 3) AS f1_score,
  true_positives,
  false_positives
FROM ML.ROC_CURVE(MODEL `propensity_modeling.gold_user_retention_model`)
WHERE threshold IN (0.3, 0.5, 0.7, 0.9)
ORDER BY threshold;
```

### Expected Output

```
threshold | precision | recall | f1_score | true_positives | false_positives
----------|-----------|--------|----------|----------------|----------------
0.30      | 0.645     | 0.892  | 0.749    | 9753           | 5369
0.50      | 0.724     | 0.681  | 0.702    | 7434           | 2413
0.70      | 0.812     | 0.423  | 0.556    | 4619           | 1069
0.90      | 0.891     | 0.156  | 0.265    | 1705           | 209
```

### Interpretation

**At threshold 0.3 (cast wide net):**
- Catch 89% of churners (high recall)
- But only 65% of predictions are correct (low precision)
- Use case: Cheap intervention (email campaign)

**At threshold 0.7 (be selective):**
- Only catch 42% of churners (low recall)
- But 81% of predictions are correct (high precision)
- Use case: Expensive intervention (personal outreach)

**Key Point:** The threshold depends on the cost of intervention vs. cost of losing a customer.

---

## Step 6: Compare to Baseline

What if we just predicted "everyone will return"?

### Baseline Accuracy

```sql
SELECT
  ROUND(SUM(CASE WHEN will_return = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS baseline_accuracy
FROM `propensity_modeling.gold_training_features`;
```

### Expected Output

```
baseline_accuracy
-----------------
60.2
```

**Comparison:**
- **Baseline (always predict return):** 60.2% accuracy
- **Our model:** 74% accuracy
- **Lift:** +13.8 percentage points

**Key Point:** The model provides real value over naive approaches. In sales terms: "14% improvement means 14% fewer lost customers."

---

## How This Was Built (Reference)

The model training is defined in `definitions/propensity_modeling/ml/gold_user_retention_model.sqlx`:

**Key components:**
1. **TRANSFORM clause:** Feature preprocessing (scaling, encoding)
2. **OPTIONS:** Model type, parameters, Vertex AI registration
3. **AS SELECT:** Training data source

**Automatic capabilities:**
- Train/test split (BigQuery ML handles this)
- Hyperparameter tuning (default AUTO settings)
- Model versioning (via Vertex AI)
- Explainability (enable_global_explain=TRUE)

**No manual steps needed for:**
- Data export
- Python environment setup
- Model serialization
- Registry integration

---

## Key Takeaways

| Capability | Implementation | Business Value |
|------------|----------------|----------------|
| **SQL-only ML training** | BigQuery ML CREATE MODEL | No data science team required |
| **Automatic evaluation** | ML.EVALUATE, ML.ROC_CURVE | Built-in model validation |
| **Feature importance** | ML.GLOBAL_EXPLAIN | Regulatory compliance, trust |
| **Vertex AI integration** | model_registry='vertex_ai' | Production deployment path |
| **Production-ready performance** | 79% AUC, 74% accuracy | Real business impact |

---

## What We've Accomplished

At this point in the demo, we've:
- Built features from 5.7M events
- Trained a logistic regression model (79% AUC)
- Evaluated performance with multiple metrics
- Identified key churn predictors
- All in SQL, no Python required

**But there's a problem...**

The model tells us **WHO will churn** (users with low activity, low completion rates), but not **WHY they're unhappy**.

Without understanding the "why," we can't take targeted action. Generic retention campaigns are expensive and often ineffective.

**Solution:** Add unstructured data (user reviews) to understand sentiment and root causes.

---

## Navigation

**Previous:** [01 - Feature Engineering](01-feature-engineering.md)
**Next:** [03 - Churn Predictions](03-churn-predictions.md)
**Home:** [README](../../README.md)
