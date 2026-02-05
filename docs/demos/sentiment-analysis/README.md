# Sentiment Analysis

Analyze unstructured user reviews with Gemini AI to understand WHY users are frustrated.

## What You'll Build

Use Gemini 2.0 Flash to analyze reviews directly in BigQuery:
1. **BigLake** — Query JSON review files from Cloud Storage without ETL
2. **Gemini Enrichment** — Extract sentiment, category, and scores via SQL
3. **Insights** — Identify top complaints and trends

## Technologies

| Service | Purpose |
|---------|---------|
| BigLake | Query JSON files in GCS without loading |
| Gemini 2.0 Flash | AI sentiment analysis via ML.GENERATE_TEXT |
| Dataform | Incremental processing pipeline |

## Results

- **523 reviews** analyzed with AI sentiment
- **Top complaint:** Ads (42% of negative reviews)
- **Zero ETL** — Query GCS files directly
- **Incremental** — Only new reviews processed

## Guides

- [Quick Reference](quick.md) — SQL queries with expected outputs
- [Enrichment](01-enrichment.md) — BigLake + Gemini walkthrough
- [Insights](02-insights.md) — Analyze sentiment patterns

## What's Next

This tells you WHY users are unhappy. Continue to [Multimodal Insights](../multimodal-insights/) to combine WHO + WHY.
