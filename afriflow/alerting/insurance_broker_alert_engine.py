"""
Insurance Broker Alert Engine

Generates alerts for insurance brokers covering:

  RENEWAL_DUE     — Policy expiry within 60/30/14/7 days
  COVERAGE_GAP    — Client's CIB corridor or workforce not covered
  CLAIM_SURGE     — Claim frequency spike suggests systemic issue
  UNDERINSURANCE  — Sum assured < 60% of estimated asset value
  FREE_LOOK_END   — Free-look period ending; client may cancel

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class InsuranceBrokerAlert:
    alert_id: str
    broker_id: str
    client_golden_id: str
    client_name: str
    alert_type: str
    urgency: str
    policy_id: Optional[str]
    headline: str
    details: str
    recommended_action: str
    estimated_premium_zar: float
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class InsuranceBrokerAlertBatch:
    broker_id: str
    alerts: List[InsuranceBrokerAlert]
    total_premium_at_risk_zar: float
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class InsuranceBrokerAlertEngine:
    """
    Generate insurance broker alerts from insurance and CIB profiles.

    Usage::

        engine = InsuranceBrokerAlertEngine()
        batch = engine.build_batch(
            broker_id="BRK-012",
            client_portfolio=[
                {
                    "golden_id": "GLD-001",
                    "client_name": "Acme",
                    "insurance_profile": {...},
                    "cib_profile": {...},
                }
            ],
        )
    """

    _RENEWAL_THRESHOLDS = [7, 14, 30, 60]   # days before expiry

    def build_batch(
        self,
        broker_id: str,
        client_portfolio: List[Dict],
    ) -> InsuranceBrokerAlertBatch:
        alerts: List[InsuranceBrokerAlert] = []

        for client in client_portfolio:
            alerts.extend(self._process_client(broker_id, client))

        alerts.sort(
            key=lambda a: {"IMMEDIATE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                a.urgency, 9
            )
        )

        total_at_risk = sum(a.estimated_premium_zar for a in alerts)

        return InsuranceBrokerAlertBatch(
            broker_id=broker_id,
            alerts=alerts,
            total_premium_at_risk_zar=total_at_risk,
        )

    def _process_client(
        self, broker_id: str, client: Dict
    ) -> List[InsuranceBrokerAlert]:
        alerts: List[InsuranceBrokerAlert] = []
        golden_id = client.get("golden_id", "UNK")
        client_name = client.get("client_name", "Unknown")
        ins = client.get("insurance_profile", {})
        cib = client.get("cib_profile", {})

        if not ins:
            return []

        # --- Renewal due ---
        for policy in ins.get("policies", []):
            alert = self._renewal_alert(
                broker_id, golden_id, client_name, policy
            )
            if alert:
                alerts.append(alert)

            # --- Free-look ending ---
            alert = self._free_look_alert(
                broker_id, golden_id, client_name, policy
            )
            if alert:
                alerts.append(alert)

        # --- Coverage gap ---
        gap_alert = self._coverage_gap_alert(
            broker_id, golden_id, client_name, ins, cib
        )
        if gap_alert:
            alerts.append(gap_alert)

        # --- Underinsurance ---
        under_alert = self._underinsurance_alert(
            broker_id, golden_id, client_name, ins, cib
        )
        if under_alert:
            alerts.append(under_alert)

        # --- Claim surge ---
        claim_alert = self._claim_surge_alert(
            broker_id, golden_id, client_name, ins
        )
        if claim_alert:
            alerts.append(claim_alert)

        return alerts

    def _renewal_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        policy: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        expiry_str = policy.get("expiry_date")
        if not expiry_str:
            return None

        try:
            from datetime import date
            expiry = date.fromisoformat(expiry_str)
            days_left = (expiry - date.today()).days
        except (ValueError, TypeError):
            return None

        if days_left > 60 or days_left < 0:
            return None

        urgency = (
            "IMMEDIATE" if days_left <= 7
            else "HIGH" if days_left <= 14
            else "MEDIUM" if days_left <= 30
            else "LOW"
        )
        premium = policy.get("annual_premium_zar", 0.0)
        policy_type = policy.get("policy_type", "policy")

        return InsuranceBrokerAlert(
            alert_id=f"INS-REN-{golden_id}-{policy.get('policy_id', 'UNK')}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="RENEWAL_DUE",
            urgency=urgency,
            policy_id=policy.get("policy_id"),
            headline=(
                f"{policy_type.replace('_', ' ').title()} "
                f"renewal due in {days_left} days"
            ),
            details=(
                f"Policy #{policy.get('policy_id', 'UNK')} expires "
                f"{expiry_str}. Premium: R{premium:,.0f}/year."
            ),
            recommended_action=(
                f"Prepare renewal quote and send to client. "
                f"Check if sum assured should be adjusted."
            ),
            estimated_premium_zar=premium,
        )

    def _free_look_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        policy: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        free_look_end = policy.get("free_look_end_date")
        if not free_look_end:
            return None

        try:
            from datetime import date
            end = date.fromisoformat(free_look_end)
            days_left = (end - date.today()).days
        except (ValueError, TypeError):
            return None

        if days_left > 7 or days_left < 0:
            return None

        return InsuranceBrokerAlert(
            alert_id=f"INS-FL-{golden_id}-{policy.get('policy_id', 'UNK')}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="FREE_LOOK_END",
            urgency="HIGH",
            policy_id=policy.get("policy_id"),
            headline=(
                f"Free-look period ends in {days_left} days — "
                f"client may cancel"
            ),
            details=(
                f"Policy #{policy.get('policy_id', 'UNK')} free-look "
                f"ends {free_look_end}. "
                f"Engage client to confirm satisfaction."
            ),
            recommended_action=(
                "Schedule onboarding check-in call with client. "
                "Address any outstanding questions."
            ),
            estimated_premium_zar=policy.get("annual_premium_zar", 0.0),
        )

    def _coverage_gap_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        ins: Dict,
        cib: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        covered = set(ins.get("covered_countries", []))
        active_corridors = set(cib.get("active_payment_corridors", []))
        gaps = active_corridors - covered

        if not gaps:
            return None

        gap_countries = sorted(gaps)
        corridor_value = cib.get("annual_cross_border_value_zar", 0)
        est_premium = corridor_value * 0.008

        return InsuranceBrokerAlert(
            alert_id=f"INS-GAP-{golden_id}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="COVERAGE_GAP",
            urgency="MEDIUM",
            policy_id=None,
            headline=(
                f"Coverage gap: {len(gaps)} active corridors uninsured"
            ),
            details=(
                f"Active CIB corridors in "
                f"{', '.join(gap_countries)} have no matching "
                f"insurance coverage. CIB corridor value: "
                f"R{corridor_value:,.0f}/year."
            ),
            recommended_action=(
                f"Prepare trade credit / marine cargo proposal "
                f"for {', '.join(gap_countries[:3])}."
            ),
            estimated_premium_zar=est_premium,
        )

    def _underinsurance_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        ins: Dict,
        cib: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        sum_assured = ins.get("total_sum_assured_zar", 0)
        facility_value = cib.get("total_facility_value_zar", 0)

        if not facility_value or not sum_assured:
            return None

        coverage_ratio = sum_assured / facility_value
        if coverage_ratio >= 0.60:
            return None

        shortfall = facility_value * 0.80 - sum_assured

        return InsuranceBrokerAlert(
            alert_id=f"INS-UNDER-{golden_id}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="UNDERINSURANCE",
            urgency="HIGH",
            policy_id=None,
            headline=(
                f"Underinsured: {coverage_ratio*100:.0f}% coverage "
                f"vs CIB exposure"
            ),
            details=(
                f"Sum assured R{sum_assured:,.0f} covers only "
                f"{coverage_ratio*100:.0f}% of facility value "
                f"R{facility_value:,.0f}. "
                f"Recommend increasing cover by R{shortfall:,.0f}."
            ),
            recommended_action=(
                "Present comprehensive review with recommended "
                "sum-assured uplift to match credit exposure."
            ),
            estimated_premium_zar=shortfall * 0.008,
        )

    def _claim_surge_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        ins: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        claims_90d = ins.get("claims_count_90d", 0)
        avg_claims_90d = ins.get("avg_claims_90d_baseline", 1)

        if avg_claims_90d == 0 or claims_90d < 3:
            return None

        surge_ratio = claims_90d / avg_claims_90d
        if surge_ratio < 2.0:
            return None

        return InsuranceBrokerAlert(
            alert_id=f"INS-SURGE-{golden_id}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="CLAIM_SURGE",
            urgency="HIGH",
            policy_id=None,
            headline=(
                f"Claim surge: {claims_90d} claims in 90 days "
                f"({surge_ratio:.1f}× baseline)"
            ),
            details=(
                f"{claims_90d} claims in last 90 days vs "
                f"baseline average {avg_claims_90d:.0f}. "
                f"Surge ratio: {surge_ratio:.1f}×. "
                f"May indicate systemic risk or fraud ring."
            ),
            recommended_action=(
                "Escalate to claims investigations team. "
                "Review all open claims for the client."
            ),
            estimated_premium_zar=0.0,
        )
