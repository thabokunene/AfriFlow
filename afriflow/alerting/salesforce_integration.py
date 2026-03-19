"""
@file salesforce_integration.py
@description Builds and formats Salesforce CRM API payloads from AfriFlow alerts
             and NBA recommendations. Converts RMAlert objects into Salesforce
             Tasks (assigned to the RM, with SLA-derived due dates), NBA results
             into Salesforce Opportunities (staged by propensity score), and
             outcome updates into Task status closures. Designed as a stub that
             produces production-correct API payload structures; in production
             these payloads are sent via the Salesforce REST API with OAuth2
             authentication.
@author Thabo Kunene
@created 2026-03-19
"""

# Salesforce Integration
#
# Pushes AfriFlow alerts and NBA recommendations to Salesforce
# CRM as Tasks and Opportunities, so RMs receive the insights
# within their existing workflow without switching systems.
#
# Integration points:
#   RMAlert      → Salesforce Task (assigned to RM, with due date)
#   NBA result   → Salesforce Opportunity (on client Account)
#   Outcome      → Salesforce Task status update (Completed/Closed)
#
# This is a stub implementation that produces the correct Salesforce
# API payload structures. In production, these would be sent via
# the Salesforce REST API with OAuth2 authentication.
#
# Record types:
#   Task subject prefixes: [AfriFlow] to distinguish from manual tasks
#   Opportunity stages:
#     NBA score >= 80 → "Proposal/Price Quote"
#     NBA score >= 60 → "Needs Analysis"
#     NBA score >= 40 → "Prospecting"
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data classes, date/time logic, and typing
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Salesforce standard field constant values
# ---------------------------------------------------------------------------

# Salesforce Task Status field values.
_TASK_STATUS_OPEN = "Not Started"
_TASK_STATUS_DONE = "Completed"

# Salesforce Task Priority field values.
_TASK_PRIORITY_HIGH   = "High"
_TASK_PRIORITY_NORMAL = "Normal"

# NBA score → Salesforce Opportunity Stage mapping.
_NBA_SCORE_TO_STAGE: List[tuple] = [
    (80, "Proposal/Price Quote"),
    (60, "Needs Analysis"),
    (40, "Prospecting"),
    (0,  "Qualification"),
]


# ---------------------------------------------------------------------------
# Data classes — Salesforce API payload structures
# ---------------------------------------------------------------------------

@dataclass
class SalesforceTask:
    """
    Salesforce Task payload matching the REST API field schema.

    Maps directly to the Salesforce Task sobject.

    :param subject: Task title displayed in RM's Salesforce activity feed
    :param description: Full alert detail including talking point and CTA
    :param owner_id: Salesforce User ID of the assigned RM
    :param what_id: Salesforce Account ID of the client record
    :param activity_date: Due date in YYYY-MM-DD
    :param priority: Salesforce priority field value (e.g., High)
    :param status: Task status (e.g., Not Started)
    :param type: Task type (e.g., Call)
    :param custom_fields: Dict of AfriFlow custom field API names to values
    """

    subject: str
    description: str
    owner_id: str
    what_id: str
    activity_date: str
    priority: str
    status: str
    type: str
    custom_fields: Dict


@dataclass
class SalesforceOpportunity:
    """
    Salesforce Opportunity payload matching the REST API field schema.

    Created for NBA results with a propensity score >= 40.

    :param name: Opportunity name with [AfriFlow] prefix
    :param account_id: Salesforce Account ID of the client
    :param stage_name: Pipeline stage derived from NBA score
    :param close_date: Expected close date (YYYY-MM-DD)
    :param amount: Estimated deal revenue in ZAR from the NBA model
    :param description: Full context including NBA score and talking point
    :param owner_id: Salesforce User ID of the owning RM
    :param custom_fields: AfriFlow NBA metadata for Salesforce reporting
    """

    name: str
    account_id: str
    stage_name: str
    close_date: str
    amount: float
    description: str
    owner_id: str
    custom_fields: Dict


@dataclass
class SalesforceSyncBatch:
    """
    A batch of Salesforce records to upsert in a single API call.

    :param tasks: List of SalesforceTask objects to upsert
    :param opportunities: List of SalesforceOpportunity objects to upsert
    :param batch_id: Unique batch identifier for audit and retry tracking
    :param created_at: Timestamp when the batch was built
    """

    tasks: List[SalesforceTask]
    opportunities: List[SalesforceOpportunity]
    batch_id: str
    # Automatically capture the creation time of the sync batch
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Salesforce integration engine
# ---------------------------------------------------------------------------

class SalesforceIntegration:
    """
    Build Salesforce API payloads from AfriFlow alerts and NBA results.

    Translates AfriFlow's internal data models into Salesforce REST API
    compatible structures for seamless CRM integration.
    """

    def __init__(
        self,
        rm_sf_id_map: Optional[Dict[str, str]] = None,
        client_sf_id_map: Optional[Dict[str, str]] = None,
    ):
        """
        Initialise the integration with ID mapping dictionaries.

        :param rm_sf_id_map: Maps AfriFlow RM IDs to Salesforce User IDs
        :param client_sf_id_map: Maps client golden IDs to Salesforce Account IDs
        """
        # Dictionary for translating RM internal IDs to Salesforce identifiers
        self.rm_sf_id_map = rm_sf_id_map or {}
        # Dictionary for translating client golden IDs to Salesforce identifiers
        self.client_sf_id_map = client_sf_id_map or {}

    def build_sync_batch(
        self,
        batch_id: str,
        rm_alerts: List[RMAlert],
        nba_results: List[Dict],
        outcomes: Optional[List[AlertOutcome]] = None,
    ) -> SalesforceSyncBatch:
        """
        Build a comprehensive sync batch containing Tasks and Opportunities.

        :param batch_id: Unique identifier for the current sync run
        :param rm_alerts: List of active RMAlert objects to sync as Tasks
        :param nba_results: List of NBA result dictionaries to sync as Opportunities
        :param outcomes: Optional list of AlertOutcome objects to sync as Task closures
        :return: A SalesforceSyncBatch containing all generated record payloads.
        """
        tasks: List[SalesforceTask] = []
        opportunities: List[SalesforceOpportunity] = []

        # Convert active RM alerts into Salesforce Tasks assigned to the RM
        for alert in rm_alerts:
            tasks.append(self._build_task_from_alert(alert))

        # Convert NBA recommendations into Salesforce Opportunities if score threshold is met
        for nba in nba_results:
            opp = self._build_opportunity_from_nba(nba)
            if opp:
                opportunities.append(opp)

        # Process alert outcomes to close existing Salesforce Tasks
        for outcome in (outcomes or []):
            tasks.append(self._build_task_closure(outcome))

        return SalesforceSyncBatch(
            tasks=tasks,
            opportunities=opportunities,
            batch_id=batch_id,
        )

    def _build_task_from_alert(self, alert: RMAlert) -> SalesforceTask:
        """
        Map an RMAlert object to a SalesforceTask REST API payload.

        :param alert: The source RMAlert object
        :return: A populated SalesforceTask payload.
        """
        # Extract Salesforce-specific IDs using the mapping dictionaries
        rm_sf_id = self.rm_sf_id_map.get(alert.rm_id, alert.rm_id)
        client_sf_id = self.client_sf_id_map.get(
            alert.client_golden_id, alert.client_golden_id
        )

        # Derive Salesforce priority from AfriFlow urgency multiplier
        priority = _TASK_PRIORITY_NORMAL
        if alert.alert_type in ["FRAUD_FLAG", "CHURN_RISK", "CURRENCY_RISK"]:
            priority = _TASK_PRIORITY_HIGH

        # Calculate the due date (activity_date) from the SLA expiry timestamp
        try:
            # Parse the ISO timestamp and format as YYYY-MM-DD
            expiry_dt = datetime.fromisoformat(alert.sla_expires_at)
            activity_date = expiry_dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            # Fallback to 48 hours from now if the timestamp is invalid
            activity_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

        # Compile the full task description for the RM's preparação
        description = (
            f"{alert.talking_point}\n\n"
            f"Call to Action: {alert.call_to_action}\n\n"
            f"Evidence:\n- " + "\n- ".join(alert.supporting_evidence)
        )

        return SalesforceTask(
            subject=f"[AfriFlow] {alert.alert_type.replace('_', ' ').title()}",
            description=description,
            owner_id=rm_sf_id,
            what_id=client_sf_id,
            activity_date=activity_date,
            priority=priority,
            status=_TASK_STATUS_OPEN,
            type="Call",
            # Attach AfriFlow-specific metadata for CRM reporting
            custom_fields={
                "AfriFlow_Alert_ID__c": alert.alert_id,
                "AfriFlow_Priority_Score__c": alert.priority_score,
                "AfriFlow_Revenue_At_Stake__c": alert.revenue_at_stake_zar,
                "AfriFlow_Domains__c": ";".join(alert.domains_triggered),
            },
        )
                                  e.g. {"GLD-001": "0011X000002FSmT"}
        """
        self._rm_ids = rm_sf_id_map or {}        # AfriFlow RM ID → Salesforce User ID
        self._client_ids = client_sf_id_map or {}  # Golden ID → Salesforce Account ID

    def build_sync_batch(
        self,
        rm_alerts: Optional[List[Dict]] = None,
        nba_results: Optional[List[Dict]] = None,
        outcome_updates: Optional[List[Dict]] = None,
    ) -> SalesforceSyncBatch:
        """
        Build a complete Salesforce sync batch from AfriFlow data.

        Processes three input streams in sequence:
          1. RM alerts → SalesforceTask (open, due at SLA expiry)
          2. NBA results → SalesforceOpportunity (staged by score)
          3. Outcome updates → SalesforceTask (closed, with outcome notes)

        Payloads that cannot be built (e.g. missing required fields) are
        silently skipped to avoid a single bad record blocking the entire batch.

        :param rm_alerts: List of RM alert dicts from RMAlertEngine
        :param nba_results: List of NBA result dicts from the NBA engine
        :param outcome_updates: List of outcome update dicts from OutcomeTracker
        :return: SalesforceSyncBatch ready for upsert to Salesforce API
        """
        tasks: List[SalesforceTask] = []
        opportunities: List[SalesforceOpportunity] = []

        # Convert each RM alert into a Salesforce Task for the assigned RM
        for alert in (rm_alerts or []):
            task = self._alert_to_task(alert)
            if task:
                tasks.append(task)

        # Convert each NBA result into a Salesforce Opportunity on the client Account
        for nba in (nba_results or []):
            opty = self._nba_to_opportunity(nba)
            if opty:
                opportunities.append(opty)

        # Convert each outcome update into a closed Salesforce Task for audit trail
        for update in (outcome_updates or []):
            task = self._outcome_to_task_update(update)
            if task:
                tasks.append(task)

        # Generate a time-stamped batch ID for logging, idempotency, and retry tracking
        batch_id = (
            f"SFBATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        return SalesforceSyncBatch(
            tasks=tasks,
            opportunities=opportunities,
            batch_id=batch_id,
        )

    # ------------------------------------------------------------------
    # Converters: one per Salesforce record type
    # ------------------------------------------------------------------

    def _alert_to_task(self, alert: Dict) -> Optional[SalesforceTask]:
        """
        Convert an AfriFlow RM alert dict into a Salesforce Task payload.

        The task is assigned to the RM who owns the client relationship.
        Task type (Call, Meeting, Other) is derived from alert_type, reflecting
        the expected interaction mode for each alert category. Priority maps
        urgency IMMEDIATE/HIGH → High, MEDIUM/LOW → Normal.

        Who receives this task: the RM assigned to the client in Salesforce.
        Urgency routing: High priority tasks surface at the top of the RM's
        Salesforce activity feed and trigger mobile push notifications.

        :param alert: RM alert dict with alert_id, rm_id, client_golden_id,
                      alert_type, client_name, urgency, sla_expires_at,
                      talking_point, call_to_action, revenue_at_stake_zar,
                      created_at, domains_triggered
        :return: SalesforceTask or None if required fields are missing
        """
        # Extract core identifiers used to route the task to the correct RM and account
        rm_id = alert.get("rm_id", "")
        golden_id = alert.get("client_golden_id", "")
        alert_type = alert.get("alert_type", "UNKNOWN")
        client_name = alert.get("client_name", "Unknown")

        # Translate AfriFlow IDs to Salesforce 18-char record IDs.
        # Falls back to the AfriFlow ID if no mapping exists (e.g. in test environments).
        sf_owner = self._rm_ids.get(rm_id, rm_id)
        sf_account = self._client_ids.get(golden_id, golden_id)

        # Urgency → Salesforce Priority mapping:
        # IMMEDIATE and HIGH alerts become High priority tasks (surface first in SF task list)
        # MEDIUM and LOW alerts become Normal priority (deferred action acceptable)
        urgency = alert.get("urgency", "MEDIUM")
        priority = _TASK_PRIORITY_HIGH if urgency in (
            "IMMEDIATE", "HIGH"
        ) else _TASK_PRIORITY_NORMAL

        # Derive the task due date from the alert's SLA expiry timestamp.
        # The RM must complete the task by this date or the alert goes stale.
        sla_expires = alert.get("sla_expires_at", "")
        due_date = self._iso_to_date(sla_expires)

        # Map alert type to the expected task type for Salesforce activity reporting.
        # FRAUD_FLAG and unknown types use "Other" to avoid incorrectly scheduling a call.
        task_type = {
            "CHURN_RISK":     "Call",     # RM should call the client to understand dissatisfaction
            "EXPANSION_OPTY": "Meeting",  # RM should meet client for proposal presentation
            "CURRENCY_RISK":  "Call",     # Urgent call to discuss hedging options
            "FRAUD_FLAG":     "Other",    # Compliance escalation; do NOT call client
            "PAYROLL_DELAY":  "Call",     # Call to assess liquidity situation
            "RENEWAL_DUE":    "Call",     # Renewal conversation call
        }.get(alert_type, "Other")

        # Task subject: [AfriFlow] prefix makes it easy to filter AfriFlow tasks in SF views
        subject = (
            f"[AfriFlow] {alert_type.replace('_', ' ').title()}: "
            f"{client_name}"
        )

        # Task description: full context the RM needs for client call preparation.
        # Structured so RMs can read it before dialling without switching to AfriFlow.
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
            status=_TASK_STATUS_OPEN,    # New tasks are always open until RM closes them
            type=task_type,
            custom_fields={
                # AfriFlow custom fields enable Salesforce reports and dashboards
                # to slice pipeline by AfriFlow alert type and source domain
                "AfriFlow_Alert_ID__c":        alert.get("alert_id", ""),
                "AfriFlow_Alert_Type__c":       alert_type,
                "AfriFlow_Revenue_At_Stake_ZAR__c": alert.get(
                    "revenue_at_stake_zar", 0
                ),
                # Semicolon-separated domain list maps to a multi-select custom field
                "AfriFlow_Domains_Triggered__c": "; ".join(
                    alert.get("domains_triggered", [])
                ),
            },
        )

    def _nba_to_opportunity(
        self, nba: Dict
    ) -> Optional[SalesforceOpportunity]:
        """
        Convert an AfriFlow NBA result into a Salesforce Opportunity payload.

        Only creates Opportunities for NBA scores >= 40 (minimum propensity
        threshold for pipeline tracking). Below 40, the signal is too weak
        to justify creating a pipeline record in Salesforce.

        Opportunity stage is derived from the NBA score using _NBA_SCORE_TO_STAGE:
          >= 80 → Proposal/Price Quote (RM should be preparing the term sheet)
          >= 60 → Needs Analysis (client conversation needed to validate fit)
          >= 40 → Prospecting (initial outreach justified)

        Close date defaults to 90 days from generation — typical CIB deal cycle.

        Who receives this opportunity: the RM is set after NBA result is linked
        to the client RM mapping in the calling pipeline.

        :param nba: NBA result dict with client_golden_id, client_name, top_action,
                    data_completeness_score, generated_at
        :return: SalesforceOpportunity or None if score < 40 or no top_action
        """
        top_action = nba.get("top_action")
        if not top_action:
            return None  # Cannot create an opportunity without a recommended action

        # Extract client and action details
        golden_id = nba.get("client_golden_id", "")
        client_name = nba.get("client_name", "Unknown")
        score = top_action.get("score", 0)           # NBA propensity score 0–100
        revenue = top_action.get("estimated_revenue_zar", 0)  # Estimated deal value in ZAR
        product = top_action.get("product_name", "Product")   # Product being recommended
        category = top_action.get("product_category", "CIB")  # CIB, PBB, Insurance, FX

        # Minimum score filter: below 40 the propensity signal is too weak for pipeline tracking
        if score < 40:
            return None

        # Translate golden ID to Salesforce Account ID for record linkage
        sf_account = self._client_ids.get(golden_id, golden_id)

        # Derive Salesforce pipeline stage from the NBA propensity score
        stage = self._score_to_stage(score)

        # Project the close date 90 days out — standard CIB deal cycle assumption
        close_date = self._iso_to_date(
            (datetime.now() + timedelta(days=90)).isoformat()
        )

        return SalesforceOpportunity(
            # [AfriFlow] prefix and "—" separator make the opportunity name readable and filterable
            name=f"[AfriFlow] {client_name} — {product}",
            account_id=sf_account,
            stage_name=stage,
            close_date=close_date,
            amount=revenue,     # Estimated deal revenue; informs Salesforce pipeline value
            description=(
                f"NBA Score: {score:.0f}/100\n"
                f"Category: {category}\n"
                f"Talking point: {top_action.get('rm_talking_point', '')}\n"
                f"Data completeness: "
                f"{nba.get('data_completeness_score', 0)*100:.0f}%\n"
                f"Generated: {nba.get('generated_at', '')}"
            ),
            owner_id="",  # Populated by calling pipeline once RM mapping is resolved
            custom_fields={
                # Custom fields drive AfriFlow pipeline analytics reports in Salesforce
                "AfriFlow_NBA_Score__c":          score,          # Raw score for threshold filtering
                "AfriFlow_Product_Category__c":   category,       # CIB / PBB / Insurance / FX
                "AfriFlow_Client_Golden_ID__c":   golden_id,      # Links back to AfriFlow entity
                "AfriFlow_Generated_At__c":       nba.get("generated_at", ""),  # For staleness checks
            },
        )

    def _outcome_to_task_update(
        self, update: Dict
    ) -> Optional[SalesforceTask]:
        """
        Convert an AfriFlow outcome record into a Salesforce Task closure update.

        When an RM records an outcome (CONVERTED, REJECTED, EXPIRED, or FALSE_POSITIVE),
        this creates a Salesforce Task that closes the original alert's activity.
        IN_PROGRESS outcomes leave the task open to reflect ongoing work.

        This creates an audit trail in Salesforce: every AfriFlow alert that
        reaches an outcome has a corresponding closed Task with the outcome notes,
        actual revenue, and resolution timestamp.

        Who receives this task: the RM who actioned the original alert.
        Urgency routing: always Normal priority (outcome recording is administrative).

        :param update: Outcome update dict with alert_id, outcome, rm_id, rm_notes,
                       actual_revenue_zar, client_golden_id, recorded_at
        :return: SalesforceTask (open if IN_PROGRESS, closed otherwise)
        """
        alert_id = update.get("alert_id", "")
        outcome = update.get("outcome", "")
        rm_id = update.get("rm_id", "")
        notes = update.get("rm_notes", "")  # RM's free-text qualitative explanation

        # Resolve RM's Salesforce User ID for the task owner field
        sf_owner = self._rm_ids.get(rm_id, rm_id)

        # Determine task status: terminal outcomes close the task; IN_PROGRESS keeps it open.
        # Deduplication note: the alert_id in custom_fields allows idempotent upserts.
        status = (
            _TASK_STATUS_DONE
            if outcome in ("CONVERTED", "REJECTED", "EXPIRED", "FALSE_POSITIVE")
            else _TASK_STATUS_OPEN   # IN_PROGRESS: RM is still working the opportunity
        )

        return SalesforceTask(
            # Subject includes the original alert ID to link the closure to the original task
            subject=f"[AfriFlow] Outcome Update: {alert_id}",
            description=(
                f"Outcome: {outcome}\n"
                f"Revenue: R{update.get('actual_revenue_zar', 0):,.0f}\n"
                f"Notes: {notes}\n"
                f"Recorded: {update.get('recorded_at', '')}"
            ),
            owner_id=sf_owner,
            # Resolve the Salesforce Account ID for the client associated with this outcome
            what_id=self._client_ids.get(
                update.get("client_golden_id", ""), ""
            ),
            # Activity date is today: outcome was recorded now
            activity_date=self._iso_to_date(datetime.now().isoformat()),
            priority=_TASK_PRIORITY_NORMAL,  # Outcome recording is administrative, not urgent
            status=status,
            type="Other",   # Outcome updates are administrative; not a specific activity type
            custom_fields={
                # Custom fields enable cross-referencing outcomes in Salesforce analytics
                "AfriFlow_Alert_ID__c":             alert_id,   # Links closure to original alert
                "AfriFlow_Outcome__c":              outcome,    # CONVERTED / REJECTED / EXPIRED etc.
                "AfriFlow_Actual_Revenue_ZAR__c":   update.get(
                    "actual_revenue_zar", 0
                ),  # Actual revenue for pipeline accuracy reporting
            },
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _iso_to_date(self, iso_str: str) -> str:
        """
        Extract a YYYY-MM-DD date string from an ISO 8601 datetime string.

        Salesforce date fields (activity_date, close_date) require YYYY-MM-DD
        format, not the full ISO datetime that AfriFlow uses internally.
        Falls back to today's date if the input string is empty or malformed.

        :param iso_str: ISO 8601 datetime string e.g. '2026-03-18T14:30:00'
        :return: Date portion as string e.g. '2026-03-18'
        """
        if not iso_str:
            return datetime.now().strftime("%Y-%m-%d")  # Default to today if no timestamp
        return iso_str[:10]  # Slice first 10 characters: 'YYYY-MM-DD'

    def _score_to_stage(self, score: float) -> str:
        """
        Map an NBA propensity score to a Salesforce Opportunity stage name.

        Iterates through _NBA_SCORE_TO_STAGE from highest to lowest threshold
        and returns the first matching stage. The final entry (threshold 0) acts
        as a catch-all for any score that doesn't match the higher thresholds.

        :param score: NBA propensity score in range 0–100
        :return: Salesforce Opportunity stage name string
        """
        # Iterate threshold entries from highest to lowest
        for threshold, stage in _NBA_SCORE_TO_STAGE:
            if score >= threshold:
                return stage  # Return first matching stage (highest applicable threshold)
        return "Qualification"  # Fallback: should not be reached due to the (0, ...) entry
