# Sentiment Analysis Architecture

Data flow and pipeline structure for AI-powered review analysis with Gemini.

---

## Pipeline Overview

```mermaid
graph TB
    subgraph "Bronze Layer - Raw Data"
        GCS[GCS Bucket<br/>Play Store Reviews JSON]
    end

    subgraph "BigQuery + Dataform"
        subgraph "Bronze Objects"
            BRONZE[bronze_user_reviews<br/>BigLake Object Table]
        end

        subgraph "Silver Layer - Enriched"
            SILVER[silver_review_sentiment<br/>Gemini Enriched]
        end
    end

    subgraph "Vertex AI"
        GEMINI[Gemini 2.0 Flash<br/>Remote Model]
    end

    GCS --> BRONZE
    BRONZE --> |ML.GENERATE_TEXT| SILVER
    GEMINI -.-> |powers| SILVER

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef external fill:#4285f4,stroke:#333,color:#fff

    class BRONZE bronze
    class SILVER silver
    class GEMINI external
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant User as Python Scraper
    participant GCS as Cloud Storage
    participant BQ as BigQuery
    participant Gemini as Gemini 2.0 Flash
    participant DT as silver_review_sentiment

    User->>GCS: Upload review JSON files
    Note over GCS: gs://.../user-reviews/play-store/flood-it/*.json

    GCS->>BQ: BigLake Object Table<br/>bronze_user_reviews
    Note over BQ: No data movement,<br/>query JSON in-place

    BQ->>Gemini: ML.GENERATE_TEXT(review_text)<br/>"Analyze this app review..."
    Gemini->>BQ: Return sentiment JSON<br/>{sentiment, category, score}

    BQ->>DT: Incremental INSERT<br/>Only new review_ids
    Note over DT: Type: incremental<br/>uniqueKey: review_id
```

---

## Key Components

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `bronze_user_reviews` | BigLake Object Table for GCS JSON |
| Silver | `silver_review_sentiment` | Gemini-enriched reviews (incremental) |

---

## AI Model

| Model | Type | Purpose |
|-------|------|---------|
| `gemini_sentiment_model` | Remote (Gemini 2.0 Flash) | Sentiment classification with structured JSON output |

**Output fields:** sentiment (positive/negative/neutral), category (bug/feature/praise/complaint), confidence_score

---

## Incremental Processing

The `silver_review_sentiment` table uses Dataform's incremental mode:

```javascript
config {
  type: "incremental",
  uniqueKey: ["review_id"]
}
```

Only new reviews are processed on each run, avoiding duplicate Gemini API calls.

---

## Navigation

[Guide](01-enrichment.md) | [Quick Reference](quick.md) | [Patterns Reference](../../architecture.md)
