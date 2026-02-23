#!/usr/bin/env python3
"""
Data Center Topology Generator for Demo

Generates realistic data center hardware topology data for demonstrating
Vertica-to-BigQuery ingestion with Dataproc and Spark.

Entity Tables (Nodes):
- locations: Data centers, regions, rows
- racks: Physical rack units
- hardware_assets: Servers, switches, storage
- nic_interfaces: NICs, ports (renamed from network_interfaces to avoid Vertica reserved name)
- applications: Deployed software

Relationship Tables (Edges):
- network_connections: Physical network links
- app_deployments: App-to-server mappings
- app_dependencies: App-to-app dependencies
- maintenance_events: Historical maintenance records

Target scale:
- 3 regions, 5 data centers
- ~500 racks
- ~6,000 servers
- ~200 applications
"""

import argparse
import logging
import random
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from tqdm import tqdm

# Configuration
LOG_FILE = "datacenter_topology_generator.log"
DEFAULT_PROJECT = None

# Topology configuration
REGIONS = [
    {"name": "us-west", "datacenters": ["US-West-1", "US-West-2"]},
    {"name": "us-east", "datacenters": ["US-East-1", "US-East-2"]},
    {"name": "eu-west", "datacenters": ["EU-West-1"]},
]
ROWS_PER_DC = 8
RACKS_PER_ROW = 12
SERVERS_PER_RACK = 12
SWITCHES_PER_ROW = 2
APPS_COUNT = 200

# Hardware configuration
SERVER_MODELS = [
    ("Dell", "PowerEdge R750", 64, 256, 8),
    ("Dell", "PowerEdge R650", 32, 128, 4),
    ("HP", "ProLiant DL380 Gen10", 48, 192, 6),
    ("HP", "ProLiant DL360 Gen10", 24, 64, 2),
    ("Supermicro", "SYS-620U-TNR", 64, 512, 16),
]

SWITCH_MODELS = [
    ("Cisco", "Nexus 9336C-FX2", 36),
    ("Cisco", "Catalyst 9500", 48),
    ("Arista", "7050X3", 32),
    ("Juniper", "QFX5220", 64),
]

APP_TYPES = ["web_service", "database", "message_queue", "cache", "api_gateway", "batch_job"]
APP_TECH_STACKS = ["Java/Spring", "Python/Django", "Node.js/Express", "Go", "Rust", ".NET Core"]
BUSINESS_DOMAINS = ["finance", "hr", "customer", "infrastructure", "analytics", "security"]
TEAM_NAMES = ["Platform", "Data", "Security", "DevOps", "Backend", "Frontend", "ML", "SRE"]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class Target(Enum):
    """Output target for generated data."""
    BIGQUERY = "bigquery"
    VERTICA = "vertica"
    SPANNER = "spanner"
    CSV = "csv"


@dataclass
class GenerationStats:
    """Statistics from data generation."""
    locations: int = 0
    racks: int = 0
    hardware_assets: int = 0
    nic_interfaces: int = 0
    applications: int = 0
    network_connections: int = 0
    app_deployments: int = 0
    app_dependencies: int = 0
    maintenance_events: int = 0


class DataCenterTopologyGenerator:
    """Generates realistic data center topology data."""

    def __init__(self, project_id: str, target: Target):
        self.project_id = project_id
        self.target = target
        self.stats = GenerationStats()

        # Data storage
        self.locations: List[Dict] = []
        self.racks: List[Dict] = []
        self.hardware_assets: List[Dict] = []
        self.nic_interfaces: List[Dict] = []
        self.applications: List[Dict] = []
        self.network_connections: List[Dict] = []
        self.app_deployments: List[Dict] = []
        self.app_dependencies: List[Dict] = []
        self.maintenance_events: List[Dict] = []

        # Lazy-loaded clients
        self._bq_client = None
        self._vertica_conn = None
        self._spanner_client = None

    @property
    def bq_client(self):
        """Lazy-load BigQuery client."""
        if self._bq_client is None:
            from google.cloud import bigquery
            self._bq_client = bigquery.Client(project=self.project_id)
        return self._bq_client

    @property
    def vertica_conn(self):
        """Lazy-load Vertica connection."""
        if self._vertica_conn is None:
            import vertica_python
            import os
            conn_info = {
                "host": os.environ.get("VERTICA_HOST", "localhost"),
                "port": int(os.environ.get("VERTICA_PORT", 5433)),
                "user": os.environ.get("VERTICA_USER", "dbadmin"),
                "password": os.environ.get("VERTICA_PASSWORD", ""),
                "database": os.environ.get("VERTICA_DATABASE", "demo"),
            }
            self._vertica_conn = vertica_python.connect(**conn_info)
        return self._vertica_conn

    @property
    def spanner_client(self):
        """Lazy-load Spanner client."""
        if self._spanner_client is None:
            from google.cloud import spanner
            self._spanner_client = spanner.Client(project=self.project_id)
        return self._spanner_client

    def _generate_uuid(self) -> str:
        """Generate a UUID string."""
        return str(uuid.uuid4())

    def _random_date(self, start_years_ago: int = 5, end_years_ago: int = 0) -> datetime:
        """Generate a random date within a range."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=start_years_ago * 365)
        end = now - timedelta(days=end_years_ago * 365)
        delta = end - start
        random_days = random.randint(0, delta.days)
        return start + timedelta(days=random_days)

    def _generate_hostname(self, dc: str, asset_type: str, index: int) -> str:
        """Generate a realistic hostname."""
        type_prefix = {"server": "srv", "switch": "sw", "storage": "nas"}
        prefix = type_prefix.get(asset_type, "dev")
        return f"{dc.lower().replace('-', '')}-{prefix}-{index:04d}"

    def generate_locations(self) -> None:
        """Generate location hierarchy (regions, DCs, rows)."""
        logger.info("Generating locations...")

        for region in tqdm(REGIONS, desc="Regions"):
            # Region
            region_id = self._generate_uuid()
            self.locations.append({
                "location_id": region_id,
                "location_type": "region",
                "name": region["name"],
                "parent_location_id": None,
                "geo_latitude": random.uniform(30.0, 50.0),
                "geo_longitude": random.uniform(-120.0, -70.0),
                "address": None,
                "timezone": "America/Los_Angeles" if "west" in region["name"] else "America/New_York",
                "created_at": self._random_date(5, 3),
                "updated_at": datetime.now(timezone.utc),
            })

            for dc_name in region["datacenters"]:
                # Data Center
                dc_id = self._generate_uuid()
                self.locations.append({
                    "location_id": dc_id,
                    "location_type": "data_center",
                    "name": dc_name,
                    "parent_location_id": region_id,
                    "geo_latitude": random.uniform(30.0, 50.0),
                    "geo_longitude": random.uniform(-120.0, -70.0),
                    "address": f"{random.randint(100, 9999)} Data Center Way, Tech City",
                    "timezone": "America/Los_Angeles" if "West" in dc_name else "America/New_York",
                    "created_at": self._random_date(4, 2),
                    "updated_at": datetime.now(timezone.utc),
                })

                for row_num in range(1, ROWS_PER_DC + 1):
                    # Row
                    row_id = self._generate_uuid()
                    self.locations.append({
                        "location_id": row_id,
                        "location_type": "row",
                        "name": f"{dc_name}-R{row_num:02d}",
                        "parent_location_id": dc_id,
                        "geo_latitude": None,
                        "geo_longitude": None,
                        "address": None,
                        "timezone": None,
                        "created_at": self._random_date(3, 1),
                        "updated_at": datetime.now(timezone.utc),
                    })

        self.stats.locations = len(self.locations)
        logger.info(f"Generated {self.stats.locations} locations")

    def generate_racks(self) -> None:
        """Generate racks within rows."""
        logger.info("Generating racks...")

        rows = [loc for loc in self.locations if loc["location_type"] == "row"]

        for row in tqdm(rows, desc="Rows"):
            for rack_num in range(1, RACKS_PER_ROW + 1):
                rack_id = self._generate_uuid()
                self.racks.append({
                    "rack_id": rack_id,
                    "location_id": row["location_id"],
                    "rack_name": f"{row['name']}-{rack_num:02d}",
                    "rack_units": 42,
                    "power_capacity_kw": random.choice([10.0, 15.0, 20.0]),
                    "cooling_zone": f"CRAC-{random.randint(1, 4)}",
                    "install_date": self._random_date(3, 1).date(),
                    "status": random.choices(["active", "planned", "decommissioning"], weights=[95, 3, 2])[0],
                    "created_at": self._random_date(3, 1),
                    "updated_at": datetime.now(timezone.utc),
                })

        self.stats.racks = len(self.racks)
        logger.info(f"Generated {self.stats.racks} racks")

    def generate_hardware_assets(self) -> None:
        """Generate servers and switches."""
        logger.info("Generating hardware assets...")

        server_index = 1
        switch_index = 1

        # Get DC names for hostnames
        dcs = [loc for loc in self.locations if loc["location_type"] == "data_center"]

        for rack in tqdm(self.racks, desc="Racks"):
            if rack["status"] == "planned":
                continue

            # Find the DC for this rack
            row = next((loc for loc in self.locations if loc["location_id"] == rack["location_id"]), None)
            dc = next((loc for loc in self.locations if loc["location_id"] == row["parent_location_id"]), None) if row else None
            dc_name = dc["name"] if dc else "UNKNOWN"

            # Generate servers
            num_servers = random.randint(8, SERVERS_PER_RACK)
            for i in range(num_servers):
                model = random.choice(SERVER_MODELS)
                purchase_date = self._random_date(4, 0)
                warranty_years = random.choice([3, 5])

                asset_id = self._generate_uuid()
                self.hardware_assets.append({
                    "asset_id": asset_id,
                    "asset_type": "server",
                    "rack_id": rack["rack_id"],
                    "rack_position_start": i * 3 + 1,
                    "rack_position_end": i * 3 + 2,
                    "hostname": self._generate_hostname(dc_name, "server", server_index),
                    "serial_number": f"SN{random.randint(100000, 999999)}",
                    "asset_tag": f"AT-{random.randint(10000, 99999)}",
                    "manufacturer": model[0],
                    "model": model[1],
                    "cpu_model": f"Intel Xeon Gold {random.choice([6248, 6258, 8280])}",
                    "cpu_cores": model[2],
                    "ram_gb": model[3],
                    "storage_tb": model[4],
                    "purchase_date": purchase_date.date(),
                    "warranty_expiry": (purchase_date + timedelta(days=warranty_years * 365)).date(),
                    "end_of_life_date": (purchase_date + timedelta(days=7 * 365)).date(),
                    "status": random.choices(["active", "maintenance", "decommissioned", "failed"], weights=[90, 5, 3, 2])[0],
                    "environment": random.choices(["production", "staging", "development", "disaster_recovery"], weights=[60, 20, 15, 5])[0],
                    "criticality_tier": random.choices([1, 2, 3, 4], weights=[10, 25, 40, 25])[0],
                    "owner_team": random.choice(TEAM_NAMES),
                    "cost_center": f"CC-{random.randint(1000, 9999)}",
                    "created_at": purchase_date,
                    "updated_at": datetime.now(timezone.utc),
                })
                server_index += 1

        # Generate network interfaces for all assets
        for asset in self.hardware_assets:
            num_interfaces = 4 if asset["asset_type"] == "server" else 48
            for i in range(num_interfaces):
                self.nic_interfaces.append({
                    "interface_id": self._generate_uuid(),
                    "asset_id": asset["asset_id"],
                    "interface_name": f"eth{i}" if asset["asset_type"] == "server" else f"Gi1/0/{i+1}",
                    "mac_address": ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)]),
                    "ip_address": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}" if i < 2 else None,
                    "subnet_mask": "255.255.255.0" if i < 2 else None,
                    "vlan_id": random.choice([100, 200, 300, 400, 500]) if i < 2 else None,
                    "speed_gbps": random.choice([10.0, 25.0, 100.0]),
                    "interface_type": random.choice(["ethernet", "fiber"]),
                    "status": "up" if asset["status"] == "active" else "down",
                    "created_at": asset["created_at"],
                    "updated_at": datetime.now(timezone.utc),
                })

        self.stats.hardware_assets = len(self.hardware_assets)
        self.stats.nic_interfaces = len(self.nic_interfaces)
        logger.info(f"Generated {self.stats.hardware_assets} hardware assets")
        logger.info(f"Generated {self.stats.nic_interfaces} NIC interfaces")

    def generate_applications(self) -> None:
        """Generate applications."""
        logger.info("Generating applications...")

        for i in tqdm(range(APPS_COUNT), desc="Applications"):
            app_type = random.choice(APP_TYPES)
            domain = random.choice(BUSINESS_DOMAINS)

            self.applications.append({
                "app_id": self._generate_uuid(),
                "app_name": f"{domain.capitalize()}{app_type.replace('_', ' ').title().replace(' ', '')}{i+1}",
                "app_code": f"{domain[:3].upper()}{i+1:03d}",
                "description": f"A {app_type.replace('_', ' ')} for {domain} operations",
                "app_type": app_type,
                "technology_stack": random.choice(APP_TECH_STACKS),
                "business_domain": domain,
                "criticality_tier": random.choices([1, 2, 3, 4], weights=[15, 30, 35, 20])[0],
                "data_classification": random.choices(["public", "internal", "confidential", "restricted"], weights=[5, 50, 35, 10])[0],
                "owner_team": random.choice(TEAM_NAMES),
                "technical_contact": f"{random.choice(['alice', 'bob', 'carol', 'dave'])}@example.com",
                "business_contact": f"{random.choice(['exec1', 'exec2', 'exec3'])}@example.com",
                "status": random.choices(["active", "deprecated", "planned", "retired"], weights=[85, 8, 5, 2])[0],
                "go_live_date": self._random_date(4, 1).date(),
                "sunset_date": None,
                "created_at": self._random_date(4, 1),
                "updated_at": datetime.now(timezone.utc),
            })

        self.stats.applications = len(self.applications)
        logger.info(f"Generated {self.stats.applications} applications")

    def generate_relationships(self) -> None:
        """Generate relationship tables."""
        logger.info("Generating relationships...")

        active_servers = [a for a in self.hardware_assets if a["asset_type"] == "server" and a["status"] == "active"]
        active_apps = [a for a in self.applications if a["status"] == "active"]

        # App deployments
        logger.info("Generating app deployments...")
        for app in tqdm(active_apps, desc="App Deployments"):
            num_servers = random.randint(2, 8)
            servers = random.sample(active_servers, min(num_servers, len(active_servers)))
            for i, server in enumerate(servers):
                self.app_deployments.append({
                    "deployment_id": self._generate_uuid(),
                    "app_id": app["app_id"],
                    "asset_id": server["asset_id"],
                    "deployment_role": "primary" if i == 0 else random.choice(["replica", "standby", "worker"]),
                    "instance_count": random.randint(1, 4),
                    "port_number": random.choice([8080, 8443, 3000, 5000, 9000]),
                    "resource_cpu_cores": random.randint(2, 16),
                    "resource_ram_gb": random.randint(4, 32),
                    "deployment_date": self._random_date(2, 0).date(),
                    "status": "running",
                    "created_at": self._random_date(2, 0),
                    "updated_at": datetime.now(timezone.utc),
                })

        # App dependencies
        logger.info("Generating app dependencies...")
        for app in tqdm(active_apps, desc="App Dependencies"):
            num_deps = random.randint(0, 5)
            potential_deps = [a for a in active_apps if a["app_id"] != app["app_id"]]
            deps = random.sample(potential_deps, min(num_deps, len(potential_deps)))
            for dep in deps:
                self.app_dependencies.append({
                    "dependency_id": self._generate_uuid(),
                    "app_id": app["app_id"],
                    "depends_on_app_id": dep["app_id"],
                    "dependency_type": random.choice(["database", "api", "message_queue", "cache", "authentication"]),
                    "protocol": random.choice(["tcp", "http", "https", "grpc", "amqp"]),
                    "port_number": random.choice([5432, 3306, 6379, 5672, 443, 8080]),
                    "is_critical": random.choice([True, False]),
                    "data_flow_direction": random.choice(["inbound", "outbound", "bidirectional"]),
                    "created_at": self._random_date(2, 0),
                    "updated_at": datetime.now(timezone.utc),
                })

        # Network connections (simplified - connect servers within same rack)
        logger.info("Generating network connections...")
        interfaces_by_asset = {}
        for iface in self.nic_interfaces:
            if iface["asset_id"] not in interfaces_by_asset:
                interfaces_by_asset[iface["asset_id"]] = []
            interfaces_by_asset[iface["asset_id"]].append(iface)

        for rack in tqdm(self.racks[:100], desc="Network Connections"):  # Limit for performance
            rack_servers = [a for a in self.hardware_assets if a["rack_id"] == rack["rack_id"] and a["asset_type"] == "server"]
            for i, server in enumerate(rack_servers[:-1]):
                next_server = rack_servers[i + 1]
                src_ifaces = interfaces_by_asset.get(server["asset_id"], [])
                dst_ifaces = interfaces_by_asset.get(next_server["asset_id"], [])
                if src_ifaces and dst_ifaces:
                    self.network_connections.append({
                        "connection_id": self._generate_uuid(),
                        "source_interface_id": src_ifaces[0]["interface_id"],
                        "target_interface_id": dst_ifaces[0]["interface_id"],
                        "connection_type": "physical_cable",
                        "bandwidth_gbps": 10.0,
                        "cable_type": random.choice(["cat6", "fiber_sm"]),
                        "status": "active",
                        "created_at": self._random_date(2, 0),
                        "updated_at": datetime.now(timezone.utc),
                    })

        # Maintenance events
        logger.info("Generating maintenance events...")
        for asset in tqdm(random.sample(self.hardware_assets, min(500, len(self.hardware_assets))), desc="Maintenance Events"):
            num_events = random.randint(1, 5)
            for _ in range(num_events):
                started = self._random_date(2, 0)
                resolved = started + timedelta(hours=random.randint(1, 48))
                self.maintenance_events.append({
                    "event_id": self._generate_uuid(),
                    "asset_id": asset["asset_id"],
                    "event_type": random.choice(["hardware_failure", "firmware_update", "replacement", "inspection", "upgrade"]),
                    "severity": random.choice(["critical", "major", "minor", "informational"]),
                    "description": "Scheduled maintenance event",
                    "started_at": started,
                    "resolved_at": resolved,
                    "downtime_minutes": int((resolved - started).total_seconds() / 60),
                    "root_cause": random.choice(["hardware", "software", "network", "power", "cooling", None]),
                    "technician": f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe', 'Johnson'])}",
                    "ticket_number": f"TKT-{random.randint(10000, 99999)}",
                    "created_at": started,
                })

        self.stats.network_connections = len(self.network_connections)
        self.stats.app_deployments = len(self.app_deployments)
        self.stats.app_dependencies = len(self.app_dependencies)
        self.stats.maintenance_events = len(self.maintenance_events)

        logger.info(f"Generated {self.stats.app_deployments} app deployments")
        logger.info(f"Generated {self.stats.app_dependencies} app dependencies")
        logger.info(f"Generated {self.stats.network_connections} network connections")
        logger.info(f"Generated {self.stats.maintenance_events} maintenance events")

    def generate_all(self) -> GenerationStats:
        """Generate all data."""
        logger.info("Starting data generation...")

        self.generate_locations()
        self.generate_racks()
        self.generate_hardware_assets()
        self.generate_applications()
        self.generate_relationships()

        logger.info("Data generation complete!")
        return self.stats

    def load_to_bigquery(self, dataset_id: str = "data_center_topology") -> None:
        """Load generated data to BigQuery."""
        from google.cloud import bigquery

        logger.info(f"Loading data to BigQuery dataset: {dataset_id}")

        tables = {
            "locations": self.locations,
            "racks": self.racks,
            "hardware_assets": self.hardware_assets,
            "nic_interfaces": self.nic_interfaces,
            "applications": self.applications,
            "network_connections": self.network_connections,
            "app_deployments": self.app_deployments,
            "app_dependencies": self.app_dependencies,
            "maintenance_events": self.maintenance_events,
        }

        for table_name, data in tqdm(tables.items(), desc="Loading to BigQuery"):
            if not data:
                logger.warning(f"No data for {table_name}, skipping")
                continue

            table_ref = f"{self.project_id}.{dataset_id}.{table_name}"

            # Convert datetime objects to strings for JSON serialization
            json_rows = []
            for row in data:
                json_row = {}
                for k, v in row.items():
                    if isinstance(v, datetime):
                        json_row[k] = v.isoformat()
                    elif hasattr(v, 'isoformat'):  # date objects
                        json_row[k] = v.isoformat()
                    else:
                        json_row[k] = v
                json_rows.append(json_row)

            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                autodetect=True,
            )

            job = self.bq_client.load_table_from_json(
                json_rows,
                table_ref,
                job_config=job_config,
            )
            job.result()  # Wait for completion

            logger.info(f"Loaded {len(data)} rows to {table_name}")

        logger.info("BigQuery load complete!")

    def load_to_vertica(self) -> None:
        """Load generated data to Vertica."""
        logger.info("Loading data to Vertica...")

        # Create tables and load data
        tables = {
            "locations": self.locations,
            "racks": self.racks,
            "hardware_assets": self.hardware_assets,
            "nic_interfaces": self.nic_interfaces,
            "applications": self.applications,
            "network_connections": self.network_connections,
            "app_deployments": self.app_deployments,
            "app_dependencies": self.app_dependencies,
            "maintenance_events": self.maintenance_events,
        }

        cursor = self.vertica_conn.cursor()

        for table_name, data in tqdm(tables.items(), desc="Loading to Vertica"):
            if not data:
                logger.warning(f"No data for {table_name}, skipping")
                continue

            # Drop and create table
            columns = list(data[0].keys())
            col_defs = ", ".join([f"{col} VARCHAR(65000)" for col in columns])

            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute(f"CREATE TABLE {table_name} ({col_defs})")

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                placeholders = ", ".join(["%s"] * len(columns))
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                for row in batch:
                    values = []
                    for col in columns:
                        v = row[col]
                        if isinstance(v, datetime):
                            values.append(v.isoformat())
                        elif hasattr(v, 'isoformat'):
                            values.append(v.isoformat())
                        elif v is None:
                            values.append(None)
                        else:
                            values.append(str(v))
                    cursor.execute(insert_sql, values)

            self.vertica_conn.commit()
            logger.info(f"Loaded {len(data)} rows to {table_name}")

        logger.info("Vertica load complete!")

    def load_to_spanner(
        self,
        instance_id: str = "data-center-graph",
        database_id: str = "topology",
    ) -> None:
        """Load generated data to Spanner."""
        logger.info(f"Loading data to Spanner: {instance_id}/{database_id}")

        instance = self.spanner_client.instance(instance_id)
        database = instance.database(database_id)

        tables = {
            "locations": self.locations,
            "racks": self.racks,
            "hardware_assets": self.hardware_assets,
            "nic_interfaces": self.nic_interfaces,
            "applications": self.applications,
            "network_connections": self.network_connections,
            "app_deployments": self.app_deployments,
            "app_dependencies": self.app_dependencies,
            "maintenance_events": self.maintenance_events,
        }

        for table_name, data in tqdm(tables.items(), desc="Loading to Spanner"):
            if not data:
                logger.warning(f"No data for {table_name}, skipping")
                continue

            columns = list(data[0].keys())

            # Convert to Spanner-compatible values
            rows = []
            for row in data:
                values = []
                for col in columns:
                    v = row[col]
                    # Spanner client handles datetime and date natively
                    values.append(v)
                rows.append(values)

            # Batch insert (500 rows per batch for Spanner)
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                with database.batch() as transaction:
                    transaction.insert(
                        table=table_name,
                        columns=columns,
                        values=batch,
                    )

            logger.info(f"Loaded {len(data)} rows to {table_name}")

        logger.info("Spanner load complete!")

    def cleanup_bigquery(self, dataset_id: str = "data_center_topology") -> None:
        """Delete all tables in BigQuery dataset."""
        logger.info(f"Cleaning up BigQuery dataset: {dataset_id}")

        tables = self.bq_client.list_tables(f"{self.project_id}.{dataset_id}")
        for table in tables:
            self.bq_client.delete_table(table.reference)
            logger.info(f"Deleted table: {table.table_id}")

        logger.info("Cleanup complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Generate data center topology data for Vertica-to-BigQuery ingestion demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID",
    )

    parser.add_argument(
        "--target",
        choices=["bigquery", "vertica", "spanner"],
        default="bigquery",
        help="Target database (default: bigquery)",
    )

    parser.add_argument(
        "--dataset",
        default="data_center_topology",
        help="BigQuery dataset ID (default: data_center_topology)",
    )

    parser.add_argument(
        "--spanner-instance",
        default="data-center-graph",
        help="Spanner instance ID (default: data-center-graph)",
    )

    parser.add_argument(
        "--spanner-database",
        default="topology",
        help="Spanner database ID (default: topology)",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete existing data before loading",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate data but don't load to database",
    )

    args = parser.parse_args()

    target_map = {
        "bigquery": Target.BIGQUERY,
        "vertica": Target.VERTICA,
        "spanner": Target.SPANNER,
    }
    target = target_map[args.target]

    logger.info(f"Starting data center topology generation")
    logger.info(f"Project: {args.project}")
    logger.info(f"Target: {args.target}")

    generator = DataCenterTopologyGenerator(args.project, target)

    # Generate data
    stats = generator.generate_all()

    print("\n" + "=" * 60)
    print("Generation Statistics")
    print("=" * 60)
    print(f"  Locations:           {stats.locations:,}")
    print(f"  Racks:               {stats.racks:,}")
    print(f"  Hardware Assets:     {stats.hardware_assets:,}")
    print(f"  NIC Interfaces:      {stats.nic_interfaces:,}")
    print(f"  Applications:        {stats.applications:,}")
    print(f"  Network Connections: {stats.network_connections:,}")
    print(f"  App Deployments:     {stats.app_deployments:,}")
    print(f"  App Dependencies:    {stats.app_dependencies:,}")
    print(f"  Maintenance Events:  {stats.maintenance_events:,}")
    print("=" * 60)

    if args.dry_run:
        logger.info("Dry run - skipping database load")
        return

    # Load to target
    if target == Target.BIGQUERY:
        if args.cleanup:
            generator.cleanup_bigquery(args.dataset)
        generator.load_to_bigquery(args.dataset)
    elif target == Target.VERTICA:
        generator.load_to_vertica()
    elif target == Target.SPANNER:
        generator.load_to_spanner(args.spanner_instance, args.spanner_database)

    logger.info("Done!")


if __name__ == "__main__":
    main()
