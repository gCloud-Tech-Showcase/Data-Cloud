# Feature Engineering

Build ML-ready features from GA4 behavioral data using rolling 7-day windows.

**Time:** 5-7 minutes

---

## Step 1: Explore Raw GA4 Data

```sql
SELECT
  event_date,
  event_name,
  user_pseudo_id,
  device.category AS device_category
FROM `firebase-public-project.analytics_153293282.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20180612' AND '20180620'
LIMIT 10;
```

GA4 stores dates as YYYYMMDD strings. The `silver_events_flattened` view parses these and unnests the nested `event_params` array.

---

## Step 2: View Training Features

```sql
SELECT
  user_pseudo_id,
  observation_date,
  days_in_window,
  days_active,
  total_events,
  level_completion_rate,
  will_return
FROM `propensity_modeling.gold_training_features`
ORDER BY observation_date
LIMIT 10;
```

Each row represents a user at a specific point in time. Multiple rows per user enable the model to learn temporal patterns.

---

## Step 3: Rolling Window Approach

This is a critical design decision:

**Traditional (Static Cohorts):**
```
User A: Days 1-7 → Predict day 8
Result: 1 training row per user
```

**Our Approach (Rolling Windows):**
```
User A, Week 1: Days 1-7   → Did they return days 8-14?
User A, Week 2: Days 8-14  → Did they return days 15-21?
Result: Multiple rows per user
```

**Benefits:**
- More training data (18K rows vs. 15K users)
- Captures temporal dynamics
- Can score users at any lifecycle stage

---

## Step 4: Check Class Balance

```sql
SELECT
  will_return,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `propensity_modeling.gold_training_features`
GROUP BY will_return;
```

Expected: ~40/60 split. Severe imbalance would require class weighting.

---

## Step 5: Feature Distributions

```sql
SELECT
  ROUND(AVG(days_active), 2) AS avg_days_active,
  ROUND(AVG(level_completion_rate), 3) AS avg_completion_rate,
  COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `propensity_modeling.gold_training_features`;
```

Wide range in completion rates (0.0 to 1.0) suggests this will be a strong predictor.

---

## How It Works

The feature engineering in `gold_training_features.sqlx`:

1. **Date Spine** - Generate observation dates every 7 days
2. **Feature Calculation** - Aggregate events from 7 days BEFORE observation_date
3. **Label Calculation** - Check if user returned in 7 days AFTER observation_date

```sql
WITH date_spine AS (
  SELECT observation_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2018-07-01', '2018-09-15', INTERVAL 7 DAY))
)
-- Features: 7 days before, Labels: 7 days after
```

---

## Key Takeaways

| Capability | Business Value |
|------------|----------------|
| Query 5.7M events in seconds | Fast iteration on features |
| Rolling windows via SQL | Captures user lifecycle |
| No Python required | Accessible to analysts |

---

## Navigation

[Next: Model Training →](02-training.md) | [Quick Reference](quick.md) | [Overview](overview.md)
