"""
@file constants.py
@description Shared constants for date formats, Kafka topics, thresholds, and platform defaults across all AfriFlow domains.
@author Thabo Kunene
@created 2026-03-19
"""

"""
AfriFlow Domain Constants.

We define shared constants used across all domains
for consistency and maintainability.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Access to environment variables for default values and backward compatibility
import os
# Type hint for immutable constant values
from typing import Final

# =============================================================================
# DATE FORMATS
# =============================================================================

# Standard ISO 8601 date format for string representation
ISO_DATE_FORMAT: Final[str] = "%Y-%m-%d"
# Detailed ISO 8601 datetime format with millisecond precision and UTC suffix
ISO_DATETIME_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S.%fZ"

# =============================================================================
# KAFKA CONFIGURATION
# =============================================================================

# Default Kafka bootstrap server, falls back to localhost for development
DEFAULT_KAFKA_BROKER: Final[str] = os.getenv(
    "KAFKA_BROKER", "localhost:9092"
)

# Shared logic for retrieving the schema registry URL from environment
_schema_registry: Final[str] = (
    os.getenv("SCHEMA_REGISTRY_URL")
    or os.getenv("SCHEMA_REGISTRY", "http://localhost:8081")
)

# Legacy alias for the schema registry endpoint
DEFAULT_SCHEMA_REGISTRY: Final[str] = _schema_registry

# Modern, explicit name for the schema registry endpoint
DEFAULT_SCHEMA_REGISTRY_URL: Final[str] = _schema_registry

# =============================================================================
# KAFKA TOPICS
# =============================================================================

# Corporate and Investment Banking (CIB) topics
TOPIC_CIB_PAYMENTS: Final[str] = "cib.payments.v1"
TOPIC_CIB_TRADE_FINANCE: Final[str] = "cib.trade_finance.v1"
TOPIC_CIB_CASH_MGMT: Final[str] = "cib.cash_management.v1"

# Foreign Exchange (Forex) topics
TOPIC_FOREX_TRADES: Final[str] = "forex.trades.v1"
TOPIC_FOREX_RATES: Final[str] = "forex.rates.v1"

# Insurance domain topics for policies and claims lifecycle
TOPIC_INSURANCE_POLICIES: Final[str] = "insurance.policies.v1"
TOPIC_INSURANCE_CLAIMS: Final[str] = "insurance.claims.v1"

# Telecommunications (Cell) and Mobile Money topics
TOPIC_CELL_ACTIVATIONS: Final[str] = "cell.activations.v1"
TOPIC_CELL_USAGE: Final[str] = "cell.usage.v1"
TOPIC_CELL_MOMO: Final[str] = "cell.momo.v1"

# Personal and Business Banking (PBB) topics
TOPIC_PBB_ACCOUNTS: Final[str] = "pbb.accounts.v1"
TOPIC_PBB_PAYROLL: Final[str] = "pbb.payroll.v1"
TOPIC_PBB_TRANSACTIONS: Final[str] = "pbb.transactions.v1"

# =============================================================================
# ENTITY RESOLUTION
# =============================================================================

# Minimum score (0-100) for matching client records across different domains
MATCH_THRESHOLD: Final[int] = 85

# =============================================================================
# DATA QUALITY
# =============================================================================

# Minimum ratio of non-null required fields
MIN_COMPLETENESS_THRESHOLD: Final[float] = 0.95
# Minimum ratio of fields matching expected patterns/ranges
MIN_ACCURACY_THRESHOLD: Final[float] = 0.98
# Maximum allowed delay between event occurrence and ingestion processing
MAX_LATENCY_SECONDS: Final[int] = 300

# =============================================================================
# SECURITY
# =============================================================================

# Duration for which a session token remains valid
TOKEN_EXPIRY_HOURS: Final[int] = 24
# Maximum failed login attempts before account lockout
MAX_LOGIN_ATTEMPTS: Final[int] = 5
# Minimum character count for user passwords
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
