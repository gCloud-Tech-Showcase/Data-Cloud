# Campaign Intelligence - Quick Reference

SQL queries with expected outputs. Run these in BigQuery Console.

---

## 1. theLook Users with Coordinates

```sql
SELECT
  id AS user_id,
  first_name,
  city,
  state,
  latitude,
  longitude
FROM `bigquery-public-data.thelook_ecommerce.users`
WHERE country = 'United States' AND latitude IS NOT NULL
LIMIT 5;
```

---

## 2. Users Joined to Census Tracts

```sql
SELECT
  user_id,
  city,
  state,
  census_tract_id
FROM `campaign_intelligence.silver_users_with_census`
WHERE census_tract_id IS NOT NULL
LIMIT 10;
```

---

## 3. Census Tract Demographics

```sql
SELECT
  census_tract_id,
  total_population,
  ROUND(homeownership_rate, 2) AS homeownership_rate,
  ROUND(renter_rate, 2) AS renter_rate,
  median_income,
  income_category
FROM `campaign_intelligence.silver_tract_demographics`
WHERE total_population > 1000
ORDER BY renter_rate DESC
LIMIT 10;
```

**Output:**
```
census_tract_id | total_population | homeownership_rate | renter_rate | median_income | income_category
----------------|------------------|--------------------| ------------|---------------|----------------
06075010100     | 4523             | 0.25               | 0.75        | 65000         | middle
17031010100     | 3876             | 0.32               | 0.68        | 58000         | middle
```

---

## 4. Digital Engagement Signals

```sql
SELECT
  user_id,
  total_events,
  days_active,
  total_orders,
  engagement_score
FROM `campaign_intelligence.silver_engagement_signals`
WHERE engagement_score > 50
ORDER BY engagement_score DESC
LIMIT 10;
```

---

## 5. Campaign Scores by Tract

```sql
SELECT
  census_tract_id,
  users_in_tract,
  ROUND(renter_rate, 2) AS renter_rate,
  income_category,
  ROUND(first_time_buyer_score, 1) AS ftb_score
FROM `campaign_intelligence.gold_tract_campaign_features`
WHERE users_in_tract >= 5
ORDER BY first_time_buyer_score DESC
LIMIT 10;
```

---

## 6. User Segments

```sql
SELECT
  primary_segment,
  segment_tier,
  COUNT(*) AS user_count,
  ROUND(AVG(first_time_buyer_propensity), 1) AS avg_ftb_propensity
FROM `campaign_intelligence.gold_user_segments`
GROUP BY primary_segment, segment_tier
ORDER BY primary_segment, segment_tier;
```

---

## 7. AI Campaign Recommendations

```sql
SELECT
  campaign_type,
  target_tracts,
  total_target_users,
  campaign_name,
  priority
FROM `campaign_intelligence.gold_campaign_recommendations`;
```

---

## Navigation

- [Overview](overview.md)
- [Full Guide](guide.md)
- [Back to Demos](../README.md)
