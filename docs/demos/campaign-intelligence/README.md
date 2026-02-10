# Campaign Intelligence *(Proof of Concept)*

> **Note:** This use case demonstrates the approach — spatial joins, public data enrichment, Gemini recommendations. Results may vary; some outputs need refinement.

Target campaigns using public Census data and digital signals — no customer data required.

## What You'll Build

Combine public Census housing data with digital engagement signals:
1. **Census ACS** — Housing demographics by census tract (renter rates, income)
2. **theLook eCommerce** — User engagement signals (events, orders)
3. **Gemini AI** — Generate campaign recommendations

Users in high-renter, middle-income neighborhoods who are actively engaging are likely first-time buyer prospects — no internal customer data needed.

## Technologies

| Service | Purpose |
|---------|---------|
| BigQuery Geography | Spatial joins (ST_CONTAINS) |
| Census ACS | Housing and income demographics |
| theLook eCommerce | User engagement signals |
| Gemini 2.0 Flash | Campaign recommendations |

## Results

- **No PII required** — Uses only public datasets
- **AI-powered recommendations** — Campaign strategies generated automatically

## Guides

- [Quick Reference](quick.md) — SQL queries with expected outputs
- [Full Guide](guide.md) — Complete walkthrough

## Standalone

This use case is independent from the Churn Prediction → Sentiment Analysis flow.
