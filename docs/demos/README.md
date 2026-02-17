# Guides

Explore GCP Data Cloud capabilities through these use cases.

| Use Case | Description |
|----------|-------------|
| [**Churn Prediction**](churn-prediction/) | Train a retention model with BigQuery ML |
| [**Sentiment Analysis**](sentiment-analysis/) | Analyze reviews with Gemini AI |
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

---

## Prerequisites by Demo

| Demo | Data Source | Setup Required | Notes |
|------|-------------|----------------|-------|
| **Churn Prediction** | GA4 public dataset | None | Public dataset, automatically accessible |
| **Sentiment Analysis** | Play Store reviews in GCS | Python scraper | Run `scripts/scrape_play_store_reviews.py` ([instructions](../../scripts/README.md)) |
| **Campaign Intelligence** | theLook + Census public datasets | None | Public datasets, automatically accessible |
| **Security Logs** | Cloud Audit Logs | Terraform + log generator | Run `terraform apply`, then `scripts/generate_security_logs.py` |

---

## Quick Reference

SQL queries with expected outputs — run these directly in BigQuery Console.

- [Churn Prediction](churn-prediction/quick.md)
- [Sentiment Analysis](sentiment-analysis/quick.md)
- [Campaign Intelligence](campaign-intelligence/quick.md)
- [Security Logs](security-logs/quick.md)

---

## Full Walkthroughs

Step-by-step guides with explanations.

- [Churn Prediction](churn-prediction/01-features.md)
- [Sentiment Analysis](sentiment-analysis/01-enrichment.md)
- [Campaign Intelligence](campaign-intelligence/guide.md)
- [Security Logs](security-logs/guide.md)

---

## Navigation

- [Getting Started](../getting-started.md)
- [Architecture](../architecture.md)
