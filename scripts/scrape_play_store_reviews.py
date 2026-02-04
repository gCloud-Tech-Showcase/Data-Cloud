#!/usr/bin/env python3
"""
Google Play Store Review Scraper for Flood-it

Scrapes all reviews from the Play Store and uploads them to GCS
as individual JSON files with resumable checkpoint capability.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from google.cloud import storage
from google_play_scraper import Sort, reviews

# Configuration
APP_ID = "com.labpixies.flood"
CHECKPOINT_FILE = "checkpoint.json"
LOG_FILE = "scrape.log"
REVIEWS_PER_BATCH = 200
RATE_LIMIT_DELAY = 3  # seconds between batches

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_env() -> tuple[str, str]:
    """Load environment variables."""
    load_dotenv()

    project_id = os.getenv('GCP_PROJECT_ID')
    region = os.getenv('GCP_REGION', 'us-central1')

    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID not set. Create a .env file with:\n"
            "GCP_PROJECT_ID=your-project-id\n"
            "GCP_REGION=us-central1"
        )

    return project_id, region


def load_checkpoint() -> Dict[str, Any]:
    """Load checkpoint from file if exists."""
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            checkpoint = json.load(f)
            logger.info(f"Loaded checkpoint: {checkpoint['reviews_scraped']} reviews scraped")
            return checkpoint

    return {
        'continuation_token': None,
        'reviews_scraped': 0,
        'last_review_id': None,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'last_updated': None
    }


def save_checkpoint(checkpoint: Dict[str, Any]) -> None:
    """Save checkpoint to file."""
    checkpoint['last_updated'] = datetime.now(timezone.utc).isoformat()

    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

    logger.info(f"Checkpoint saved: {checkpoint['reviews_scraped']} reviews total")


def normalize_review(review: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Play Store review to common schema.

    Args:
        review: Raw review from google-play-scraper

    Returns:
        Normalized review dict
    """
    # Parse date
    review_date = review['at']
    if hasattr(review_date, 'isoformat'):
        date_str = review_date.date().isoformat()
    else:
        date_str = str(review_date)[:10]

    # Parse developer reply date if exists
    developer_reply_date = None
    if review.get('repliedAt'):
        replied_at = review['repliedAt']
        if hasattr(replied_at, 'isoformat'):
            developer_reply_date = replied_at.date().isoformat()
        else:
            developer_reply_date = str(replied_at)[:10]

    return {
        "platform": "play-store",
        "review_id": review['reviewId'],
        "user_pseudo_id": None,  # To be assigned later for GA4 join
        "user_name": review.get('userName'),
        "review_text": review['content'],
        "rating": review['score'],
        "review_date": date_str,
        "app_version": review.get('reviewCreatedVersion'),
        "thumbs_up_count": review.get('thumbsUpCount', 0),
        "developer_reply": review.get('replyContent'),
        "developer_reply_date": developer_reply_date,
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }


def upload_to_gcs(
    bucket_name: str,
    review: Dict[str, Any],
    file_number: int
) -> None:
    """
    Upload review to GCS as individual JSON file.

    Args:
        bucket_name: GCS bucket name
        review: Normalized review dict
        file_number: Sequential file number (for filename)
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Generate filename with date and zero-padded number for easy sorting
    review_date = review['review_date'].replace('-', '')  # YYYYMMDD format
    filename = f"user-reviews/play-store/flood-it/review_{review_date}_{file_number:06d}.json"
    blob = bucket.blob(filename)

    # Upload JSON with Unicode characters preserved (emojis, non-Latin text)
    blob.upload_from_string(
        json.dumps(review, ensure_ascii=False, indent=2),
        content_type='application/json; charset=utf-8'
    )

    logger.debug(f"Uploaded: gs://{bucket_name}/{filename}")


def scrape_reviews(project_id: str) -> None:
    """
    Main scraping function with checkpoint/resume capability.

    Args:
        project_id: GCP project ID
    """
    bucket_name = f"{project_id}-multimodal-data"
    checkpoint = load_checkpoint()

    logger.info(f"Starting scrape for {APP_ID}")
    logger.info(f"Target bucket: gs://{bucket_name}/user-reviews/play-store/flood-it/")

    continuation_token = checkpoint['continuation_token']
    reviews_scraped = checkpoint['reviews_scraped']

    try:
        while True:
            logger.info(f"Fetching batch (continuation_token: {'Yes' if continuation_token else 'No'})...")

            # Fetch reviews
            result, continuation_token = reviews(
                APP_ID,
                lang='en',
                country='us',
                sort=Sort.NEWEST,
                count=REVIEWS_PER_BATCH,
                continuation_token=continuation_token
            )

            if not result:
                logger.info("No more reviews returned. Scraping complete!")
                break

            logger.info(f"Fetched {len(result)} reviews")

            # Process and upload each review
            for review in result:
                reviews_scraped += 1

                # Normalize review
                normalized = normalize_review(review)

                # Upload to GCS
                upload_to_gcs(bucket_name, normalized, reviews_scraped)

                # Update checkpoint
                checkpoint['reviews_scraped'] = reviews_scraped
                checkpoint['continuation_token'] = continuation_token
                checkpoint['last_review_id'] = normalized['review_id']

            # Save checkpoint after each batch
            save_checkpoint(checkpoint)

            logger.info(f"Progress: {reviews_scraped} reviews uploaded")

            # Rate limiting
            logger.info(f"Rate limit delay: {RATE_LIMIT_DELAY} seconds...")
            time.sleep(RATE_LIMIT_DELAY)

    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Checkpoint saved. Run again to resume.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        logger.info("Checkpoint saved. Fix the error and run again to resume.")
        raise

    finally:
        save_checkpoint(checkpoint)

    logger.info(f"✓ Scraping complete! Total reviews: {reviews_scraped}")
    logger.info(f"✓ Reviews uploaded to: gs://{bucket_name}/user-reviews/play-store/flood-it/")


def main():
    """Main entry point."""
    try:
        project_id, region = load_env()
        logger.info(f"Configuration: project={project_id}, region={region}")

        scrape_reviews(project_id)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
