# Demo Guide 01: Feature Engineering

**Objective:** Build ML-ready features from GA4 behavioral data using rolling 7-day windows.

**Time:** 5-7 minutes

**What you'll demonstrate:**
- Query 5.7M GA4 events from Firebase public dataset
- Create rolling 7-day observation windows
- Engineer churn prediction features (activity, engagement, gameplay)
- Generate 18K training rows with features + labels

---

## Step 1: Explore the Raw GA4 Data

Start by querying the Firebase public dataset to understand the data structure.

### Run This Query

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

### Expected Output

```
event_date | event_name        | user_pseudo_id      | device_category | country
-----------|-------------------|---------------------|-----------------|---------------
20180612   | user_engagement   | 1234567890.1234567  | mobile          | United States
20180612   | level_start       | 1234567890.1234567  | mobile          | United States
20180612   | level_complete    | 1234567890.1234567  | mobile          | United States
20180613   | post_score        | 2345678901.2345678  | tablet          | Canada
...
```

**Key Point:** GA4 stores dates as YYYYMMDD strings. We'll need to parse these into proper dates for time-based calculations.

---

## Step 2: Understand Flattened Events

The `silver_events_flattened` view unnests nested event parameters into columns.

### Run This Query

```sql
SELECT
  event_date,
  event_datetime,
  user_pseudo_id,
  event_name,
  engagement_time_msec,
  value_in_usd
FROM `ga4_source.silver_events_flattened`
WHERE user_pseudo_id = '1234567890.1234567'
ORDER BY event_datetime
LIMIT 20;
```

### Expected Output

```
event_date | event_datetime           | user_pseudo_id     | event_name      | engagement_time_msec | value_in_usd
-----------|--------------------------|-------------------|-----------------|----------------------|-------------
2018-06-12 | 2018-06-12 14:23:45 UTC  | 1234567890.123... | user_engagement | 45231                | NULL
2018-06-12 | 2018-06-12 14:25:12 UTC  | 1234567890.123... | level_start     | NULL                 | NULL
2018-06-12 | 2018-06-12 14:27:03 UTC  | 1234567890.123... | level_complete  | NULL                 | 150.0
...
```

**Key Point:** The view handles the complexity of unnesting GA4's nested `event_params` array, making it easy to query.

---

## Step 3: Explore Training Features

View the final feature-engineered table with rolling 7-day windows.

### Run This Query

```sql
SELECT
  user_pseudo_id,
  observation_date,
  days_in_window,
  days_active,
  total_events,
  events_per_day,
  level_completion_rate,
  engagement_minutes_per_day,
  will_return  -- Label: 1 = returned, 0 = churned
FROM `propensity_modeling.gold_training_features`
ORDER BY observation_date, user_pseudo_id
LIMIT 10;
```

### Expected Output

```
user_pseudo_id     | observation_date | days_in_window | days_active | total_events | events_per_day | level_completion_rate | engagement_minutes_per_day | will_return
-------------------|------------------|----------------|-------------|--------------|----------------|----------------------|---------------------------|-------------
1234567890.123...  | 2018-07-01       | 7              | 5           | 78           | 11.1           | 0.72                 | 4.3                       | 1
2345678901.234...  | 2018-07-01       | 7              | 2           | 18           | 2.6            | 0.33                 | 1.1                       | 0
...
```

**Key Point:** Each row represents a user at a specific point in time (observation_date). Multiple rows per user enable the model to learn temporal patterns.

---

## Step 4: Understand the Rolling Window Approach

This is a critical design decision that differentiates this approach from traditional cohort analysis.

### Traditional Approach (Static Cohorts)

```
User A: Analyze days 1-7 → Predict return on day 8
Result: 1 training row per user
```

### Our Approach (Rolling Windows)

```
User A, Week 1: Days 1-7   → Did they return days 8-14?  (Row 1)
User A, Week 2: Days 8-14  → Did they return days 15-21? (Row 2)
User A, Week 3: Days 15-21 → Did they return days 22-28? (Row 3)
Result: 3 training rows per user
```

**Benefits:**
1. **More training data:** 18K rows vs. 15K users
2. **Temporal dynamics:** Captures how behavior changes over time
3. **Continuous prediction:** Can score users at any lifecycle stage
4. **Realistic labels:** Based on actual future behavior

---

## Step 5: Check Class Balance

Verify the label distribution to ensure the model has enough examples of each class.

### Run This Query

```sql
SELECT
  will_return,
  COUNT(*) AS count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `propensity_modeling.gold_training_features`
GROUP BY will_return
ORDER BY will_return;
```

### Expected Output

```
will_return | count | percentage
------------|-------|------------
0           | 7234  | 39.8
1           | 10932 | 60.2
```

**Key Point:** The 40/60 split is reasonable. Severe imbalance (e.g., 5/95) would require class weighting or resampling techniques.

---

## Step 6: Examine Feature Distributions

Understand the range and distribution of key features.

### Run This Query

```sql
SELECT
  ROUND(AVG(days_active), 2) AS avg_days_active,
  ROUND(AVG(total_events), 2) AS avg_total_events,
  ROUND(AVG(level_completion_rate), 3) AS avg_completion_rate,
  ROUND(MIN(level_completion_rate), 3) AS min_completion_rate,
  ROUND(MAX(level_completion_rate), 3) AS max_completion_rate,
  COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `propensity_modeling.gold_training_features`;
```

### Expected Output

```
avg_days_active | avg_total_events | avg_completion_rate | min_completion_rate | max_completion_rate | unique_users
----------------|------------------|---------------------|---------------------|---------------------|-------------
3.8             | 42.5             | 0.547               | 0.000               | 1.000               | 14823
```

**Key Point:** Wide range in completion rates (0.0 to 1.0) suggests this will be a strong predictor.

---

## How This Was Built (Reference)

The feature engineering happens in `definitions/propensity_modeling/marts/gold_training_features.sqlx`:

1. **Date Spine:** Generate observation dates every 7 days
2. **User Observations:** Cross join users with observation dates
3. **Feature Calculation:** Aggregate events from the 7 days BEFORE observation_date
4. **Label Calculation:** Check if user returned in the 7 days AFTER observation_date
5. **Join:** Combine features + labels into final training table

**SQL Pattern:**
```sql
WITH date_spine AS (
  SELECT observation_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2018-07-01', '2018-09-15', INTERVAL 7 DAY))
),
user_training_features AS (
  SELECT
    user_pseudo_id,
    observation_date,
    COUNT(DISTINCT event_date) AS days_active,
    -- ... more features
  FROM user_observations
  LEFT JOIN silver_events_flattened
    ON user_pseudo_id = user_pseudo_id
    AND event_date BETWEEN DATE_SUB(observation_date, INTERVAL 7 DAY)
                       AND DATE_SUB(observation_date, INTERVAL 1 DAY)
  GROUP BY user_pseudo_id, observation_date
)
-- ... label calculation and final join
```

---

## Key Takeaways

| Capability | Implementation | Business Value |
|------------|----------------|----------------|
| **Query massive datasets** | 5.7M events processed in seconds | Fast iteration on feature ideas |
| **Temporal feature engineering** | Rolling windows via date arithmetic | Captures user lifecycle dynamics |
| **SQL-based ML prep** | All in BigQuery SQL, no Python | Accessible to SQL-savvy analysts |
| **Scalable architecture** | Works on billions of events | Production-ready approach |

---

## Navigation

**Previous:** [Demo Walkthrough](../demo-walkthrough.md) (Overview)
**Next:** [02 - Train ML Model](02-train-ml-model.md)
**Home:** [README](../../README.md)
