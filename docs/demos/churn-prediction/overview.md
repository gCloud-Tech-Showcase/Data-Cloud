# Churn Prediction

Predict which users will stop using your app using BigQuery ML.

## The Problem

You have millions of user events but no way to identify who's at risk of churning before they leave.

## The Solution

Train a machine learning model entirely in SQL using BigQuery ML:
1. **Feature Engineering** - Transform raw GA4 events into ML-ready features using rolling 7-day windows
2. **Model Training** - Train logistic regression with automatic feature preprocessing
3. **Predictions** - Score users and segment by risk level

## Technologies Used

| Service | Purpose |
|---------|---------|
| BigQuery | Data warehouse and ML training |
| BigQuery ML | In-database model training (no Python) |
| Vertex AI | Model registry and deployment |
| Dataform | Pipeline orchestration |

## Key Results

- **79% AUC** - Production-ready model performance
- **18K training rows** from 5.7M events
- **Zero Python** - Everything in SQL

## Choose Your Path

| Path | Time | Description |
|------|------|-------------|
| [**Quick Reference**](quick.md) | 5 min | Just the SQL queries + outputs |
| [**Features Guide**](01-features.md) | 7 min | Feature engineering walkthrough |
| [**Training Guide**](02-training.md) | 7 min | Model training and evaluation |
| [**Predictions Guide**](03-predictions.md) | 5 min | Scoring and risk segmentation |

## What's Next

After completing this demo, you'll know WHO is likely to churn, but not WHY. Continue to [Sentiment Analysis](../sentiment-analysis/overview.md) to understand the root causes.
