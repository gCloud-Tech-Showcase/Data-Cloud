# Getting Started

Deploy the Data-Cloud project infrastructure and run your first pipeline.

---

## Prerequisites

- **Google Cloud Project** with billing enabled
- **Terraform** >= 1.6.0 ([Download](https://www.terraform.io/downloads))
- **GitHub personal access token** with `repo` scope ([Create token](https://github.com/settings/tokens))
- **Python 3.9+** (required for sentiment analysis demo)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/gCloud-Tech-Showcase/Data-Cloud.git
cd Data-Cloud
```

---

## Step 2: Configure Project Settings

Two files need your project ID:

### A. Terraform Configuration

Create `terraform.tfvars` from the example:

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Edit `infra/terraform.tfvars`:

```hcl
project_id   = "your-project-id"           # Required: Your GCP project ID
github_token = "ghp_your_token_here"       # Required: GitHub personal access token

# Optional overrides (defaults are fine for most cases)
# region           = "us-central1"
# dataset_location = "US"
```

This file is gitignored — never commit it.

### B. Dataform Configuration

Edit `workflow_settings.yaml` (already exists in repo):

```yaml
defaultProject: your-project-id    # Change from gcloud-tech-showcase to your project
defaultLocation: US
defaultDataset: propensity_modeling
```

This file is tracked in git. If you're working on a fork, commit your changes. For local testing, you can leave it modified without committing.

---

## Step 3: Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan    # Preview changes
terraform apply   # Deploy (type 'yes' to confirm)
```

### What Gets Created

| Resource | Purpose |
|----------|---------|
| **BigQuery Datasets** | `sentiment_analysis`, `propensity_modeling`, `ga4_source`, `campaign_intelligence` |
| **GCS Bucket** | Storage for review JSON files |
| **BigQuery Connection** | Enables BigLake and Gemini access |
| **Dataform Repository** | Connected to GitHub |
| **Secret Manager** | Secure storage for GitHub token |
| **Service Account** | Dataform execution identity with required IAM roles |

Terraform automatically enables required APIs (BigQuery, Dataform, Vertex AI, etc.).

---

## Step 4: Run the Pipeline

1. Open **Google Cloud Console** → **Dataform**
2. Click on the `data-cloud` repository
3. Go to **Releases & Scheduling** → **Create Release Configuration**
4. Set **Git commitish** to `main` (or your branch)
5. Click **Create**
6. Click **Create Workflow** to run the release

Alternatively, trigger a manual compilation and execution:
1. In Releases & Scheduling, click on your release configuration
2. Click **Run** to execute all actions

**First run takes ~10-15 minutes** (model training). Subsequent runs are faster due to incremental processing.

### Optional: Development Workspace

To iterate on the SQL or test changes before committing:

1. In the Dataform repository, click **Create Development Workspace**
2. Name it after your branch (e.g., `main`)
3. Use **Start Compilation** and **Start Execution** to test changes interactively

---

## Step 5: Verify Deployment

In **BigQuery Console**, run:

```sql
-- Check sentiment analysis
SELECT sentiment, COUNT(*) AS count
FROM `sentiment_analysis.silver_review_sentiment`
GROUP BY sentiment;

-- Check propensity modeling
SELECT COUNT(*) AS training_rows
FROM `propensity_modeling.gold_training_features`;

-- Check model exists
SELECT * FROM ML.EVALUATE(MODEL `propensity_modeling.gold_user_retention_model`);
```

In **Vertex AI Console** → **Model Registry**, verify `gold_user_retention_model` is registered.

---

## Note: Review Data for Sentiment Analysis

The sentiment analysis demo requires Play Store reviews in GCS. Run the scraper to populate this data:

```bash
cd scripts && python scrape_play_store_reviews.py
```

See [scripts/README.md](../scripts/README.md) for setup and details.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Dataform compilation fails with "undefined variable" | Check `workflow_settings.yaml` has correct `defaultProject` |
| `silver_review_sentiment` fails with "Connection not found" | Re-run `terraform apply` to recreate the Vertex AI connection |
| Model training fails with "Insufficient data" | Verify `gold_training_features` has 5K+ rows with balanced classes |
| Gemini API calls fail with "Permission denied" | Re-run `terraform apply` — IAM bindings may not have propagated |

---

## Cleanup

To remove all resources:

```bash
cd infra
terraform destroy
```

**Note:** GCS bucket is preserved by default. Delete manually in Cloud Console if needed.

---

## Next Steps

- **[Demo Guides](demos/README.md)** — Run the demonstrations
- **[Architecture](architecture.md)** — Technical deep dive
