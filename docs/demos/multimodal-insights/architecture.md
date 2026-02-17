# Multimodal Insights Architecture

Data flow and pipeline structure for combining behavioral and sentiment signals.

---

## Pipeline Overview

```mermaid
graph TB
    subgraph "Churn Prediction Domain"
        SCORES[gold_user_risk_scores<br/>Churn Predictions]
    end

    subgraph "Sentiment Analysis Domain"
        SENTIMENT[silver_review_sentiment<br/>Review Analysis]
    end

    subgraph "Multimodal Insights"
        JOIN[Cross-Domain Join<br/>user_pseudo_id]
        INSIGHT[Combined View<br/>WHO + WHY]
    end

    SCORES --> JOIN
    SENTIMENT --> JOIN
    JOIN --> INSIGHT

    classDef gold fill:#ffd700,stroke:#333,color:#000
    classDef silver fill:#c0c0c0,stroke:#333,color:#000
    classDef insight fill:#9c27b0,stroke:#333,color:#fff

    class SCORES gold
    class SENTIMENT silver
    class JOIN,INSIGHT insight
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant Churn as Churn Prediction
    participant Sentiment as Sentiment Analysis
    participant Multi as Multimodal Query

    Note over Churn: gold_user_risk_scores<br/>WHO will churn?

    Note over Sentiment: silver_review_sentiment<br/>WHY are they unhappy?

    Churn->>Multi: High-risk users
    Sentiment->>Multi: Negative reviews

    Note over Multi: JOIN on user identifier<br/>Targeted insights
```

---

## Key Insight

This demo combines outputs from two independent pipelines:

| Signal | Source | Question Answered |
|--------|--------|-------------------|
| Behavioral | Churn Prediction | **WHO** is likely to leave? |
| Textual | Sentiment Analysis | **WHY** are they unhappy? |

The combination enables targeted action: prioritize high-risk users with specific complaints.

---

## Cross-Domain Query

```sql
SELECT
  risk.user_pseudo_id,
  risk.churn_probability,
  sentiment.sentiment,
  sentiment.category,
  sentiment.review_text
FROM gold_user_risk_scores risk
JOIN silver_review_sentiment sentiment
  ON risk.user_pseudo_id = sentiment.user_id
WHERE risk.churn_probability > 0.7
  AND sentiment.sentiment = 'negative'
ORDER BY risk.churn_probability DESC;
```

---

## Prerequisites

This demo requires both upstream pipelines to be complete:

1. **Churn Prediction** - `gold_user_risk_scores` must be populated
2. **Sentiment Analysis** - `silver_review_sentiment` must be populated

---

## Navigation

[Guide](guide.md) | [Patterns Reference](../../architecture.md)
