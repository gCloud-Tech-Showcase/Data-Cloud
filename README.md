# GCP Data Cloud Showcase

> Explore Google Cloud's data and AI capabilities through hands-on demos.

This repository demonstrates BigQuery, Gemini AI, Vertex AI, and related services through practical use cases. Each demo is self-contained with working SQL, infrastructure as code, and documentation.

---

## Demos

| Demo | What It Shows | Key Technologies |
|------|---------------|------------------|
| [**Churn Prediction**](docs/demos/churn-prediction/) | Train ML models in SQL | BigQuery ML, Vertex AI |
| [**Sentiment Analysis**](docs/demos/sentiment-analysis/) | AI on unstructured data | BigLake, Gemini |
| [**Campaign Intelligence**](docs/demos/campaign-intelligence/) | Spatial + public data | Geography, Census |
| [**Security Logs**](docs/demos/security-logs/) | AI-powered threat detection | Pipe syntax, embeddings |

Pick a demo based on your interest — each includes SQL queries, expected outputs, and step-by-step guides.

---

## Architecture

All demos follow the **medallion architecture** pattern:

```
Bronze (Raw)  →  Silver (Enriched)  →  Gold (Analytics-Ready)
```

- **Bronze** — Raw data in place (BigLake, external tables, log sinks)
- **Silver** — Cleansed and AI-enriched (Gemini analysis, flattened events)
- **Gold** — ML-ready features, trained models, materialized insights

See [Architecture Deep Dive](docs/architecture.md) for technical details.

---

## Quick Start

```bash
# 1. Configure
cp infra/terraform.tfvars.example infra/terraform.tfvars
# Edit with your project_id and github_token

# 2. Deploy infrastructure
cd infra && terraform apply

# 3. Run pipelines (via Dataform UI)
# Google Cloud Console → Dataform → Start Execution
```

**Full setup guide:** [Getting Started](docs/getting-started.md)

---

## Technologies

| Service | Purpose |
|---------|---------|
| **BigQuery** | Serverless data warehouse |
| **BigLake** | Query GCS/external data without ETL |
| **Gemini 2.0 Flash** | AI analysis via SQL |
| **BigQuery ML** | In-database ML training |
| **Vertex AI** | Model registry and deployment |
| **Dataform** | Git-native SQL transformations |
| **Terraform** | Infrastructure as Code |

---

## Project Structure

```
Data-Cloud/
├── definitions/                  # Dataform SQL pipelines
│   ├── propensity_modeling/      #   Churn prediction
│   ├── sentiment_analysis/       #   Review analysis
│   ├── campaign_intelligence/    #   Campaign targeting
│   └── security_logs/            #   Audit log analytics
├── infra/                        # Terraform IaC
├── scripts/                      # Python utilities
├── examples/                     # Standalone SQL examples
└── docs/                         # Documentation
    ├── getting-started.md
    ├── architecture.md
    └── demos/                    # Per-demo guides
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [**Getting Started**](docs/getting-started.md) | Deploy infrastructure and run pipelines |
| [**Demos**](docs/demos/README.md) | Step-by-step walkthroughs with SQL examples |
| [**Architecture**](docs/architecture.md) | Medallion layers, design decisions |

---

## License

This project is provided for educational and demonstration purposes.
