# Security Logs Architecture

Data flow and pipeline structure for AI-powered audit log analytics.

---

## Pipeline Overview

```mermaid
graph TB
    subgraph "Bronze Layer - Raw Logs"
        SINK[Cloud Logging Sink]
        AUDIT[cloudaudit_googleapis_com_activity]
        DATA[cloudaudit_googleapis_com_data_access]
    end

    subgraph "BigQuery + Dataform"
        subgraph "Silver Layer - Enriched"
            EVENTS[silver_audit_events<br/>Flattened + Normalized]
            EMBED[silver_log_embeddings<br/>768-dim Vectors]
        end

        subgraph "Gold Layer - Analytics Ready"
            THREAT[gold_threat_classifications<br/>Gemini Triage]
        end
    end

    subgraph "Vertex AI"
        GEMINI[Gemini 2.0 Flash<br/>Threat Classifier]
        TEXT_EMB[text-embedding-005<br/>Semantic Vectors]
    end

    SINK --> AUDIT
    SINK --> DATA
    AUDIT --> EVENTS
    DATA --> EVENTS
    EVENTS --> EMBED
    TEXT_EMB -.-> |ML.GENERATE_EMBEDDING| EMBED
    EVENTS --> THREAT
    GEMINI -.-> |ML.GENERATE_TEXT| THREAT

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef gold fill:#ffd700,stroke:#333,color:#000
    classDef external fill:#4285f4,stroke:#333,color:#fff

    class AUDIT,DATA bronze
    class EVENTS,EMBED silver
    class THREAT gold
    class GEMINI,TEXT_EMB external
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant CL as Cloud Logging
    participant BQ as BigQuery
    participant Gemini as Gemini 2.0 Flash
    participant Embed as text-embedding-005

    CL->>BQ: Log Sink streams audit events
    Note over BQ: cloudaudit_googleapis_com_activity

    BQ->>BQ: Flatten nested protopayload
    Note over BQ: silver_audit_events

    BQ->>Embed: Generate embeddings
    Embed->>BQ: 768-dim vectors
    Note over BQ: silver_log_embeddings

    BQ->>Gemini: Classify threat level
    Gemini->>BQ: JSON response
    Note over BQ: gold_threat_classifications
```

---

## Key Components

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `cloudaudit_googleapis_com_activity` | Raw admin activity logs from sink |
| Bronze | `cloudaudit_googleapis_com_data_access` | Raw data access logs from sink |
| Silver | `silver_audit_events` | Flattened events with extracted fields |
| Silver | `silver_log_embeddings` | Semantic vectors for similarity search |
| Gold | `gold_threat_classifications` | AI-classified threats with explanations |

---

## AI Models

| Model | Type | Purpose |
|-------|------|---------|
| `gemini_log_analyst` | Remote (Gemini 2.0 Flash) | Threat classification and explanation |
| `text_embedding_model` | Remote (text-embedding-005) | Semantic embeddings for vector search |

---

## Navigation

[Guide](guide.md) | [Quick Reference](quick.md) | [Patterns Reference](../../architecture.md)
