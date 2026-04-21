# Video Vector Search — Quick Reference

SQL queries with expected outputs. Run these in BigQuery Console.

---

## 1. Explore the Video Library

```sql
SELECT video_id, title, year, category, mood, color_mode, style
FROM video_vector_search.gold_searchable_videos
WHERE segment_index = 0 AND video_start_sec = 0
ORDER BY title
LIMIT 10;
```

Shows all indexed videos with AI-extracted metadata.

---

## 2. Check Embedding Coverage

```sql
SELECT
  COUNT(DISTINCT video_id) AS videos_with_embeddings,
  COUNT(*) AS total_embedding_rows
FROM video_vector_search.silver_segment_embeddings;
```

---

## 3. Semantic Search — Text to Video

```sql
SELECT base.video_id, base.title, base.category, distance
FROM VECTOR_SEARCH(
  TABLE `video_vector_search.gold_searchable_videos`, 'embedding',
  (SELECT embedding FROM AI.GENERATE_EMBEDDING(
    MODEL `video_vector_search.multimodal_embedding_model`,
    (SELECT 'cartoon characters fighting' AS content)
  )),
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;
```

Searches across all video embeddings using natural language.

---

## 4. Grouped Search — Best Match Per Video

```sql
WITH segment_matches AS (
  SELECT base.video_id, base.title, base.year, base.category, distance
  FROM VECTOR_SEARCH(
    TABLE `video_vector_search.gold_searchable_videos`, 'embedding',
    (SELECT embedding FROM AI.GENERATE_EMBEDDING(
      MODEL `video_vector_search.multimodal_embedding_model`,
      (SELECT 'friendship' AS content)
    )),
    top_k => 50,
    distance_type => 'COSINE'
  )
)
SELECT
  video_id, ANY_VALUE(title) AS title, ANY_VALUE(year) AS year,
  ANY_VALUE(category) AS category,
  ROUND(MIN(distance), 4) AS best_distance,
  COUNT(*) AS matching_intervals
FROM segment_matches
GROUP BY video_id
ORDER BY best_distance ASC
LIMIT 10;
```

Groups segment-level results back to video-level, showing the best match per video.

---

## 5. Find Similar Videos

```sql
WITH seed AS (
  SELECT embedding FROM video_vector_search.gold_searchable_videos
  WHERE video_id = 'popeye-for-president' AND segment_index = 0
  LIMIT 1
)
SELECT base.video_id, base.title, distance
FROM VECTOR_SEARCH(
  (SELECT * FROM `video_vector_search.gold_searchable_videos` WHERE video_id != 'popeye-for-president'),
  'embedding',
  (SELECT embedding FROM seed),
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;
```

Uses a video's own embedding to find visually/thematically similar videos.

---

## 6. AI Metadata Overview

```sql
SELECT
  category, COUNT(DISTINCT video_id) AS videos,
  COUNTIF(has_dialogue) AS with_dialogue,
  COUNTIF(has_music) AS with_music
FROM video_vector_search.gold_searchable_videos
WHERE segment_index = 0 AND video_start_sec = 0
GROUP BY category
ORDER BY videos DESC;
```

Shows AI-extracted metadata aggregated by category.

---

## 7. Content Warnings

```sql
SELECT DISTINCT video_id, title, content_warnings
FROM video_vector_search.gold_searchable_videos
WHERE ARRAY_LENGTH(content_warnings) > 0
  AND segment_index = 0 AND video_start_sec = 0
ORDER BY title;
```

Lists videos flagged by Gemini for dated stereotypes, violence, or sensitive content.

---

## 8. AI Metadata Extraction (Gemini 2.5 Flash)

```sql
SELECT
  REGEXP_EXTRACT(uri, r'/segments/([^/]+)/') AS video_id,
  r.category, r.mood, r.description, r.characters
FROM video_vector_search.bronze_video_segments,
UNNEST([
  AI.GENERATE(
    (OBJ.GET_ACCESS_URL(ref, 'r'),
     'Classify this video. category: cartoon, educational, documentary, newsreel, or other. mood: humorous, dramatic, educational, suspenseful, lighthearted, or serious. description: one sentence about the main action. characters: character names if identifiable.'),
    connection_id => 'us.vertex-ai-connection',
    endpoint => 'gemini-2.5-flash',
    output_schema => 'category STRING, mood STRING, description STRING, characters ARRAY<STRING>'
  )
]) AS r
WHERE uri LIKE '%/popeye-for-president/seg_000.mp4';
```

Shows how `AI.GENERATE` with `OBJ.GET_ACCESS_URL` passes video content directly to Gemini 2.5 Flash for structured metadata extraction. No JSON parsing needed — `output_schema` returns typed columns.

---

## Navigation

- [Overview](./)
- [Architecture](architecture.md)
- [Full Guide](guide.md)
- [Back to Demos](../README.md)
