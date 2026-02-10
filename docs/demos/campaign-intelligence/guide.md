# Campaign Intelligence Guide

Combine public Census housing data with digital engagement signals to power AI-generated mortgage campaign recommendations.

**Time:** 8-10 minutes

---

## The Business Problem

**Scenario:** TD Bank's marketing team wants to target mortgage campaigns, but they can't access internal mortgage records due to data governance policies.

**Traditional approach:**
```
Request access to mortgage data → Wait for approval → Build targeting model
Result: Weeks of delays, compliance concerns
```

**Campaign Intelligence approach:**
```
Public Census data + Digital signals → AI-generated campaign recommendations
Result: Same-day insights, no PII required
```

---

## Step 1: Explore Public Data Sources

### theLook Users with Geographic Coordinates

```sql
SELECT
  id AS user_id,
  first_name,
  city,
  state,
  latitude,
  longitude,
  traffic_source
FROM `bigquery-public-data.thelook_ecommerce.users`
WHERE country = 'United States' AND latitude IS NOT NULL
LIMIT 10;
```

**Key Point:** theLook eCommerce is a public dataset with user demographics and lat/long coordinates.

---

## Step 2: Spatial Join - Users to Census Tracts

The `silver_users_with_census` table joins users to census tracts using ST_CONTAINS.

```sql
SELECT
  user_id,
  city,
  state,
  census_tract_id,
  state_fips_code,
  county_fips_code
FROM `campaign_intelligence.silver_users_with_census`
WHERE census_tract_id IS NOT NULL
LIMIT 10;
```

### How It Works

```sql
SELECT u.*, ct.geo_id AS census_tract_id
FROM users u
LEFT JOIN census_tracts ct
  ON ST_CONTAINS(ct.tract_geom, ST_GEOGPOINT(u.longitude, u.latitude))
```

---

## Step 3: Census Tract Demographics

The `silver_tract_demographics` table extracts housing and income features from Census ACS data.

```sql
SELECT
  census_tract_id,
  total_population,
  total_households,
  ROUND(homeownership_rate, 2) AS homeownership_rate,
  ROUND(renter_rate, 2) AS renter_rate,
  median_income,
  income_category
FROM `campaign_intelligence.silver_tract_demographics`
WHERE total_population > 1000
ORDER BY renter_rate DESC
LIMIT 10;
```

**Key Point:** High renter rates + middle income = potential first-time buyer markets.

---

## Step 4: Digital Engagement Signals

The `silver_engagement_signals` table aggregates user behavior from theLook events and orders.

```sql
SELECT
  user_id,
  total_events,
  days_active,
  total_orders,
  engagement_score,
  ROUND(cart_rate, 2) AS cart_rate
FROM `campaign_intelligence.silver_engagement_signals`
WHERE engagement_score > 50
ORDER BY engagement_score DESC
LIMIT 10;
```

---

## Step 5: Campaign Scores by Census Tract

The `gold_tract_campaign_features` table combines demographics with engagement to score tracts.

```sql
SELECT
  census_tract_id,
  users_in_tract,
  ROUND(renter_rate, 2) AS renter_rate,
  income_category,
  ROUND(first_time_buyer_score, 1) AS ftb_score,
  ROUND(refinance_score, 1) AS refi_score,
  ROUND(home_equity_score, 1) AS heloc_score
FROM `campaign_intelligence.gold_tract_campaign_features`
WHERE users_in_tract >= 5
ORDER BY first_time_buyer_score DESC
LIMIT 10;
```

### Scoring Logic

**First-Time Buyer Score (0-100):**
- High renter rate (30 points max)
- Working-age population ratio (25 points max)
- Middle income category (25 points max)
- Digital engagement (20 points max)

---

## Step 6: User Segments

The `gold_user_segments` table assigns users to campaign segments with propensity scores.

```sql
SELECT
  primary_segment,
  segment_tier,
  COUNT(*) AS user_count,
  ROUND(AVG(first_time_buyer_propensity), 1) AS avg_ftb_propensity,
  ROUND(AVG(refinance_propensity), 1) AS avg_refi_propensity
FROM `campaign_intelligence.gold_user_segments`
GROUP BY primary_segment, segment_tier
ORDER BY primary_segment, segment_tier;
```

---

## Step 7: AI-Generated Campaign Recommendations

The `gold_campaign_recommendations` table uses Gemini to generate campaign strategies.

```sql
SELECT
  campaign_type,
  target_tracts,
  total_target_users,
  ROUND(avg_score, 1) AS avg_score,
  campaign_name,
  target_audience,
  priority
FROM `campaign_intelligence.gold_campaign_recommendations`;
```

### View Full Recommendation

```sql
SELECT
  campaign_type,
  campaign_name,
  key_messaging,
  channels,
  estimated_reach
FROM `campaign_intelligence.gold_campaign_recommendations`
WHERE campaign_type = 'first_time_buyer';
```

**Key Point:** Gemini generates campaign strategies based on aggregate tract demographics — no individual customer data required.

---

## Key Takeaways

| Capability | Technology | Business Value |
|------------|------------|----------------|
| Spatial joins at scale | BigQuery Geography (ST_CONTAINS) | Join users to geographic areas |
| Public data enrichment | Census ACS + theLook | Insights without internal data |
| Campaign scoring | Feature engineering in SQL | Prioritize markets by propensity |
| AI recommendations | Gemini 2.0 Flash | Generate strategies automatically |
| Data governance friendly | No PII required | Marketing can self-serve |

---

## Demo Narrative

> "Marketing can't access mortgage records, but they can see that users in high-renter, middle-income neighborhoods are actively engaging with our site. The Gemini agent surfaces this as a campaign opportunity — no customer data crossed the wall."

---

## Navigation

[← Overview](./) | [Back to Demos](../README.md) | [Quick Reference](quick.md)
