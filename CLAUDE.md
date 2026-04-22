# CLAUDE.md

## WHAT: Project Overview

Google Cloud Data Showcase with **8 demos** using BigQuery, Gemini AI, and Vertex AI:

1. **Churn Prediction** - BQML user retention model with rolling 7-day windows
2. **Sentiment Analysis** - Gemini-powered review analysis via BigLake
3. **Campaign Intelligence** - Census geospatial + theLook targeting (proof of concept)
4. **Security Logs** - AI threat detection with log embeddings
5. **Vertica Ingestion** - Migrate data from Vertica to BigQuery with Dataproc + Spark
6. **Spanner Graph** - Property graph queries for data center topology analysis
7. **BQ Graph** - BigQuery property graph for data center topology GQL analytics
8. **Video Vector Search** - Semantic video search with Gemini multimodal embeddings, BQ Vector Search, React UI, and ADK-powered conversational agent ("The Archivist")

**Key Directories:** `definitions/{domain}/` for Dataform, `infra/` for Terraform, `docs/` for guides.

## HOW: Development

```bash
# Infrastructure
cd infra && terraform init && terraform plan && terraform apply

# Dataform: Cloud Console → Dataform → data-cloud → Compile → Execute

# Python scripts - ALWAYS use the virtual environment
cd scripts
source .venv/bin/activate  # Activate venv before running any script
python generate_security_logs.py --help
```

## Conventions

**Dataform config block:**
```javascript
config {
  type: "table",           // declaration, view, table, incremental, operations
  schema: "dataset_name",
  description: "LAYER: Description",  // BRONZE/SILVER/GOLD prefix
  tags: ["domain", "layer", "category"]
}
```

**Naming:** `bronze_*` → `silver_*` → `gold_*`

**Tags:**
- Domain: `sentiment_analysis`, `propensity_modeling`, `campaign_intelligence`, `security_logs`, `data_center_topology`, `video_vector_search`
- Layer: `bronze`, `silver`, `gold`
- Category: `sources`, `staging`, `marts`, `ml`, `models`, `examples`

**SQL:** `COALESCE()` for nulls, `SAFE_DIVIDE()` for division, `${ref("table")}` for deps.

## Gotchas

- Declarations don't support `tags` property - only type, schema, name, description
- GA4 dates are `YYYYMMDD` strings - use `PARSE_DATE('%Y%m%d', col)`
- Use `${self()}` in BQML model definitions for self-reference

## Security

**Never commit:** `terraform.tfvars`, `workflow_settings.yaml`, `.terraform/`, `*.tfstate`, `scripts/.env`, `scripts/service-account-key.json`

**Never output secrets/tokens in logs or responses.**

## References

See `docs/architecture.md` for patterns, `docs/demos/*/architecture.md` for per-demo details.
