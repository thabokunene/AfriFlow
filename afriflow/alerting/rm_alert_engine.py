"""
@file rm_alert_engine.py
@description Generates prioritised, time-sensitive alerts for relationship
             managers (RMs) when the AfriFlow cross-domain pipeline detects an
             actionable event for one of their clients. Covers churn risk,
             expansion opportunities, currency risk, payroll delay, fraud flags,
             and CLV uplift signals. Alerts are ranked by a priority score
             (urgency multiplier × revenue at stake) so RMs always see their
             most valuable action first.
@author Thabo Kunene
@created 2026-03-18
"""

# Relationship Manager Alert Engine
#
# We push prioritised, time-sensitive alerts to RMs when the
# cross-domain pipeline detects an actionable event for one
# of their clients.
#
# Alert types:
#   CHURN_RISK     — Client showing attrition signals; intervene now
#   EXPANSION_OPTY — Client expanding into new market; sell coverage
#   CURRENCY_RISK  — Unhedged corridor exposure spiked
#   PAYROLL_DELAY  — Corporate client payroll missed/delayed
#   FRAUD_FLAG     — Cross-domain fraud pattern detected
#   CLV_UPLIFT     — Data shadow closed; CLV revised upward
#   RENEWAL_DUE    — Insurance policy renewal approaching
#
# Each alert includes:
#   - A pre-drafted RM talking point
#   - The supporting evidence (which domains fired)
#   - A suggested call-to-action
#   - SLA: how many hours until the opportunity is stale
#
# Alerts are ranked by (urgency × revenue_at_stake) so RMs
# see the most valuable action first.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

from __future__ import annotations  # PEP 563: postponed annotation evaluation

from dataclasses import dataclass, field  # Structured data containers with auto-__init__
from datetime import datetime, timedelta  # Alert creation timestamps and SLA expiry calculation
from typing import Dict, List, Optional   # Type annotations for IDE support and clarity


# ---------------------------------------------------------------------------
# Alert type configuration registries
# ---------------------------------------------------------------------------

# SLA hours by alert type: how long the opportunity remains valid before it goes stale.
# These values reflect the business tempo of each signal type:
#   FRAUD_FLAG is critical and must be escalated within 4 hours.
#   CLV_UPLIFT is a strategic signal valid for up to 2 weeks.
_ALERT_SLA_HOURS: Dict[str, int] = {
    "CHURN_RISK":      48,   # 48h: churn signals are urgent but can wait overnight
    "EXPANSION_OPTY":  168,  # 168h (1 week): expansion is strategic; client may be mid-deal
    "CURRENCY_RISK":   24,   # 24h: rate moves are time-sensitive; next business day maximum
    "PAYROLL_DELAY":   72,   # 72h: payroll situations evolve quickly; 3 days to act
    "FRAUD_FLAG":      4,    # 4h: compliance escalation required same day; do not delay
    "CLV_UPLIFT":      336,  # 336h (2 weeks): CLV revision is strategic, not urgent
    "RENEWAL_DUE":     720,  # 720h (30 days): renewal conversations have a long runway
}

# Urgency multiplier by alert type: weights the revenue at stake for priority scoring.
# Higher multiplier = alert appears earlier in the RM's action queue regardless of revenue size.
# FRAUD_FLAG has the highest multiplier (10×) because compliance risk is non-negotiable.
_URGENCY_MULTIPLIER: Dict[str, float] = {
    "FRAUD_FLAG":      10.0,  # Compliance-critical; must surface regardless of revenue size
    "CHURN_RISK":       5.0,  # High urgency: revenue at risk if RM does not act quickly
    "CURRENCY_RISK":    4.0,  # Time-sensitive: rates move; hedging window closes
    "PAYROLL_DELAY":    3.0,  # Operational distress signal; client may need emergency facility
    "EXPANSION_OPTY":   2.0,  # Strategic opportunity; high value but not urgent
    "RENEWAL_DUE":      1.5,  # Renewal has a long runway; lower multiplier
    "CLV_UPLIFT":       1.2,  # Informational uplift; lowest urgency multiplier
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RMAlert:
    """
    A single alert for a relationship manager.

    priority_score: computed as (revenue_at_stake × urgency_multiplier) / 1_000_000,
                    capped at 100 for display purposes. Higher = show first in queue.

    :param alert_id: Unique ID with prefix ALERT-<TYPE>-<GOLDEN_ID>[-<PAIR>]
    :param rm_id: ID of the relationship manager who owns this client
    :param client_golden_id: Unified client ID from entity resolution
    :param client_name: Human-readable client name for the RM's dashboard
    :param alert_type: CHURN_RISK / EXPANSION_OPTY / CURRENCY_RISK / PAYROLL_DELAY /
                       FRAUD_FLAG / CLV_UPLIFT / RENEWAL_DUE
    :param priority_score: Computed priority 0–100; higher = more important
    :param revenue_at_stake_zar: ZAR revenue at risk or opportunity value
    :param sla_expires_at: ISO timestamp; alert is stale after this time
    :param talking_point: Pre-drafted opening for the RM's client conversation
    :param supporting_evidence: List of evidence bullets (domain signals that fired)
    :param call_to_action: Specific recommended next step for the RM
    :param domains_triggered: List of AfriFlow domains that contributed to this alert
    :param created_at: ISO timestamp of alert creation
    :param acknowledged: True if the RM has seen the alert
    :param actioned: True if the RM has logged an action against the alert
    """

    alert_id: str
    rm_id: str
    client_golden_id: str
    client_name: str
    alert_type: str
    priority_score: float          # 0–100; drives sort order in RM dashboard
    revenue_at_stake_zar: float    # Revenue at risk (churn) or opportunity (expansion)
    sla_expires_at: str            # ISO datetime; after this the alert is considered stale
    talking_point: str             # Pre-drafted conversation opener for the RM
    supporting_evidence: List[str] # Bullet points of the cross-domain evidence
    call_to_action: str            # Specific recommended action for the RM
    domains_triggered: List[str]   # Which AfriFlow domains fired to generate this alert
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()  # Auto-stamped at creation
    )
    acknowledged: bool = False  # True = RM has opened/viewed the alert
    actioned: bool = False      # True = RM has logged a follow-up action


@dataclass
class RMAlertBatch:
    """All pending alerts for a single RM, ranked by priority score descending.

    :param rm_id: ID of the relationship manager this batch belongs to
    :param alerts: Priority-sorted list of RMAlert objects (highest score first)
    :param total_revenue_at_stake_zar: Sum of revenue_at_stake_zar across all alerts
    :param generated_at: ISO timestamp when the batch was built
    """

    rm_id: str
    alerts: List[RMAlert]
    total_revenue_at_stake_zar: float   # KPI: total revenue in this RM's action queue
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    @property
    def top_alert(self) -> Optional[RMAlert]:
        """Return the highest-priority alert in the batch, or None if empty."""
        return self.alerts[0] if self.alerts else None


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

class RMAlertEngine:
    """
    Generate and rank alerts for relationship managers.

    Consumes NBA results, churn predictions, anomaly detections, and currency
    events to produce a prioritised RM action queue. Each client's signals are
    processed through type-specific alert builders that format pre-drafted
    talking points, evidence bullets, and call-to-actions.

    Intended recipient: relationship managers (commercial and CIB).

    Usage::

        engine = RMAlertEngine()
        batch = engine.build_alert_batch(
            rm_id="RM-00142",
            client_signals=[
                {
                    "golden_id": "GLD-001",
                    "client_name": "Acme Logistics Ltd",
                    "churn_prediction": {...},
                    "nba_result": {...},
                    "anomalies": [...],
                    "currency_events": [...],
                    "payroll_signals": [...],
                }
            ],
        )
    """

    def build_alert_batch(
        self,
        rm_id: str,
        client_signals: List[Dict],
    ) -> RMAlertBatch:
        """
        Build a ranked alert batch for one RM across all of their clients.

        Iterates over every client signal record, generates applicable alerts
        per client, and sorts the combined list by priority score descending
        so the RM's most important action is always at the top.

        :param rm_id: Relationship manager identifier
        :param client_signals: List of client signal dicts from the pipeline
        :return: RMAlertBatch sorted by priority_score descending
        """
        all_alerts: List[RMAlert] = []

        # Process each client's cross-domain signals and collect all generated alerts
        for cs in client_signals:
            alerts = self._process_client(rm_id, cs)
            all_alerts.extend(alerts)

        # Sort by priority score descending: highest-value/urgency actions appear first
        all_alerts.sort(key=lambda a: a.priority_score, reverse=True)

        # KPI: total revenue represented in this RM's alert queue
        total_revenue = sum(
            a.revenue_at_stake_zar for a in all_alerts
        )

        return RMAlertBatch(
            rm_id=rm_id,
            alerts=all_alerts,
            total_revenue_at_stake_zar=total_revenue,
        )

    def _process_client(
        self, rm_id: str, cs: Dict
    ) -> List[RMAlert]:
        """
        Process all signal types for a single client and return relevant alerts.

        Each signal type is evaluated independently; multiple alert types can
        fire for the same client in the same batch (e.g. churn + currency risk).

        :param rm_id: Relationship manager identifier
        :param cs: Client signal dict with golden_id, client_name, churn_prediction,
                   nba_result, currency_events, payroll_signals, anomalies
        :return: List of RMAlert objects for this client (may be empty)
        """
        alerts: List[RMAlert] = []
        golden_id = cs.get("golden_id", "UNKNOWN")
        client_name = cs.get("client_name", "Unknown Client")

        # --- Signal type 1: Churn risk ---
        # Triggers when the churn model assigns the client a RED or CRITICAL band.
        # RED = elevated churn probability; CRITICAL = imminent attrition.
        churn = cs.get("churn_prediction")
        if churn and churn.get("churn_band") in ("RED", "CRITICAL"):
            alerts.append(self._build_churn_alert(
                rm_id, golden_id, client_name, churn
            ))

        # --- Signal type 2: NBA expansion opportunity ---
        # Triggers when the NBA engine's top action is a SELL recommendation
        # with a score ≥ 60 (i.e. moderate-to-high propensity to buy).
        nba = cs.get("nba_result")
        if nba and nba.get("top_action"):
            action = nba["top_action"]
            if action.get("action_type") == "SELL" and action.get("score", 0) >= 60:
                alerts.append(self._build_nba_alert(
                    rm_id, golden_id, client_name, action
                ))

        # --- Signal type 3: Currency risk events ---
        # Triggers for each HIGH or CRITICAL severity currency event affecting the client.
        # One alert per event (multiple pairs can fire for the same client).
        for event in cs.get("currency_events", []):
            if event.get("severity") in ("HIGH", "CRITICAL"):
                alerts.append(self._build_currency_alert(
                    rm_id, golden_id, client_name, event
                ))

        # --- Signal type 4: Payroll delay ---
        # Triggers when a corporate client's payroll is 3 or more days late.
        # This signals potential liquidity stress or operational disruption.
        for ps in cs.get("payroll_signals", []):
            if ps.get("days_late", 0) >= 3:
                alerts.append(self._build_payroll_alert(
                    rm_id, golden_id, client_name, ps
                ))

        # --- Signal type 5: Fraud flags ---
        # Triggers for anomalies flagged as requiring a Suspicious Activity Report (SAR).
        # SAR-required anomalies have the highest urgency multiplier (10×).
        for anomaly in cs.get("anomalies", []):
            if anomaly.get("requires_sar", False):
                alerts.append(self._build_fraud_alert(
                    rm_id, golden_id, client_name, anomaly
                ))

        return alerts

    # ------------------------------------------------------------------
    # Alert builders: one per alert type
    # ------------------------------------------------------------------

    def _build_churn_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, churn: Dict
    ) -> RMAlert:
        """
        Build a CHURN_RISK alert from a churn prediction result.

        Business event: the churn model has assigned the client a RED or CRITICAL
        band, indicating elevated attrition probability. The RM should contact the
        client within the 48-hour SLA to understand dissatisfaction and intervene.

        :param rm_id: RM identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param churn: Churn prediction dict with churn_band, churn_score,
                      revenue_at_risk_zar, primary_signal, recommended_intervention
        :return: RMAlert configured for CHURN_RISK
        """
        band = churn.get("churn_band", "RED")
        revenue = churn.get("revenue_at_risk_zar", 0)
        # Convert snake_case signal to readable form for the talking point
        signal = churn.get("primary_signal", "unknown").replace("_", " ")
        intervention = churn.get("recommended_intervention", "")
        score = churn.get("churn_score", 50)

        # Priority score uses revenue × 5× urgency multiplier / R1m normaliser
        priority = self._priority(revenue, "CHURN_RISK")
        sla = self._sla_expiry("CHURN_RISK")  # 48-hour SLA for churn alerts

        return RMAlert(
            alert_id=f"ALERT-CHURN-{golden_id}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="CHURN_RISK",
            priority_score=priority,
            revenue_at_stake_zar=revenue,
            sla_expires_at=sla,
            # Pre-drafted talking point includes band, score, and primary driver
            talking_point=(
                f"{client_name} is showing {band.lower()} churn signals "
                f"(score {score:.0f}/100). Primary driver: {signal}."
            ),
            # Evidence bullets help the RM understand what the model detected
            supporting_evidence=[
                f"Churn band: {band}",
                f"Primary signal: {signal}",
                f"Revenue at risk: R{revenue:,.0f}",
            ],
            call_to_action=intervention,  # Recommended intervention from the churn model
            # Churn is a cross-domain signal: CIB, forex, and cell data all contribute
            domains_triggered=["cib", "forex", "cell"],
        )

    def _build_nba_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, action: Dict
    ) -> RMAlert:
        """
        Build an EXPANSION_OPTY alert from an NBA (Next Best Action) result.

        Business event: the NBA engine recommends a specific product to sell to
        the client with a propensity score ≥ 60. The RM should prepare a proposal
        and schedule a client meeting within the 1-week SLA.

        :param rm_id: RM identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param action: NBA top_action dict with product_name, score, estimated_revenue_zar,
                       rm_talking_point, urgency, product_category, features
        :return: RMAlert configured for EXPANSION_OPTY
        """
        product = action.get("product_name", "Product")
        revenue = action.get("estimated_revenue_zar", 0)
        talking_point = action.get("rm_talking_point", "")  # Pre-generated by NBA engine
        urgency = action.get("urgency", "MEDIUM")
        category = action.get("product_category", "CIB")

        alert_type = "EXPANSION_OPTY"
        priority = self._priority(revenue, alert_type)
        sla = self._sla_expiry(alert_type)  # 1-week SLA for expansion opportunities

        return RMAlert(
            alert_id=f"ALERT-NBA-{golden_id}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type=alert_type,
            priority_score=priority,
            revenue_at_stake_zar=revenue,
            sla_expires_at=sla,
            # The NBA engine generates the talking point; RM engine passes it through
            talking_point=talking_point,
            supporting_evidence=[
                f"Product: {product}",
                f"Category: {category}",
                f"NBA score: {action.get('score', 0):.0f}/100",
                f"Urgency: {urgency}",
            ],
            call_to_action=(
                f"Prepare {product} proposal and schedule client meeting."
            ),
            # Domain triggers are extracted from the NBA feature list
            domains_triggered=[
                f.get("domain", "unknown")
                for f in action.get("features", [])
            ],
        )

    def _build_currency_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, event: Dict
    ) -> RMAlert:
        """
        Build a CURRENCY_RISK alert from a currency event dict.

        Business event: a HIGH or CRITICAL currency event has been detected for
        a pair where the client has unhedged exposure. The RM should contact the
        client within the 24-hour SLA to present FX hedging options.

        Revenue at stake is estimated at 0.35% of exposure (indicative FX margin).
        Priority is computed at 5% of exposure (the delta on a 5% rate move).

        :param rm_id: RM identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param event: Currency event dict with currency_pair, move_pct, direction,
                      client_exposure_zar
        :return: RMAlert configured for CURRENCY_RISK
        """
        currency_pair = event.get("currency_pair", "?/ZAR")
        move_pct = event.get("move_pct", 0) * 100  # Convert to percentage for display
        direction = event.get("direction", "")
        exposure = event.get("client_exposure_zar", 0)

        # Priority uses 5% of exposure as a proxy for the dollar-move on the position
        priority = self._priority(exposure * 0.05, "CURRENCY_RISK")
        sla = self._sla_expiry("CURRENCY_RISK")  # 24-hour SLA for currency alerts

        return RMAlert(
            alert_id=f"ALERT-FX-{golden_id}-{currency_pair.replace('/', '')}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="CURRENCY_RISK",
            priority_score=priority,
            # Revenue estimate: 0.35% of exposure as indicative FX hedging margin
            revenue_at_stake_zar=exposure * 0.0035,
            sla_expires_at=sla,
            talking_point=(
                f"{currency_pair} moved {move_pct:.1f}% {direction}. "
                f"{client_name} has R{exposure:,.0f} unhedged exposure."
            ),
            supporting_evidence=[
                f"Currency pair: {currency_pair}",
                f"Move: {move_pct:.1f}%",
                f"Client exposure: R{exposure:,.0f}",
            ],
            call_to_action=(
                f"Call client within 24 hours. "
                f"Present FX hedging options for {currency_pair}."
            ),
            # Currency risk alerts are driven by forex and CIB domain data
            domains_triggered=["forex", "cib"],
        )

    def _build_payroll_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, signal: Dict
    ) -> RMAlert:
        """
        Build a PAYROLL_DELAY alert from a payroll signal dict.

        Business event: a corporate client's payroll is 3 or more days late.
        This signals potential cash flow stress or operational disruption. The RM
        should contact the client within the 72-hour SLA to assess the situation
        and offer emergency working capital if appropriate.

        Revenue is estimated at 1% of payroll amount (emergency overdraft fees).

        :param rm_id: RM identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param signal: Payroll signal dict with days_late, employee_count, payroll_amount_zar
        :return: RMAlert configured for PAYROLL_DELAY
        """
        days_late = signal.get("days_late", 0)
        employee_count = signal.get("employee_count", 0)
        amount = signal.get("payroll_amount_zar", 0)

        # Priority uses 1% of payroll amount (emergency facility fee estimate)
        priority = self._priority(amount * 0.01, "PAYROLL_DELAY")
        sla = self._sla_expiry("PAYROLL_DELAY")  # 72-hour SLA

        return RMAlert(
            alert_id=f"ALERT-PAY-{golden_id}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="PAYROLL_DELAY",
            priority_score=priority,
            revenue_at_stake_zar=amount * 0.01,  # 1% of payroll as emergency facility revenue
            sla_expires_at=sla,
            talking_point=(
                f"{client_name} payroll of R{amount:,.0f} for "
                f"{employee_count:,} employees is {days_late} days late. "
                f"Potential liquidity issue or operational disruption."
            ),
            supporting_evidence=[
                f"Days late: {days_late}",
                f"Employee count: {employee_count:,}",
                f"Payroll amount: R{amount:,.0f}",
            ],
            call_to_action=(
                "Contact client to assess liquidity situation. "
                "Consider emergency overdraft or working capital facility."
            ),
            # Payroll signals are detected via PBB transaction data and cell network signals
            domains_triggered=["pbb", "cell"],
        )

    def _build_fraud_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, anomaly: Dict
    ) -> RMAlert:
        """
        Build a FRAUD_FLAG alert from a cross-domain anomaly detection result.

        Business event: the anomaly detection model has identified a cross-domain
        pattern consistent with fraud or financial crime, and has flagged that a
        Suspicious Activity Report (SAR) may be required. The RM must escalate to
        Financial Crime Compliance immediately (4-hour SLA). The RM should NOT
        contact the client before the compliance review is complete.

        Priority is set using a fixed R5m revenue proxy to ensure all fraud alerts
        surface at the top of the RM queue regardless of actual deal size.

        :param rm_id: RM identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param anomaly: Anomaly dict with pattern_type, anomaly_score,
                        contributing_domains, narrative, requires_sar
        :return: RMAlert configured for FRAUD_FLAG
        """
        pattern = anomaly.get("pattern_type", "UNKNOWN")
        score = anomaly.get("anomaly_score", 0)
        domains = anomaly.get("contributing_domains", [])  # Domains that contributed to detection

        # Use R5m as a fixed proxy revenue to push fraud alerts to the top of the queue.
        # The 10× urgency multiplier ensures compliance alerts always rank #1.
        priority = self._priority(5_000_000, "FRAUD_FLAG")  # Flag as critical
        sla = self._sla_expiry("FRAUD_FLAG")  # 4-hour SLA: same-day compliance escalation

        return RMAlert(
            alert_id=f"ALERT-FRAUD-{golden_id}-{pattern}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="FRAUD_FLAG",
            priority_score=priority,
            revenue_at_stake_zar=0.0,  # Fraud alerts have no revenue opportunity; compliance only
            sla_expires_at=sla,
            talking_point=(
                f"Cross-domain anomaly detected for {client_name}: "
                f"{pattern.replace('_', ' ').title()} "
                f"(score {score:.0f}/100). SAR may be required."
            ),
            supporting_evidence=[
                f"Pattern: {pattern}",
                f"Anomaly score: {score:.0f}/100",
                f"Domains: {', '.join(domains)}",
                f"Narrative: {anomaly.get('narrative', '')}",
            ],
            # Critical compliance instruction: do not tip off client before review
            call_to_action=(
                "Escalate to Financial Crime Compliance immediately. "
                "Do not contact client before compliance review."
            ),
            domains_triggered=domains,  # All domains that contributed to the anomaly
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _priority(self, revenue: float, alert_type: str) -> float:
        """
        Compute a normalised priority score for an alert.

        Formula: (revenue × urgency_multiplier) / 1_000_000, capped at 100.
        The division by R1m normalises the score to a 0–100 range for typical
        CIB deal sizes. Alerts with revenue > R100m / multiplier will be capped at 100.

        :param revenue: Revenue at stake or opportunity size in ZAR
        :param alert_type: Alert type used to look up the urgency multiplier
        :return: Priority score 0.0–100.0
        """
        multiplier = _URGENCY_MULTIPLIER.get(alert_type, 1.0)  # Default 1× if type unknown
        raw = (revenue * multiplier) / 1_000_000
        return min(round(raw, 1), 100.0)  # Cap at 100; round to 1dp for clean display

    def _sla_expiry(self, alert_type: str) -> str:
        """
        Compute the SLA expiry timestamp for an alert type.

        Returns the ISO timestamp of the alert expiry by adding the configured
        SLA hours to the current time. Defaults to 48 hours for unknown types.

        :param alert_type: Alert type used to look up the SLA hours
        :return: ISO datetime string of the SLA expiry
        """
        hours = _ALERT_SLA_HOURS.get(alert_type, 48)  # Default 48h for unknown alert types
        expiry = datetime.now() + timedelta(hours=hours)
        return expiry.isoformat()
