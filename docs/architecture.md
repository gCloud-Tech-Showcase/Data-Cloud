# Architecture Patterns Reference

Shared patterns and design decisions used across all demos.

---

## Medallion Architecture

All demos follow the **bronze/silver/gold pattern**:

```
Bronze (Raw)  →  Silver (Enriched)  →  Gold (Analytics-Ready)
```

### Bronze Layer - Raw, Immutable

**Purpose:** Landing zone for raw data exactly as-is

- No transformations or data quality checks
- Append-only (immutable)
- Full audit trail and reprocessing capability
- Preserves original data formats

**Implementations:** BigLake Object Tables, external declarations, log sinks

---

### Silver Layer - Cleansed, Validated

**Purpose:** Business-ready data with quality checks and enrichment

- Type conversions (BYTES → STRING, date parsing)
- Unnesting of nested/repeated fields
- Null handling with COALESCE
- AI enrichment (Gemini analysis)
- Deduplication via incremental processing

---

### Gold Layer - Feature-Engineered, Analytics-Ready

**Purpose:** ML-ready features and business aggregations

- Feature engineering (rolling windows, aggregations)
- Dimensional modeling for analytics
- ML training datasets with features + labels
- Trained models and predictions

---

## BigLake Object Tables

Query unstructured data in GCS without ETL:

```
Traditional: GCS JSON → Load to BigQuery → Transform → Query
BigLake:     GCS JSON (stays in place) → Query directly → Transform in SQL
```

**Benefits:**
- No data movement or storage duplication
- No ETL pipelines to maintain
- Changes in GCS reflected automatically

---

## Gemini AI Integration

Gemini 2.0 Flash accessed as a **remote model** in BigQuery:

```sql
-- Create remote model
CREATE OR REPLACE MODEL `dataset.gemini_model`
  REMOTE WITH CONNECTION `project.region.connection`
  OPTIONS (endpoint = 'gemini-2.0-flash-001');

-- Use in SQL
SELECT *
FROM ML.GENERATE_TEXT(
  MODEL `dataset.gemini_model`,
  (SELECT content, prompt FROM source_table),
  STRUCT(0.2 AS temperature, 1024 AS max_output_tokens)
);
```

---

## Vector Embeddings

Semantic search with text-embedding-005:

```sql
-- Generate embeddings
SELECT *
FROM ML.GENERATE_EMBEDDING(
  MODEL `dataset.text_embedding_model`,
  (SELECT content FROM source_table),
  STRUCT('SEMANTIC_SIMILARITY' AS task_type)
);

-- Similarity search
SELECT *, ML.DISTANCE(a.embedding, b.embedding, 'COSINE') AS distance
FROM table_a a, table_b b
ORDER BY distance ASC;
```

---

## Incremental Processing

Dataform's incremental mode for efficient updates:

```javascript
config {
  type: "incremental",
  uniqueKey: ["id"]
}

SELECT * FROM source
${when(incremental(), `WHERE id NOT IN (SELECT id FROM ${self()})`)}
```

Only new rows are processed on each run.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Infrastructure | Terraform | Declarative GCP provisioning |
| Data Warehouse | BigQuery | Serverless SQL analytics |
| Object Storage | Cloud Storage | Unstructured data |
| Multimodal Data | BigLake | Query GCS without ETL |
| AI/ML | Gemini 2.0 Flash | Text analysis via SQL |
| ML Training | BigQuery ML | In-database model training |
| Model Management | Vertex AI | Registry and deployment |
| Transformation | Dataform | Git-native SQL pipelines |

---

## Design Decisions

### Why BigQuery?

1. **Serverless** - No clusters to manage
2. **Separation of storage/compute** - Pay for what you use
3. **Integrated AI** - Gemini models via SQL
4. **BigLake** - Query GCS data without ETL

### Why Dataform?

1. **Managed service** - No infrastructure
2. **Git-native** - Direct GitHub integration
3. **Tag-based workflows** - Run pipeline subsets

### Why Gemini 2.0 Flash?

1. **Fast** - Optimized for speed
2. **BigQuery integration** - No external orchestration
3. **Structured output** - Native JSON parsing

---

## Per-Demo Architecture

Each demo has its own architecture diagram:

- [Churn Prediction](demos/churn-prediction/architecture.md)
- [Sentiment Analysis](demos/sentiment-analysis/architecture.md)
- [Campaign Intelligence](demos/campaign-intelligence/architecture.md)
- [Security Logs](demos/security-logs/architecture.md)

---

## Navigation

[Getting Started](getting-started.md) | [Demos](demos/README.md)
