#!/usr/bin/env python3
"""
Vertica to BigQuery Ingestion - PySpark Job

This PySpark job reads all tables from Vertica's data center topology schema
and writes them to BigQuery. It's designed to run on Dataproc with the
Vertica Spark Connector and BigQuery Spark Connector.

Usage:
    spark-submit vertica_to_bigquery.py \
        --vertica-host 10.0.0.2 \
        --vertica-db demo \
        --vertica-user dbadmin \
        --staging-bucket my-project-vertica-staging \
        --bq-dataset data_center_topology \
        --project my-project

Dependencies (configured via Dataproc workflow template):
    - com.vertica.spark:vertica-spark:3.3.1
    - com.google.cloud.spark:spark-bigquery-with-dependencies_2.12 (built-in)
"""

import argparse
import sys
from datetime import datetime
from typing import List, NamedTuple

from pyspark.sql import SparkSession, DataFrame


class TableConfig(NamedTuple):
    """Configuration for a table ingestion."""
    name: str
    write_mode: str = "overwrite"  # overwrite, append


# Tables to migrate - matching the schema from generate_datacenter_topology.py
TABLES_TO_MIGRATE: List[TableConfig] = [
    # Entity tables (nodes)
    TableConfig("locations"),
    TableConfig("racks"),
    TableConfig("hardware_assets"),
    TableConfig("nic_interfaces"),
    TableConfig("applications"),
    # Relationship tables (edges)
    TableConfig("network_connections"),
    TableConfig("app_deployments"),
    TableConfig("app_dependencies"),
    TableConfig("maintenance_events"),
]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate data center topology from Vertica to BigQuery"
    )

    # Vertica connection
    parser.add_argument(
        "--vertica-host",
        required=True,
        help="Vertica host IP address"
    )
    parser.add_argument(
        "--vertica-port",
        type=int,
        default=5433,
        help="Vertica port (default: 5433)"
    )
    parser.add_argument(
        "--vertica-db",
        required=True,
        help="Vertica database name"
    )
    parser.add_argument(
        "--vertica-user",
        default="dbadmin",
        help="Vertica username (default: dbadmin)"
    )
    parser.add_argument(
        "--vertica-password",
        default="",
        help="Vertica password (default: empty for dbadmin)"
    )
    parser.add_argument(
        "--vertica-schema",
        default="public",
        help="Vertica schema (default: public)"
    )

    # GCS staging (required for Vertica connector)
    parser.add_argument(
        "--staging-bucket",
        required=True,
        help="GCS bucket for Vertica connector staging"
    )

    # BigQuery destination
    parser.add_argument(
        "--bq-dataset",
        required=True,
        help="BigQuery dataset name"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID"
    )

    # Optional
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Specific tables to migrate (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print configuration without executing"
    )

    return parser.parse_args()


def create_spark_session() -> SparkSession:
    """Create SparkSession with required configurations."""
    return (
        SparkSession.builder
        .appName("Vertica to BigQuery Ingestion")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


def read_from_vertica(
    spark: SparkSession,
    table_name: str,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    schema: str,
    staging_bucket: str,
) -> DataFrame:
    """Read a table from Vertica using standard JDBC."""

    # Vertica JDBC URL
    jdbc_url = f"jdbc:vertica://{host}:{port}/{database}"

    print(f"  Reading from Vertica: {schema}.{table_name}")
    print(f"  JDBC URL: {jdbc_url}")

    # Use standard JDBC read (more compatible with Vertica 9.x)
    df = (
        spark.read
        .format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", f"{schema}.{table_name}")
        .option("user", user)
        .option("password", password)
        .option("driver", "com.vertica.jdbc.Driver")
        .load()
    )

    return df


def write_to_bigquery(
    df: DataFrame,
    project: str,
    dataset: str,
    table_name: str,
    write_mode: str = "overwrite",
) -> None:
    """Write a DataFrame to BigQuery."""

    full_table_name = f"{project}.{dataset}.{table_name}"
    print(f"  Writing to BigQuery: {full_table_name}")
    print(f"  Write mode: {write_mode}")
    print(f"  Row count: {df.count()}")

    (
        df.write
        .format("bigquery")
        .option("table", full_table_name)
        .option("temporaryGcsBucket", f"{project}-vertica-staging")
        .mode(write_mode)
        .save()
    )


def migrate_table(
    spark: SparkSession,
    table_config: TableConfig,
    args: argparse.Namespace,
) -> dict:
    """Ingest a single table from Vertica to BigQuery."""

    table_name = table_config.name
    start_time = datetime.now()

    print(f"\n{'='*60}")
    print(f"Ingesting table: {table_name}")
    print(f"Started at: {start_time.isoformat()}")
    print(f"{'='*60}")

    try:
        # Read from Vertica
        df = read_from_vertica(
            spark=spark,
            table_name=table_name,
            host=args.vertica_host,
            port=args.vertica_port,
            database=args.vertica_db,
            user=args.vertica_user,
            password=args.vertica_password,
            schema=args.vertica_schema,
            staging_bucket=args.staging_bucket,
        )

        # Write to BigQuery
        write_to_bigquery(
            df=df,
            project=args.project,
            dataset=args.bq_dataset,
            table_name=table_name,
            write_mode=table_config.write_mode,
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            "table": table_name,
            "status": "success",
            "rows": df.count(),
            "duration_seconds": duration,
        }

        print(f"\nCompleted: {table_name}")
        print(f"Duration: {duration:.2f} seconds")

        return result

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            "table": table_name,
            "status": "failed",
            "error": str(e),
            "duration_seconds": duration,
        }

        print(f"\nFailed: {table_name}")
        print(f"Error: {e}")

        return result


def main() -> int:
    """Main entry point."""

    args = parse_args()

    # Print configuration
    print("\n" + "="*60)
    print("Vertica to BigQuery Ingestion")
    print("="*60)
    print(f"Vertica Host:    {args.vertica_host}:{args.vertica_port}")
    print(f"Vertica DB:      {args.vertica_db}")
    print(f"Vertica Schema:  {args.vertica_schema}")
    print(f"Vertica User:    {args.vertica_user}")
    print(f"Staging Bucket:  gs://{args.staging_bucket}")
    print(f"BigQuery:        {args.project}.{args.bq_dataset}")
    print("="*60)

    # Determine which tables to migrate
    if args.tables:
        tables_to_migrate = [
            tc for tc in TABLES_TO_MIGRATE
            if tc.name in args.tables
        ]
        if not tables_to_migrate:
            print(f"Error: No matching tables found for: {args.tables}")
            print(f"Available tables: {[tc.name for tc in TABLES_TO_MIGRATE]}")
            return 1
    else:
        tables_to_migrate = TABLES_TO_MIGRATE

    print(f"\nTables to migrate ({len(tables_to_migrate)}):")
    for tc in tables_to_migrate:
        print(f"  - {tc.name}")

    if args.dry_run:
        print("\n[DRY RUN] Exiting without executing ingestion.")
        return 0

    # Create Spark session
    spark = create_spark_session()

    # Migrate each table
    results = []
    for table_config in tables_to_migrate:
        result = migrate_table(spark, table_config, args)
        results.append(result)

    # Print summary
    print("\n" + "="*60)
    print("Ingestion Summary")
    print("="*60)

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    total_rows = sum(r.get("rows", 0) for r in results if r["status"] == "success")
    total_duration = sum(r["duration_seconds"] for r in results)

    print(f"Tables ingested: {success_count}/{len(results)}")
    print(f"Tables failed:   {failed_count}")
    print(f"Total rows:      {total_rows:,}")
    print(f"Total duration:  {total_duration:.2f} seconds")

    if failed_count > 0:
        print("\nFailed tables:")
        for r in results:
            if r["status"] == "failed":
                print(f"  - {r['table']}: {r['error']}")
        return 1

    print("\nIngestion completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
