"""
@file insurance_broker_alert_engine.py
@description Generates insurance broker alerts by analysing client insurance
             profiles alongside CIB trade corridor and facility data. Covers
             five alert types: policy renewal due dates, free-look period endings,
             coverage gaps in active trade corridors, underinsurance relative to
             CIB credit exposure, and claim frequency surges that may indicate
             systemic risk or fraud.
@author Thabo Kunene
@created 2026-03-19
"""

# Insurance Broker Alert Engine
#
# Generates alerts for insurance brokers covering:
#
#   RENEWAL_DUE     — Policy expiry within 60/30/14/7 days
#   COVERAGE_GAP    — Client's CIB corridor or workforce not covered
#   CLAIM_SURGE     — Claim frequency spike suggests systemic issue
#   UNDERINSURANCE  — Sum assured < 60% of estimated asset value
#   FREE_LOOK_END   — Free-look period ending; client may cancel
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
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class InsuranceBrokerAlert:
    """
    A single insurance broker alert representing a risk or opportunity.

    :param alert_id: Unique identifier for the alert
    :param broker_id: The ID of the broker responsible for the client
    :param client_golden_id: Unified client identifier
    :param client_name: Display name of the client
    :param alert_type: Category of insurance alert (e.g., RENEWAL_DUE)
    :param urgency: Priority level for the broker (e.g., HIGH)
    :param policy_id: ID of the policy if specific, else None
    :param headline: Brief summary of the alert
    :param details: In-depth context for broker preparation
    :param recommended_action: Suggested next step for the broker
    :param estimated_premium_zar: Estimated premium value at risk or potential upsell
    :param created_at: Timestamp when the alert was generated
    """

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
    # Automatically capture the creation time of the alert
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class InsuranceBrokerAlertBatch:
    """
    A collection of insurance alerts for a single broker's portfolio.

    :param broker_id: The ID of the broker receiving the batch
    :param alerts: List of InsuranceBrokerAlert objects
    :param total_premium_at_risk_zar: Aggregate premium value across the batch
    :param generated_at: When the batch was compiled
    """

    broker_id: str
    alerts: List[InsuranceBrokerAlert]
    # Sum of premium values for all alerts in the batch
    total_premium_at_risk_zar: float
    # Timestamp marking the completion of batch generation
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

class InsuranceBrokerAlertEngine:
    """
    Engine responsible for identifying insurance risks and opportunities by
    correlating insurance policy data with CIB exposure and market signals.
    """

    # Defined days before expiry when renewal alerts should trigger
    _RENEWAL_THRESHOLDS = [7, 14, 30, 60]

    def build_batch(
        self,
        broker_id: str,
        client_portfolio: List[Dict],
    ) -> InsuranceBrokerAlertBatch:
        """
        Scan a broker's entire portfolio and generate a prioritized alert batch.

        :param broker_id: Unique ID of the target insurance broker
        :param client_portfolio: List of client profiles with insurance and CIB data
        :return: An InsuranceBrokerAlertBatch sorted by urgency.
        """
        alerts: List[InsuranceBrokerAlert] = []

        # Iterate through every client in the portfolio to detect insurance anomalies
        for client in client_portfolio:
            alerts.extend(self._process_client(broker_id, client))

        # Sort alerts by urgency (IMMEDIATE first) for broker productivity
        alerts.sort(
            key=lambda a: {"IMMEDIATE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                a.urgency, 9
            )
        )

        # Calculate the total value at risk for the broker's action queue
        total_at_risk = sum(a.estimated_premium_zar for a in alerts)

        return InsuranceBrokerAlertBatch(
            broker_id=broker_id,
            alerts=alerts,
            total_premium_at_risk_zar=total_at_risk,
        )

    def _process_client(
        self, broker_id: str, client: Dict
    ) -> List[InsuranceBrokerAlert]:
        """
        Run all insurance-specific detectors for a single client profile.

        :param broker_id: ID of the insurance broker
        :param client: Combined client data dictionary
        :return: List of generated InsuranceBrokerAlert objects.
        """
        alerts: List[InsuranceBrokerAlert] = []

        # Extract core identifiers and profile segments
        golden_id = client.get("golden_id", "UNK")
        client_name = client.get("client_name", "Unknown")
        ins = client.get("insurance_profile", {})
        cib = client.get("cib_profile", {})

        # If no insurance data exists, the engine cannot perform its checks
        if not ins:
            return []

        # --- Detector 1: Renewal due ---
        # Check for policies expiring within the defined thresholds
        for policy in ins.get("policies", []):
            alert = self._renewal_alert(
                broker_id, golden_id, client_name, policy
            )
            if alert:
                alerts.append(alert)

            # --- Detector 2: Free-look ending ---
            # Identify new policies whose cooling-off period is expiring
            alert = self._free_look_alert(
                broker_id, golden_id, client_name, policy
            )
            if alert:
                alerts.append(alert)

        # --- Detector 3: Coverage gap ---
        # Compares the set of CIB trade corridors against insured countries.
        # A gap means the client has active cross-border exposure with no coverage.
        gap_alert = self._coverage_gap_alert(
            broker_id, golden_id, client_name, ins, cib
        )
        if gap_alert:
            alerts.append(gap_alert)

        # --- Detector 4: Underinsurance ---
        # Compares total sum assured against CIB facility value.
        # Triggers when sum assured < 60% of facility value — a material gap.
        under_alert = self._underinsurance_alert(
            broker_id, golden_id, client_name, ins, cib
        )
        if under_alert:
            alerts.append(under_alert)

        # --- Detector 5: Claim surge ---
        # Compares recent 90-day claim count against the baseline average.
        # A 2× surge may indicate systemic risk, catastrophic event, or fraud.
        claim_alert = self._claim_surge_alert(
            broker_id, golden_id, client_name, ins
        )
        if claim_alert:
            alerts.append(claim_alert)

        return alerts

    # ------------------------------------------------------------------
    # Individual detectors
    # ------------------------------------------------------------------

    def _renewal_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        policy: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        """
        Generate a renewal due alert if the policy expires within 60 days.

        Urgency escalates as expiry approaches:
          60 days → LOW (early planning phase)
          30 days → MEDIUM (quote preparation required)
          14 days → HIGH (renewal urgent)
           7 days → IMMEDIATE (lapse risk if not renewed today)

        :param broker_id: Broker identifier
        :param golden_id: Client golden ID
        :param client_name: Client name for display
        :param policy: Policy dict with 'expiry_date', 'policy_id',
                       'policy_type', 'annual_premium_zar'
        :return: InsuranceBrokerAlert or None if expiry is >60 days away or already lapsed
        """
        expiry_str = policy.get("expiry_date")
        if not expiry_str:
            return None  # Cannot compute days left without an expiry date

        try:
            from datetime import date
            expiry = date.fromisoformat(expiry_str)   # Parse ISO date string
            days_left = (expiry - date.today()).days   # Positive = future, negative = lapsed
        except (ValueError, TypeError):
            return None  # Malformed date string; skip rather than raise

        # Only alert within the 60-day window; don't alert on already-lapsed policies
        if days_left > 60 or days_left < 0:
            return None

        # Urgency escalation: the closer to expiry, the more urgent the alert
        urgency = (
            "IMMEDIATE" if days_left <= 7   # 7 days: imminent lapse
            else "HIGH" if days_left <= 14  # 14 days: urgent renewal
            else "MEDIUM" if days_left <= 30  # 30 days: prepare quote
            else "LOW"                        # 60 days: plan ahead
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
                # Convert 'trade_credit' → 'Trade Credit' for display
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
            estimated_premium_zar=premium,  # Renewal premium represents revenue at risk
        )

    def _free_look_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        policy: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        """
        Generate a free-look ending alert within 7 days of the free-look period end.

        The free-look period (typically 31 days from policy inception) allows
        new clients to cancel for a full refund. If the broker hasn't confirmed
        satisfaction, there is cancellation risk. Urgency is always HIGH.

        :param broker_id: Broker identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param policy: Policy dict with 'free_look_end_date' and 'annual_premium_zar'
        :return: InsuranceBrokerAlert or None
        """
        free_look_end = policy.get("free_look_end_date")
        if not free_look_end:
            return None  # No free-look date means policy is past the free-look window

        try:
            from datetime import date
            end = date.fromisoformat(free_look_end)
            days_left = (end - date.today()).days
        except (ValueError, TypeError):
            return None  # Invalid date; skip silently

        # Alert window: within 7 days of free-look end (not yet expired)
        if days_left > 7 or days_left < 0:
            return None

        return InsuranceBrokerAlert(
            alert_id=f"INS-FL-{golden_id}-{policy.get('policy_id', 'UNK')}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="FREE_LOOK_END",
            urgency="HIGH",  # Always HIGH: cancellation window is imminent
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
        """
        Detect a coverage gap: active CIB trade corridors not covered by insurance.

        Uses set difference to identify countries where the client trades (CIB data)
        but has no insurance coverage. The estimated premium is based on 0.8% of the
        annual cross-border corridor value — a typical trade credit insurance rate.

        Urgency: MEDIUM (gap is a risk but not an immediate expiry situation)

        :param broker_id: Broker identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param ins: Insurance profile dict with 'covered_countries' list
        :param cib: CIB profile dict with 'active_payment_corridors' list and
                    'annual_cross_border_value_zar'
        :return: InsuranceBrokerAlert or None if no gap exists
        """
        covered = set(ins.get("covered_countries", []))           # Countries with insurance
        active_corridors = set(cib.get("active_payment_corridors", []))  # Countries with trade

        # Set difference: countries where client trades but is not insured
        gaps = active_corridors - covered

        if not gaps:
            return None  # Full coverage; no alert needed

        gap_countries = sorted(gaps)   # Alphabetical for consistent display
        corridor_value = cib.get("annual_cross_border_value_zar", 0)

        # Estimated new premium based on 0.8% trade credit insurance rate
        est_premium = corridor_value * 0.008

        return InsuranceBrokerAlert(
            alert_id=f"INS-GAP-{golden_id}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="COVERAGE_GAP",
            urgency="MEDIUM",  # Gap is a revenue opportunity, not an emergency
            policy_id=None,    # Gap alert is client-level, not tied to a specific policy
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
                # Limit the displayed country list to 3 to keep the CTA concise
                f"Prepare trade credit / marine cargo proposal "
                f"for {', '.join(gap_countries[:3])}."
            ),
            estimated_premium_zar=est_premium,  # New business opportunity value
        )

    def _underinsurance_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        ins: Dict,
        cib: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        """
        Detect underinsurance: sum assured is less than 60% of CIB facility value.

        The 60% threshold is the minimum coverage ratio considered adequate.
        The recommended sum-assured uplift targets 80% of facility value (a
        more conservative benchmark), leaving a 20% buffer for undrawn facilities.

        Estimated additional premium uses the 0.8% trade credit insurance rate.

        :param broker_id: Broker identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param ins: Insurance profile with 'total_sum_assured_zar'
        :param cib: CIB profile with 'total_facility_value_zar'
        :return: InsuranceBrokerAlert or None if coverage ratio is adequate
        """
        sum_assured = ins.get("total_sum_assured_zar", 0)
        facility_value = cib.get("total_facility_value_zar", 0)

        # Cannot assess underinsurance without both values
        if not facility_value or not sum_assured:
            return None

        # Coverage ratio: what fraction of the CIB facility is insured
        coverage_ratio = sum_assured / facility_value

        # Below 60% coverage is considered materially underinsured
        if coverage_ratio >= 0.60:
            return None

        # Shortfall to reach 80% coverage (the recommended adequate coverage level)
        shortfall = facility_value * 0.80 - sum_assured

        return InsuranceBrokerAlert(
            alert_id=f"INS-UNDER-{golden_id}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="UNDERINSURANCE",
            urgency="HIGH",  # Underinsurance creates material credit and asset risk
            policy_id=None,  # Client-level alert; not tied to one specific policy
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
            # Premium opportunity: 0.8% on the shortfall amount
            estimated_premium_zar=shortfall * 0.008,
        )

    def _claim_surge_alert(
        self,
        broker_id: str,
        golden_id: str,
        client_name: str,
        ins: Dict,
    ) -> Optional[InsuranceBrokerAlert]:
        """
        Detect a claim frequency surge: recent 90-day claim count exceeds
        2× the historical baseline average.

        Minimum claim count of 3 prevents alerts on isolated single incidents.
        A surge ratio ≥ 2× indicates a systemic issue, catastrophic event,
        or potential fraud ring that requires investigation.

        :param broker_id: Broker identifier
        :param golden_id: Client golden ID
        :param client_name: Client name
        :param ins: Insurance profile with 'claims_count_90d' and
                    'avg_claims_90d_baseline' fields
        :return: InsuranceBrokerAlert or None if no surge detected
        """
        claims_90d = ins.get("claims_count_90d", 0)         # Recent claim count
        avg_claims_90d = ins.get("avg_claims_90d_baseline", 1)  # Historical baseline

        # Guard: avoid division by zero; ignore isolated incidents (< 3 claims)
        if avg_claims_90d == 0 or claims_90d < 3:
            return None

        # Surge ratio: how many times above baseline the current period is
        surge_ratio = claims_90d / avg_claims_90d

        # Only alert on a material surge: ≥ 2× baseline claim frequency
        if surge_ratio < 2.0:
            return None

        return InsuranceBrokerAlert(
            alert_id=f"INS-SURGE-{golden_id}",
            broker_id=broker_id,
            client_golden_id=golden_id,
            client_name=client_name,
            alert_type="CLAIM_SURGE",
            urgency="HIGH",  # Surge may indicate fraud or catastrophic event; needs fast review
            policy_id=None,  # Portfolio-level event; not tied to a single policy
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
            estimated_premium_zar=0.0,  # Surge is a risk signal; no direct premium opportunity
        )
