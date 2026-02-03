# Google Cloud Tech Showcase: Propensity Modeling with BQML and Vertex AI

This repository is the first in a series for the Google Cloud Tech Showcase. It provides a complete, end-to-end demonstration of a high-impact, real-world use case: **predicting user retention** using Google Cloud's powerful data and AI portfolio.

The primary goal is to empower data analysts and democratize the journey from raw data to deployed AI by leveraging SQL-native tools, while also providing a path to more sophisticated MLOps for advanced personas.

## Use Case: User Retention Prediction

This demo solves a common business problem: identifying which users are likely to return to an application. By analyzing user behavior data from Google Analytics 4 (GA4) / Firebase, we build a machine learning model that predicts whether a user will return within 7 days based on their first week of activity.

This enables product and marketing teams to:

- Focus retention efforts on users who are unlikely to return on their own.
- Optimize engagement campaigns by targeting users with low return probability.
- Personalize the user experience to increase retention rates.

---

## Architecture

The entire demo is built on a modern, scalable, and serverless data architecture. All infrastructure is managed via Terraform for consistency and one-click replicability.

The data flows through the following stages:

1. **Source Data**: We use the public Firebase gaming dataset (`firebase-public-project.analytics_153293282.events_*`) available in BigQuery. This provides raw, event-level user interaction data.
2. **SQL Transformation**: **Dataform** is used to orchestrate a series of SQL-based transformations. It cleans the raw, nested GA4 data, engineers features, and builds clean, model-ready tables (`training_data`). This demonstrates how to apply software engineering best practices (version control, testing, dependency management) to a data transformation pipeline.
3. **In-Database ML Training**: **BigQuery Machine Learning (BQML)** is used to train a logistic regression model directly within BigQuery. The model is defined in Dataform using a `CREATE MODEL` statement, showcasing the democratization of ML for SQL-savvy analysts.
4. **Centralized Model Management**: Upon creation, the BQML model is automatically registered in the **Vertex AI Model Registry**. This provides a unified hub for managing, versioning, and governing all ML models, regardless of their origin.
5. **Operationalization (Optional Extension)**: Once in Vertex AI, the model can be easily deployed to an endpoint for real-time predictions or used in a batch prediction pipeline, catering to more advanced ML operationalization needs.

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Infrastructure as Code | Terraform | >= 1.6.0 |
| Data Warehouse | Google BigQuery | - |
| Data Transformation | Dataform | 3.0.0 |
| Machine Learning | BigQuery ML (BQML) | - |
| MLOps Platform | Vertex AI Model Registry | - |
| Secret Management | Google Secret Manager | - |
| Version Control | Git | - |

---

## Getting Started

Follow these steps to deploy the entire demo environment into your own Google Cloud project.

### 1. Prerequisites

- A Google Cloud Project with Billing enabled.
- Google Cloud SDK (`gcloud`) installed and configured.
- Terraform (v1.6.0+) installed locally.
- A GitLab personal access token for Dataform repository sync.
- Sufficient IAM permissions (e.g., `Project Owner` or `Editor`) to create the resources defined in the Terraform scripts.

### 2. Configuration

1. Clone this repository to your local machine:

    ```bash
    git clone <your-repository-url>
    cd Data-Cloud
    ```

2. Create a `terraform.tfvars` file in the `infra/` directory using the provided example:

    ```bash
    cd infra
    cp terraform.tfvars.example terraform.tfvars
    ```

3. Edit `terraform.tfvars` with your values:

    ```hcl
    project_id   = "your-gcp-project-id"
    region       = "us-central1"
    gitlab_token = "your-gitlab-personal-access-token"

    # Optional overrides (defaults shown)
    # dataset_id       = "propensity_modeling"
    # dataset_location = "US"
    # network_name     = "data-cloud-vpc"
    # subnet_cidr      = "10.0.0.0/24"
    ```

### 3. Deployment

1. Initialize Terraform in the `infra/` directory. This will download the necessary Google Cloud provider plugins.

    ```bash
    cd infra
    terraform init
    ```

2. Review the execution plan to see the resources Terraform will create.

    ```bash
    terraform plan
    ```

3. Apply the configuration to deploy the infrastructure. This will provision:
   - Required GCP APIs (Compute, BigQuery, Vertex AI, Dataform, Secret Manager)
   - VPC network and subnet
   - BigQuery datasets (`propensity_modeling`, `ga4_source`)
   - Dataform repository with GitLab integration
   - IAM bindings and service accounts
   - Dataform release and workflow configurations

    ```bash
    terraform apply
    ```

    Enter `yes` when prompted to confirm.

### 4. Running the Demo

1. **Dataform Pipeline Execution**:
   - The Dataform release configuration automatically compiles the code every hour (cron: `0 * * * *`).
   - To trigger manually: Navigate to the Dataform UI in the Google Cloud Console, select the "data-cloud" repository, and initiate a workflow execution.
   - This will create the staging views and `training_data` table in BigQuery.

2. **Model Training**:
   - The `user_retention_model` is defined in Dataform and trains automatically as part of the pipeline.
   - The model uses logistic regression with L2 regularization and automatic train/test splitting.

3. **Verify the Results**:
   - **In BigQuery**: After execution completes, find your model in the BigQuery `Models` section under the `propensity_modeling` dataset. Inspect evaluation metrics, feature importance, and training statistics.
   - **In Vertex AI**: Navigate to the Vertex AI Model Registry. Your model `user_retention_model` will be listed, ready for governance and deployment.

4. **Run Predictions** (Optional):
   - Enable the prediction queries in `definitions/propensity_modeling/ml/predictions.sqlx` by setting `hasOutput: true`.
   - Re-run the Dataform workflow to generate batch predictions.

---

## Project Structure

```
.
├── infra/                              # Terraform Infrastructure as Code
│   ├── main.tf                         # Core resource definitions (APIs, VPC, BigQuery, Dataform, IAM)
│   ├── variables.tf                    # Input variables with defaults
│   ├── outputs.tf                      # Outputs from the deployment
│   ├── providers.tf                    # Google Cloud provider configuration
│   ├── versions.tf                     # Terraform and provider version constraints
│   └── terraform.tfvars.example        # Example configuration template
│
├── definitions/                        # Dataform SQL transformation pipeline
│   └── propensity_modeling/
│       ├── sources/
│       │   └── ga4_events.sqlx         # Declares the raw GA4/Firebase BigQuery table as source
│       ├── staging/
│       │   ├── v_events_flattened.sqlx # Unnests nested GA4 event parameters into flat columns
│       │   └── v_user_sessions.sqlx    # Aggregates events into user sessions
│       ├── marts/
│       │   └── training_data.sqlx      # Feature engineering for ML (7-day windows, 18 features)
│       └── ml/
│           ├── user_retention_model.sqlx   # BQML logistic regression model definition
│           ├── model_evaluation.sqlx       # Model evaluation queries (disabled by default)
│           └── predictions.sqlx            # Batch prediction queries (disabled by default)
│
├── package.json                        # Dataform dependencies (@dataform/core 3.0.0)
├── workflow_settings.yaml              # Dataform project configuration
├── .gitignore                          # Excludes sensitive files (tfvars, tfstate, etc.)
└── README.md                           # This file
```

---

## Data Pipeline Details

### Source Data

- **Dataset**: `firebase-public-project.analytics_153293282.events_*`
- **Date Range**: November 1, 2020 - January 31, 2021
- **Data Type**: GA4/Firebase event-level user interactions from a gaming app

### Transformation Layers

| Layer | Schema | Purpose |
|-------|--------|---------|
| **Sources** | - | External table declarations |
| **Staging** | `ga4_source` | Data cleaning, unnesting nested JSON, session aggregation |
| **Marts** | `propensity_modeling` | Feature engineering, ML-ready datasets |
| **ML** | `propensity_modeling` | Model training and predictions |

### Feature Engineering

The `training_data` table creates 18 features across several categories:

- **Engagement**: days_active, total_sessions, total_events
- **Gameplay**: levels_started, levels_completed, level_completion_rate
- **Scoring**: max_score, avg_score
- **Time**: total_engagement_minutes, days_since_last_activity
- **Device**: device_category, operating_system, country

### Model Configuration

- **Algorithm**: Logistic Regression
- **Regularization**: L2 (lambda = 0.1)
- **Training Window**: First 7 days of user activity
- **Label Window**: Days 8-14 (non-overlapping)
- **Target**: `will_return` (binary: did user return in label window?)

---

## Cleanup

To remove all deployed resources:

```bash
cd infra
terraform destroy
```

Enter `yes` when prompted to confirm.

---

## License

This project is provided as a demonstration for educational purposes.
