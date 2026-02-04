# Data Collection Scripts

This directory contains Python scripts for collecting unstructured data from external sources.

## Setup

### 1. Create Virtual Environment

```bash
cd scripts
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with your GCP project configuration:

```bash
# .env
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
```

For local development, authenticate with gcloud:

```bash
gcloud auth application-default login
```

For production, set `GOOGLE_APPLICATION_CREDENTIALS`:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## Scripts

### `scrape_play_store_reviews.py`

Scrapes Google Play Store reviews for the Flood-it app and uploads them to GCS.

**Usage:**

```bash
python scrape_play_store_reviews.py
```

**Features:**
- Resumable scraping with checkpoint file
- Automatic rate limiting (3-5 second delays)
- Progress tracking and logging
- Uploads each review as individual JSON file to GCS

**Output:**
- GCS bucket: `gs://{PROJECT_ID}-multimodal-data/user-reviews/play-store/flood-it/`
- Local checkpoint: `checkpoint.json`

**Resume from interruption:**

The script automatically resumes from the last checkpoint. Simply run the script again after an interruption.

## File Structure

```
scripts/
├── .gitignore
├── README.md
├── requirements.txt
├── scrape_play_store_reviews.py
├── .venv/                    # Git-ignored
├── checkpoint.json           # Git-ignored
└── scrape.log               # Git-ignored
```

## Notes

- The script respects Google Play Store rate limits with automatic delays
- Checkpoint file is saved after each batch (200 reviews)
- Reviews are stored as individual JSON files with normalized schema
- All sensitive files (.env, credentials) are git-ignored
