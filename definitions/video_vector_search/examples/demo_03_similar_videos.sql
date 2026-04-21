-- =============================================================================
-- DEMO 03: Find Videos Similar to a Given Video
-- =============================================================================
--
-- "I like this video — show me more like it"
--
-- Uses a video's own embedding as the search query to find other videos
-- with similar visual/thematic content.
--
-- =============================================================================

-- Find videos similar to a specific video (replace video_id as needed)
WITH seed_embedding AS (
  SELECT embedding, video_id AS seed_video_id
  FROM `gcloud-tech-showcase.video_vector_search.gold_searchable_videos`
  WHERE video_id = 'popeye-for-president'
    AND segment_index = 0
  LIMIT 1
),

similar_matches AS (
  SELECT
    base.video_id,
    base.title,
    base.year,
    base.segment_index,
    distance
  FROM VECTOR_SEARCH(
    (
      SELECT * FROM `gcloud-tech-showcase.video_vector_search.gold_searchable_videos`
      WHERE video_id != (SELECT seed_video_id FROM seed_embedding)
    ),
    'embedding',
    (SELECT embedding FROM seed_embedding),
    top_k => 20,
    distance_type => 'COSINE'
  )
)

SELECT
  video_id,
  ANY_VALUE(title) AS title,
  ANY_VALUE(year) AS year,
  MIN(distance) AS best_distance,
  COUNT(*) AS matching_intervals,
  ARRAY_AGG(
    STRUCT(segment_index, ROUND(distance, 4) AS distance)
    ORDER BY distance
    LIMIT 3
  ) AS top_matches
FROM similar_matches
GROUP BY video_id
ORDER BY best_distance ASC;
