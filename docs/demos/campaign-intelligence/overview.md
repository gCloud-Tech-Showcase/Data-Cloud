# Campaign Intelligence

Target mortgage campaigns using public Census data and digital signals — no customer data required.

## The Problem

Marketing wants to target mortgage campaigns, but can't access internal mortgage records due to data governance policies.

## The Solution

Combine public Census housing data with digital engagement signals to identify campaign opportunities:
1. **Census ACS** - Housing demographics by census tract (renter rates, income)
2. **theLook eCommerce** - User engagement signals (events, orders)
3. **Gemini AI** - Generate campaign recommendations

**Key insight:** Users in high-renter, middle-income neighborhoods who are actively engaging are likely first-time buyer prospects — no customer mortgage data needed.

## Technologies Used

| Service | Purpose |
|---------|---------|
| BigQuery Geography | Spatial joins (ST_CONTAINS) |
| Census ACS | Housing and income demographics |
| theLook eCommerce | User engagement signals |
| Gemini 2.0 Flash | Campaign recommendations |

## Key Results

- **Same-day insights** vs weeks of data access requests
- **No PII required** - Marketing can self-serve
- **AI-powered recommendations** - Campaign strategies generated automatically

## Choose Your Path

| Path | Time | Description |
|------|------|-------------|
| [**Quick Reference**](quick.md) | 5 min | Just the SQL queries + outputs |
| [**Full Guide**](guide.md) | 10 min | Complete walkthrough |

## Standalone Demo

This demo is independent from the Churn Prediction → Sentiment Analysis narrative. It can be run on its own.

---

## Navigation

[← Multimodal Insights](../multimodal-insights/overview.md) | [Back to Demos](../README.md)
