# Video Vector Search — Step-by-Step Guide

Deploy the full video search pipeline and UI from scratch.

**Time:** ~30 minutes (plus video processing time)

---

## Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated
- `terraform` installed (>= 1.6)
- `ffmpeg` installed (for local segmentation script)
- Node.js 20+ and Python 3.12+ (for the UI)

---

## Step 1: Deploy Infrastructure

```bash
cd infra
terraform init
terraform apply
```

This creates:
- BigQuery dataset (`video_vector_search`)
- GCS bucket (`{project}-video-search`)
- Cloud Function (`segment-video`) with Eventarc trigger
- Service account and IAM bindings
- Dataform release config and scheduled workflow

---

## Step 2: Source Videos

Download public domain videos from Archive.org:

```bash
cd scripts
source .venv/bin/activate
pip install -r requirements.txt

# Quick start: download 10 diverse videos (~3 minutes)
python source_archive_videos.py --limit 10

# Or download the full curated list (106 videos, ~30 minutes)
# python source_archive_videos.py
```

The first 10 videos in the curated list are pre-selected for diversity: Popeye, Superman, Betty Boop, Bugs Bunny, Casper, plus educational and documentary films.

This uploads videos to `gs://{project}-video-search/raw/` with custom metadata (title, year, source URL, etc.) attached to each GCS object.

> **Tip:** For the full list, increase Cloud Function instances:
> `terraform apply -var="video_search_max_instances=50"`

The Cloud Function automatically triggers on each upload:
- Splits the video into 2-minute segments
- Extracts a thumbnail frame
- Attaches timing metadata to each segment
- Writes a per-video metadata CSV

---

## Step 3: Run Dataform Pipeline

In the Google Cloud Console:

1. Go to **Dataform** → **data-cloud** repository
2. Create a compilation from the release config
3. Execute with tag: `video_vector_search`

Or wait for the hourly scheduled execution.

The pipeline:
1. **bronze_video_segments** — Object table refreshes (sees new segments in GCS)
2. **silver_segment_embeddings** — Generates multimodal embeddings (incremental — only new segments)
3. **silver_video_metadata** — Gemini 2.5 Flash extracts 14 metadata fields per video (incremental)
4. **gold_searchable_videos** — Joins embeddings + GCS metadata + AI metadata

---

## Step 4: Verify in BigQuery

Run a quick search to verify the pipeline:

```sql
SELECT base.video_id, base.title, distance
FROM VECTOR_SEARCH(
  TABLE `video_vector_search.gold_searchable_videos`, 'embedding',
  (SELECT embedding FROM AI.GENERATE_EMBEDDING(
    MODEL `video_vector_search.multimodal_embedding_model`,
    (SELECT 'cartoon characters fighting' AS content)
  )),
  top_k => 5,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;
```

See [Quick Reference](quick.md) for more queries.

---

## Step 5: Run the UI (Local)

### Backend (Terminal 1):

```bash
cd ui/video-search/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Terminal 2):

```bash
cd ui/video-search/frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Step 5b: Deploy UI to Cloud Run (Optional)

Instead of running locally, deploy the UI to a public Cloud Run endpoint:

```bash
cd infra
terraform apply -var="enable_video_search_ui=true"
```

Terraform outputs the URL. No Docker build needed — the image is pre-built and published automatically on each push to main via Cloud Build.

To use a custom image:

```bash
terraform apply -var="enable_video_search_ui=true" \
  -var="video_search_ui_image=us-central1-docker.pkg.dev/YOUR-PROJECT/public/video-search-ui:latest"
```

To tear down:

```bash
terraform apply -var="enable_video_search_ui=false"
```

---

## Step 6: Explore the UI

- **Search** — Type natural language queries ("friendship", "adventure", "educational health")
- **Filter** — Use the AI-generated sidebar filters (category, mood, color, style, content warnings)
- **Video Detail** — Click a video title to see the full Gemini analysis (14 metadata fields)
- **Play** — Click play to watch the full video with segment navigation
- **Find Similar** — Click "Similar" on any video to find visually related content
- **Collections** — Select videos with checkboxes, export as JSON/CSV with all AI metadata
- **Highlight Reel** — After searching, click "Highlight reel" to watch a compilation of best matches
- **Dark Mode** — Toggle with the moon/sun icon in the header
- **Share** — Click "Share" to copy a URL that reproduces your search + filters

---

## Adding New Videos

Upload a video via the **"Add videos"** button in the UI:

1. Search Archive.org for public domain videos
2. Click "Add to library" on any result
3. The Cloud Function segments it automatically
4. The next Dataform run generates embeddings and AI metadata
5. The video appears in search results

Or upload directly to GCS:

```bash
gsutil cp my-video.mp4 gs://{project}-video-search/raw/my-video.mp4
```

---

## Incremental Processing

The Dataform pipeline is incremental:
- **New videos** are embedded and analyzed automatically on the next run
- **Existing videos** are skipped (no redundant Gemini API calls)
- **Gold table** is rebuilt each run (cheap join, ensures consistency)

To re-analyze a video, delete its row from `silver_video_metadata` and re-run Dataform.

---

## Navigation

- [Overview](./)
- [Architecture](architecture.md)
- [Quick Reference](quick.md)
- [Back to Demos](../README.md)
