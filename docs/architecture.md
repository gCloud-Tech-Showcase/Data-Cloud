# Architecture Deep Dive

This document explains the technical architecture, design decisions, and data flow patterns in the Data-Cloud project.

---

## Architecture Overview

### Sentiment Analysis & Propensity Modeling

```mermaid
graph TB
    subgraph "Bronze Layer - Raw Data"
        GCS[GCS Bucket<br/>Play Store Reviews JSON]
        GA4[Firebase GA4<br/>Public Dataset]
    end

    subgraph "BigQuery + Dataform"
        subgraph "Bronze Objects"
            BRONZE_REV[bronze_user_reviews<br/>BigLake Object Table]
            BRONZE_EVT[events_*<br/>External Declaration]
        end

        subgraph "Silver Layer - Cleansed"
            SILVER_REV[silver_review_sentiment<br/>Gemini Enriched]
            SILVER_EVT[silver_events_flattened<br/>Unnested GA4]
        end

        subgraph "Gold Layer - ML Ready"
            GOLD_FEAT[gold_training_features<br/>7-day Windows]
            GOLD_MODEL[gold_user_retention_model<br/>BQML Logistic Reg]
            GOLD_FI[gold_user_retention_model_feature_importance<br/>ML.GLOBAL_EXPLAIN]
            GOLD_SCORES[gold_user_risk_scores<br/>ML.PREDICT Materialized]
        end
    end

    subgraph "Vertex AI"
        GEMINI[Gemini 2.0 Flash<br/>Remote Model]
        REGISTRY[Model Registry<br/>Versioning]
    end

    GCS --> BRONZE_REV
    GA4 --> BRONZE_EVT

    BRONZE_REV --> |ML.GENERATE_TEXT| SILVER_REV
    GEMINI -.-> |powers| SILVER_REV

    BRONZE_EVT --> SILVER_EVT
    SILVER_EVT --> GOLD_FEAT
    GOLD_FEAT --> GOLD_MODEL
    GOLD_MODEL --> REGISTRY
    GOLD_MODEL --> GOLD_FI
    GOLD_MODEL --> GOLD_SCORES

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef gold fill:#ffd700,stroke:#333,color:#000
    classDef external fill:#4285f4,stroke:#333,color:#fff

    class BRONZE_REV,BRONZE_EVT bronze
    class SILVER_REV,SILVER_EVT silver
    class GOLD_FEAT,GOLD_MODEL,GOLD_FI,GOLD_SCORES gold
    class GEMINI,REGISTRY external
```

### Campaign Intelligence *(Proof of Concept)*

```mermaid
graph TB
    subgraph "Bronze Layer - Public Datasets"
        THELOOK[theLook eCommerce<br/>users • events • orders]
        CENSUS_GEO[Census Tracts<br/>Geographic Boundaries]
        CENSUS_ACS[Census ACS<br/>Housing & Income]
    end

    subgraph "BigQuery + Dataform"
        subgraph "Silver Layer - Spatial Joins"
            SILVER_USERS[silver_users_with_census<br/>ST_CONTAINS Join]
            SILVER_ENGAGE[silver_engagement_signals<br/>User Aggregates]
            SILVER_DEMO[silver_tract_demographics<br/>Housing Features]
        end

        subgraph "Gold Layer - Campaign Ready"
            GOLD_TRACT[gold_tract_campaign_features<br/>Tract Scoring]
            GOLD_SEG[gold_user_segments<br/>User Segments]
            GOLD_REC[gold_campaign_recommendations<br/>AI Recommendations]
        end
    end

    subgraph "Vertex AI"
        GEMINI_AGENT[Gemini 2.0 Flash<br/>Campaign Agent]
    end

    THELOOK --> SILVER_USERS
    THELOOK --> SILVER_ENGAGE
    CENSUS_GEO --> SILVER_USERS
    CENSUS_ACS --> SILVER_DEMO

    SILVER_USERS --> GOLD_TRACT
    SILVER_ENGAGE --> GOLD_TRACT
    SILVER_DEMO --> GOLD_TRACT

    SILVER_USERS --> GOLD_SEG
    SILVER_ENGAGE --> GOLD_SEG
    GOLD_TRACT --> GOLD_SEG

    GOLD_TRACT --> GOLD_REC
    GEMINI_AGENT -.-> |ML.GENERATE_TEXT| GOLD_REC

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef gold fill:#ffd700,stroke:#333,color:#000
    classDef external fill:#4285f4,stroke:#333,color:#fff

    class THELOOK,CENSUS_GEO,CENSUS_ACS bronze
    class SILVER_USERS,SILVER_ENGAGE,SILVER_DEMO silver
    class GOLD_TRACT,GOLD_SEG,GOLD_REC gold
    class GEMINI_AGENT external
```

**Campaign Intelligence Pipeline:**
- **Bronze** - Declarations for 3 public datasets (theLook eCommerce, Census tracts, Census ACS)
- **Silver** - Spatial joins (ST_CONTAINS), engagement aggregation, demographic features
- **Gold** - Campaign scoring by census tract, user segmentation, Gemini-generated recommendations

---

## Data Flow: Sentiment Analysis Domain

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

## Data Flow: Propensity Modeling Domain

```mermaid
sequenceDiagram
    participant GA4 as Firebase GA4<br/>Public Dataset
    participant Silver as silver_events_flattened
    participant Gold as gold_training_features
    participant BQML as gold_user_retention_model
    participant VA as Vertex AI

    GA4->>Silver: Unnest event_params<br/>Parse dates, flatten structure
    Note over Silver: View with UNNEST,<br/>type conversions

    Silver->>Gold: Rolling 7-day windows<br/>Feature engineering
    Note over Gold: CTE-based:<br/>date_spine × users

    Gold->>BQML: CREATE MODEL<br/>TRANSFORM + LOGISTIC_REG
    Note over BQML: Auto-scaling,<br/>categorical encoding

    BQML->>VA: Register to Model Registry<br/>model_registry='vertex_ai'
    Note over VA: Versioning,<br/>explainability enabled
```

---

## Data Flow: Campaign Intelligence Domain *(Proof of Concept)*

```mermaid
sequenceDiagram
    participant TL as theLook eCommerce<br/>Public Dataset
    participant CT as Census Tracts<br/>Public Dataset
    participant ACS as Census ACS<br/>Public Dataset
    participant Silver as Silver Layer<br/>Spatial Joins
    participant Gold as Gold Layer<br/>Campaign Scores
    participant Gemini as Gemini 2.0 Flash

    TL->>Silver: Users with lat/long
    CT->>Silver: Tract geometries
    Note over Silver: ST_CONTAINS spatial join<br/>silver_users_with_census

    TL->>Silver: Events + Orders
    Note over Silver: Aggregate engagement<br/>silver_engagement_signals

    ACS->>Silver: Housing + Income data
    Note over Silver: Demographics by tract<br/>silver_tract_demographics

    Silver->>Gold: Combined features
    Note over Gold: Campaign scoring<br/>gold_tract_campaign_features

    Silver->>Gold: User-level features
    Note over Gold: Segment assignment<br/>gold_user_segments

    Gold->>Gemini: Campaign summaries
    Gemini->>Gold: AI recommendations
    Note over Gold: gold_campaign_recommendations
```

---

## Medallion Architecture Explained

This project follows the **bronze/silver/gold pattern** popularized by modern data lakehouses.

### Bronze Layer - Raw, Immutable

**Purpose:** Landing zone for raw data exactly as-is

**Characteristics:**
- No transformations or data quality checks
- Append-only (immutable)
- Full audit trail and reprocessing capability
- Preserves original data formats

**Implementation:**
- `bronze_user_reviews` - BigLake Object Table pointing to GCS JSON files
- `events_*` - External declaration for Firebase GA4 dataset

---

### Silver Layer - Cleansed, Validated

**Purpose:** Business-ready data with quality checks and enrichment

**Characteristics:**
- Type conversions (BYTES → STRING, date parsing)
- Unnesting of nested/repeated fields
- Null handling with COALESCE
- AI enrichment (Gemini sentiment analysis)
- Deduplication via incremental processing

**Implementation:**
- `silver_review_sentiment` - Incremental table with Gemini-enriched reviews
- `silver_events_flattened` - View that unnests GA4 event_params array

---

### Gold Layer - Feature-Engineered, Analytics-Ready

**Purpose:** ML-ready features and business aggregations

**Characteristics:**
- Feature engineering (rolling windows, aggregations)
- Dimensional modeling for analytics
- ML training datasets with features + labels
- Trained models and predictions

**Implementation:**
- `gold_training_features` - 7-day rolling window features with labels
- `gold_user_retention_model` - BQML logistic regression model

---

## Data Mesh with Domain Ownership

```
definitions/
├── sentiment_analysis/          # Domain 1: Review analysis
│   ├── sources/                # Bronze layer
│   ├── models/                 # AI models
│   └── staging/                # Silver layer
│
├── propensity_modeling/        # Domain 2: User retention
│   ├── sources/                # Bronze layer
│   ├── staging/                # Silver layer
│   ├── marts/                  # Gold layer
│   └── ml/                     # Gold layer (models)
│
└── campaign_intelligence/      # Domain 3: Campaign targeting
    ├── sources/                # Bronze layer (Census + theLook)
    ├── staging/                # Silver layer (spatial joins)
    ├── marts/                  # Gold layer (scoring)
    └── models/                 # Gold layer (Gemini agent)
```

---

## Feature Engineering Strategy

The propensity model uses **rolling 7-day windows** instead of static "first 7 days":

### Traditional Approach (Not Recommended)
```
User A: Days 1-7 → Will they return on Day 8?
(Single training row per user)
```

### Our Approach
```
User A, Week 1: Days 1-7   → Did they return Days 8-14?
User A, Week 2: Days 8-14  → Did they return Days 15-21?
User A, Week 3: Days 15-21 → Did they return Days 22-28?
(Multiple training rows per user)
```

**Why?**
1. **More training data**: ~18K rows instead of ~15K
2. **Temporal dynamics**: Captures how behavior changes over time
3. **Continuous prediction**: Can score users at any point in their lifecycle
4. **Realistic labels**: Based on actual future behavior

---

## BigLake Object Tables

Traditional approach: **ETL (Extract-Transform-Load)**
```
GCS JSON → Load to BigQuery → Transform → Query
```

Our approach: **ELT with BigLake (Extract-Load-Transform)**
```
GCS JSON (stays in place) → BigQuery queries directly → Transform in SQL
```

**Benefits:**
1. **No data movement**: Query GCS files directly via SQL
2. **Efficiency**: Query data in place, no storage duplication
3. **Simplicity**: No ETL pipelines to maintain
4. **Freshness**: Changes in GCS reflected automatically

---

## Gemini AI Integration

Gemini 2.0 Flash is accessed as a **remote model** in BigQuery:

```sql
-- 1. Create remote model connection
CREATE OR REPLACE MODEL gemini_sentiment_model
  REMOTE WITH CONNECTION `US.vertex-ai-connection`
  OPTIONS (endpoint = 'gemini-2.0-flash-001');

-- 2. Use in SQL query
SELECT *
FROM ML.GENERATE_TEXT(
  MODEL sentiment_analysis.gemini_sentiment_model,
  (SELECT uri, data_string, CONCAT('...') AS prompt FROM bronze_user_reviews),
  STRUCT(0.2 AS temperature, 1024 AS max_output_tokens, TRUE AS flatten_json_output)
);
```

---

## Incremental Processing

The `silver_review_sentiment` table uses Dataform's incremental mode:

```javascript
config {
  type: "incremental",
  uniqueKey: ["review_id"]
}
```

**How it works:**
1. First run: Processes all reviews
2. Subsequent runs: Only new reviews not in the target table
3. Deduplication: Uses `uniqueKey` to prevent duplicates

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Infrastructure** | Terraform 1.6+ | Declarative GCP resource provisioning |
| **Data Warehouse** | BigQuery | Serverless SQL analytics and storage |
| **Object Storage** | Cloud Storage (GCS) | Unstructured data (JSON reviews) |
| **Multimodal Data** | BigLake Object Tables | Query GCS files without data movement |
| **AI/ML** | Gemini 2.0 Flash | Multimodal sentiment analysis |
| **ML Training** | BigQuery ML | In-database logistic regression |
| **Model Management** | Vertex AI | Model registry, versioning, deployment |
| **Data Transformation** | Dataform 3.0 | SQL-based ETL with Git integration |

---

## Design Decisions

### Why BigQuery instead of a traditional lakehouse?

1. **Serverless**: No clusters to manage or tune
2. **Separation of storage/compute**: Pay only for what you use
3. **Integrated AI**: Gemini models via SQL
4. **BigLake**: Query GCS data without ETL
5. **Google Cloud native**: Tight integration with Vertex AI, Dataform

### Why Dataform instead of dbt or Apache Airflow?

1. **Managed service**: No infrastructure to maintain
2. **Git-native**: Direct GitHub integration
3. **BigQuery optimized**: Uses SCRIPT, MERGE, CREATE OR REPLACE efficiently
4. **Tag-based workflows**: Run subsets of pipeline

### Why Gemini 2.0 Flash?

1. **Multimodal**: Can analyze text, images, and video
2. **Fast**: Flash variant optimized for speed
3. **BigQuery integration**: No external API orchestration
4. **Structured output**: Native JSON parsing

---

## Related Documentation

- [Getting Started](../getting-started.md) - Installation and configuration
- [Demo Guides](../demos/README.md) - Step-by-step demonstrations
- [CLAUDE.md](../../CLAUDE.md) - Development guide
