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
        C --> F[GCS metadata CSVs]
    end

    subgraph "Bronze Layer"
        D --> G[bronze_video_segments<br/>Object Table]
    end

    subgraph "Silver Layer"
        G -->|AI.GENERATE_EMBEDDING| H[silver_segment_embeddings<br/>1408-dim vectors]
        G -->|AI.GENERATE + Gemini 2.5| I[silver_video_metadata<br/>14 AI-extracted fields]
    end

    subgraph "Gold Layer"
        H --> J[gold_searchable_videos]
        I --> J
        G -->|GCS object metadata| J
    end

    subgraph "UI Layer"
        J -->|VECTOR_SEARCH| K[FastAPI Backend]
        K --> L[React Frontend]
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
    participant UI as React UI

    User->>GCS: Upload video to raw/
    GCS->>CF: Object finalization event
    CF->>CF: ffmpeg split (2-min segments)
    CF->>GCS: Upload segments + thumbnail + CSV

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
```

---

## Key Components

| Layer | Table/Resource | Type | Purpose |
|-------|---------------|------|---------|
| Bronze | `bronze_video_segments` | Object Table (SIMPLE) | GCS video segments queryable via SQL |
| Bronze | `bronze_segment_mapping` | External Table (CSV) | Per-video metadata CSVs |
| Model | `multimodal_embedding_model` | Remote Model | `multimodalembedding@001` for video/text embeddings |
| Model | `gemini_video_model` | Remote Model | Gemini 2.5 Flash for AI metadata extraction |
| Silver | `silver_segment_embeddings` | Incremental Table | 1408-dim embeddings per segment interval |
| Silver | `silver_video_metadata` | Incremental Table | 14 AI-extracted fields per video |
| Gold | `gold_searchable_videos` | Table | Embeddings + GCS metadata + AI metadata joined |

---

## AI Models

| Model | Endpoint | Purpose | Input |
|-------|----------|---------|-------|
| Multimodal Embedding | `multimodalembedding@001` | Cross-modal vector embeddings | Video segments (16s intervals) |
| Gemini 2.5 Flash | `gemini-2.5-flash` | Structured metadata extraction | Video segment 0 via `AI.GENERATE` |

---

## Key Technical Details

- **2-minute segment limit**: `AI.GENERATE_EMBEDDING` analyzes max 120 seconds per video. Videos are split into 2-min segments; results grouped by parent video at query time.
- **GCS object metadata**: Title, year, timing info stored as custom metadata on each segment GCS object. Extracted in gold table via `UNNEST(metadata)`.
- **Incremental processing**: Silver tables use `type: "incremental"` with `uniqueKey` — only new segments/videos are processed on each Dataform run.
- **Object table cache**: `AUTOMATIC` mode with 30-minute staleness. New segments visible within 30 minutes.
- **Cross-modal search**: Text queries search against video embeddings because `multimodalembedding@001` encodes both modalities in the same vector space.

---

## Infrastructure (Terraform)

| Resource | Purpose |
|----------|---------|
| `google_bigquery_dataset.video_vector_search` | BQ dataset |
| `google_storage_bucket.video_search` | GCS bucket for all video data |
| `google_cloudfunctions2_function.segment_video` | Auto-segmentation on upload |
| `google_service_account.video_segmenter` | SA for Cloud Function |
| `google_dataform_repository_release_config.video_search_dev` | Dataform compilation from feature branch |
| `google_dataform_repository_workflow_config.video_search` | Scheduled hourly Dataform execution |

---

## Navigation

[Guide](guide.md) | [Quick Reference](quick.md) | [Patterns Reference](../../architecture.md)
