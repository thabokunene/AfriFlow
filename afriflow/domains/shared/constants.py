"""
AfriFlow Domain Constants.

We define shared constants used across all domains
for consistency and maintainability.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import os
from typing import Final

# =============================================================================
# DATE FORMATS
# =============================================================================

ISO_DATE_FORMAT: Final[str] = "%Y-%m-%d"
ISO_DATETIME_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S.%fZ"

# =============================================================================
# KAFKA CONFIGURATION
# =============================================================================

# Support both legacy and new env var names for schema registry
# to maintain backward compatibility.
DEFAULT_KAFKA_BROKER: Final[str] = os.getenv(
    "KAFKA_BROKER", "localhost:9092"
)

_schema_registry: Final[str] = (
    os.getenv("SCHEMA_REGISTRY_URL")
    or os.getenv("SCHEMA_REGISTRY", "http://localhost:8081")
)

# Backward-compatible name
DEFAULT_SCHEMA_REGISTRY: Final[str] = _schema_registry

# Preferred explicit name
DEFAULT_SCHEMA_REGISTRY_URL: Final[str] = _schema_registry

# =============================================================================
# KAFKA TOPICS
# =============================================================================

# CIB Domain
TOPIC_CIB_PAYMENTS: Final[str] = "cib.payments.v1"
TOPIC_CIB_TRADE_FINANCE: Final[str] = "cib.trade_finance.v1"
TOPIC_CIB_CASH_MGMT: Final[str] = "cib.cash_management.v1"

# Forex Domain
TOPIC_FOREX_TRADES: Final[str] = "forex.trades.v1"
TOPIC_FOREX_RATES: Final[str] = "forex.rates.v1"

# Insurance Domain
TOPIC_INSURANCE_POLICIES: Final[str] = "insurance.policies.v1"
TOPIC_INSURANCE_CLAIMS: Final[str] = "insurance.claims.v1"

# Cell Domain
TOPIC_CELL_ACTIVATIONS: Final[str] = "cell.activations.v1"
TOPIC_CELL_USAGE: Final[str] = "cell.usage.v1"
TOPIC_CELL_MOMO: Final[str] = "cell.momo.v1"

# PBB Domain
TOPIC_PBB_ACCOUNTS: Final[str] = "pbb.accounts.v1"
TOPIC_PBB_PAYROLL: Final[str] = "pbb.payroll.v1"
TOPIC_PBB_TRANSACTIONS: Final[str] = "pbb.transactions.v1"

# =============================================================================
# ENTITY RESOLUTION
# =============================================================================

MATCH_THRESHOLD: Final[int] = 85

# =============================================================================
# DATA QUALITY
# =============================================================================

MIN_COMPLETENESS_THRESHOLD: Final[float] = 0.95
MIN_ACCURACY_THRESHOLD: Final[float] = 0.98
MAX_LATENCY_SECONDS: Final[int] = 300

# =============================================================================
# SECURITY
# =============================================================================

TOKEN_EXPIRY_HOURS: Final[int] = 24
MAX_LOGIN_ATTEMPTS: Final[int] = 5
PASSWORD_MIN_LENGTH: Final[int] = 12

# =============================================================================
# PERFORMANCE
# =============================================================================

BATCH_SIZE_DEFAULT: Final[int] = 1000
STREAMING_PARALLELISM: Final[int] = 4
CHECKPOINT_INTERVAL_SECONDS: Final[int] = 60

# =============================================================================
# EKS INFRASTRUCTURE
# =============================================================================

# Default EKS cluster name
EKS_CLUSTER_NAME: Final[str] = "afriflow-cluster"

# Country pod namespaces
COUNTRY_POD_NAMESPACES: Final[dict] = {
    "ZA": "afriflow-south-africa",
    "NG": "afriflow-nigeria",
    "KE": "afriflow-kenya",
    "GH": "afriflow-ghana",
    "TZ": "afriflow-tanzania",
    "UG": "afriflow-uganda",
    "ZM": "afriflow-zambia",
    "MZ": "afriflow-mozambique",
    "CD": "afriflow-drc",
    "AO": "afriflow-angola",
}

# Node group instance types by tier
NODE_GROUP_INSTANCE_TYPES: Final[dict] = {
    "processing": "m5.2xlarge",
    "streaming": "c5.2xlarge",
    "ingestion": "m5.xlarge",
    "monitoring": "t3.large",
}
