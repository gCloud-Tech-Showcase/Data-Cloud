# Data-Cloud Project

## Project Identity

Google Cloud Data Showcase - 8 demos using BigQuery, Gemini AI, and Vertex AI.

## Demos

| Demo | Description |
|------|-------------|
| `churn-prediction` | BQML user retention model |
| `sentiment-analysis` | Gemini review analysis |
| `campaign-intelligence` | Census geospatial targeting |
| `security-logs` | AI threat detection |
| `vertica-ingestion` | Migrate from Vertica to BigQuery |
| `spanner-graph` | Property graph on Cloud Spanner |
| `bq-graph` | BigQuery property graph (GQL) |
| `video-vector-search` | Semantic video search with Gemini multimodal embeddings + React UI |

## Architecture

**Medallion Pattern:** Bronze (raw) → Silver (cleansed) → Gold (analytics-ready)

**Directory Layout:** `definitions/{domain}/{sources,staging,marts,ml}/`

## Technology Stack

- **Infrastructure:** Terraform
- **Data:** BigQuery, BigLake, Dataform
- **AI:** Gemini 2.5 Flash, BQML, Vertex AI, multimodalembedding@001
- **Functions:** Cloud Functions (2nd gen), Eventarc
- **Frontend:** React, Vite, Tailwind CSS, shadcn/ui (video-vector-search demo)
- **Backend:** Python FastAPI (video-vector-search demo)

## Conventions

**Dataform:**
```javascript
config {
  type: "table",
  schema: "dataset_name",
  description: "LAYER: Description",
  tags: ["domain", "layer", "category"]
}
```

**Naming:** `bronze_*` → `silver_*` → `gold_*`

**SQL:** `COALESCE()`, `SAFE_DIVIDE()`, `${ref("table")}`

## Security

Never commit: `terraform.tfvars`, `*.tfstate`, `.terraform/`, `scripts/.env`

## References

See `docs/architecture.md` for detailed patterns.
