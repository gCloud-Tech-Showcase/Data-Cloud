# Sentiment Analysis

Understand WHY users are frustrated using Gemini AI to analyze unstructured reviews.

## The Problem

After predicting WHO will churn, you need to understand WHY they're unhappy to take targeted action.

## The Solution

Use Gemini 2.0 Flash to analyze unstructured user reviews directly in BigQuery:
1. **BigLake** - Query JSON review files from Cloud Storage without ETL
2. **Gemini Enrichment** - Extract sentiment, category, and scores via SQL
3. **Insights** - Identify top complaints and trends

## Technologies Used

| Service | Purpose |
|---------|---------|
| BigLake | Query JSON files in GCS without loading |
| Gemini 2.0 Flash | AI sentiment analysis via ML.GENERATE_TEXT |
| BigQuery | Unified analytics platform |
| Dataform | Incremental processing pipeline |

## Key Results

- **523 reviews** analyzed with AI sentiment
- **Top complaint:** Ads (42% of negative reviews)
- **Zero ETL** - Query GCS files directly
- **Incremental** - Only new reviews processed

## Choose Your Path

| Path | Time | Description |
|------|------|-------------|
| [**Quick Reference**](quick.md) | 5 min | Just the SQL queries + outputs |
| [**Enrichment Guide**](01-enrichment.md) | 7 min | BigLake + Gemini walkthrough |
| [**Insights Guide**](02-insights.md) | 5 min | Sentiment analysis and patterns |

## What's Next

After this demo, you'll know WHY users are unhappy. Continue to [Multimodal Insights](../multimodal-insights/overview.md) to combine WHO + WHY for targeted interventions.

---

## Navigation

[← Churn Prediction](../churn-prediction/overview.md) | [Multimodal Insights →](../multimodal-insights/overview.md) | [Back to Demos](../README.md)
