"""
Governance - Contract Monitor

We monitor data contract compliance across all domains.
When a domain violates its contract (quality threshold
breached, freshness SLA missed, unexpected volume drop),
we activate circuit breakers and serve last-known-good
data with staleness warnings.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
import yaml

from afriflow.exceptions import ConfigurationError, DataQualityError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("governance.contract_monitor")


class ContractStatus(Enum):
    """Status of a data contract."""
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    VIOLATED = "VIOLATED"
    CIRCUIT_BROKEN = "CIRCUIT_BROKEN"


@dataclass
class DataContract:
    """
    A data contract defining quality, freshness, and
    volume expectations for a domain data product.

    Attributes:
        domain: Domain name (cib, forex, insurance, cell, pbb)
        entity: Entity name (payments, trades, policies, etc.)
        version: Contract version
        quality_thresholds: Quality metric thresholds
        freshness_sla_minutes: Maximum acceptable latency
        volume_expectations: Expected volume ranges
    """
    domain: str
    entity: str
    version: str
    quality_thresholds: Dict[str, float] = field(default_factory=dict)
    freshness_sla_minutes: float = 60.0
    volume_expectations: Dict[str, float] = field(default_factory=dict)
    owners: List[str] = field(default_factory=list)
    consumers: List[str] = field(default_factory=list)


@dataclass
class ContractViolation:
    """
    Records a contract violation event.

    Attributes:
        contract: The violated contract
        violation_type: Type of violation
        expected_value: Expected value
        actual_value: Actual value
        severity: Violation severity
        detected_at: Detection timestamp
    """
    contract: DataContract
    violation_type: str
    expected_value: float
    actual_value: float
    severity: str
    detected_at: str
    details: Dict[str, Any] = field(default_factory=dict)


class ContractMonitor:
    """
    Monitors data contract compliance across all domains.

    We load contracts from YAML files, evaluate incoming
    data against contract terms, and trigger alerts and
    circuit breakers on violations.

    Attributes:
        contracts: Loaded data contracts by domain.entity
        violations: Recent violations by domain
        circuit_breakers: Active circuit breakers
    """

    def __init__(
        self,
        contract_dir: Optional[str] = None
    ) -> None:
        """
        Initialize the contract monitor.

        Args:
            contract_dir: Directory containing contract YAML files
        """
        self.contracts: Dict[str, DataContract] = {}
        self.violations: Dict[str, List[ContractViolation]] = {}
        self.circuit_breakers: Dict[str, bool] = {}
        self.contract_dir = contract_dir

        logger.info("ContractMonitor initialized")

        if contract_dir:
            self.load_contracts()

    def load_contracts(self) -> int:
        """
        Load data contracts from YAML files.

        Returns:
            Number of contracts loaded

        Raises:
            ConfigurationError: If contract files are invalid
        """
        log_operation(
            logger,
            "load_contracts",
            "started",
            contract_dir=self.contract_dir,
        )

        try:
            import os
            from pathlib import Path

            contract_path = Path(self.contract_dir)
            if not contract_path.exists():
                logger.warning(f"Contract directory not found: {contract_path}")
                return 0

            loaded = 0
            for yaml_file in contract_path.glob("*_contract.yml"):
                try:
                    with open(yaml_file, 'r') as f:
                        contract_data = yaml.safe_load(f)

                    contract = self._parse_contract(contract_data)
                    key = f"{contract.domain}.{contract.entity}"
                    self.contracts[key] = contract
                    loaded += 1

                    logger.info(f"Loaded contract: {key} v{contract.version}")

                except Exception as e:
                    logger.error(f"Failed to load {yaml_file}: {e}")
                    raise ConfigurationError(
                        f"Invalid contract file {yaml_file}: {e}"
                    ) from e

            log_operation(
                logger,
                "load_contracts",
                "completed",
                contracts_loaded=loaded,
            )

            return loaded

        except Exception as e:
            log_operation(
                logger,
                "load_contracts",
                "failed",
                error=str(e),
            )
            raise ConfigurationError(
                f"Failed to load contracts: {e}"
            ) from e

    def _parse_contract(self, data: Dict) -> DataContract:
        """
        Parse a contract from YAML data.

        Args:
            data: Parsed YAML dictionary

        Returns:
            DataContract object
        """
        contract_info = data.get('contract', {})

        return DataContract(
            domain=contract_info.get('domain', 'unknown'),
            entity=contract_info.get('name', 'unknown'),
            version=contract_info.get('version', '1.0'),
            quality_thresholds=data.get('quality', {}).get('completeness', {}),
            freshness_sla_minutes=data.get('quality', {}).get(
                'freshness', {}
            ).get('max_latency_seconds', 60) / 60,
            volume_expectations=data.get('quality', {}).get('volume', {}),
            owners=[contract_info.get('owner', 'unknown')],
            consumers=[
                c.get('name', 'unknown')
                for c in data.get('consumers', [])
            ],
        )

    def evaluate_quality(
        self,
        domain: str,
        entity: str,
        metrics: Dict[str, float]
    ) -> ContractStatus:
        """
        Evaluate data quality metrics against contract.

        Args:
            domain: Domain name
            entity: Entity name
            metrics: Quality metrics to evaluate

        Returns:
            Contract status (COMPLIANT, WARNING, VIOLATED)
        """
        key = f"{domain}.{entity}"
        contract = self.contracts.get(key)

        if not contract:
            logger.warning(f"No contract found for {key}")
            return ContractStatus.COMPLIANT

        log_operation(
            logger,
            "evaluate_quality",
            "started",
            domain=domain,
            entity=entity,
        )

        violations = []

        for metric_name, threshold in contract.quality_thresholds.items():
            actual_value = metrics.get(metric_name, 0)

            if actual_value < threshold:
                violations.append(ContractViolation(
                    contract=contract,
                    violation_type=f"quality_{metric_name}",
                    expected_value=threshold,
                    actual_value=actual_value,
                    severity="WARNING" if actual_value > threshold * 0.9 else "VIOLATED",
                    detected_at=datetime.utcnow().isoformat(),
                    details={"metric": metric_name}
                ))

        if violations:
            self._record_violations(domain, violations)
            status = ContractStatus.VIOLATED
        else:
            status = ContractStatus.COMPLIANT

        log_operation(
            logger,
            "evaluate_quality",
            "completed",
            domain=domain,
            entity=entity,
            status=status.value,
            violations=len(violations),
        )

        return status

    def evaluate_freshness(
        self,
        domain: str,
        entity: str,
        last_update: datetime
    ) -> ContractStatus:
        """
        Evaluate data freshness against contract SLA.

        Args:
            domain: Domain name
            entity: Entity name
            last_update: Last update timestamp

        Returns:
            Contract status
        """
        key = f"{domain}.{entity}"
        contract = self.contracts.get(key)

        if not contract:
            return ContractStatus.COMPLIANT

        now = datetime.utcnow()
        latency_minutes = (now - last_update).total_seconds() / 60

        if latency_minutes > contract.freshness_sla_minutes * 2:
            status = ContractStatus.VIOLATED
            self._activate_circuit_breaker(key)
        elif latency_minutes > contract.freshness_sla_minutes:
            status = ContractStatus.WARNING
        else:
            status = ContractStatus.COMPLIANT

        logger.debug(
            f"Freshness check for {key}: "
            f"{latency_minutes:.1f}min (SLA: {contract.freshness_sla_minutes}min) "
            f"-> {status.value}"
        )

        return status

    def evaluate_volume(
        self,
        domain: str,
        entity: str,
        actual_volume: float
    ) -> ContractStatus:
        """
        Evaluate data volume against contract expectations.

        Args:
            domain: Domain name
            entity: Entity name
            actual_volume: Actual record count

        Returns:
            Contract status
        """
        key = f"{domain}.{entity}"
        contract = self.contracts.get(key)

        if not contract:
            return ContractStatus.COMPLIANT

        min_expected = contract.volume_expectations.get(
            'minimum_daily_events', 0
        )
        max_expected = contract.volume_expectations.get(
            'maximum_daily_events', float('inf')
        )

        if actual_volume < min_expected * 0.5:
            status = ContractStatus.VIOLATED
            self._activate_circuit_breaker(key)
        elif actual_volume < min_expected:
            status = ContractStatus.WARNING
        elif actual_volume > max_expected * 1.5:
            status = ContractStatus.WARNING  # Unexpected spike
        else:
            status = ContractStatus.COMPLIANT

        logger.debug(
            f"Volume check for {key}: "
            f"{actual_volume:.0f} (expected: {min_expected:.0f}-{max_expected:.0f}) "
            f"-> {status.value}"
        )

        return status

    def _record_violations(
        self,
        domain: str,
        violations: List[ContractViolation]
    ) -> None:
        """Record violations for alerting."""
        if domain not in self.violations:
            self.violations[domain] = []

        self.violations[domain].extend(violations)

        # Keep only last 100 violations per domain
        self.violations[domain] = self.violations[domain][-100:]

        logger.warning(
            f"Recorded {len(violations)} violations for {domain}"
        )

    def _activate_circuit_breaker(self, key: str) -> None:
        """Activate circuit breaker for a domain."""
        self.circuit_breakers[key] = True
        logger.error(f"Circuit breaker activated for {key}")

    def is_circuit_broken(self, domain: str, entity: str) -> bool:
        """
        Check if circuit breaker is active for a domain.

        Args:
            domain: Domain name
            entity: Entity name

        Returns:
            True if circuit breaker is active
        """
        key = f"{domain}.{entity}"
        return self.circuit_breakers.get(key, False)

    def reset_circuit_breaker(self, domain: str, entity: str) -> None:
        """
        Reset circuit breaker for a domain.

        Args:
            domain: Domain name
            entity: Entity name
        """
        key = f"{domain}.{entity}"
        if key in self.circuit_breakers:
            del self.circuit_breakers[key]
            logger.info(f"Circuit breaker reset for {key}")

    def get_violations(
        self,
        domain: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[ContractViolation]:
        """
        Get contract violations.

        Args:
            domain: Optional domain filter
            since: Optional time filter

        Returns:
            List of violations
        """
        violations = []

        for dom, dom_violations in self.violations.items():
            if domain and dom != domain:
                continue

            for violation in dom_violations:
                if since:
                    detected = datetime.fromisoformat(
                        violation.detected_at
                    )
                    if detected < since:
                        continue
                violations.append(violation)

        return violations

    def get_contract_status(
        self,
        domain: str,
        entity: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive contract status for a domain.

        Args:
            domain: Domain name
            entity: Entity name

        Returns:
            Status dictionary
        """
        key = f"{domain}.{entity}"
        contract = self.contracts.get(key)

        if not contract:
            return {"status": "NO_CONTRACT"}

        return {
            "contract": key,
            "version": contract.version,
            "status": (
                "CIRCUIT_BROKEN" if self.is_circuit_broken(domain, entity)
                else "COMPLIANT"
            ),
            "freshness_sla_minutes": contract.freshness_sla_minutes,
            "quality_thresholds": contract.quality_thresholds,
            "recent_violations": len([
                v for v in self.violations.get(domain, [])
                if v.contract.entity == entity
            ]),
        }


if __name__ == "__main__":
    # Demo usage
    monitor = ContractMonitor()

    # Create a test contract
    test_contract = DataContract(
        domain="cib",
        entity="payments",
        version="1.0",
        quality_thresholds={"debtor_country": 0.995},
        freshness_sla_minutes=5.0,
    )
    monitor.contracts["cib.payments"] = test_contract

    # Evaluate quality
    status = monitor.evaluate_quality(
        "cib",
        "payments",
        {"debtor_country": 0.99}
    )
    print(f"Quality status: {status.value}")
