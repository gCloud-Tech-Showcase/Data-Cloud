# Multimodal Insights

Combine churn predictions with sentiment analysis for targeted interventions.

## What You'll Build

Join behavioral predictions with sentiment data:
1. **WHO** — Users at high churn risk (from BQML model)
2. **WHY** — Their specific complaints (from Gemini sentiment)
3. **WHAT** — Targeted action based on both signals

## Technologies

| Service | Purpose |
|---------|---------|
| BigQuery ML | Churn predictions |
| Gemini 2.0 Flash | Sentiment categorization |
| Vertex AI | Model registry and deployment |

## Results

- **Targeted interventions** based on complaint category
- **Production-ready** deployment to Vertex AI

## Guides

- [Quick Reference](quick.md) — SQL queries with expected outputs
- [Full Guide](guide.md) — Complete walkthrough

## Prerequisites

Complete [Churn Prediction](../churn-prediction/) and [Sentiment Analysis](../sentiment-analysis/) first.
