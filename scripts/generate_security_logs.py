#!/usr/bin/env python3
"""
GCP Security Log Generator for Demo

Generates realistic GCP audit logs by performing actual GCP API operations.
Designed to populate the security_logs dataset for demonstrating Gemini AI
threat classification and BigQuery security analytics.

Operations are organized by MITRE ATT&CK categories:
- Reconnaissance (TA0043): Resource enumeration, policy viewing
- Privilege Escalation (TA0004): IAM changes, service account operations
- Defense Evasion (TA0005): Logging sink modifications
- Persistence (TA0003): Service account creation
- Lateral Movement (TA0008): Cross-service access patterns
"""

import argparse
import logging
import random
import string
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from tqdm import tqdm

# Google Cloud imports
from google.api_core import exceptions as google_exceptions
from google.cloud import storage
from google.cloud import logging as cloud_logging
from google.cloud.iam_admin_v1 import IAMClient, types as iam_types
from google.cloud.compute_v1 import InstancesClient, FirewallsClient, ZonesClient
from google.cloud.resourcemanager_v3 import ProjectsClient
from google.iam.v1 import iam_policy_pb2, policy_pb2

# Configuration
LOG_FILE = "security_logs_generator.log"
DEMO_PREFIX = "demo-"
DEFAULT_DELAY = 2.0  # seconds between operations
SUSPICIOUS_REGIONS = ["asia-east1", "southamerica-east1", "europe-north1"]
NORMAL_REGION = "us-central1"

# MITRE ATT&CK Category Mapping
MITRE_CATEGORIES = {
    "recon": "TA0043 - Reconnaissance",
    "privesc": "TA0004 - Privilege Escalation",
    "defense-evasion": "TA0005 - Defense Evasion",
    "persistence": "TA0003 - Persistence",
    "lateral-movement": "TA0008 - Lateral Movement",
}

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


class Mode(Enum):
    """Operation mode for the generator."""
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"


class Scenario(Enum):
    """Available scenarios to run."""
    RECON = "recon"
    PRIVESC = "privesc"
    DEFENSE_EVASION = "defense-evasion"
    PERSISTENCE = "persistence"
    LATERAL_MOVEMENT = "lateral-movement"
    ALL = "all"


@dataclass
class OperationResult:
    """Result of a single GCP operation."""
    operation: str
    success: bool
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    """Aggregate result of running a scenario."""
    scenario: str
    mitre_category: str
    total_operations: int
    successful: int
    failed: int
    operations: List[OperationResult] = field(default_factory=list)


class SecurityLogGenerator:
    """
    Generates realistic GCP audit logs by executing actual API operations.

    All created resources use 'demo-' prefix for easy identification and cleanup.
    Supports both 'normal' and 'suspicious' operation modes.

    Attributes:
        project_id: GCP project ID
        mode: Operation mode (normal or suspicious)
        dry_run: If True, print actions without executing
        delay: Seconds to wait between operations
    """

    def __init__(
        self,
        project_id: str,
        mode: Mode = Mode.NORMAL,
        dry_run: bool = False,
        delay: float = DEFAULT_DELAY,
    ) -> None:
        """
        Initialize the security log generator.

        Args:
            project_id: GCP project ID
            mode: Operation mode (normal or suspicious)
            dry_run: If True, print actions without executing
            delay: Seconds to wait between operations
        """
        self.project_id = project_id
        self.mode = mode
        self.dry_run = dry_run
        self.delay = delay if mode == Mode.NORMAL else delay / 2  # Faster in suspicious mode

        # Lazy-loaded clients
        self._iam_client: Optional[IAMClient] = None
        self._compute_instances_client: Optional[InstancesClient] = None
        self._compute_firewalls_client: Optional[FirewallsClient] = None
        self._compute_zones_client: Optional[ZonesClient] = None
        self._storage_client: Optional[storage.Client] = None
        self._logging_client: Optional[cloud_logging.Client] = None
        self._projects_client: Optional[ProjectsClient] = None

    @property
    def iam_client(self) -> IAMClient:
        """Lazy-load IAM admin client."""
        if self._iam_client is None:
            self._iam_client = IAMClient()
        return self._iam_client

    @property
    def compute_instances_client(self) -> InstancesClient:
        """Lazy-load Compute Engine instances client."""
        if self._compute_instances_client is None:
            self._compute_instances_client = InstancesClient()
        return self._compute_instances_client

    @property
    def compute_firewalls_client(self) -> FirewallsClient:
        """Lazy-load Compute Engine firewalls client."""
        if self._compute_firewalls_client is None:
            self._compute_firewalls_client = FirewallsClient()
        return self._compute_firewalls_client

    @property
    def compute_zones_client(self) -> ZonesClient:
        """Lazy-load Compute Engine zones client."""
        if self._compute_zones_client is None:
            self._compute_zones_client = ZonesClient()
        return self._compute_zones_client

    @property
    def storage_client(self) -> storage.Client:
        """Lazy-load Cloud Storage client."""
        if self._storage_client is None:
            self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client

    @property
    def logging_client(self) -> cloud_logging.Client:
        """Lazy-load Cloud Logging client."""
        if self._logging_client is None:
            self._logging_client = cloud_logging.Client(project=self.project_id)
        return self._logging_client

    @property
    def projects_client(self) -> ProjectsClient:
        """Lazy-load Resource Manager projects client."""
        if self._projects_client is None:
            self._projects_client = ProjectsClient()
        return self._projects_client

    def _get_region(self) -> str:
        """Get region based on mode (suspicious uses unusual regions)."""
        if self.mode == Mode.SUSPICIOUS:
            return random.choice(SUSPICIOUS_REGIONS)
        return NORMAL_REGION

    def _generate_unique_name(self, prefix: str, max_length: int = 30) -> str:
        """Generate unique resource name with demo- prefix and timestamp.

        Args:
            prefix: Short prefix for the resource type
            max_length: Maximum allowed length (default 30 for service accounts)

        Returns:
            Unique name within max_length characters
        """
        timestamp = datetime.now().strftime("%m%d%H%M")  # Shorter: MMDDHHMM (8 chars)
        random_suffix = "".join(random.choices(string.ascii_lowercase, k=4))
        name = f"{DEMO_PREFIX}{prefix}-{timestamp}-{random_suffix}"

        # Truncate if needed (keep prefix and suffix, trim middle)
        if len(name) > max_length:
            name = name[:max_length]

        return name

    def _execute_operation(
        self,
        operation_name: str,
        operation_func: Callable[[], Any],
        description: str,
    ) -> OperationResult:
        """
        Execute an operation with logging, error handling, and delay.

        Args:
            operation_name: Name for logging
            operation_func: Callable that performs the operation
            description: Human-readable description

        Returns:
            OperationResult with success/failure info
        """
        timestamp = datetime.now(timezone.utc)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {description}")
            return OperationResult(
                operation=operation_name,
                success=True,
                message="Dry run - not executed",
                timestamp=timestamp,
            )

        try:
            logger.info(f"Executing: {description}")
            result = operation_func()

            # Sleep between operations
            time.sleep(self.delay)

            return OperationResult(
                operation=operation_name,
                success=True,
                message="Completed successfully",
                timestamp=timestamp,
                details={"result": str(result)[:200] if result else "OK"},
            )

        except google_exceptions.PermissionDenied as e:
            logger.warning(f"Permission denied for {operation_name}: {e}")
            return OperationResult(
                operation=operation_name,
                success=False,
                message=f"Permission denied: {e}",
                timestamp=timestamp,
            )

        except google_exceptions.NotFound as e:
            logger.warning(f"Resource not found for {operation_name}: {e}")
            return OperationResult(
                operation=operation_name,
                success=False,
                message=f"Not found: {e}",
                timestamp=timestamp,
            )

        except google_exceptions.AlreadyExists as e:
            logger.info(f"Resource already exists for {operation_name}: {e}")
            return OperationResult(
                operation=operation_name,
                success=True,
                message=f"Already exists: {e}",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}", exc_info=True)
            return OperationResult(
                operation=operation_name,
                success=False,
                message=f"Error: {e}",
                timestamp=timestamp,
            )

    # =========================================================================
    # RECONNAISSANCE SCENARIO (MITRE ATT&CK: TA0043)
    # =========================================================================

    def run_recon_scenario(self) -> ScenarioResult:
        """
        Execute reconnaissance operations.

        Operations:
        1. List all IAM service accounts
        2. Get project IAM policy
        3. List GCS buckets
        4. List Compute Engine instances
        5. List firewall rules
        6. List logging sinks

        Returns:
            ScenarioResult with operation outcomes
        """
        logger.info("=" * 60)
        logger.info(f"Running scenario: recon ({MITRE_CATEGORIES['recon']})")
        logger.info("=" * 60)

        operations = [
            ("list_service_accounts", self._list_service_accounts, "List all service accounts"),
            ("get_iam_policy", self._get_project_iam_policy, "Get project IAM policy"),
            ("list_buckets", self._list_gcs_buckets, "List GCS buckets"),
            ("list_instances", self._list_compute_instances, "List Compute Engine instances"),
            ("list_firewalls", self._list_firewall_rules, "List firewall rules"),
            ("list_sinks", self._list_logging_sinks, "List logging sinks"),
        ]

        results = []
        for op_name, op_func, op_desc in tqdm(operations, desc="Recon", unit="op"):
            result = self._execute_operation(op_name, op_func, op_desc)
            results.append(result)

        return ScenarioResult(
            scenario="recon",
            mitre_category=MITRE_CATEGORIES["recon"],
            total_operations=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            operations=results,
        )

    def _list_service_accounts(self) -> List[str]:
        """List all service accounts in the project."""
        request = iam_types.ListServiceAccountsRequest(
            name=f"projects/{self.project_id}"
        )
        accounts = list(self.iam_client.list_service_accounts(request=request))
        logger.info(f"  Found {len(accounts)} service accounts")
        return [sa.email for sa in accounts]

    def _get_project_iam_policy(self) -> Dict[str, Any]:
        """Get the IAM policy for the project."""
        request = iam_policy_pb2.GetIamPolicyRequest(
            resource=f"projects/{self.project_id}"
        )
        policy = self.projects_client.get_iam_policy(request=request)
        logger.info(f"  Found {len(policy.bindings)} IAM bindings")
        return {"bindings_count": len(policy.bindings)}

    def _list_gcs_buckets(self) -> List[str]:
        """List all GCS buckets in the project."""
        buckets = list(self.storage_client.list_buckets())
        logger.info(f"  Found {len(buckets)} buckets")
        return [b.name for b in buckets]

    def _list_compute_instances(self) -> List[str]:
        """List Compute Engine instances across all zones."""
        instances = []
        for zone in self.compute_zones_client.list(project=self.project_id):
            zone_instances = list(
                self.compute_instances_client.list(
                    project=self.project_id, zone=zone.name
                )
            )
            instances.extend(zone_instances)
        logger.info(f"  Found {len(instances)} instances")
        return [i.name for i in instances]

    def _list_firewall_rules(self) -> List[str]:
        """List all firewall rules in the project."""
        rules = list(self.compute_firewalls_client.list(project=self.project_id))
        logger.info(f"  Found {len(rules)} firewall rules")
        return [r.name for r in rules]

    def _list_logging_sinks(self) -> List[str]:
        """List all logging sinks in the project."""
        sinks = list(self.logging_client.list_sinks())
        logger.info(f"  Found {len(sinks)} logging sinks")
        return [s.name for s in sinks]

    # =========================================================================
    # PRIVILEGE ESCALATION SCENARIO (MITRE ATT&CK: TA0004)
    # =========================================================================

    def run_privesc_scenario(self) -> ScenarioResult:
        """
        Execute privilege escalation operations.

        Operations:
        1. Create a demo service account
        2. List service account keys
        3. Get service account IAM policy

        Note: Actually granting roles requires elevated permissions,
        so we focus on operations that generate useful audit logs.

        Returns:
            ScenarioResult with operation outcomes
        """
        logger.info("=" * 60)
        logger.info(f"Running scenario: privesc ({MITRE_CATEGORIES['privesc']})")
        logger.info("=" * 60)

        # Generate unique service account name
        sa_id = self._generate_unique_name("sa")

        operations = [
            (
                "create_service_account",
                lambda: self._create_service_account(sa_id),
                f"Create service account: {sa_id}",
            ),
            (
                "list_sa_keys",
                lambda: self._list_service_account_keys(
                    f"{sa_id}@{self.project_id}.iam.gserviceaccount.com"
                ),
                f"List keys for service account: {sa_id}",
            ),
            (
                "get_sa_iam_policy",
                lambda: self._get_service_account_iam_policy(
                    f"{sa_id}@{self.project_id}.iam.gserviceaccount.com"
                ),
                f"Get IAM policy for service account: {sa_id}",
            ),
        ]

        results = []
        for op_name, op_func, op_desc in tqdm(operations, desc="PrivEsc", unit="op"):
            result = self._execute_operation(op_name, op_func, op_desc)
            results.append(result)

        return ScenarioResult(
            scenario="privesc",
            mitre_category=MITRE_CATEGORIES["privesc"],
            total_operations=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            operations=results,
        )

    def _create_service_account(self, account_id: str) -> str:
        """Create a new service account with demo- prefix."""
        request = iam_types.CreateServiceAccountRequest(
            name=f"projects/{self.project_id}",
            account_id=account_id,
            service_account=iam_types.ServiceAccount(
                display_name=f"Demo security log generator - {account_id}",
                description="Created by generate_security_logs.py for demo purposes",
            ),
        )
        sa = self.iam_client.create_service_account(request=request)
        logger.info(f"  Created service account: {sa.email}")
        return sa.email

    def _list_service_account_keys(self, sa_email: str) -> List[str]:
        """List keys for a service account."""
        request = iam_types.ListServiceAccountKeysRequest(
            name=f"projects/{self.project_id}/serviceAccounts/{sa_email}"
        )
        response = self.iam_client.list_service_account_keys(request=request)
        keys = response.keys
        logger.info(f"  Found {len(keys)} keys")
        return [k.name for k in keys]

    def _get_service_account_iam_policy(self, sa_email: str) -> Dict[str, Any]:
        """Get IAM policy for a service account."""
        request = iam_policy_pb2.GetIamPolicyRequest(
            resource=f"projects/{self.project_id}/serviceAccounts/{sa_email}"
        )
        policy = self.iam_client.get_iam_policy(request=request)
        logger.info(f"  Found {len(policy.bindings)} bindings")
        return {"bindings_count": len(policy.bindings)}

    # =========================================================================
    # DEFENSE EVASION SCENARIO (MITRE ATT&CK: TA0005)
    # =========================================================================

    def run_defense_evasion_scenario(self) -> ScenarioResult:
        """
        Execute defense evasion operations.

        Operations:
        1. List existing sinks (reconnaissance)
        2. Create a demo logging sink
        3. Update the sink's filter
        4. Delete the demo sink

        Returns:
            ScenarioResult with operation outcomes
        """
        logger.info("=" * 60)
        logger.info(f"Running scenario: defense-evasion ({MITRE_CATEGORIES['defense-evasion']})")
        logger.info("=" * 60)

        sink_name = self._generate_unique_name("sink")

        operations = [
            ("list_sinks", self._list_logging_sinks, "List existing logging sinks"),
            (
                "create_sink",
                lambda: self._create_logging_sink(sink_name),
                f"Create logging sink: {sink_name}",
            ),
            (
                "update_sink",
                lambda: self._update_logging_sink(sink_name),
                f"Update logging sink filter: {sink_name}",
            ),
            (
                "delete_sink",
                lambda: self._delete_logging_sink(sink_name),
                f"Delete logging sink: {sink_name}",
            ),
        ]

        results = []
        for op_name, op_func, op_desc in tqdm(operations, desc="Defense Evasion", unit="op"):
            result = self._execute_operation(op_name, op_func, op_desc)
            results.append(result)

        return ScenarioResult(
            scenario="defense-evasion",
            mitre_category=MITRE_CATEGORIES["defense-evasion"],
            total_operations=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            operations=results,
        )

    def _create_logging_sink(self, sink_name: str) -> str:
        """Create a logging sink that exports to a bucket."""
        # Create sink that exports to the existing iceberg bucket
        sink = self.logging_client.sink(
            sink_name,
            filter_='logName:"cloudaudit.googleapis.com"',
            destination=f"storage.googleapis.com/{self.project_id}-security-logs-iceberg",
        )
        sink.create(unique_writer_identity=True)
        logger.info(f"  Created sink: {sink_name}")
        return sink_name

    def _update_logging_sink(self, sink_name: str) -> str:
        """Update a logging sink's filter (suspicious: exclude audit logs)."""
        sink = self.logging_client.sink(sink_name)
        sink.reload()
        # Change filter to exclude some logs (suspicious behavior)
        sink.filter_ = 'logName:"cloudaudit.googleapis.com" AND severity>=WARNING'
        sink.update(unique_writer_identity=True)
        logger.info(f"  Updated sink filter: {sink_name}")
        return sink_name

    def _delete_logging_sink(self, sink_name: str) -> str:
        """Delete a logging sink."""
        sink = self.logging_client.sink(sink_name)
        sink.delete()
        logger.info(f"  Deleted sink: {sink_name}")
        return sink_name

    # =========================================================================
    # PERSISTENCE SCENARIO (MITRE ATT&CK: TA0003)
    # =========================================================================

    def run_persistence_scenario(self) -> ScenarioResult:
        """
        Execute persistence operations.

        Operations:
        1. Create multiple demo service accounts
        2. List service account keys for each
        3. Create a demo GCS bucket

        In suspicious mode:
        - Creates more service accounts
        - Uses unusual bucket location

        Returns:
            ScenarioResult with operation outcomes
        """
        logger.info("=" * 60)
        logger.info(f"Running scenario: persistence ({MITRE_CATEGORIES['persistence']})")
        logger.info("=" * 60)

        # Create multiple service accounts in suspicious mode
        num_accounts = 3 if self.mode == Mode.SUSPICIOUS else 1
        operations = []

        for i in range(num_accounts):
            sa_id = self._generate_unique_name(f"persist{i}")
            operations.append((
                f"create_sa_{i}",
                lambda sid=sa_id: self._create_service_account(sid),
                f"Create persistence service account: {sa_id}",
            ))

        # Create bucket in region based on mode
        bucket_name = self._generate_unique_name("bucket")
        location = self._get_region()
        operations.append((
            "create_bucket",
            lambda: self._create_gcs_bucket(bucket_name, location),
            f"Create GCS bucket: {bucket_name} in {location}",
        ))

        results = []
        for op_name, op_func, op_desc in tqdm(operations, desc="Persistence", unit="op"):
            result = self._execute_operation(op_name, op_func, op_desc)
            results.append(result)

        return ScenarioResult(
            scenario="persistence",
            mitre_category=MITRE_CATEGORIES["persistence"],
            total_operations=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            operations=results,
        )

    def _create_gcs_bucket(self, bucket_name: str, location: str) -> str:
        """Create a GCS bucket."""
        bucket = self.storage_client.bucket(bucket_name)
        bucket.storage_class = "STANDARD"
        self.storage_client.create_bucket(bucket, location=location)
        logger.info(f"  Created bucket: {bucket_name} in {location}")
        return bucket_name

    # =========================================================================
    # LATERAL MOVEMENT SCENARIO (MITRE ATT&CK: TA0008)
    # =========================================================================

    def run_lateral_movement_scenario(self) -> ScenarioResult:
        """
        Execute lateral movement operations.

        Operations:
        1. List resources across multiple services rapidly
        2. Access storage in multiple locations
        3. Enumerate compute instances across zones

        In suspicious mode:
        - Rapid-fire enumeration
        - Unusual access patterns

        Returns:
            ScenarioResult with operation outcomes
        """
        logger.info("=" * 60)
        logger.info(f"Running scenario: lateral-movement ({MITRE_CATEGORIES['lateral-movement']})")
        logger.info("=" * 60)

        operations = [
            ("enum_storage", self._list_gcs_buckets, "Enumerate Cloud Storage"),
            ("enum_compute", self._list_compute_instances, "Enumerate Compute Engine"),
            ("enum_iam", self._list_service_accounts, "Enumerate IAM accounts"),
            ("enum_logging", self._list_logging_sinks, "Enumerate Logging sinks"),
            ("enum_firewalls", self._list_firewall_rules, "Enumerate firewall rules"),
        ]

        # In suspicious mode, repeat enumeration (rapid scanning)
        if self.mode == Mode.SUSPICIOUS:
            operations = operations * 2

        results = []
        for op_name, op_func, op_desc in tqdm(operations, desc="Lateral Movement", unit="op"):
            result = self._execute_operation(op_name, op_func, op_desc)
            results.append(result)

        return ScenarioResult(
            scenario="lateral-movement",
            mitre_category=MITRE_CATEGORIES["lateral-movement"],
            total_operations=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            operations=results,
        )

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self) -> ScenarioResult:
        """
        Remove all resources created by this script.

        Finds and deletes:
        - Service accounts with demo- prefix
        - GCS buckets with demo- prefix
        - Logging sinks with demo- prefix

        Returns:
            ScenarioResult with cleanup outcomes
        """
        logger.info("=" * 60)
        logger.info("Running cleanup: Removing all demo- resources")
        logger.info("=" * 60)

        results = []

        # Delete demo service accounts
        logger.info("Finding demo service accounts...")
        try:
            request = iam_types.ListServiceAccountsRequest(
                name=f"projects/{self.project_id}"
            )
            for sa in self.iam_client.list_service_accounts(request=request):
                if sa.email.startswith(DEMO_PREFIX) or f"/{DEMO_PREFIX}" in sa.email:
                    result = self._execute_operation(
                        f"delete_sa_{sa.email}",
                        lambda email=sa.email: self._delete_service_account(email),
                        f"Delete service account: {sa.email}",
                    )
                    results.append(result)
        except Exception as e:
            logger.warning(f"Error listing service accounts: {e}")

        # Delete demo buckets
        logger.info("Finding demo buckets...")
        try:
            for bucket in self.storage_client.list_buckets():
                if bucket.name.startswith(DEMO_PREFIX):
                    result = self._execute_operation(
                        f"delete_bucket_{bucket.name}",
                        lambda name=bucket.name: self._delete_gcs_bucket(name),
                        f"Delete bucket: {bucket.name}",
                    )
                    results.append(result)
        except Exception as e:
            logger.warning(f"Error listing buckets: {e}")

        # Delete demo sinks
        logger.info("Finding demo sinks...")
        try:
            for sink in self.logging_client.list_sinks():
                if sink.name.startswith(DEMO_PREFIX):
                    result = self._execute_operation(
                        f"delete_sink_{sink.name}",
                        lambda name=sink.name: self._delete_logging_sink(name),
                        f"Delete sink: {sink.name}",
                    )
                    results.append(result)
        except Exception as e:
            logger.warning(f"Error listing sinks: {e}")

        if not results:
            logger.info("No demo resources found to clean up")

        return ScenarioResult(
            scenario="cleanup",
            mitre_category="N/A",
            total_operations=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            operations=results,
        )

    def _delete_service_account(self, email: str) -> str:
        """Delete a service account."""
        request = iam_types.DeleteServiceAccountRequest(
            name=f"projects/{self.project_id}/serviceAccounts/{email}"
        )
        self.iam_client.delete_service_account(request=request)
        logger.info(f"  Deleted service account: {email}")
        return email

    def _delete_gcs_bucket(self, bucket_name: str) -> str:
        """Delete a GCS bucket (must be empty)."""
        bucket = self.storage_client.bucket(bucket_name)
        # Delete all objects first
        blobs = list(bucket.list_blobs())
        for blob in blobs:
            blob.delete()
        bucket.delete()
        logger.info(f"  Deleted bucket: {bucket_name}")
        return bucket_name

    # =========================================================================
    # RUN SCENARIOS
    # =========================================================================

    def run_scenario(self, scenario: Scenario) -> List[ScenarioResult]:
        """
        Run specified scenario(s).

        Args:
            scenario: Which scenario to run (or ALL)

        Returns:
            List of ScenarioResult objects
        """
        scenario_map = {
            Scenario.RECON: self.run_recon_scenario,
            Scenario.PRIVESC: self.run_privesc_scenario,
            Scenario.DEFENSE_EVASION: self.run_defense_evasion_scenario,
            Scenario.PERSISTENCE: self.run_persistence_scenario,
            Scenario.LATERAL_MOVEMENT: self.run_lateral_movement_scenario,
        }

        if scenario == Scenario.ALL:
            results = []
            for s, func in scenario_map.items():
                results.append(func())
            return results
        else:
            return [scenario_map[scenario]()]


def print_results(results: List[ScenarioResult]) -> None:
    """Print summary of scenario results."""
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    total_ops = sum(r.total_operations for r in results)
    total_success = sum(r.successful for r in results)
    total_failed = sum(r.failed for r in results)

    for r in results:
        status = "PASS" if r.failed == 0 else "PARTIAL"
        logger.info(
            f"  {r.scenario}: {r.successful}/{r.total_operations} succeeded ({status})"
        )

    logger.info("-" * 60)
    logger.info(f"  TOTAL: {total_success}/{total_ops} operations succeeded")
    if total_failed > 0:
        logger.info(f"  FAILED: {total_failed} operations (check logs for details)")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate realistic GCP audit logs for security demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run reconnaissance scenario
  python generate_security_logs.py --project my-project --scenario recon

  # Run all scenarios in suspicious mode
  python generate_security_logs.py --project my-project --scenario all --mode suspicious

  # Dry run to see what would happen
  python generate_security_logs.py --project my-project --scenario privesc --dry-run

  # Clean up demo resources
  python generate_security_logs.py --project my-project --cleanup

  # Run with faster operations (for demo)
  python generate_security_logs.py --project my-project --scenario all --delay 0.5
        """,
    )

    parser.add_argument(
        "--project",
        "-p",
        required=True,
        help="GCP project ID (required)",
    )
    parser.add_argument(
        "--scenario",
        "-s",
        choices=["recon", "privesc", "defense-evasion", "persistence", "lateral-movement", "all"],
        default="all",
        help="Scenario to run (default: all)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["normal", "suspicious"],
        default="normal",
        help="Operation mode: normal or suspicious (default: normal)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print what would happen without executing",
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Seconds between operations (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--cleanup",
        "-c",
        action="store_true",
        help="Remove all demo- prefixed resources and exit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Adjust logging level if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Security Log Generator starting")
    logger.info(f"  Project: {args.project}")
    logger.info(f"  Mode: {args.mode}")
    logger.info(f"  Scenario: {args.scenario}")
    logger.info(f"  Dry run: {args.dry_run}")
    logger.info(f"  Delay: {args.delay}s")

    try:
        # Initialize generator
        generator = SecurityLogGenerator(
            project_id=args.project,
            mode=Mode(args.mode),
            dry_run=args.dry_run,
            delay=args.delay,
        )

        # Run cleanup or scenarios
        if args.cleanup:
            result = generator.cleanup()
            print_results([result])
        else:
            results = generator.run_scenario(Scenario(args.scenario))
            print_results(results)

        logger.info("Security Log Generator completed successfully")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
