"""
@file __init__.py
@description Package initialiser for the AfriFlow alerting layer. Exposes all
             alert engines, alert data classes, and supporting types so that
             downstream consumers (API layer, notebooks, tests) can import from
             a single namespace: ``from afriflow.alerting import RMAlertEngine``.
@author Thabo Kunene
@created 2026-03-18
"""

# ---------------------------------------------------------------------------
# AfriFlow Alerting Layer
#
# Generates, routes, and tracks alerts across all AfriFlow user personas:
#   - Relationship Managers  → rm_alert_engine
#   - FX Advisors            → fx_advisor_alert_engine
#   - Insurance Brokers      → insurance_broker_alert_engine
#   - PBB Branch Managers    → pbb_branch_alert_engine
#   - Trading Desks          → currency_event_alert_engine
#   - CRM Integration        → salesforce_integration
#   - Model Calibration      → outcome_tracker
# ---------------------------------------------------------------------------

# --- RM alert engine: priority-ranked actions for relationship managers ---
from .rm_alert_engine import RMAlertEngine, RMAlert, RMAlertBatch

# --- FX advisor alert engine: rate thresholds, forwards, parallel markets ---
from .fx_advisor_alert_engine import (
    FXAdvisorAlertEngine,
    FXAdvisorAlert,
    FXAdvisorAlertBatch,
)

# --- Insurance broker alert engine: renewals, gaps, claim surges ---
from .insurance_broker_alert_engine import (
    InsuranceBrokerAlertEngine,
    InsuranceBrokerAlert,
    InsuranceBrokerAlertBatch,
)

# --- PBB branch alert engine: dormancy, KYC, overdraft, salary capture ---
from .pbb_branch_alert_engine import (
    PBBBranchAlertEngine,
    PBBBranchAlert,
    PBBBranchAlertBatch,
)

# --- Currency event alert engine: rate shocks, illiquidity, swap spikes ---
from .currency_event_alert_engine import (
    CurrencyEventAlertEngine,
    CurrencyEvent,
    CurrencyEventReport,
)

# --- Outcome tracker: records alert outcomes and produces calibration data ---
from .outcome_tracker import OutcomeTracker, AlertOutcome, OutcomeReport

# --- Salesforce integration: builds CRM task and opportunity payloads ---
from .salesforce_integration import (
    SalesforceIntegration,
    SalesforceSyncBatch,
)

# Public API surface — controls what ``from afriflow.alerting import *`` exposes
__all__ = [
    # RM alert engine
    "RMAlertEngine", "RMAlert", "RMAlertBatch",
    # FX advisor alert engine
    "FXAdvisorAlertEngine", "FXAdvisorAlert", "FXAdvisorAlertBatch",
    # Insurance broker alert engine
    "InsuranceBrokerAlertEngine", "InsuranceBrokerAlert", "InsuranceBrokerAlertBatch",
    # PBB branch alert engine
    "PBBBranchAlertEngine", "PBBBranchAlert", "PBBBranchAlertBatch",
    # Currency event alert engine
    "CurrencyEventAlertEngine", "CurrencyEvent", "CurrencyEventReport",
    # Outcome tracker and reporting
    "OutcomeTracker", "AlertOutcome", "OutcomeReport",
    # Salesforce CRM integration
    "SalesforceIntegration", "SalesforceSyncBatch",
]
