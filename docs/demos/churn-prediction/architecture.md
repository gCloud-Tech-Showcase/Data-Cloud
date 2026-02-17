# Churn Prediction Architecture

Data flow and pipeline structure for user retention modeling with BigQuery ML.

---

## Pipeline Overview

```mermaid
graph TB
    subgraph "Bronze Layer - Raw Data"
        GA4[Firebase GA4<br/>Public Dataset]
    end

    subgraph "BigQuery + Dataform"
        subgraph "Silver Layer - Cleansed"
            FLAT[silver_events_flattened<br/>Unnested GA4]
        end

        subgraph "Gold Layer - ML Ready"
            FEAT[gold_training_features<br/>7-day Windows]
            MODEL[gold_user_retention_model<br/>BQML Logistic Reg]
            FI[gold_feature_importance<br/>ML.GLOBAL_EXPLAIN]
            SCORES[gold_user_risk_scores<br/>ML.PREDICT]
        end
    end

    subgraph "Vertex AI"
        REGISTRY[Model Registry<br/>Versioning]
    end

    GA4 --> FLAT
    FLAT --> FEAT
    FEAT --> MODEL
    MODEL --> REGISTRY
    MODEL --> FI
    MODEL --> SCORES

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef gold fill:#ffd700,stroke:#333,color:#000
    classDef external fill:#4285f4,stroke:#333,color:#fff

    class GA4 bronze
    class FLAT silver
    class FEAT,MODEL,FI,SCORES gold
    class REGISTRY external
```

---

## Data Flow

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
    Note over Gold: CTE-based:<br/>date_spine x users

    Gold->>BQML: CREATE MODEL<br/>TRANSFORM + LOGISTIC_REG
    Note over BQML: Auto-scaling,<br/>categorical encoding

    BQML->>VA: Register to Model Registry<br/>model_registry='vertex_ai'
    Note over VA: Versioning,<br/>explainability enabled
```

---

## Key Components

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `events_*` | Raw GA4 events (external declaration) |
| Silver | `silver_events_flattened` | Unnested event parameters |
| Gold | `gold_training_features` | Rolling 7-day window features |
| Gold | `gold_user_retention_model` | Trained logistic regression |
| Gold | `gold_feature_importance` | Feature weights via ML.GLOBAL_EXPLAIN |
| Gold | `gold_user_risk_scores` | Materialized predictions |

---

## Feature Engineering

Uses **rolling 7-day windows** instead of static "first 7 days":

```
User A, Week 1: Days 1-7   → Did they return Days 8-14?
User A, Week 2: Days 8-14  → Did they return Days 15-21?
User A, Week 3: Days 15-21 → Did they return Days 22-28?
```

This creates multiple training rows per user, capturing behavioral dynamics over time.

---

## Navigation

[Guide](01-features.md) | [Quick Reference](quick.md) | [Patterns Reference](../../architecture.md)
