# Google Cloud Tech Showcase: Propensity Modeling with BQML and Vertex AI

This repository is the first in a series for the GitLab Google Cloud Tech Showcase. It provides a complete, end-to-end demonstration of a high-impact, real-world use case: **predicting user purchase propensity** using Google Cloud's powerful data and AI portfolio.

The primary goal is to empower data analysts and democratize the journey from raw data to deployed AI by leveraging SQL-native tools, while also providing a path to more sophisticated MLOps for advanced personas.

## Use Case: E-commerce Purchase Propensity

This demo solves a common business problem: identifying which website visitors are most likely to make a purchase. By analyzing user behavior data from Google Analytics 4 (GA4), we build a machine learning model that assigns a "propensity score" to each user.

This enables marketing and sales teams to:

- Focus retention efforts on high-value users who are unlikely to convert on their own.
- Optimize ad spend by targeting users with a high propensity to buy.
- Personalize the user experience to nudge potential buyers towards a purchase.

---

## Architecture

The entire demo is built on a modern, scalable, and serverless data architecture. All infrastructure is managed via Terraform for consistency and one-click replicability.

The data flows through the following stages:

1.  **Source Data**: We use the public `ga4_obfuscated_sample_ecommerce` dataset available in BigQuery. This provides raw, event-level user interaction data.
2.  **SQL Transformation**: **Dataform** is used to orchestrate a series of SQL-based transformations. It cleans the raw, nested GA4 data, engineers features, and builds clean, model-ready tables (`fct_user_features`). This demonstrates how to apply software engineering best practices (version control, testing, dependency management) to a data transformation pipeline.
3.  **In-Database ML Training**: **BigQuery Machine Learning (BQML)** is used to train a logistic regression model directly on the feature table within BigQuery. This is done using a single `CREATE MODEL` SQL statement, showcasing the democratization of ML for SQL-savvy analysts.
4.  **Centralized Model Management**: Upon creation, the BQML model is automatically registered in the **Vertex AI Model Registry**. This provides a unified hub for managing, versioning, and governing all ML models, regardless of their origin.
5.  **Operationalization (Optional Extension)**: Once in Vertex AI, the model can be easily deployed to an endpoint for real-time predictions or used in a batch prediction pipeline, catering to more advanced ML operationalization needs.

!Architecture Diagram
_Note: You can create a simple diagram using a tool like diagrams.net and embed it here._

---

## Technology Stack

- **Infrastructure as Code**: Terraform
- **Data Warehouse**: Google BigQuery
- **Data Transformation**: Dataform
- **Machine Learning (Training)**: BigQuery ML (BQML)
- **MLOps Platform**: Vertex AI Model Registry
- **Version Control**: GitLab

---

## Getting Started

Follow these steps to deploy the entire demo environment into your own Google Cloud project.

### 1. Prerequisites

- A Google Cloud Project with the Billing Account configured.
- The following APIs enabled: `iam.googleapis.com`, `bigquery.googleapis.com`, `dataform.googleapis.com`, `aiplatform.googleapis.com`, `cloudresourcemanager.googleapis.com`.
- Google Cloud SDK installed and configured.
- Terraform (v1.0+) installed locally.
- Sufficient IAM permissions (e.g., `Project Owner` or `Editor`) to create the resources defined in the Terraform scripts.

### 2. Configuration

1.  Clone this repository to your local machine:

    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  Create a `terraform.tfvars` file in the root of the project. This file is in `.gitignore` to prevent accidental commits of sensitive information.
    ```terraform
    // terraform.tfvars
    project_id      = "your-gcp-project-id"
    region          = "us-central1" // Or your preferred region
    dataset_id      = "propensity_showcase"
    dataform_repo_id = "propensity-dataform-repo"
    ```

### 3. Deployment

1.  Initialize Terraform in the project directory. This will download the necessary Google Cloud provider plugins.

    ```bash
    terraform init
    ```

2.  Review the execution plan to see the resources Terraform will create.

    ```bash
    terraform plan
    ```

3.  Apply the configuration to deploy the infrastructure. This will provision the BigQuery dataset, Dataform repository, and all necessary IAM bindings.
    ```bash
    terraform apply
    ```
    Enter `yes` when prompted to confirm.

### 4. Running the Demo

1.  **Run the Dataform Pipeline**:
    - Navigate to the Dataform UI in the Google Cloud Console.
    - Select your repository (`propensity-dataform-repo`).
    - Initiate a workflow execution to run the SQL transformations. This will generate the `fct_user_features` table in your BigQuery dataset.

2.  **Train the BQML Model**:
    - Navigate to the BigQuery SQL Workspace.
    - Open and run the SQL script located in `src/bqml/create_model.sql`. This script trains the model and registers it to Vertex AI.

3.  **Verify the Model**:
    - **In BigQuery**: After the query completes, you can see your new model in the BigQuery `Models` directory. You can inspect its evaluation metrics, feature importance, and other details.
    - **In Vertex AI**: Navigate to the Vertex AI Model Registry in the console. Your new model, `propensity_model`, will be listed, ready for governance and deployment.

---

## Project Structure

.
├── terraform/ # All Terraform Infrastructure as Code
│ ├── main.tf # Core resource definitions (BigQuery, Dataform, IAM)
│ ├── variables.tf # Input variables (project_id, region, etc.)
│ └── outputs.tf # Outputs from the Terraform deployment
│
├── dataform/ # The Dataform project root
│ ├── definitions/
│ │ ├── sources/
│ │ │ └── ga4_source.js # Declares the raw GA4 BigQuery table as a source
│ │ ├── staging/
│ │ │ └── stg_ga4\_\_events.sqlx # Cleans, unnests, and prepares raw event data
│ │ └── marts/
│ │ └── fct_user_propensity.sqlx # Aggregates user data into a feature table for ML
│ ├── dataform.json # Dataform project configuration
│ └── package.json # Project dependencies and definitions
│
├── bqml/ # SQL scripts for BigQuery ML tasks
│ ├── 01_create_model.sql # Trains the propensity model and registers it to Vertex AI
│ └── 02_evaluate_model.sql # Runs a BQML.EVALUATE query against the trained model
│
├── .gitignore # Specifies files for Git to ignore (e.g., terraform.tfvars)
└── README.md # This file
