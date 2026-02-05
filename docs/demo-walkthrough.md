# Demo Walkthrough

This walkthrough demonstrates Google Cloud's multimodal analytics capabilities through a real-world use case: predicting customer churn and understanding why users leave.

**Time:** 25-30 minutes
**Prerequisites:** Infrastructure deployed via [Getting Started](getting-started.md)

---

## The Story

Most analytics platforms answer **"who will churn?"** but not **"why are they churning?"**

This demo shows how Google Cloud's open lakehouse architecture combines:
- **Structured data** (GA4 behavioral events) → Predict churn
- **Unstructured data** (Play Store reviews) → Understand sentiment
- **Multimodal analytics** → Target interventions based on both

---

## Demo Flow

### Part 1: Churn Prediction (Guides 1-3)

Build a traditional churn prediction model to establish the business problem.

**[01 - Feature Engineering](demos/01-feature-engineering.md)**
- Query 5.7M GA4 events from Firebase public dataset
- Build rolling 7-day window features (days active, level completion, engagement)
- Create 18K training rows with features + labels

**[02 - Train ML Model](demos/02-train-ml-model.md)**
- Train logistic regression model with BigQuery ML
- Evaluate model performance (79% AUC)
- Explore feature importance and explainability

**[03 - Churn Predictions](demos/03-churn-predictions.md)**
- Score users and segment by churn risk
- Identify high-risk users (18% return probability)
- **Problem revealed:** We know WHO will churn, but not WHY

---

### Part 2: Sentiment Analysis (Guides 4-5)

Introduce multimodal data to understand the "why" behind churn.

**[04 - Sentiment Enrichment](demos/04-sentiment-enrichment.md)**
- Query unstructured JSON reviews directly from Cloud Storage (no ETL)
- Enrich with Gemini AI sentiment analysis via SQL
- Process 500+ reviews with sentiment, category, and scores

**[05 - Sentiment Insights](demos/05-sentiment-insights.md)**
- Analyze sentiment distribution and trends
- Identify top complaint categories (ads, bugs, difficulty)
- Discover actionable product insights from text data

---

### Part 3: Multimodal Analytics (Guide 6)

Combine both domains for contextualized interventions.

**[06 - Multimodal Analytics](demos/06-multimodal-analytics.md)**
- Join churn predictions with sentiment analysis
- Target high-risk users with specific complaints
- **Business value:** "User X has 18% return probability AND complains about ads" → Offer premium ad-free trial
- Verify Vertex AI model registry integration
- Review incremental processing approach

---

## Key Differentiators

This demo highlights Google Cloud capabilities that set it apart:

| Capability | Technology | Business Value |
|------------|------------|----------------|
| Query unstructured data without ETL | BigLake Object Tables | Faster time-to-insight, simpler architecture |
| AI enrichment via SQL | Gemini 2.0 Flash | No external API orchestration |
| In-database ML training | BigQuery ML | Train where data lives, no data movement |
| Model explainability | Vertex AI | Regulatory compliance, trust |
| Incremental pipelines | Dataform incremental processing | Only process new data |
| Multimodal analytics | BigQuery + BigLake + Gemini | Contextualized insights, not just predictions |

---

## Demo Tips

### For Technical Audiences
- Emphasize SQL-first approach (no Python notebooks required)
- Show Dataform dependency graph for pipeline visualization
- Demonstrate tag-based execution for domain isolation

### For Data Scientists
- Focus on `ML.GLOBAL_EXPLAIN()` and `ML.EXPLAIN_PREDICT()`
- Show TRANSFORM clause for feature engineering
- Discuss hyperparameter tuning options in BQML

### For Business Stakeholders
- Start with Guide 3 (churn predictions) to show the limitation
- Jump to Guide 6 (multimodal analytics) for the business value
- Emphasize value: targeted interventions vs. generic campaigns

---

## Navigation

- **[Getting Started](getting-started.md)** - Deploy the infrastructure
- **[Architecture Deep Dive](architecture.md)** - Technical details
- **[README](../README.md)** - Project overview

---

## Start the Demo

Begin with **[Guide 01 - Feature Engineering](demos/01-feature-engineering.md)**
