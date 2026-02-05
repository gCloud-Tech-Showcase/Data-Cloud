# Demo Guides

Choose your path based on time and audience.

| Demo | Time | Audience | Description |
|------|------|----------|-------------|
| [**Churn Prediction**](churn-prediction/overview.md) | 5-20 min | Analysts, Data Scientists | Predict user retention with BigQuery ML |
| [**Sentiment Analysis**](sentiment-analysis/overview.md) | 5-20 min | Analysts, Data Scientists | Gemini-powered review analysis |
| [**Multimodal Insights**](multimodal-insights/overview.md) | 5-15 min | Executives, Analysts | Combine WHO churns + WHY they're unhappy |
| [**Campaign Intelligence**](campaign-intelligence/overview.md) | 5-20 min | Marketing, Analysts | Public data campaign targeting |

---

## Quick Path (15 min)

Just the SQL queries with expected outputs. Perfect for demos or quick exploration.

1. [Churn Prediction - Quick](churn-prediction/quick.md)
2. [Sentiment Analysis - Quick](sentiment-analysis/quick.md)
3. [Multimodal Insights - Quick](multimodal-insights/quick.md)
4. [Campaign Intelligence - Quick](campaign-intelligence/quick.md)

---

## Full Demo Path (45 min)

Step-by-step walkthrough with explanations and business context.

### Narrative Flow (Recommended)

These three demos build on each other:

```
Churn Prediction → Sentiment Analysis → Multimodal Insights
   (WHO churns)      (WHY unhappy)       (Targeted action)
```

1. Start: [Churn Prediction Guide](churn-prediction/01-features.md)
2. Continue: [Sentiment Analysis Guide](sentiment-analysis/01-enrichment.md)
3. Capstone: [Multimodal Insights Guide](multimodal-insights/guide.md)

### Standalone Demo

Campaign Intelligence stands alone - no prerequisites:

- [Campaign Intelligence Guide](campaign-intelligence/guide.md)

---

## Demo Tips

### For Technical Audiences
- Emphasize SQL-first approach (no Python required)
- Show Dataform dependency graph
- Highlight incremental processing

### For Data Scientists
- Focus on `ML.GLOBAL_EXPLAIN()` and `ML.EXPLAIN_PREDICT()`
- Discuss TRANSFORM clause for feature engineering
- Show model evaluation metrics

### For Business Stakeholders
- Start with Churn Predictions to show the limitation
- Jump to Multimodal Insights for the business value
- Emphasize: targeted interventions vs. generic campaigns

---

## Navigation

- [Getting Started](../getting-started.md) - Deploy infrastructure
- [Architecture](../reference/architecture.md) - Technical deep dive
- [Home](../../README.md) - Project overview
