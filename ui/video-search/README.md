# Video Library Intelligence — UI

React + FastAPI web application for the Video Vector Search demo.

## Architecture

```
Frontend (React + Vite)        Backend (Python FastAPI)        Google Cloud
localhost:5173          →      localhost:8000          →      BigQuery + GCS
                               /api/search                   VECTOR_SEARCH
                               /api/videos                   gold_searchable_videos
                               /api/archive                  Archive.org API
                               /api/agent/chat               ADK Agent + Gemini 3.5 Flash
```

## Quick Start

### Backend (Terminal 1)

```bash
cd ui/video-search/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Terminal 2)

```bash
cd ui/video-search/frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Features

- **AI Agent ("The Archivist")** — Conversational assistant powered by Google ADK + Gemini 3.5 Flash. Search, filter, play, and analyze videos through natural language chat
- **Semantic Search** — Natural language queries powered by BQ Vector Search
- **AI Filters** — Category, mood, color, style, content warnings (all Gemini-generated)
- **Video Playback** — Full video with segment navigation and match timeline
- **Video Detail Panel** — Full AI analysis (14 metadata fields) in a slide-out panel
- **Find Similar** — Video-to-video similarity search
- **Collections** — Select videos, export as JSON/CSV with AI metadata
- **Conversational Analytics** — Ask analytical questions about the library data via the Conversational Analytics API
- **Highlight Reel** — Auto-compiled best segments from search results
- **Add Videos** — Search and ingest from Archive.org
- **Dark Mode** — Toggle in header
- **Shareable URLs** — Search + filters encoded in URL params
- **Keyboard Shortcuts** — Ctrl+K (search), Escape (close)

## Tech Stack

- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui, Lucide icons
- **Backend:** Python FastAPI, google-cloud-bigquery, google-cloud-storage
- **AI Agent:** Google ADK, Gemini 3.5 Flash (via Vertex AI), Conversational Analytics API
- **Design System:** `local/branding_guide.md` (Roboto font, GCP blue primary)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search?q={query}` | Semantic video search |
| GET | `/api/videos` | List all videos |
| GET | `/api/videos/stats` | Library stats + filter dimensions |
| GET | `/api/videos/{id}/details` | Full AI metadata |
| GET | `/api/videos/{id}/thumbnail` | Thumbnail image |
| GET | `/api/videos/{id}/play` | Stream full video |
| GET | `/api/videos/{id}/segments/{n}/play` | Stream segment |
| GET | `/api/videos/{id}/similar` | Find similar videos |
| GET | `/api/archive/search?q={query}` | Search Archive.org |
| POST | `/api/archive/{id}/ingest` | Ingest from Archive.org |
| POST | `/api/agent/chat` | Conversational agent (The Archivist) |
| GET | `/api/health` | Health check |

## Project Structure

```
ui/video-search/
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Root application
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui components
│   │   │   ├── Header.tsx             # App header with branding
│   │   │   ├── SearchBar.tsx          # Search input + explore chips
│   │   │   ├── FilterSidebar.tsx      # AI-generated filter panel (drawer on mobile)
│   │   │   ├── VideoGrid.tsx          # Results grid with pagination
│   │   │   ├── VideoCard.tsx          # Video card with hover actions
│   │   │   ├── VideoPlayer.tsx        # Full video + segment nav
│   │   │   ├── VideoDetailPanel.tsx   # Slide-out AI metadata panel
│   │   │   ├── HighlightReel.tsx      # Auto-compiled segment reel
│   │   │   ├── SelectionBar.tsx       # Floating selection + export
│   │   │   ├── ChatPanel.tsx          # AI agent chat panel
│   │   │   ├── ChatMessage.tsx        # Chat message rendering
│   │   │   ├── AgentAvatar.tsx        # Agent avatar icon
│   │   │   ├── AddVideos.tsx          # Archive.org search + ingest
│   │   │   ├── ResultsBar.tsx         # Count + sort + share
│   │   │   ├── LibraryStats.tsx       # Stats cards
│   │   │   └── Footer.tsx             # Page footer
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client
│   │   │   └── utils.ts               # shadcn/ui utilities
│   │   └── types/
│   │       └── index.ts               # TypeScript interfaces
│   └── index.html
├── api/
│   ├── main.py                        # FastAPI app
│   ├── agent/
│   │   ├── agent.py                   # ADK agent definition (The Archivist)
│   │   └── tools.py                   # 9 agent tool functions
│   ├── routers/
│   │   ├── agent.py                   # /api/agent/chat
│   │   ├── search.py                  # /api/search
│   │   ├── videos.py                  # /api/videos + playback
│   │   └── archive.py                 # /api/archive
│   ├── services/
│   │   ├── bigquery.py                # BQ queries
│   │   ├── storage.py                 # GCS media serving
│   │   └── archive.py                 # Archive.org API
│   └── requirements.txt
├── Dockerfile                         # Multi-stage build for Cloud Run
└── README.md                          # This file
```
