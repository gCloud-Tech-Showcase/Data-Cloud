-- =============================================================================
-- DEMO 01: Basic Video Search by Natural Language
-- =============================================================================
--
-- Find videos matching a text description using multimodal vector search.
-- The magic: text queries search against VIDEO embeddings because
-- multimodalembedding@001 encodes both modalities in the same vector space.
--
-- =============================================================================

-- Search for "cartoon characters fighting"
SELECT
  base.video_id,
  base.title,
  base.year,
  base.segment_index,
  base.start_seconds,
  base.end_seconds,
  distance
FROM VECTOR_SEARCH(
  TABLE `gcloud-tech-showcase.video_vector_search.gold_searchable_videos`,
  'embedding',
  (
    SELECT embedding
    FROM AI.GENERATE_EMBEDDING(
      MODEL `gcloud-tech-showcase.video_vector_search.multimodal_embedding_model`,
      (SELECT 'cartoon characters fighting' AS content)
    )
  ),
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;
