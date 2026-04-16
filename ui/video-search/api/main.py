"""Video Library Intelligence — FastAPI Backend

Serves the search API and media endpoints for the Video Vector Search demo.
In production (Cloud Run), also serves the built React frontend as static files.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from routers import search, videos

app = FastAPI(
    title="Video Library Intelligence",
    description="Semantic video search powered by BigQuery Vector Search and Gemini",
)

# CORS for local dev (Vite on :5173 → API on :8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(search.router)
app.include_router(videos.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve static frontend in production (when built files exist)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
