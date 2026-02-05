# Demo Guide 07: Campaign Intelligence

**Objective:** Combine public Census housing data with digital engagement signals to power AI-generated mortgage campaign recommendations.

**Time:** 8-10 minutes

**What you'll demonstrate:**
- Spatial joins using BigQuery Geography functions (ST_CONTAINS)
- Public data enrichment (Census ACS + theLook eCommerce)
- Campaign scoring and user segmentation
- Gemini-powered campaign recommendations via SQL
- **The payoff:** Target mortgage campaigns without accessing internal customer data

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

**Key insight:** Users in high-renter, middle-income neighborhoods who are actively engaging with the site are likely first-time buyer prospects — no customer mortgage data needed.

---

## Step 1: Explore Public Data Sources

### View theLook Users with Geographic Coordinates

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
WHERE country = 'United States'
  AND latitude IS NOT NULL
LIMIT 10;
```

### Expected Output

```
user_id | first_name | city          | state | latitude  | longitude   | traffic_source
--------|------------|---------------|-------|-----------|-------------|---------------
12345   | John       | San Francisco | CA    | 37.7749   | -122.4194   | Search
23456   | Jane       | Austin        | TX    | 30.2672   | -97.7431    | Organic
34567   | Bob        | Chicago       | IL    | 41.8781   | -87.6298    | Facebook
```

**Key Point:** theLook eCommerce is a public dataset with user demographics and lat/long coordinates.

---

## Step 2: Spatial Join - Users to Census Tracts

The `silver_users_with_census` table joins users to census tracts using ST_CONTAINS.

### Run This Query

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

### Expected Output

```
user_id | city          | state | census_tract_id | state_fips_code | county_fips_code
--------|---------------|-------|-----------------|-----------------|------------------
12345   | San Francisco | CA    | 06075010100     | 06              | 075
23456   | Austin        | TX    | 48453001100     | 48              | 453
34567   | Chicago       | IL    | 17031010100     | 17              | 031
```

### How It Works

```sql
-- Spatial join using ST_CONTAINS
SELECT u.*, ct.geo_id AS census_tract_id
FROM users u
LEFT JOIN census_tracts ct
  ON ST_CONTAINS(ct.tract_geom, ST_GEOGPOINT(u.longitude, u.latitude))
```

**Key Point:** BigQuery Geography functions enable efficient spatial joins at scale.

---

## Step 3: View Census Tract Demographics

The `silver_tract_demographics` table extracts housing and income features from Census ACS data.

### Run This Query

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

### Expected Output

```
census_tract_id | total_population | total_households | homeownership_rate | renter_rate | median_income | income_category
----------------|------------------|------------------|--------------------| ------------|---------------|----------------
06075010100     | 4523             | 2100             | 0.25               | 0.75        | 65000         | middle
17031010100     | 3876             | 1850             | 0.32               | 0.68        | 58000         | middle
48453001100     | 5234             | 2400             | 0.38               | 0.62        | 72000         | middle
```

**Key Point:** High renter rates + middle income = potential first-time buyer markets.

---

## Step 4: View Digital Engagement Signals

The `silver_engagement_signals` table aggregates user behavior from theLook events and orders.

### Run This Query

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

### Expected Output

```
user_id | total_events | days_active | total_orders | engagement_score | cart_rate
--------|--------------|-------------|--------------|------------------|----------
12345   | 156          | 23          | 8            | 142              | 0.45
23456   | 134          | 19          | 6            | 118              | 0.38
34567   | 98           | 15          | 5            | 95               | 0.42
```

**Key Point:** High engagement score indicates digitally active users who respond well to online campaigns.

---

## Step 5: View Campaign Scores by Census Tract

The `gold_tract_campaign_features` table combines demographics with engagement to score tracts.

### Run This Query

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

### Expected Output

```
census_tract_id | users_in_tract | renter_rate | income_category | ftb_score | refi_score | heloc_score
----------------|----------------|-------------|-----------------|-----------|------------|------------
06075010100     | 23             | 0.75        | middle          | 78.5      | 42.3       | 38.1
17031010100     | 18             | 0.68        | middle          | 72.3      | 45.6       | 41.2
48453001100     | 31             | 0.62        | upper_middle    | 68.9      | 52.1       | 48.7
```

### Scoring Logic

**First-Time Buyer Score (0-100):**
- High renter rate (30 points max)
- Working-age population ratio (25 points max)
- Middle income category (25 points max)
- Digital engagement (20 points max)

**Key Point:** Tracts with high FTB scores have demographics matching first-time homebuyer profiles AND digitally engaged users.

---

## Step 6: View User Segments

The `gold_user_segments` table assigns users to campaign segments with propensity scores.

### Run This Query

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

### Expected Output

```
primary_segment          | segment_tier | user_count | avg_ftb_propensity | avg_refi_propensity
-------------------------|--------------|------------|--------------------|--------------------|
first_time_buyer_prospect| high         | 1234       | 78.5               | 42.3
first_time_buyer_prospect| medium       | 2567       | 58.2               | 45.1
first_time_buyer_prospect| low          | 3890       | 38.4               | 48.2
home_equity_prospect     | high         | 876        | 35.2               | 41.8
refinance_prospect       | high         | 1123       | 42.1               | 72.4
```

**Key Point:** Segment users by their highest propensity score for targeted campaigns.

---

## Step 7: View AI-Generated Campaign Recommendations

The `gold_campaign_recommendations` table uses Gemini to generate campaign strategies.

### Run This Query

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

### Expected Output

```
campaign_type      | target_tracts | total_target_users | avg_score | campaign_name                    | target_audience                           | priority
-------------------|---------------|--------------------| ----------|----------------------------------|-------------------------------------------|----------
first_time_buyer   | 156           | 4523               | 72.3      | "Your First Home Starts Here"    | Young professionals in urban rental areas | high
refinance          | 89            | 2876               | 68.5      | "Lower Your Rate, Keep Your Home"| Established homeowners with equity        | medium
home_equity        | 67            | 1987               | 65.2      | "Unlock Your Home's Potential"   | Long-term owners with renovation plans    | medium
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

## How This Compares to Traditional Approaches

### Traditional Campaign Targeting

**Steps:**
1. Request access to internal mortgage data
2. Wait for compliance approval (weeks)
3. Build propensity model on customer data
4. Deploy targeting to marketing platforms
5. Ongoing data governance concerns

**Problems:**
- Data access delays
- PII handling requirements
- Compliance overhead
- Siloed data teams

### Campaign Intelligence Approach

**Steps:**
1. Query public Census data (immediate)
2. Join with digital engagement signals
3. Generate AI-powered recommendations
4. Deploy to marketing platforms

**Benefits:**
- Same-day insights
- No PII required
- No compliance delays
- Marketing team self-service

---

## Key Takeaways

| Capability | Technology | Business Value |
|------------|------------|----------------|
| **Spatial joins at scale** | BigQuery Geography (ST_CONTAINS) | Join users to geographic areas efficiently |
| **Public data enrichment** | Census ACS + theLook | Insights without internal data access |
| **Campaign scoring** | Feature engineering in SQL | Prioritize markets by propensity |
| **AI recommendations** | Gemini 2.0 Flash | Generate campaign strategies automatically |
| **Data governance friendly** | No PII required | Marketing can self-serve |

---

## Demo Narrative

> "Marketing can't access mortgage records, but they can see that users in high-renter, middle-income neighborhoods are actively engaging with our site. The Gemini agent surfaces this as a campaign opportunity — no customer data crossed the wall."

---

## Navigation

**Previous:** [06 - Multimodal Analytics](06-multimodal-analytics.md)
**Home:** [README](../../README.md)
