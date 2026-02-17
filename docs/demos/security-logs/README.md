# Security Logs Analytics

Analyze Cloud Audit Logs with AI-powered threat detection and semantic search.

## What You'll Build

Use BigQuery's pipe syntax, Gemini AI, and vector embeddings for security operations:
1. **Pipe Syntax** — Intuitive log queries familiar to Splunk/KQL users
2. **Gemini Triage** — AI-powered threat classification with explanations
3. **Vector Search** — Semantic similarity for threat hunting

## Technologies

| Service | Purpose |
|---------|---------|
| Cloud Logging Sink | Stream audit logs to BigQuery |
| Pipe Syntax | Top-to-bottom query language |
| Gemini 2.0 Flash | AI threat classification |
| Text Embeddings | Semantic vector search |
| Dataform | Pipeline orchestration |

## Results

- **Real-time audit logs** streamed to BigQuery via log sink
- **AI classification** with threat levels (CRITICAL/HIGH/MEDIUM/LOW/INFO)
- **Semantic search** across 768-dimensional embedding space
- **Zero data movement** — analyze logs where they land

## Guides

- [Quick Reference](quick.md) — SQL queries with expected outputs
- [Architecture](architecture.md) — Pipeline diagram and data flow
- [Full Guide](guide.md) — Step-by-step walkthrough

## Standalone

This demo is independent from other demos. Requires Terraform setup for log sink infrastructure.
