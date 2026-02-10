# Sentiment Analysis - Quick Reference

SQL queries with expected outputs. Run these in BigQuery Console.

---

## 1. Query Raw Reviews from Cloud Storage

```sql
SELECT
  uri,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_id') AS review_id,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_text') AS review_text,
  SAFE_CAST(JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.rating') AS INT64) AS rating
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 5;
```

**Output:**
```
uri                          | review_id | review_text                      | rating
-----------------------------|-----------|----------------------------------|--------
gs://.../review_abc123.json  | abc123    | Love this game! Very addictive   | 5
gs://.../review_def456.json  | def456    | Too many ads, can't even play    | 2
```

---

## 2. View Gemini-Enriched Reviews

```sql
SELECT
  review_date,
  rating,
  LEFT(review_text, 60) AS review_snippet,
  sentiment,
  category,
  sentiment_score
FROM `sentiment_analysis.silver_review_sentiment`
ORDER BY review_date DESC
LIMIT 10;
```

**Output:**
```
review_date | rating | review_snippet                          | sentiment | category | sentiment_score
------------|--------|-----------------------------------------|-----------|----------|----------------
2018-09-28  | 5      | Best puzzle game ever! Hours of fun     | positive  | praise   | 0.92
2018-09-20  | 1      | Constant crashes, literally unplayable  | negative  | bugs     | -0.88
```

---

## 3. Sentiment Distribution

```sql
SELECT
  sentiment,
  COUNT(*) AS review_count,
  ROUND(AVG(rating), 2) AS avg_rating,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY sentiment
ORDER BY review_count DESC;
```

**Output:**
```
sentiment | review_count | avg_rating | percentage
----------|--------------|------------|------------
positive  | 327          | 4.8        | 62.5
neutral   | 98           | 3.2        | 18.7
negative  | 98           | 1.7        | 18.7
```

---

## 4. Complaint Categories

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
performance | 7     | -0.754
```

---

## 5. Sample Negative Reviews

```sql
SELECT
  category,
  rating,
  review_text,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 5;
```

**Output:**
```
category | rating | review_text                                  | score
---------|--------|----------------------------------------------|-------
bugs     | 1      | App crashes constantly, can't finish a level | -0.92
ads      | 1      | Way too many ads! Literally unplayable       | -0.88
bugs     | 2      | Freezes every time I try to play             | -0.85
```

---

## 6. Sentiment Over Time

```sql
SELECT
  DATE_TRUNC(review_date, MONTH) AS month,
  sentiment,
  COUNT(*) AS review_count
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY month, sentiment
ORDER BY month, sentiment;
```

**Output:**
```
month      | sentiment | review_count
-----------|-----------|-------------
2018-06-01 | negative  | 18
2018-06-01 | positive  | 52
2018-07-01 | negative  | 25
2018-07-01 | positive  | 68
```

---

## Navigation

- [Overview](./)
- [Full Guides](01-enrichment.md)
- [Back to Demos](../README.md)
