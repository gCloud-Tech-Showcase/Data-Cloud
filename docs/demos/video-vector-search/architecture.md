# Video Vector Search Architecture

Data flow and pipeline structure for semantic video search.

---

## Pipeline Overview

```mermaid
graph TB
    subgraph "Data Ingestion"
        A[Archive.org] -->|source_archive_videos.py| B[GCS raw/]
        B -->|Cloud Function trigger| C[ffmpeg segmentation]
        C --> D[GCS segments/]
        C --> E[GCS thumbnails/]
    end

    subgraph "Bronze Layer"
        D --> G[bronze_video_segments<br/>Object Table]
    end

    subgraph "Silver Layer"
        G -->|AI.GENERATE_EMBEDDING| H[silver_segment_embeddings<br/>1408-dim vectors]
        G -->|AI.GENERATE + Gemini 2.5| I[silver_video_metadata<br/>15 AI-extracted fields]
    end

    subgraph "Gold Layer"
        H --> J[gold_searchable_videos]
        I --> J
        G -->|GCS object metadata| J
    end

    subgraph "UI Layer"
        J -->|VECTOR_SEARCH| K[FastAPI Backend]
        K --> L[React Frontend]
        K -->|ADK Agent| M[Gemini 2.5 Flash<br/>The Archivist]
        M -->|Conversational Analytics| J
    end
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant GCS
    participant CF as Cloud Function
    participant DF as Dataform
    participant BQ as BigQuery
    participant Gemini
    participant K as ADK Agent
    participant UI as React UI

    User->>GCS: Upload video to raw/
    GCS->>CF: Object finalization event
    CF->>CF: ffmpeg split (2-min segments)
    CF->>GCS: Upload segments + thumbnail

    Note over DF: Scheduled (hourly)
    DF->>BQ: Refresh object table cache
    DF->>Gemini: AI.GENERATE_EMBEDDING (per segment)
    DF->>BQ: Store embeddings in silver table
    DF->>Gemini: AI.GENERATE (metadata extraction)
    DF->>BQ: Store metadata in silver table
    DF->>BQ: Rebuild gold table (join all)

    User->>UI: Search "friendship"
    UI->>BQ: VECTOR_SEARCH on gold table
    BQ->>UI: Ranked results with metadata
    UI->>User: Video cards with AI descriptions

    User->>UI: Chat "Find adventure cartoons"
    UI->>K: POST /api/agent/chat
    K->>Gemini: ADK Agent (tool selection)
    Gemini->>K: Call search_videos("adventure cartoons")
    K->>BQ: VECTOR_SEARCH
    BQ->>K: Results
    K->>UI: {text, actions: [{type: "search"}]}
    UI->>User: Chat response + UI updates
```

---

## Key Components

| Layer | Table/Resource | Type | Purpose |
|-------|---------------|------|---------|
| Bronze | `bronze_video_segments` | Object Table (SIMPLE) | GCS video segments queryable via SQL |
| Model | `multimodal_embedding_model` | Remote Model | `multimodalembedding@001` for video/text embeddings |
| Model | `gemini_video_model` | Remote Model | Gemini 2.5 Flash for AI metadata extraction |
| Silver | `silver_segment_embeddings` | Incremental Table | 1408-dim embeddings per segment interval |
| Silver | `silver_video_metadata` | Incremental Table | 15 AI-extracted fields per video |
| Gold | `gold_searchable_videos` | Table | Embeddings + GCS metadata + AI metadata joined |
| Agent | The Archivist (ADK) | LlmAgent | Conversational assistant with 9 tools (Gemini 2.5 Flash) |

---

## AI Models

| Model | Endpoint | Purpose | Input |
|-------|----------|---------|-------|
| Multimodal Embedding | `multimodalembedding@001` | Cross-modal vector embeddings | Video segments (16s intervals) |
| Gemini 2.5 Flash | `gemini-2.5-flash` | Structured metadata extraction | Video segment 0 via `AI.GENERATE` |
| Gemini 2.5 Flash | `gemini-2.5-flash` | Agent reasoning + tool use | Natural language via ADK Agent (runtime) |
| Conversational Analytics | `geminidataanalytics` | NL-to-SQL on video metadata | Agent `query_metadata` tool |

---

## Key Technical Details

- **2-minute segment limit**: `AI.GENERATE_EMBEDDING` analyzes max 120 seconds per video. Videos are split into 2-min segments; results grouped by parent video at query time.
- **GCS object metadata**: Title, year, timing info stored as custom metadata on each segment GCS object. Extracted in gold table via `UNNEST(metadata)`.
- **Incremental processing**: Silver tables use `type: "incremental"` with `uniqueKey` — only new segments/videos are processed on each Dataform run.
- **Object table cache**: `AUTOMATIC` mode with 30-minute staleness. New segments visible within 30 minutes.
- **Cross-modal search**: Text queries search against video embeddings because `multimodalembedding@001` encodes both modalities in the same vector space.
- **Vector indexing**: Not enabled — brute-force scan is fast enough at this scale (~4K rows). For larger libraries, create a [vector index](https://cloud.google.com/bigquery/docs/vector-index) on `gold_searchable_videos.embedding` to accelerate `VECTOR_SEARCH` queries.

---

## Infrastructure (Terraform)

| Resource | Purpose |
|----------|---------|
| `google_bigquery_dataset.video_vector_search` | BQ dataset |
| `google_storage_bucket.video_search` | GCS bucket for all video data |
| `google_cloudfunctions2_function.segment_video` | Auto-segmentation on upload |
| `google_service_account.video_segmenter` | SA for Cloud Function + Dataform execution |
| `google_bigquery_dataset_iam_member.segmenter_bq_data_editor` | Dataform write access (scoped to dataset) |
| `google_dataform_repository_workflow_config.video_search` | Scheduled hourly Dataform execution (uses shared release config) |
| `local_file.video_search_api_env` | Generated `.env` for local API development |
| `google_cloud_run_v2_service.video_search_ui` | Cloud Run UI deployment (optional, `enable_video_search_ui`) |
| `google_service_account.video_search_ui` | SA for Cloud Run with BQ, GCS, and Vertex AI access |
| `google_project_iam_member.ui_vertex_ai_user` | Cloud Run SA access to Gemini via Vertex AI |
| `google_vertex_ai_reasoning_engine.the_archivist` | Agent Engine deployment (optional, `enable_agent_engine`) |
| `google_service_account.agent_engine` | SA for Agent Engine with BQ and Vertex AI access |

---

## Navigation

[Guide](guide.md) | [Quick Reference](quick.md) | [Patterns Reference](../../architecture.md)
