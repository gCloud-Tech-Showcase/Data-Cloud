# Sentiment Enrichment

Query unstructured review data and enrich with Gemini AI sentiment analysis.

**Time:** 5-7 minutes

---

## Step 1: Query Raw Reviews from Cloud Storage

BigLake Object Tables let you query JSON files directly from GCS using SQL.

```sql
SELECT
  uri,
  SAFE_CONVERT_BYTES_TO_STRING(data) AS review_json
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 5;
```

**Key Point:** The data stays in Cloud Storage. BigQuery queries it in place without loading or duplicating data.

---

## Step 2: Parse JSON Fields

Extract specific fields from the JSON data.

```sql
SELECT
  uri,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_id') AS review_id,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.user_name') AS user_name,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_text') AS review_text,
  SAFE_CAST(JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.rating') AS INT64) AS rating
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 10;
```

---

## Step 3: View Gemini-Enriched Reviews

The `silver_review_sentiment` table contains reviews enriched with Gemini AI analysis.

```sql
SELECT
  review_date,
  rating,
  LEFT(review_text, 80) AS review_snippet,
  sentiment,
  category,
  sentiment_score
FROM `sentiment_analysis.silver_review_sentiment`
ORDER BY review_date DESC
LIMIT 15;
```

**Gemini AI extracts:**
- **Sentiment:** positive, neutral, or negative
- **Category:** bugs, ads, difficulty, performance, praise, other
- **Score:** Numeric value from -1 (very negative) to +1 (very positive)

---

## Step 4: How Gemini Enrichment Works

The enrichment happens in `silver_review_sentiment.sqlx` using `ML.GENERATE_TEXT()`.

```sql
SELECT
  uri,
  JSON_EXTRACT_SCALAR(data_string, '$.review_id') AS review_id,
  JSON_EXTRACT_SCALAR(ml_generate_text_llm_result, '$.predictions[0].content.sentiment') AS sentiment,
  JSON_EXTRACT_SCALAR(ml_generate_text_llm_result, '$.predictions[0].content.category') AS category,
  SAFE_CAST(JSON_EXTRACT_SCALAR(ml_generate_text_llm_result, '$.predictions[0].content.score') AS FLOAT64) AS sentiment_score
FROM ML.GENERATE_TEXT(
    MODEL `sentiment_analysis.gemini_sentiment_model`,
    (
      SELECT
        uri,
        SAFE_CONVERT_BYTES_TO_STRING(data) AS data_string,
        CONCAT(
          'Analyze this app review and return ONLY a valid JSON object:\n',
          '{"sentiment": "positive|neutral|negative", "category": "bugs|ads|difficulty|performance|praise|other", "score": <float -1 to 1>}\n\n',
          'Review: "', SAFE_CONVERT_BYTES_TO_STRING(data), '"'
        ) AS prompt
      FROM `sentiment_analysis.bronze_user_reviews`
    ),
    STRUCT(0.2 AS temperature, 1024 AS max_output_tokens, TRUE AS flatten_json_output)
  );
```

**Key features:**
- **Model:** Gemini 2.0 Flash (multimodal)
- **Temperature:** 0.2 (deterministic results)
- **flatten_json_output:** Automatically parses JSON responses
- **No external API:** Gemini called directly from SQL

---

## Step 5: Incremental Processing

The table uses incremental mode to avoid reprocessing existing reviews.

```sql
-- See which reviews are already processed
SELECT COUNT(DISTINCT review_id) AS processed_reviews
FROM `sentiment_analysis.silver_review_sentiment`;

-- See which reviews exist in bronze but not in silver
SELECT COUNT(*) AS unprocessed_reviews
FROM `sentiment_analysis.bronze_user_reviews` bronze
WHERE JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_id') NOT IN (
  SELECT review_id FROM `sentiment_analysis.silver_review_sentiment`
);
```

**How it works:**
1. First run: Process all 523 reviews
2. Second run (no new data): Process 0 reviews
3. New reviews added to GCS: Process only new reviews

**Configuration:**
```javascript
config {
  type: "incremental",
  uniqueKey: ["review_id"]
}
```

---

## Step 6: Sample Reviews by Sentiment

```sql
SELECT
  sentiment,
  rating,
  review_text,
  category,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'negative'
ORDER BY sentiment_score ASC
LIMIT 5;
```

**Pattern:** Low ratings correlate with negative sentiment and specific complaint categories.

---

## Key Takeaways

| Capability | Technology | Business Value |
|------------|------------|----------------|
| Query unstructured data | BigLake Object Tables | No ETL, no data duplication |
| AI enrichment via SQL | Gemini + ML.GENERATE_TEXT() | No external APIs |
| Structured output | flatten_json_output=TRUE | Easy to query results |
| Incremental processing | Dataform incremental tables | Process only new data |

---

## Navigation

[← Overview](./) | [Next: Insights →](02-insights.md) | [Quick Reference](quick.md)
