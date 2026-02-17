# Data-Cloud Project

## Project Identity

Google Cloud Data Showcase - 4 demos using BigQuery, Gemini AI, and Vertex AI.

## Demos

| Demo | Description |
|------|-------------|
| `churn-prediction` | BQML user retention model |
| `sentiment-analysis` | Gemini review analysis |
| `campaign-intelligence` | Census geospatial targeting |
| `security-logs` | AI threat detection |

## Architecture

**Medallion Pattern:** Bronze (raw) → Silver (cleansed) → Gold (analytics-ready)

**Directory Layout:** `definitions/{domain}/{sources,staging,marts,ml}/`

## Technology Stack

- **Infrastructure:** Terraform
- **Data:** BigQuery, BigLake, Dataform
- **AI:** Gemini 2.0 Flash, BQML, Vertex AI

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
