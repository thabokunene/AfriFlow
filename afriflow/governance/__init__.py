"""
Governance package for AfriFlow.

We centralise all compliance, access control, audit,
lineage, and regulatory logic here so that every
domain data product can import shared governance
primitives without circular dependencies.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .access_control_matrix import (
    AccessControlMatrix,
    Permission,
    Role,
)
from .audit_trail_logger import (
    AuditEvent,
    AuditTrailLogger,
    AuditAction,
)
from .cell_privacy_compliance import (
    CellPrivacyCompliance,
    RICARetentionPolicy,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker,
    get_all_circuit_states,
)
from .consent_manager import (
    ConsentManager,
    ConsentRecord,
    ProcessingPurpose,
)
from .contract_monitor import (
    ContractMonitor,
    DataContract,
    ContractViolation,
    ContractStatus,
)
from .country_regulatory_registry import (
    CountryRegulatoryRegistry,
    RegulatoryProfile,
)
from .cross_border_data_rules import (
    CrossBorderDataRules,
    DataClassification,
    DataResidencyTier,
)
from .data_lineage_tracker import (
    DataLineageTracker,
    LineageNode,
    LineageEdge,
)
from .fais_compliance import (
    FAISComplianceChecker,
    FAISAdviceRecord,
)
from .freshness_monitor import (
    FreshnessMonitor,
    StalenessLevel,
)
from .insurance_act_compliance import (
    InsuranceActCompliance,
    PolicyholderProtectionCheck,
)
from .popia_classifier import (
    POPIAClassifier,
    POPIACategory,
    LawfulBasis,
)

__all__ = [
    # Access Control
    "AccessControlMatrix", "Permission", "Role",
    # Audit
    "AuditEvent", "AuditTrailLogger", "AuditAction",
    # Cell Privacy
    "CellPrivacyCompliance", "RICARetentionPolicy",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitBreakerConfig",
    "CircuitState",
    "get_circuit_breaker",
    "get_all_circuit_states",
    # Consent
    "ConsentManager", "ConsentRecord", "ProcessingPurpose",
    # Contract Monitor
    "ContractMonitor",
    "DataContract",
    "ContractViolation",
    "ContractStatus",
    # Regulatory
    "CountryRegulatoryRegistry", "RegulatoryProfile",
    # Cross-Border
    "CrossBorderDataRules", "DataClassification", "DataResidencyTier",
    # Lineage
    "DataLineageTracker", "LineageNode", "LineageEdge",
    # FAIS
    "FAISComplianceChecker", "FAISAdviceRecord",
    # Freshness
    "FreshnessMonitor", "StalenessLevel",
    # Insurance
    "InsuranceActCompliance", "PolicyholderProtectionCheck",
    # POPIA
    "POPIAClassifier", "POPIACategory", "LawfulBasis",
]
