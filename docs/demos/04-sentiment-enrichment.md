# Demo Guide 04: Sentiment Enrichment

**Objective:** Query unstructured review data and enrich with Gemini AI sentiment analysis.

**Time:** 5-7 minutes

**What you'll demonstrate:**
- Query JSON files in Cloud Storage without ETL (BigLake)
- Enrich reviews with Gemini AI via SQL (no external APIs)
- Process 500+ reviews with sentiment, category, and scores
- Incremental processing (only new data is processed)

---

## Step 1: Query Raw Reviews from Cloud Storage

BigLake Object Tables let you query JSON files directly from GCS using SQL.

### Run This Query

```sql
SELECT
  uri,
  SAFE_CONVERT_BYTES_TO_STRING(data) AS review_json
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 5;
```

### Expected Output

```
uri                                                          | review_json
-------------------------------------------------------------|----------------------------------------
gs://.../user-reviews/play-store/flood-it/review_abc123.json | {"platform": "play-store", "review_id": "abc123", ...}
gs://.../user-reviews/play-store/flood-it/review_def456.json | {"platform": "play-store", "review_id": "def456", ...}
...
```

**Key Point:** The data stays in Cloud Storage. BigQuery queries it in place without loading or duplicating data.

---

## Step 2: Parse JSON Fields

Extract specific fields from the JSON data.

### Run This Query

```sql
SELECT
  uri,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_id') AS review_id,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.user_name') AS user_name,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_text') AS review_text,
  SAFE_CAST(JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.rating') AS INT64) AS rating,
  JSON_EXTRACT_SCALAR(SAFE_CONVERT_BYTES_TO_STRING(data), '$.review_date') AS review_date
FROM `sentiment_analysis.bronze_user_reviews`
LIMIT 10;
```

### Expected Output

```
uri                          | review_id | user_name   | review_text                                    | rating | review_date
-----------------------------|-----------|-------------|------------------------------------------------|--------|-------------
gs://.../review_abc123.json  | abc123    | John Doe    | Love this game! Very addictive                 | 5      | 2018-06-20
gs://.../review_def456.json  | def456    | Jane Smith  | Too many ads, can't even play                  | 2      | 2018-07-15
gs://.../review_ghi789.json  | ghi789    | Bob Johnson | Crashes all the time on my device              | 1      | 2018-08-03
...
```

**Key Point:** BigQuery's JSON functions make it easy to work with semi-structured data.

---

## Step 3: View Gemini-Enriched Reviews

The `silver_review_sentiment` table contains reviews enriched with Gemini AI analysis.

### Run This Query

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

### Expected Output

```
review_date | rating | review_snippet                                            | sentiment | category    | sentiment_score
------------|--------|-----------------------------------------------------------|-----------|-------------|----------------
2018-09-28  | 5      | Best puzzle game ever! Hours of fun                       | positive  | praise      | 0.92
2018-09-25  | 4      | Good game but gets repetitive after a while               | neutral   | difficulty  | 0.15
2018-09-20  | 1      | Constant crashes, literally unplayable                    | negative  | bugs        | -0.88
2018-09-18  | 2      | Would be good without so many ads                         | negative  | ads         | -0.76
2018-09-15  | 5      | Super addictive, can't stop playing!                      | positive  | praise      | 0.89
...
```

**Gemini AI extracts:**
- **Sentiment:** positive, neutral, or negative
- **Category:** bugs, ads, difficulty, performance, praise, other
- **Score:** Numeric value from -1 (very negative) to +1 (very positive)

---

## Step 4: Understand How Gemini Enrichment Works

The enrichment happens in `silver_review_sentiment.sqlx` using `ML.GENERATE_TEXT()`.

### SQL Pattern

```sql
SELECT
  uri,
  JSON_EXTRACT_SCALAR(data_string, '$.review_id') AS review_id,
  JSON_EXTRACT_SCALAR(data_string, '$.review_text') AS review_text,
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
          'Analyze this app review and return ONLY a valid JSON object with these fields:\n',
          '{"sentiment": "positive|neutral|negative", "category": "bugs|ads|difficulty|performance|praise|other", "score": <float between -1 and 1>}\n\n',
          'Review: "', SAFE_CONVERT_BYTES_TO_STRING(data), '"'
        ) AS prompt
      FROM `sentiment_analysis.bronze_user_reviews`
    ),
    STRUCT(
      0.2 AS temperature,
      1024 AS max_output_tokens,
      TRUE AS flatten_json_output
    )
  );
```

**Key features:**
- **Model:** Gemini 2.0 Flash (multimodal model)
- **Temperature:** 0.2 (deterministic, consistent results)
- **flatten_json_output:** Automatically parses JSON responses
- **No external API:** Gemini is called directly from SQL

---

## Step 5: See Incremental Processing in Action

The table uses incremental mode to avoid reprocessing existing reviews.

### Check for New Reviews

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

### Expected Output

```
processed_reviews
-----------------
523

unprocessed_reviews
-------------------
0
```

**How incremental processing works:**
1. First Dataform run: Process all 523 reviews → Calls Gemini API 523 times
2. Second run (no new data): Process 0 reviews → Calls Gemini API 0 times
3. New reviews added to GCS: Process only new reviews → Efficient

**Configuration:**
```javascript
config {
  type: "incremental",
  uniqueKey: ["review_id"]
}
```

**Key Point:** Only new data is processed on each run, avoiding redundant API calls.

---

## Step 6: Sample Reviews by Sentiment

See examples of each sentiment category.

### Run This Query

```sql
SELECT
  sentiment,
  rating,
  review_text,
  category,
  ROUND(sentiment_score, 2) AS score
FROM `sentiment_analysis.silver_review_sentiment`
WHERE sentiment = 'positive'
ORDER BY sentiment_score DESC
LIMIT 3;
```

### Expected Output (Positive Reviews)

```
sentiment | rating | review_text                                               | category | score
----------|--------|-----------------------------------------------------------|----------|------
positive  | 5      | Absolutely love this game! Best puzzle game I've played   | praise   | 0.95
positive  | 5      | Super addictive! Can't stop playing                       | praise   | 0.92
positive  | 4      | Great game, really challenging levels                     | praise   | 0.78
```

### Run for Negative Reviews

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

### Expected Output (Negative Reviews)

```
sentiment | rating | review_text                                               | category    | score
----------|--------|-----------------------------------------------------------|-------------|-------
negative  | 1      | App crashes constantly, can't even finish a level         | bugs        | -0.92
negative  | 1      | Way too many ads! Literally unplayable                    | ads         | -0.88
negative  | 2      | Freezes every time I try to play                          | bugs        | -0.85
negative  | 2      | Would be great without the constant ad interruptions      | ads         | -0.81
negative  | 1      | Levels are impossible, super frustrating                  | difficulty  | -0.76
```

**Pattern:** Low ratings correlate with negative sentiment and specific complaint categories.

---

## How This Compares to Traditional Approaches

### Traditional Sentiment Analysis

**Steps:**
1. Export reviews from app store to CSV
2. Upload CSV to sentiment analysis tool (external service)
3. Wait for batch processing
4. Download results
5. Join with BigQuery data via ETL pipeline

**Problems:**
- Multiple tools and platforms
- Data duplication
- Complex pipeline maintenance
- API rate limits and quotas
- Latency (hours to days)

### Google Cloud Approach

**Steps:**
1. Query reviews directly from Cloud Storage (BigLake)
2. Enrich with Gemini via SQL (ML.GENERATE_TEXT)
3. Results immediately available in BigQuery

**Benefits:**
- Single platform (BigQuery)
- No data movement
- SQL-based (accessible to analysts)
- Incremental processing (efficient)
- Real-time enrichment capability

---

## Key Takeaways

| Capability | Technology | Business Value |
|------------|------------|----------------|
| **Query unstructured data** | BigLake Object Tables | No ETL, no data duplication |
| **AI enrichment via SQL** | Gemini 2.0 Flash + ML.GENERATE_TEXT() | No external APIs, unified platform |
| **Structured output** | flatten_json_output=TRUE | Easy to query sentiment results |
| **Incremental processing** | Dataform incremental tables | Process only new data |
| **Multimodal capabilities** | Gemini 2.0 Flash | Supports text, images, and video |

---

## Navigation

**Previous:** [03 - Churn Predictions](03-churn-predictions.md)
**Next:** [05 - Sentiment Insights](05-sentiment-insights.md)
**Home:** [README](../../README.md)
