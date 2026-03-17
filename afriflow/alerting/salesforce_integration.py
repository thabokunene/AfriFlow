"""
Salesforce Integration

Pushes AfriFlow alerts and NBA recommendations to Salesforce
CRM as Tasks and Opportunities, so RMs receive the insights
within their existing workflow without switching systems.

Integration points:
  RMAlert      → Salesforce Task (assigned to RM, with due date)
  NBA result   → Salesforce Opportunity (on client Account)
  Outcome      → Salesforce Task status update (Completed/Closed)

This is a stub implementation that produces the correct Salesforce
API payload structures. In production, these would be sent via
the Salesforce REST API with OAuth2 authentication.

Record types:
  Task subject prefixes: [AfriFlow] to distinguish from manual tasks
  Opportunity stages:
    NBA score ≥ 80 → "Proposal/Price Quote"
    NBA score ≥ 60 → "Needs Analysis"
    NBA score ≥ 40 → "Prospecting"

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# Salesforce standard field values
_TASK_STATUS_OPEN = "Not Started"
_TASK_STATUS_DONE = "Completed"
_TASK_PRIORITY_HIGH = "High"
_TASK_PRIORITY_NORMAL = "Normal"

_NBA_SCORE_TO_STAGE: List[tuple] = [
    (80, "Proposal/Price Quote"),
    (60, "Needs Analysis"),
    (40, "Prospecting"),
    (0,  "Qualification"),
]


@dataclass
class SalesforceTask:
    """Salesforce Task payload (REST API format)."""

    subject: str
    description: str
    owner_id: str           # Salesforce User ID of RM
    what_id: str            # Salesforce Account ID of client
    activity_date: str      # Due date (YYYY-MM-DD)
    priority: str
    status: str
    type: str               # "Call", "Email", "Meeting", "Other"
    custom_fields: Dict     # AfriFlow-specific custom fields


@dataclass
class SalesforceOpportunity:
    """Salesforce Opportunity payload (REST API format)."""

    name: str
    account_id: str
    stage_name: str
    close_date: str         # Expected close date
    amount: float           # Estimated revenue ZAR
    description: str
    owner_id: str
    custom_fields: Dict


@dataclass
class SalesforceSyncBatch:
    """Batch of Salesforce records to upsert."""

    tasks: List[SalesforceTask]
    opportunities: List[SalesforceOpportunity]
    batch_id: str
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class SalesforceIntegration:
    """
    Build Salesforce API payloads from AfriFlow alerts and NBA results.

    Usage::

        sf = SalesforceIntegration(
            rm_sf_id_map={"RM-00142": "0051X000003TukS"},
            client_sf_id_map={"GLD-001": "0011X000002FSmT"},
        )
        batch = sf.build_sync_batch(
            rm_alerts=[...],
            nba_results=[...],
        )
        # In production: post batch.tasks and batch.opportunities to SF API
    """

    def __init__(
        self,
        rm_sf_id_map: Optional[Dict[str, str]] = None,
        client_sf_id_map: Optional[Dict[str, str]] = None,
    ):
        self._rm_ids = rm_sf_id_map or {}
        self._client_ids = client_sf_id_map or {}

    def build_sync_batch(
        self,
        rm_alerts: Optional[List[Dict]] = None,
        nba_results: Optional[List[Dict]] = None,
        outcome_updates: Optional[List[Dict]] = None,
    ) -> SalesforceSyncBatch:
        tasks: List[SalesforceTask] = []
        opportunities: List[SalesforceOpportunity] = []

        for alert in (rm_alerts or []):
            task = self._alert_to_task(alert)
            if task:
                tasks.append(task)

        for nba in (nba_results or []):
            opty = self._nba_to_opportunity(nba)
            if opty:
                opportunities.append(opty)

        for update in (outcome_updates or []):
            task = self._outcome_to_task_update(update)
            if task:
                tasks.append(task)

        batch_id = (
            f"SFBATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        return SalesforceSyncBatch(
            tasks=tasks,
            opportunities=opportunities,
            batch_id=batch_id,
        )

    # ------------------------------------------------------------------
    # Converters
    # ------------------------------------------------------------------

    def _alert_to_task(self, alert: Dict) -> Optional[SalesforceTask]:
        rm_id = alert.get("rm_id", "")
        golden_id = alert.get("client_golden_id", "")
        alert_type = alert.get("alert_type", "UNKNOWN")
        client_name = alert.get("client_name", "Unknown")

        sf_owner = self._rm_ids.get(rm_id, rm_id)
        sf_account = self._client_ids.get(golden_id, golden_id)

        urgency = alert.get("urgency", "MEDIUM")
        priority = _TASK_PRIORITY_HIGH if urgency in (
            "IMMEDIATE", "HIGH"
        ) else _TASK_PRIORITY_NORMAL

        sla_expires = alert.get("sla_expires_at", "")
        due_date = self._iso_to_date(sla_expires)

        task_type = {
            "CHURN_RISK":    "Call",
            "EXPANSION_OPTY": "Meeting",
            "CURRENCY_RISK": "Call",
            "FRAUD_FLAG":    "Other",
            "PAYROLL_DELAY": "Call",
            "RENEWAL_DUE":   "Call",
        }.get(alert_type, "Other")

        subject = (
            f"[AfriFlow] {alert_type.replace('_', ' ').title()}: "
            f"{client_name}"
        )

        description = (
            f"Alert ID: {alert.get('alert_id', '')}\n"
            f"Talking point: {alert.get('talking_point', '')}\n"
            f"Call to action: {alert.get('call_to_action', '')}\n"
            f"Revenue at stake: R{alert.get('revenue_at_stake_zar', 0):,.0f}\n"
            f"Generated: {alert.get('created_at', '')}"
        )

        return SalesforceTask(
            subject=subject,
            description=description,
            owner_id=sf_owner,
            what_id=sf_account,
            activity_date=due_date,
            priority=priority,
            status=_TASK_STATUS_OPEN,
            type=task_type,
            custom_fields={
                "AfriFlow_Alert_ID__c": alert.get("alert_id", ""),
                "AfriFlow_Alert_Type__c": alert_type,
                "AfriFlow_Revenue_At_Stake_ZAR__c": alert.get(
                    "revenue_at_stake_zar", 0
                ),
                "AfriFlow_Domains_Triggered__c": "; ".join(
                    alert.get("domains_triggered", [])
                ),
            },
        )

    def _nba_to_opportunity(
        self, nba: Dict
    ) -> Optional[SalesforceOpportunity]:
        top_action = nba.get("top_action")
        if not top_action:
            return None

        golden_id = nba.get("client_golden_id", "")
        client_name = nba.get("client_name", "Unknown")
        score = top_action.get("score", 0)
        revenue = top_action.get("estimated_revenue_zar", 0)
        product = top_action.get("product_name", "Product")
        category = top_action.get("product_category", "CIB")

        if score < 40:
            return None

        sf_account = self._client_ids.get(golden_id, golden_id)
        stage = self._score_to_stage(score)

        close_date = self._iso_to_date(
            (datetime.now() + timedelta(days=90)).isoformat()
        )

        return SalesforceOpportunity(
            name=f"[AfriFlow] {client_name} — {product}",
            account_id=sf_account,
            stage_name=stage,
            close_date=close_date,
            amount=revenue,
            description=(
                f"NBA Score: {score:.0f}/100\n"
                f"Category: {category}\n"
                f"Talking point: {top_action.get('rm_talking_point', '')}\n"
                f"Data completeness: "
                f"{nba.get('data_completeness_score', 0)*100:.0f}%\n"
                f"Generated: {nba.get('generated_at', '')}"
            ),
            owner_id="",  # Will be set from RM mapping
            custom_fields={
                "AfriFlow_NBA_Score__c": score,
                "AfriFlow_Product_Category__c": category,
                "AfriFlow_Client_Golden_ID__c": golden_id,
                "AfriFlow_Generated_At__c": nba.get("generated_at", ""),
            },
        )

    def _outcome_to_task_update(
        self, update: Dict
    ) -> Optional[SalesforceTask]:
        alert_id = update.get("alert_id", "")
        outcome = update.get("outcome", "")
        rm_id = update.get("rm_id", "")
        notes = update.get("rm_notes", "")

        sf_owner = self._rm_ids.get(rm_id, rm_id)

        status = (
            _TASK_STATUS_DONE
            if outcome in ("CONVERTED", "REJECTED", "EXPIRED", "FALSE_POSITIVE")
            else _TASK_STATUS_OPEN
        )

        return SalesforceTask(
            subject=f"[AfriFlow] Outcome Update: {alert_id}",
            description=(
                f"Outcome: {outcome}\n"
                f"Revenue: R{update.get('actual_revenue_zar', 0):,.0f}\n"
                f"Notes: {notes}\n"
                f"Recorded: {update.get('recorded_at', '')}"
            ),
            owner_id=sf_owner,
            what_id=self._client_ids.get(
                update.get("client_golden_id", ""), ""
            ),
            activity_date=self._iso_to_date(datetime.now().isoformat()),
            priority=_TASK_PRIORITY_NORMAL,
            status=status,
            type="Other",
            custom_fields={
                "AfriFlow_Alert_ID__c": alert_id,
                "AfriFlow_Outcome__c": outcome,
                "AfriFlow_Actual_Revenue_ZAR__c": update.get(
                    "actual_revenue_zar", 0
                ),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _iso_to_date(self, iso_str: str) -> str:
        """Extract YYYY-MM-DD from ISO datetime string."""
        if not iso_str:
            return datetime.now().strftime("%Y-%m-%d")
        return iso_str[:10]

    def _score_to_stage(self, score: float) -> str:
        for threshold, stage in _NBA_SCORE_TO_STAGE:
            if score >= threshold:
                return stage
        return "Qualification"
