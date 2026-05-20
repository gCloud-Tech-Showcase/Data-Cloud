# Video Vector Search

Semantic video search using Gemini multimodal embeddings and BigQuery Vector Search, with a React UI and an ADK-powered conversational agent ("The Archivist").

## What You'll Build

1. **Video Ingestion** — Upload videos to GCS, automatically segment into 2-minute chunks via Cloud Function, and attach metadata
2. **Multimodal Embeddings** — Generate 1408-dimensional vector embeddings from video content using `multimodalembedding@001`
3. **AI Metadata Extraction** — Gemini 2.5 Flash analyzes each video to extract category, mood, characters, themes, content warnings, and more (15 fields total via `AI.GENERATE`)
4. **Semantic Search** — Find videos by natural language query ("friendship", "chase scene") using BigQuery `VECTOR_SEARCH`
5. **Web UI** — React application with search, filters, video playback, collections, highlight reels, and a detail panel
6. **AI Agent ("The Archivist")** — Conversational assistant powered by Google ADK + Gemini 2.5 Flash that controls the UI through natural language, plus Conversational Analytics for ad-hoc data questions

## Technologies

| Service | Purpose |
|---------|---------|
| BigQuery | Vector storage, search, and analytics |
| `multimodalembedding@001` | Generate cross-modal embeddings (text + video in same space) |
| Gemini 2.5 Flash | AI metadata extraction via `AI.GENERATE` |
| BigLake Object Tables | Query video segments in GCS via SQL |
| Cloud Functions (2nd gen) | Event-driven video segmentation on upload |
| Eventarc | GCS upload event triggers |
| GCS | Video storage (raw, segments, thumbnails, metadata) |
| Dataform | Incremental data pipeline (bronze/silver/gold) |
| Terraform | Infrastructure as code (all resources) |
| Google ADK | Agent framework (The Archivist) |
| Gemini 2.5 Flash (runtime) | Agent reasoning and tool use via Vertex AI |
| Conversational Analytics API | Natural language queries on BQ data |
| Vertex AI Agent Engine | Optional standalone agent deployment (`enable_agent_engine`) |
| Gemini Enterprise / Agentspace | Optional registration of The Archivist into a GE app via `app_type = APP_TYPE_INTRANET` (`enable_gemini_enterprise`, requires GE license) |
| React + Vite + Tailwind + shadcn/ui | Frontend UI |
| Python FastAPI | Backend API |

## Results

- **100+ videos** from Archive.org indexed and searchable
- **Sub-second** semantic search across all video content
- **15 AI-extracted metadata fields** per video (zero manual tagging)
- **Event-driven pipeline** — upload a video, it's automatically segmented
- **Full web UI** — search, filter, play, create collections, highlight reels
- **Conversational AI agent** — natural language control of the UI + analytical queries
- **Three deployment surfaces for the agent** — embedded in the React UI, Vertex AI Agent Engine (standalone API), and Gemini Enterprise (Agentspace app, preview-only by default; all 9 agent tools verified working through GE)

## Guides

- [Quick Reference](quick.md) — SQL queries with expected outputs
- [Architecture](architecture.md) — Pipeline diagram, data flow, components
- [Step-by-Step Guide](guide.md) — Deploy infrastructure, source videos, run pipeline, use UI

## Standalone

This demo is independent from other demos. It creates its own BQ dataset, GCS bucket, and Cloud Function.
