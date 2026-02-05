# Multimodal Insights

Combine churn predictions with sentiment analysis for targeted interventions.

## The Problem

Churn prediction tells you WHO will leave. Sentiment analysis tells you WHY users are unhappy. But these insights are in separate silos.

## The Solution

Combine behavioral predictions with sentiment data to enable targeted interventions:
1. **WHO** - Users at high churn risk (from BQML model)
2. **WHY** - Their specific complaints (from Gemini sentiment analysis)
3. **WHAT** - Targeted action based on both signals

## Technologies Used

| Service | Purpose |
|---------|---------|
| BigQuery ML | Churn predictions |
| Gemini 2.0 Flash | Sentiment categorization |
| Vertex AI | Model registry and deployment |
| BigQuery | Unified analytics platform |

## Key Results

- **60-70% conversion** vs 30-40% with generic campaigns
- **Targeted interventions** based on complaint category
- **Production-ready** deployment to Vertex AI

## Choose Your Path

| Path | Time | Description |
|------|------|-------------|
| [**Quick Reference**](quick.md) | 5 min | Just the SQL queries + outputs |
| [**Full Guide**](guide.md) | 7 min | Complete walkthrough |

## This Is The Capstone

This demo combines everything from Churn Prediction + Sentiment Analysis. Make sure you've completed those demos first.

---

## Navigation

[← Sentiment Analysis](../sentiment-analysis/overview.md) | [Campaign Intelligence →](../campaign-intelligence/overview.md) | [Back to Demos](../README.md)
