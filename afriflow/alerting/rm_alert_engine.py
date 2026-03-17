"""
Relationship Manager Alert Engine

We push prioritised, time-sensitive alerts to RMs when the
cross-domain pipeline detects an actionable event for one
of their clients.

Alert types:
  CHURN_RISK     — Client showing attrition signals; intervene now
  EXPANSION_OPTY — Client expanding into new market; sell coverage
  CURRENCY_RISK  — Unhedged corridor exposure spiked
  PAYROLL_DELAY  — Corporate client payroll missed/delayed
  FRAUD_FLAG     — Cross-domain fraud pattern detected
  CLV_UPLIFT     — Data shadow closed; CLV revised upward
  RENEWAL_DUE    — Insurance policy renewal approaching

Each alert includes:
  - A pre-drafted RM talking point
  - The supporting evidence (which domains fired)
  - A suggested call-to-action
  - SLA: how many hours until the opportunity is stale

Alerts are ranked by (urgency × revenue_at_stake) so RMs
see the most valuable action first.

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Alert type registry
# ---------------------------------------------------------------------------

# SLA hours by alert type (how long the opportunity is live)
_ALERT_SLA_HOURS: Dict[str, int] = {
    "CHURN_RISK":      48,
    "EXPANSION_OPTY":  168,   # 1 week
    "CURRENCY_RISK":   24,
    "PAYROLL_DELAY":   72,
    "FRAUD_FLAG":      4,
    "CLV_UPLIFT":      336,   # 2 weeks
    "RENEWAL_DUE":     720,   # 30 days
}

# Revenue urgency multiplier by alert type
_URGENCY_MULTIPLIER: Dict[str, float] = {
    "FRAUD_FLAG":      10.0,
    "CHURN_RISK":       5.0,
    "CURRENCY_RISK":    4.0,
    "PAYROLL_DELAY":    3.0,
    "EXPANSION_OPTY":   2.0,
    "RENEWAL_DUE":      1.5,
    "CLV_UPLIFT":       1.2,
}


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class RMAlert:
    """
    A single alert for a relationship manager.

    priority_score : (revenue_at_stake × urgency_multiplier) / 1_000_000
                     normalised to 0–100 for display purposes
    """

    alert_id: str
    rm_id: str
    client_golden_id: str
    client_name: str
    alert_type: str
    priority_score: float
    revenue_at_stake_zar: float
    sla_expires_at: str
    talking_point: str
    supporting_evidence: List[str]
    call_to_action: str
    domains_triggered: List[str]
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    acknowledged: bool = False
    actioned: bool = False


@dataclass
class RMAlertBatch:
    """All pending alerts for a single RM, ranked by priority."""

    rm_id: str
    alerts: List[RMAlert]
    total_revenue_at_stake_zar: float
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    @property
    def top_alert(self) -> Optional[RMAlert]:
        return self.alerts[0] if self.alerts else None


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

class RMAlertEngine:
    """
    Generate and rank alerts for relationship managers.

    Consumes NBA results, churn predictions, anomaly detections,
    and currency events to produce a prioritised RM action queue.

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
        """Build ranked alert batch for one RM across all their clients."""

        all_alerts: List[RMAlert] = []

        for cs in client_signals:
            alerts = self._process_client(rm_id, cs)
            all_alerts.extend(alerts)

        # Sort by priority score descending
        all_alerts.sort(key=lambda a: a.priority_score, reverse=True)

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
        alerts: List[RMAlert] = []
        golden_id = cs.get("golden_id", "UNKNOWN")
        client_name = cs.get("client_name", "Unknown Client")

        # --- Churn risk ---
        churn = cs.get("churn_prediction")
        if churn and churn.get("churn_band") in ("RED", "CRITICAL"):
            alerts.append(self._build_churn_alert(
                rm_id, golden_id, client_name, churn
            ))

        # --- NBA expansion opportunity ---
        nba = cs.get("nba_result")
        if nba and nba.get("top_action"):
            action = nba["top_action"]
            if action.get("action_type") == "SELL" and action.get("score", 0) >= 60:
                alerts.append(self._build_nba_alert(
                    rm_id, golden_id, client_name, action
                ))

        # --- Currency events ---
        for event in cs.get("currency_events", []):
            if event.get("severity") in ("HIGH", "CRITICAL"):
                alerts.append(self._build_currency_alert(
                    rm_id, golden_id, client_name, event
                ))

        # --- Payroll delay ---
        for ps in cs.get("payroll_signals", []):
            if ps.get("days_late", 0) >= 3:
                alerts.append(self._build_payroll_alert(
                    rm_id, golden_id, client_name, ps
                ))

        # --- Fraud flags ---
        for anomaly in cs.get("anomalies", []):
            if anomaly.get("requires_sar", False):
                alerts.append(self._build_fraud_alert(
                    rm_id, golden_id, client_name, anomaly
                ))

        return alerts

    # ------------------------------------------------------------------
    # Alert builders
    # ------------------------------------------------------------------

    def _build_churn_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, churn: Dict
    ) -> RMAlert:
        band = churn.get("churn_band", "RED")
        revenue = churn.get("revenue_at_risk_zar", 0)
        signal = churn.get("primary_signal", "unknown").replace("_", " ")
        intervention = churn.get("recommended_intervention", "")
        score = churn.get("churn_score", 50)

        priority = self._priority(revenue, "CHURN_RISK")
        sla = self._sla_expiry("CHURN_RISK")

        return RMAlert(
            alert_id=f"ALERT-CHURN-{golden_id}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="CHURN_RISK",
            priority_score=priority,
            revenue_at_stake_zar=revenue,
            sla_expires_at=sla,
            talking_point=(
                f"{client_name} is showing {band.lower()} churn signals "
                f"(score {score:.0f}/100). Primary driver: {signal}."
            ),
            supporting_evidence=[
                f"Churn band: {band}",
                f"Primary signal: {signal}",
                f"Revenue at risk: R{revenue:,.0f}",
            ],
            call_to_action=intervention,
            domains_triggered=["cib", "forex", "cell"],
        )

    def _build_nba_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, action: Dict
    ) -> RMAlert:
        product = action.get("product_name", "Product")
        revenue = action.get("estimated_revenue_zar", 0)
        talking_point = action.get("rm_talking_point", "")
        urgency = action.get("urgency", "MEDIUM")
        category = action.get("product_category", "CIB")

        alert_type = "EXPANSION_OPTY"
        priority = self._priority(revenue, alert_type)
        sla = self._sla_expiry(alert_type)

        return RMAlert(
            alert_id=f"ALERT-NBA-{golden_id}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type=alert_type,
            priority_score=priority,
            revenue_at_stake_zar=revenue,
            sla_expires_at=sla,
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
            domains_triggered=[
                f.get("domain", "unknown")
                for f in action.get("features", [])
            ],
        )

    def _build_currency_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, event: Dict
    ) -> RMAlert:
        currency_pair = event.get("currency_pair", "?/ZAR")
        move_pct = event.get("move_pct", 0) * 100
        direction = event.get("direction", "")
        exposure = event.get("client_exposure_zar", 0)

        priority = self._priority(exposure * 0.05, "CURRENCY_RISK")
        sla = self._sla_expiry("CURRENCY_RISK")

        return RMAlert(
            alert_id=f"ALERT-FX-{golden_id}-{currency_pair.replace('/', '')}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="CURRENCY_RISK",
            priority_score=priority,
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
            domains_triggered=["forex", "cib"],
        )

    def _build_payroll_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, signal: Dict
    ) -> RMAlert:
        days_late = signal.get("days_late", 0)
        employee_count = signal.get("employee_count", 0)
        amount = signal.get("payroll_amount_zar", 0)

        priority = self._priority(amount * 0.01, "PAYROLL_DELAY")
        sla = self._sla_expiry("PAYROLL_DELAY")

        return RMAlert(
            alert_id=f"ALERT-PAY-{golden_id}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="PAYROLL_DELAY",
            priority_score=priority,
            revenue_at_stake_zar=amount * 0.01,
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
            domains_triggered=["pbb", "cell"],
        )

    def _build_fraud_alert(
        self, rm_id: str, golden_id: str,
        client_name: str, anomaly: Dict
    ) -> RMAlert:
        pattern = anomaly.get("pattern_type", "UNKNOWN")
        score = anomaly.get("anomaly_score", 0)
        domains = anomaly.get("contributing_domains", [])

        priority = self._priority(5_000_000, "FRAUD_FLAG")  # Flag as critical
        sla = self._sla_expiry("FRAUD_FLAG")

        return RMAlert(
            alert_id=f"ALERT-FRAUD-{golden_id}-{pattern}",
            rm_id=rm_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="FRAUD_FLAG",
            priority_score=priority,
            revenue_at_stake_zar=0.0,
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
            call_to_action=(
                "Escalate to Financial Crime Compliance immediately. "
                "Do not contact client before compliance review."
            ),
            domains_triggered=domains,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _priority(self, revenue: float, alert_type: str) -> float:
        multiplier = _URGENCY_MULTIPLIER.get(alert_type, 1.0)
        raw = (revenue * multiplier) / 1_000_000
        return min(round(raw, 1), 100.0)

    def _sla_expiry(self, alert_type: str) -> str:
        hours = _ALERT_SLA_HOURS.get(alert_type, 48)
        expiry = datetime.now() + timedelta(hours=hours)
        return expiry.isoformat()
