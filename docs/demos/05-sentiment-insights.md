# Demo Guide 05: Sentiment Insights

**Objective:** Analyze sentiment patterns to understand what customers complain about.

**Time:** 5 minutes

**What you'll demonstrate:**
- Sentiment distribution analysis
- Category breakdowns (bugs, ads, difficulty)
- Time-based sentiment trends
- Actionable product insights from unstructured feedback

---

## Step 1: Overall Sentiment Distribution

Understand the breakdown of positive, neutral, and negative reviews.

### Run This Query

```sql
SELECT
  sentiment,
  COUNT(*) AS review_count,
  ROUND(AVG(rating), 2) AS avg_rating,
  ROUND(AVG(sentiment_score), 3) AS avg_sentiment_score,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY sentiment
ORDER BY avg_sentiment_score DESC;
```

### Expected Output

```
sentiment | review_count | avg_rating | avg_sentiment_score | percentage
----------|--------------|------------|---------------------|------------
positive  | 327          | 4.8        | 0.856               | 62.5
neutral   | 98           | 3.2        | 0.012               | 18.7
negative  | 98           | 1.7        | -0.742              | 18.7
```

**Insights:**
- **62.5% positive sentiment** - Most users are happy
- **18.7% negative sentiment** - But significant minority is frustrated
- **Correlation:** Sentiment score strongly correlates with star rating
- **Opportunity:** Focus on the ~100 negative reviews to understand root causes

---

## Step 2: Complaint Category Breakdown

Identify the most common complaint categories.

### Run This Query

```sql
SELECT
  category,
  sentiment,
  COUNT(*) AS count,
  ROUND(AVG(rating), 1) AS avg_rating,
  ROUND(AVG(sentiment_score), 3) AS avg_score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
GROUP BY category, sentiment
ORDER BY count DESC;
```

### Expected Output

```
category     | sentiment | count | avg_rating | avg_score
-------------|-----------|-------|------------|----------
ads          | negative  | 42    | 1.8        | -0.810
bugs         | negative  | 32    | 1.5        | -0.872
difficulty   | negative  | 15    | 2.1        | -0.687
performance  | negative  | 7     | 1.9        | -0.754
other        | negative  | 2     | 2.0        | -0.623
```

**Key Findings:**
1. **Ads (42 reviews):** The #1 complaint - ads are disruptive
2. **Bugs (32 reviews):** Crashes and technical issues frustrate users
3. **Difficulty (15 reviews):** Some find levels too hard

**Business actions:**
- **Ads:** Consider premium ad-free tier or reduce ad frequency
- **Bugs:** Prioritize stability fixes for high-impact crashes
- **Difficulty:** Add difficulty settings or tutorial content

---

## Step 3: See Actual Ad Complaints

Drill into the ads category to read actual feedback.

### Run This Query

```sql
SELECT
  review_date,
  rating,
  review_text,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE category = 'ads'
  AND sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 10;
```

### Expected Output

```
review_date | rating | review_text                                                  | score
------------|--------|--------------------------------------------------------------|-------
2018-08-15  | 1      | Way too many ads! Can't even play the game                   | -0.92
2018-07-22  | 2      | Ad after every level is ridiculous                           | -0.88
2018-09-03  | 1      | Literally unplayable because of constant ad interruptions    | -0.85
2018-06-28  | 2      | Would be 5 stars without the aggressive advertising          | -0.81
2018-08-11  | 2      | Love the game but the ads make it frustrating                | -0.79
```

**Pattern:** Users love the game but find ads disruptive. This is a **monetization vs. experience tradeoff**.

**Business opportunity:** Offer premium ad-free version. Based on feedback, users would pay to remove ads.

---

## Step 4: See Actual Bug Complaints

Drill into the bugs category for technical issues.

### Run This Query

```sql
SELECT
  review_date,
  rating,
  review_text,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE category = 'bugs'
  AND sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 10;
```

### Expected Output

```
review_date | rating | review_text                                                  | score
------------|--------|--------------------------------------------------------------|-------
2018-07-15  | 1      | Crashes every time I reach level 3                           | -0.95
2018-08-22  | 1      | App freezes constantly on my phone                           | -0.91
2018-09-05  | 1      | Can't even open the app anymore after update                 | -0.89
2018-06-30  | 2      | Keeps crashing mid-game and I lose all progress              | -0.86
2018-07-18  | 1      | Worked great before last update, now won't load              | -0.83
```

**Patterns:**
- Crashes at specific points ("level 3", "mid-game")
- Device-specific issues ("on my phone")
- Update-related regressions ("after update")

**Business action:** Prioritize crash analytics, add better error logging, QA testing for specific devices.

---

## Step 5: Sentiment Over Time

Track how sentiment changes over time (e.g., after updates).

### Run This Query

```sql
SELECT
  DATE_TRUNC(review_date, MONTH) AS month,
  sentiment,
  COUNT(*) AS review_count,
  ROUND(AVG(sentiment_score), 3) AS avg_score
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY month, sentiment
ORDER BY month, sentiment;
```

### Expected Output

```
month      | sentiment | review_count | avg_score
-----------|-----------|--------------|----------
2018-06-01 | positive  | 52           | 0.871
2018-06-01 | neutral   | 15           | 0.018
2018-06-01 | negative  | 18           | -0.752
2018-07-01 | positive  | 68           | 0.845
2018-07-01 | neutral   | 21           | 0.009
2018-07-01 | negative  | 25           | -0.738
2018-08-01 | positive  | 87           | 0.862
2018-08-01 | neutral   | 28           | 0.015
2018-08-01 | negative  | 32           | -0.741
```

**Trend analysis:** Negative reviews increasing month-over-month (18 → 25 → 32). This could indicate:
- Growing user base (more reviews overall)
- Degrading experience (bugs introduced)
- Increased monetization pressure (more ads)

---

## Step 6: Most Helpful Reviews

Find reviews with high engagement (thumbs up count).

### Run This Query

```sql
SELECT
  review_date,
  rating,
  LEFT(review_text, 100) AS review_snippet,
  thumbs_up_count,
  sentiment,
  category
FROM `sentiment_analysis.silver_review_sentiment`
WHERE thumbs_up_count > 10
ORDER BY thumbs_up_count DESC
LIMIT 10;
```

### Expected Output

```
review_date | rating | review_snippet                                                              | thumbs_up_count | sentiment | category
------------|--------|-----------------------------------------------------------------------------|-----------------|-----------|-------------
2018-07-22  | 2      | Would be 5 stars without the ads. Every level = ad. Too much!               | 45              | negative  | ads
2018-06-28  | 5      | Best puzzle game ever! Super addictive, love the challenge                  | 38              | positive  | praise
2018-08-15  | 1      | Crashes constantly on Galaxy S8. Fix your bugs!                             | 32              | negative  | bugs
2018-09-03  | 4      | Fun game but gets repetitive after 50 levels. Need more variety             | 28              | neutral   | difficulty
```

**Insight:** High-engagement reviews often represent the sentiment of many users. The top ad complaint has 45 thumbs up - likely reflects broader frustration.

---

## Step 7: Compare Positive vs. Negative Feedback

See what users praise vs. what they complain about.

### Positive Feedback

```sql
SELECT
  category,
  COUNT(*) AS count,
  ROUND(AVG(rating), 1) AS avg_rating
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'positive'
GROUP BY category
ORDER BY count DESC;
```

### Expected Output (Positive)

```
category     | count | avg_rating
-------------|-------|------------
praise       | 187   | 5.0
difficulty   | 52    | 4.6
performance  | 38    | 4.7
other        | 50    | 4.5
```

**What users love:**
- **Praise (187):** Addictive gameplay, fun mechanics, great design
- **Difficulty (52):** Challenging but fair levels
- **Performance (38):** Runs smoothly, good graphics

---

## Actionable Insights Summary

| Finding | Evidence | Business Action |
|---------|----------|-----------------|
| **Ads are the #1 complaint** | 42 negative reviews, avg score -0.81 | Offer premium ad-free tier at $2.99/mo |
| **Crash issues frustrating users** | 32 negative reviews, avg score -0.87 | Prioritize stability fixes, add crash analytics |
| **Users love the core gameplay** | 187 positive reviews mentioning "addictive" | Double down on level design, add content |
| **Negative sentiment increasing** | 18 → 25 → 32 over 3 months | Investigate recent updates for regressions |
| **High-value users frustrated by ads** | Most-liked review (45 thumbs up) about ads | Target engaged users for premium conversion |

---

## Key Takeaways

| Capability | What We Did | Business Value |
|------------|-------------|----------------|
| **Sentiment distribution** | Analyzed 523 reviews | Understand overall user satisfaction |
| **Category breakdown** | Grouped by complaint type | Prioritize product improvements |
| **Drill-downs** | Read actual feedback | Specific, actionable insights |
| **Trend analysis** | Sentiment over time | Catch degrading experience early |
| **SQL-based analytics** | All in BigQuery | No export, no separate tools |

---

## What We've Accomplished

We now understand:
1. **What users complain about:** Ads (42%), Bugs (33%), Difficulty (15%)
2. **How severe complaints are:** Avg sentiment score -0.81 for ads, -0.87 for bugs
3. **What users love:** Addictive gameplay, challenging levels
4. **Trends:** Negative sentiment increasing month-over-month

**But we still haven't connected this to churn predictions...**

In the next guide, we'll combine behavioral churn predictions with sentiment insights to enable targeted interventions.

---

## Navigation

**Previous:** [04 - Sentiment Enrichment](04-sentiment-enrichment.md)
**Next:** [06 - Multimodal Analytics](06-multimodal-analytics.md)
**Home:** [README](../../README.md)
