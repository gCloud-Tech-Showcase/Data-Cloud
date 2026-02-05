# Demo Guide 03: Churn Predictions

**Objective:** Score users for churn risk and reveal the limitation of behavioral data alone.

**Time:** 5 minutes

**What you'll demonstrate:**
- Make churn predictions using ML.PREDICT()
- Segment users by risk level
- Identify high-risk users
- **Reveal the problem:** We know WHO will churn, but not WHY

---

## Step 1: Make Batch Predictions

Score a batch of users using the trained model.

### Run This Query

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

### Expected Output

```
user_pseudo_id      | predicted_will_return | return_probability
--------------------|----------------------|--------------------
1234567890.1234567  | 0                    | 0.182
2345678901.2345678  | 0                    | 0.237
3456789012.3456789  | 0                    | 0.284
4567890123.4567890  | 0                    | 0.312
5678901234.5678901  | 0                    | 0.428
6789012345.6789012  | 1                    | 0.547
7890123456.7890123  | 1                    | 0.623
8901234567.8901234  | 1                    | 0.701
9012345678.9012345  | 1                    | 0.785
0123456789.0123456  | 1                    | 0.842
```

**Key Point:** The model returns both a binary prediction (0 or 1) and probability scores. Probabilities enable risk segmentation.

---

## Step 2: Segment Users by Risk

Create business-friendly risk categories based on return probability.

### Run This Query

```sql
SELECT
  user_pseudo_id,
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
ORDER BY return_probability ASC;
```

### Expected Output

```
user_pseudo_id      | return_probability | risk_category
--------------------|--------------------|-----------------
1234567890.1234567  | 0.182              | HIGH CHURN RISK
2345678901.2345678  | 0.237              | HIGH CHURN RISK
3456789012.3456789  | 0.284              | HIGH CHURN RISK
4567890123.4567890  | 0.428              | MEDIUM RISK
5678901234.5678901  | 0.547              | MEDIUM RISK
6789012345.6789012  | 0.623              | LOW RISK
7890123456.7890123  | 0.701              | LOW RISK
8901234567.8901234  | 0.842              | LOW RISK
```

**Business application:**
- **HIGH CHURN RISK (<30%):** Immediate intervention required
- **MEDIUM RISK (30-60%):** Monitor closely, light engagement
- **LOW RISK (>60%):** Standard communication cadence

---

## Step 3: Count Users by Risk Segment

Understand the distribution of risk across the user base.

### Run This Query

```sql
WITH predictions AS (
  SELECT
    (SELECT prob FROM UNNEST(predicted_will_return_probs) WHERE label = 1) AS return_probability
  FROM ML.PREDICT(
    MODEL `propensity_modeling.gold_user_retention_model`,
    (SELECT * FROM `propensity_modeling.gold_training_features`)
  )
)
SELECT
  CASE
    WHEN return_probability < 0.3 THEN 'HIGH CHURN RISK'
    WHEN return_probability < 0.6 THEN 'MEDIUM RISK'
    ELSE 'LOW RISK'
  END AS risk_category,
  COUNT(*) AS user_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM predictions
GROUP BY risk_category
ORDER BY
  CASE risk_category
    WHEN 'HIGH CHURN RISK' THEN 1
    WHEN 'MEDIUM RISK' THEN 2
    ELSE 3
  END;
```

### Expected Output

```
risk_category    | user_count | percentage
-----------------|------------|------------
HIGH CHURN RISK  | 3872       | 21.3
MEDIUM RISK      | 6845       | 37.6
LOW RISK         | 7449       | 41.1
```

**Business insight:** ~21% of users are at high churn risk. This is your retention campaign target audience.

---

## Step 4: Identify Top At-Risk Users with Context

Get the behavioral patterns of high-risk users.

### Run This Query

```sql
SELECT
  f.user_pseudo_id,
  ROUND(p.return_probability, 3) AS return_probability,
  f.days_active,
  f.total_events,
  ROUND(f.level_completion_rate, 2) AS completion_rate,
  ROUND(f.engagement_minutes_per_day, 1) AS engagement_mins,
  f.days_since_last_activity
FROM ML.PREDICT(
  MODEL `propensity_modeling.gold_user_retention_model`,
  (SELECT * FROM `propensity_modeling.gold_training_features`)
) p
JOIN `propensity_modeling.gold_training_features` f
  ON p.user_pseudo_id = f.user_pseudo_id
  AND p.observation_date = f.observation_date
WHERE (SELECT prob FROM UNNEST(p.predicted_will_return_probs) WHERE label = 1) < 0.3
ORDER BY return_probability ASC
LIMIT 20;
```

### Expected Output

```
user_pseudo_id  | return_probability | days_active | total_events | completion_rate | engagement_mins | days_since_last_activity
----------------|--------------------| ------------|--------------|-----------------|-----------------|------------------------
1234567890.12...| 0.182              | 1           | 8            | 0.25            | 0.8             | 5
2345678901.23...| 0.237              | 2           | 15           | 0.33            | 1.2             | 4
3456789012.34...| 0.284              | 2           | 22           | 0.40            | 1.5             | 3
```

**Patterns in high-risk users:**
- Low days active (1-2 days in the window)
- Low total events (<30 events)
- Low completion rate (<0.5)
- Low engagement (<2 minutes/day)
- High recency (3-5 days since last activity)

---

## Step 5: The Limitation (Critical Demo Moment)

Now ask the question that sets up the next phase:

**"We know User 1234567890 has an 18% probability of returning. What should we do about it?"**

**Possible actions:**
1. Send generic "we miss you" email
2. Offer 10% discount on premium features
3. Send push notification about new levels
4. Personalized outreach from customer success

**The problem:** We don't know WHY this user stopped engaging.

**Scenarios:**
- **Scenario A:** User finds levels too difficult → Solution: Suggest easier levels or tips
- **Scenario B:** User frustrated by ads → Solution: Offer ad-free trial
- **Scenario C:** User experiencing bugs → Solution: Prioritize bug fixes
- **Scenario D:** User simply lost interest → Solution: Accept and move on

**Without understanding the "why," we're guessing.**

Generic retention campaigns are:
- Expensive (sending offers to everyone)
- Ineffective (wrong intervention for the problem)
- Annoying (users get irrelevant messages)

---

## Step 6: The Business Case for Multimodal Analytics

**Current state:**
```
Behavioral data → Churn prediction → Generic intervention
Result: 30-40% success rate on retention campaigns
```

**Desired state:**
```
Behavioral data + Sentiment data → Contextualized intervention
Result: 60-70% success rate on retention campaigns
```

**Example:**
- **Behavioral only:** "User X is at risk" → Send generic discount
- **Behavioral + Sentiment:** "User X is at risk AND complained about ads" → Offer premium ad-free trial

**ROI calculation:**
- If generic campaign converts 30%, you waste 70% of spend
- If targeted campaign converts 65%, you waste only 35% of spend
- That's a 2x improvement in campaign efficiency

---

## The Solution: Multimodal Analytics

To understand the "why" behind churn, we need to analyze **unstructured data**:
- User reviews (Play Store, App Store)
- Customer support tickets
- In-app feedback
- Social media mentions

**Traditional approach:**
1. Export reviews to CSV
2. Load into separate sentiment analysis tool
3. Manually join results with churn predictions
4. Complex pipeline, multiple tools

**Google Cloud approach:**
1. Query JSON reviews directly from Cloud Storage (BigLake)
2. Enrich with Gemini AI via SQL (no external API)
3. Join with churn predictions in BigQuery
4. Single platform, unified analysis

**This is where we're headed next.**

---

## Key Takeaways

| What We've Shown | Technology | Business Value |
|------------------|------------|----------------|
| **Churn scoring** | ML.PREDICT() | Identify at-risk users |
| **Risk segmentation** | SQL CASE statements | Prioritize interventions |
| **Behavioral patterns** | Feature analysis | Understand risk factors |
| **The limitation** | Missing sentiment context | Sets up multimodal need |

---

## What's Next

In the next guides, we'll:
1. **Query unstructured review data** from Cloud Storage (no ETL)
2. **Enrich with Gemini AI** for sentiment analysis (via SQL)
3. **Analyze sentiment patterns** to understand complaints
4. **Combine both domains** for targeted interventions

**The payoff:** "User X has 18% return probability AND recent reviews complain about ads" → Precise, data-driven intervention.

---

## Navigation

**Previous:** [02 - Train ML Model](02-train-ml-model.md)
**Next:** [04 - Sentiment Enrichment](04-sentiment-enrichment.md)
**Home:** [README](../../README.md)
