"""
AfriFlow Alerting Layer

Generates, routes, and tracks alerts across all AfriFlow user personas:
  - Relationship Managers  → rm_alert_engine
  - FX Advisors            → fx_advisor_alert_engine
  - Insurance Brokers      → insurance_broker_alert_engine
  - PBB Branch Managers    → pbb_branch_alert_engine
  - Trading Desks          → currency_event_alert_engine
  - CRM Integration        → salesforce_integration
  - Model Calibration      → outcome_tracker
"""

from .rm_alert_engine import RMAlertEngine, RMAlert, RMAlertBatch
from .fx_advisor_alert_engine import (
    FXAdvisorAlertEngine,
    FXAdvisorAlert,
    FXAdvisorAlertBatch,
)
from .insurance_broker_alert_engine import (
    InsuranceBrokerAlertEngine,
    InsuranceBrokerAlert,
    InsuranceBrokerAlertBatch,
)
from .pbb_branch_alert_engine import (
    PBBBranchAlertEngine,
    PBBBranchAlert,
    PBBBranchAlertBatch,
)
from .currency_event_alert_engine import (
    CurrencyEventAlertEngine,
    CurrencyEvent,
    CurrencyEventReport,
)
from .outcome_tracker import OutcomeTracker, AlertOutcome, OutcomeReport
from .salesforce_integration import (
    SalesforceIntegration,
    SalesforceSyncBatch,
)

__all__ = [
    "RMAlertEngine", "RMAlert", "RMAlertBatch",
    "FXAdvisorAlertEngine", "FXAdvisorAlert", "FXAdvisorAlertBatch",
    "InsuranceBrokerAlertEngine", "InsuranceBrokerAlert", "InsuranceBrokerAlertBatch",
    "PBBBranchAlertEngine", "PBBBranchAlert", "PBBBranchAlertBatch",
    "CurrencyEventAlertEngine", "CurrencyEvent", "CurrencyEventReport",
    "OutcomeTracker", "AlertOutcome", "OutcomeReport",
    "SalesforceIntegration", "SalesforceSyncBatch",
]
