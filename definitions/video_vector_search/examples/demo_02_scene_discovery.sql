-- =============================================================================
-- DEMO 02: Scene Discovery with Parent Video Grouping
-- =============================================================================
--
-- Multiple segments (and multiple intervals within segments) from the same
-- video may match a query. This demo groups results by parent video to show
-- "which VIDEOS match" rather than "which embedding intervals match."
--
-- Pattern: VECTOR_SEARCH → GROUP BY video_id → MIN(distance)
--
-- =============================================================================

-- Find videos about "music and dancing", grouped by parent video
WITH segment_matches AS (
  SELECT
    base.video_id,
    base.title,
    base.year,
    base.segment_index,
    base.start_seconds,
    base.end_seconds,
    base.source_url,
    distance
  FROM VECTOR_SEARCH(
    TABLE `gcloud-tech-showcase.video_vector_search.gold_searchable_videos`,
    'embedding',
    (
      SELECT embedding
      FROM AI.GENERATE_EMBEDDING(
        MODEL `gcloud-tech-showcase.video_vector_search.multimodal_embedding_model`,
        (SELECT 'music and dancing' AS content)
      )
    ),
    top_k => 50,
    distance_type => 'COSINE'
  )
),

video_scores AS (
  SELECT
    video_id,
    ANY_VALUE(title) AS title,
    ANY_VALUE(year) AS year,
    ANY_VALUE(source_url) AS source_url,
    MIN(distance) AS best_distance,
    COUNT(*) AS matching_intervals,
    ARRAY_AGG(
      STRUCT(segment_index, start_seconds, end_seconds, ROUND(distance, 4) AS distance)
      ORDER BY distance
      LIMIT 3
    ) AS top_matches
  FROM segment_matches
  GROUP BY video_id
)

SELECT
  video_id,
  title,
  year,
  ROUND(best_distance, 4) AS relevance_score,
  matching_intervals,
  top_matches,
  source_url
FROM video_scores
ORDER BY best_distance ASC;
