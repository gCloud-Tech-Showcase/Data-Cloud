# Churn Prediction

Predict which users will stop using your app using BigQuery ML.

## What You'll Build

Train a machine learning model entirely in SQL:
1. **Feature Engineering** — Transform raw GA4 events into ML-ready features using rolling 7-day windows
2. **Model Training** — Train logistic regression with automatic feature preprocessing
3. **Predictions** — Score users and segment by risk level

## Technologies

| Service | Purpose |
|---------|---------|
| BigQuery ML | In-database model training |
| Vertex AI | Model registry |
| Dataform | Pipeline orchestration |

## Results

- **79% AUC** — Production-ready model
- **18K training rows** from 5.7M events
- **Zero Python** — Everything in SQL

## Guides

- [Quick Reference](quick.md) — SQL queries with expected outputs
- [Feature Engineering](01-features.md) — Build ML-ready features
- [Model Training](02-training.md) — Train and evaluate the model
- [Predictions](03-predictions.md) — Score users by risk level

## What's Next

This tells you WHO will churn, but not WHY. Continue to [Sentiment Analysis](../sentiment-analysis/overview.md) to understand root causes.
