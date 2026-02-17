# Guides

Explore GCP Data Cloud capabilities through these use cases.

| Use Case | Description |
|----------|-------------|
| [**Churn Prediction**](churn-prediction/) | Train a retention model with BigQuery ML |
| [**Sentiment Analysis**](sentiment-analysis/) | Analyze reviews with Gemini AI |
| [**Multimodal Insights**](multimodal-insights/) | Combine behavioral + sentiment data |
| [**Campaign Intelligence**](campaign-intelligence/) | Target campaigns using public Census data *(proof of concept)* |
| [**Security Logs**](security-logs/) | AI-powered audit log analysis with semantic search |

---

## Choose Your Path

| If you're interested in... | Start here |
|---------------------------|------------|
| ML/AI model training in SQL | [Churn Prediction](churn-prediction/) |
| Unstructured data + Gemini | [Sentiment Analysis](sentiment-analysis/) |
| Security / log analytics | [Security Logs](security-logs/) |
| Geospatial + public data | [Campaign Intelligence](campaign-intelligence/) |
| Combining multiple data signals | [Multimodal Insights](multimodal-insights/) |

---

## Prerequisites by Demo

| Demo | Data Source | Setup Required | Notes |
|------|-------------|----------------|-------|
| **Churn Prediction** | GA4 public dataset | None | Public dataset, automatically accessible |
| **Sentiment Analysis** | Play Store reviews in GCS | Python scraper | Run `scripts/scrape_play_store_reviews.py` ([instructions](../../scripts/README.md)) |
| **Multimodal Insights** | Both above | Same as above | Combines churn predictions with sentiment data |
| **Campaign Intelligence** | theLook + Census public datasets | None | Public datasets, automatically accessible |
| **Security Logs** | Cloud Audit Logs | Terraform + log generator | Run `terraform apply`, then `scripts/generate_security_logs.py` |

---

## Quick Reference

SQL queries with expected outputs — run these directly in BigQuery Console.

- [Churn Prediction](churn-prediction/quick.md)
- [Sentiment Analysis](sentiment-analysis/quick.md)
- [Multimodal Insights](multimodal-insights/quick.md)
- [Campaign Intelligence](campaign-intelligence/quick.md)
- [Security Logs](security-logs/quick.md)

---

## Full Walkthroughs

Step-by-step guides with explanations.

### Connected Use Cases

These three build on each other:

```
Churn Prediction → Sentiment Analysis → Multimodal Insights
   (WHO churns)      (WHY unhappy)       (Targeted action)
```

1. [Churn Prediction](churn-prediction/01-features.md)
2. [Sentiment Analysis](sentiment-analysis/01-enrichment.md)
3. [Multimodal Insights](multimodal-insights/guide.md)

### Standalone

These can be explored independently:

- [Campaign Intelligence](campaign-intelligence/guide.md)
- [Security Logs](security-logs/guide.md)

---

## Navigation

- [Getting Started](../getting-started.md)
- [Architecture](../architecture.md)
