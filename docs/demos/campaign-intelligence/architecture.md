# Campaign Intelligence Architecture

Data flow and pipeline structure for AI-powered campaign targeting with Census data.

---

## Pipeline Overview

```mermaid
graph TB
    subgraph "Bronze Layer - Public Datasets"
        THELOOK[theLook eCommerce<br/>users - events - orders]
        CENSUS_GEO[Census Tracts<br/>Geographic Boundaries]
        CENSUS_ACS[Census ACS<br/>Housing & Income]
    end

    subgraph "BigQuery + Dataform"
        subgraph "Silver Layer - Spatial Joins"
            USERS[silver_users_with_census<br/>ST_CONTAINS Join]
            ENGAGE[silver_engagement_signals<br/>User Aggregates]
            DEMO[silver_tract_demographics<br/>Housing Features]
        end

        subgraph "Gold Layer - Campaign Ready"
            TRACT[gold_tract_campaign_features<br/>Tract Scoring]
            SEG[gold_user_segments<br/>User Segments]
            REC[gold_campaign_recommendations<br/>AI Recommendations]
        end
    end

    subgraph "Vertex AI"
        GEMINI[Gemini 2.0 Flash<br/>Campaign Agent]
    end

    THELOOK --> USERS
    THELOOK --> ENGAGE
    CENSUS_GEO --> USERS
    CENSUS_ACS --> DEMO

    USERS --> TRACT
    ENGAGE --> TRACT
    DEMO --> TRACT

    USERS --> SEG
    ENGAGE --> SEG
    TRACT --> SEG

    TRACT --> REC
    GEMINI -.-> |ML.GENERATE_TEXT| REC

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef gold fill:#ffd700,stroke:#333,color:#000
    classDef external fill:#4285f4,stroke:#333,color:#fff

    class THELOOK,CENSUS_GEO,CENSUS_ACS bronze
    class USERS,ENGAGE,DEMO silver
    class TRACT,SEG,REC gold
    class GEMINI external
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant TL as theLook eCommerce
    participant CT as Census Tracts
    participant ACS as Census ACS
    participant Silver as Silver Layer
    participant Gold as Gold Layer
    participant Gemini as Gemini 2.0 Flash

    TL->>Silver: Users with lat/long
    CT->>Silver: Tract geometries
    Note over Silver: ST_CONTAINS spatial join<br/>silver_users_with_census

    TL->>Silver: Events + Orders
    Note over Silver: Aggregate engagement<br/>silver_engagement_signals

    ACS->>Silver: Housing + Income data
    Note over Silver: Demographics by tract<br/>silver_tract_demographics

    Silver->>Gold: Combined features
    Note over Gold: Campaign scoring<br/>gold_tract_campaign_features

    Silver->>Gold: User-level features
    Note over Gold: Segment assignment<br/>gold_user_segments

    Gold->>Gemini: Campaign summaries
    Gemini->>Gold: AI recommendations
    Note over Gold: gold_campaign_recommendations
```

---

## Key Components

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `thelook_users` | User demographics with lat/long |
| Bronze | `thelook_events` | Web events (page views, carts) |
| Bronze | `thelook_orders` | Purchase transactions |
| Bronze | `census_tracts` | Geographic tract boundaries |
| Bronze | `census_acs` | Housing tenure, income by tract |
| Silver | `silver_users_with_census` | Users joined to tracts via ST_CONTAINS |
| Silver | `silver_engagement_signals` | Aggregated digital engagement |
| Silver | `silver_tract_demographics` | Housing and income features |
| Gold | `gold_tract_campaign_features` | Campaign scoring by tract |
| Gold | `gold_user_segments` | User segments with propensity |
| Gold | `gold_campaign_recommendations` | AI-generated recommendations |

---

## Spatial Join

Users are mapped to census tracts using BigQuery's geography functions:

```sql
WHERE ST_CONTAINS(
  tracts.tract_geom,
  ST_GEOGPOINT(users.longitude, users.latitude)
)
```

This enables demographic enrichment without PII.

---

## Navigation

[Guide](guide.md) | [Quick Reference](quick.md) | [Patterns Reference](../../architecture.md)
