# Sentiment Insights

Analyze sentiment patterns to understand what customers complain about.

**Time:** 5 minutes

---

## Step 1: Overall Sentiment Distribution

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

| sentiment | review_count | avg_rating | avg_sentiment_score | percentage |
|-----------|--------------|------------|---------------------|------------|
| positive | 327 | 4.8 | 0.856 | 62.5 |
| neutral | 98 | 3.2 | 0.012 | 18.7 |
| negative | 98 | 1.7 | -0.742 | 18.7 |

**Insights:**
- 62.5% positive sentiment - Most users are happy
- 18.7% negative sentiment - Significant minority is frustrated
- Sentiment score strongly correlates with star rating

---

## Step 2: Complaint Category Breakdown

```sql
SELECT
  category,
  COUNT(*) AS count,
  ROUND(AVG(rating), 1) AS avg_rating,
  ROUND(AVG(sentiment_score), 3) AS avg_score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
GROUP BY category
ORDER BY count DESC;
```

| category | count | avg_rating | avg_score |
|----------|-------|------------|-----------|
| ads | 42 | 1.8 | -0.810 |
| bugs | 32 | 1.5 | -0.872 |
| difficulty | 15 | 2.1 | -0.687 |
| performance | 7 | 1.9 | -0.754 |

**Key Findings:**
1. **Ads (42 reviews):** The #1 complaint - ads are disruptive
2. **Bugs (32 reviews):** Crashes and technical issues
3. **Difficulty (15 reviews):** Some find levels too hard

---

## Step 3: Drill Into Ad Complaints

```sql
SELECT
  review_date,
  rating,
  review_text,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE category = 'ads' AND sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 5;
```

| review_date | rating | review_text | score |
|-------------|--------|-------------|-------|
| 2018-08-15 | 1 | Way too many ads! Can't even play the game | -0.92 |
| 2018-07-22 | 2 | Ad after every level is ridiculous | -0.88 |
| 2018-09-03 | 1 | Literally unplayable because of constant ad interruptions | -0.85 |

**Business opportunity:** Users would pay to remove ads. Offer premium ad-free version.

---

## Step 4: Drill Into Bug Complaints

```sql
SELECT
  review_date,
  rating,
  review_text,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE category = 'bugs' AND sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 5;
```

| review_date | rating | review_text | score |
|-------------|--------|-------------|-------|
| 2018-07-15 | 1 | Crashes every time I reach level 3 | -0.95 |
| 2018-08-22 | 1 | App freezes constantly on my phone | -0.91 |
| 2018-09-05 | 1 | Can't even open the app anymore after update | -0.89 |

**Patterns:** Crashes at specific points, device-specific issues, update-related regressions.

---

## Step 5: Sentiment Over Time

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

**Trend:** Negative reviews increasing month-over-month (18 → 25 → 32). Could indicate:
- Growing user base (more reviews overall)
- Degrading experience (bugs introduced)
- Increased monetization pressure (more ads)

---

## Step 6: High-Engagement Reviews

```sql
SELECT
  review_date,
  rating,
  LEFT(review_text, 80) AS review_snippet,
  thumbs_up_count,
  sentiment,
  category
FROM `sentiment_analysis.silver_review_sentiment`
WHERE thumbs_up_count > 10
ORDER BY thumbs_up_count DESC
LIMIT 5;
```

High-engagement reviews often represent the sentiment of many users. The top ad complaint has 45 thumbs up - likely reflects broader frustration.

---

## Actionable Insights

| Finding | Evidence | Business Action |
|---------|----------|-----------------|
| Ads are #1 complaint | 42 reviews, avg -0.81 | Offer premium ad-free tier |
| Crashes frustrating users | 32 reviews, avg -0.87 | Prioritize stability fixes |
| Users love core gameplay | 187 positive reviews | Double down on level design |
| Negative sentiment increasing | 18 → 32 over 3 months | Investigate recent updates |

---

## The Limitation

We now understand:
- **What users complain about:** Ads (42%), Bugs (33%), Difficulty (15%)
- **How severe complaints are:** Avg score -0.81 for ads, -0.87 for bugs
- **What users love:** Addictive gameplay, challenging levels

**But we still haven't connected this to churn predictions.**

---

## What's Next

Continue to [Multimodal Insights](../multimodal-insights/) to combine WHO will churn with WHY they're unhappy.

---

## Navigation

[← Enrichment](01-enrichment.md) | [Multimodal Insights →](../multimodal-insights/) | [Quick Reference](quick.md)
