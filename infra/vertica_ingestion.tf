# =============================================================================
# VERTICA INGESTION DEMO
# Vertica-to-BigQuery data pipeline with Dataproc and Cloud Scheduler
# All resources conditional on enable_vertica_demo = true
# =============================================================================

# -----------------------------------------------------------------------------
# Service Accounts
# -----------------------------------------------------------------------------

resource "google_service_account" "vertica" {
  count = var.enable_vertica_demo ? 1 : 0

  account_id   = "vertica-demo-vm"
  display_name = "Vertica Demo VM"
  description  = "Service account for Vertica demo instance"
}

resource "google_service_account" "dataproc" {
  count = var.enable_vertica_demo ? 1 : 0

  account_id   = "dataproc-vertica-ingestion"
  display_name = "Dataproc Vertica Ingestion"
  description  = "Service account for Dataproc workflow running Vertica to BigQuery jobs"
}

resource "google_service_account" "scheduler" {
  count = var.enable_vertica_demo ? 1 : 0

  account_id   = "scheduler-vertica-ingestion"
  display_name = "Cloud Scheduler Vertica Ingestion"
  description  = "Service account for Cloud Scheduler to trigger Dataproc workflows"
}

# -----------------------------------------------------------------------------
# IAM Bindings - Dataproc Service Account
# -----------------------------------------------------------------------------

resource "google_project_iam_member" "dataproc_bq_editor" {
  count = var.enable_vertica_demo ? 1 : 0

  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataproc[0].email}"
}

resource "google_project_iam_member" "dataproc_bq_job" {
  count = var.enable_vertica_demo ? 1 : 0

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dataproc[0].email}"
}

resource "google_project_iam_member" "dataproc_worker" {
  count = var.enable_vertica_demo ? 1 : 0

  project = var.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.dataproc[0].email}"
}

# -----------------------------------------------------------------------------
# IAM Bindings - Scheduler Service Account
# -----------------------------------------------------------------------------

resource "google_project_iam_member" "scheduler_dataproc_editor" {
  count = var.enable_vertica_demo ? 1 : 0

  project = var.project_id
  role    = "roles/dataproc.editor"
  member  = "serviceAccount:${google_service_account.scheduler[0].email}"
}

# -----------------------------------------------------------------------------
# GCS Buckets
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "vertica_staging" {
  count = var.enable_vertica_demo ? 1 : 0

  name          = "${var.project_id}-vertica-staging"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  labels = {
    project = "data-cloud"
    purpose = "vertica-spark-staging"
    demo    = "vertica-ingestion"
  }

  depends_on = [google_project_service.storage]
}

resource "google_storage_bucket" "spark_scripts" {
  count = var.enable_vertica_demo ? 1 : 0

  name          = "${var.project_id}-spark-scripts"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  labels = {
    project = "data-cloud"
    purpose = "pyspark-jobs"
    demo    = "vertica-ingestion"
  }

  depends_on = [google_project_service.storage]
}

# Grant Dataproc SA access to buckets
resource "google_storage_bucket_iam_member" "dataproc_staging_admin" {
  count = var.enable_vertica_demo ? 1 : 0

  bucket = google_storage_bucket.vertica_staging[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.dataproc[0].email}"
}

resource "google_storage_bucket_iam_member" "dataproc_scripts_viewer" {
  count = var.enable_vertica_demo ? 1 : 0

  bucket = google_storage_bucket.spark_scripts[0].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.dataproc[0].email}"
}

# Upload PySpark job to GCS
resource "google_storage_bucket_object" "vertica_spark_job" {
  count = var.enable_vertica_demo ? 1 : 0

  name   = "vertica_to_bigquery.py"
  bucket = google_storage_bucket.spark_scripts[0].name
  source = "${path.module}/../scripts/spark/vertica_to_bigquery.py"
}

# -----------------------------------------------------------------------------
# Vertica VM (Single Node Community Edition)
# -----------------------------------------------------------------------------

resource "google_compute_instance" "vertica" {
  count = var.enable_vertica_demo ? 1 : 0

  name         = "vertica-demo"
  machine_type = "e2-standard-4" # 4 vCPU, 16GB RAM
  zone         = "${var.region}-a"

  boot_disk {
    initialize_params {
      image = "centos-cloud/centos-stream-9"
      size  = 100 # GB
    }
  }

  network_interface {
    network    = google_compute_network.main.id
    subnetwork = google_compute_subnetwork.main.id
    # No external IP - use IAP for SSH access (secure by default)
  }

  # Required by org policy
  shielded_instance_config {
    enable_secure_boot = true
  }

  metadata_startup_script = file("${path.module}/scripts/vertica-install.sh")

  service_account {
    email  = google_service_account.vertica[0].email
    scopes = ["cloud-platform"]
  }

  labels = {
    project = "data-cloud"
    demo    = "vertica-ingestion"
  }

  tags = ["vertica", "allow-ssh"]

  depends_on = [
    google_project_service.compute,
    google_compute_network.main
  ]
}

# -----------------------------------------------------------------------------
# Firewall Rules
# -----------------------------------------------------------------------------

# SSH via IAP tunneling (always enabled when Vertica demo is on)
# IAP uses Google's IP range 35.235.240.0/20
resource "google_compute_firewall" "vertica_iap_ssh" {
  count = var.enable_vertica_demo ? 1 : 0

  name    = "allow-vertica-iap-ssh"
  network = google_compute_network.main.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # IAP's IP range
  target_tags   = ["allow-ssh"]
}

resource "google_compute_firewall" "vertica_internal" {
  count = var.enable_vertica_demo ? 1 : 0

  name    = "allow-vertica-internal"
  network = google_compute_network.main.id

  allow {
    protocol = "tcp"
    ports    = ["5433"] # Vertica default port
  }

  source_ranges = [var.subnet_cidr]
  target_tags   = ["vertica"]
}

# Internal communication for Dataproc clusters (required for internal-IP-only clusters)
resource "google_compute_firewall" "dataproc_internal" {
  count = var.enable_vertica_demo ? 1 : 0

  name    = "allow-dataproc-internal"
  network = google_compute_network.main.id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
  target_tags   = ["dataproc"]
}

# -----------------------------------------------------------------------------
# Dataproc Workflow Template
# -----------------------------------------------------------------------------

resource "google_dataproc_workflow_template" "vertica_to_bq" {
  count = var.enable_vertica_demo ? 1 : 0

  name     = "vertica-to-bigquery"
  location = var.region

  placement {
    managed_cluster {
      cluster_name = "vertica-ingestion-ephemeral"
      config {
        gce_cluster_config {
          # Only specify subnetwork (network is inferred)
          subnetwork       = google_compute_subnetwork.main.id
          zone             = "${var.region}-a"
          internal_ip_only = true # Required by org policy - no external IPs
          tags             = ["dataproc"] # For firewall rules

          service_account        = google_service_account.dataproc[0].email
          service_account_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        }

        master_config {
          num_instances = 1
          machine_type  = "n2-standard-4"
          disk_config {
            boot_disk_type    = "pd-standard"
            boot_disk_size_gb = 100
          }
        }

        software_config {
          image_version = "2.1-debian11"
          properties = {
            # Use Vertica JDBC driver for standard JDBC connectivity (more compatible with Vertica 9.x)
            "spark:spark.jars.packages" = "com.vertica.jdbc:vertica-jdbc:12.0.4-0"
          }
        }
      }
    }
  }

  jobs {
    step_id = "vertica-to-bigquery-copy"
    pyspark_job {
      main_python_file_uri = "gs://${google_storage_bucket.spark_scripts[0].name}/vertica_to_bigquery.py"
      args = [
        "--vertica-host=${google_compute_instance.vertica[0].network_interface[0].network_ip}",
        "--vertica-db=demo",
        "--vertica-user=dbadmin",
        "--staging-bucket=${google_storage_bucket.vertica_staging[0].name}",
        "--bq-dataset=data_center_topology",
        "--project=${var.project_id}"
      ]
      properties = {
        "spark.executor.memory"              = "4g"
        "spark.driver.memory"                = "4g"
        "spark.dynamicAllocation.enabled"    = "true"
      }
    }
  }

  labels = {
    project = "data-cloud"
    demo    = "vertica-ingestion"
  }

  depends_on = [
    google_project_service.dataproc,
    google_storage_bucket_object.vertica_spark_job
  ]
}

# -----------------------------------------------------------------------------
# Cloud Scheduler
# -----------------------------------------------------------------------------

resource "google_cloud_scheduler_job" "vertica_sync" {
  count = var.enable_vertica_demo ? 1 : 0

  name      = "vertica-to-bigquery-weekly"
  region    = var.region
  schedule  = "0 2 * * 0" # Weekly: Sunday 2 AM
  time_zone = "America/Los_Angeles"
  paused    = true # Paused by default - trigger manually for demo

  description = "Weekly Vertica to BigQuery sync (paused - trigger manually for demo)"

  http_target {
    http_method = "POST"
    uri         = "https://dataproc.googleapis.com/v1/projects/${var.project_id}/regions/${var.region}/workflowTemplates/${google_dataproc_workflow_template.vertica_to_bq[0].name}:instantiate"

    oauth_token {
      service_account_email = google_service_account.scheduler[0].email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  retry_config {
    retry_count = 0 # No retries for demo
  }

  depends_on = [
    google_project_service.cloudscheduler,
    google_dataproc_workflow_template.vertica_to_bq
  ]
}
