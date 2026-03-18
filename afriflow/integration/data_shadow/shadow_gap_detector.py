"""
@file shadow_gap_detector.py
@description Shadow Gap Detector for the AfriFlow Data Shadow model.
             Detects data shadow gaps for CIB clients by comparing CIB
             activity levels against expected cross-domain signals. For each
             CIB activity record that exceeds a domain-specific threshold,
             the detector checks whether the expected downstream signal is
             present (e.g. an FX hedge for a cross-border payment). Absent
             signals produce ShadowGap records scored 0–1, classified by
             severity (INFO → CRITICAL), and tagged with recommended RM actions.
@author Thabo Kunene
@created 2026-03-18

Data Shadow - Shadow Gap Detector

A "data shadow" is the absence of expected data — treated
as a signal in its own right. If a CIB client is making
large payments into Nigeria but we see no corresponding:
  - Forex hedge in our treasury system
  - Insurance policies in Nigeria
  - SIM activations / MoMo activity in Nigeria
  - PBB salary or account links to Nigerian employees

...then the absence is MORE informative than any presence.
It suggests either data leakage to a competitor, off-
balance-sheet activity, or a genuine new expansion that
we haven't yet captured.

We score gaps by domain, severity, and expected-vs-actual
signal presence, then route the highest-severity gaps to
RM alert queues.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field  # structured gap and expectation value objects
from datetime import datetime             # gap detection timestamps and ID components
from typing import Dict, List, Optional, Any  # full type annotations
from enum import Enum                    # typed domain and severity enumerations

from afriflow.exceptions import ConfigurationError  # raised on invalid configuration inputs
from afriflow.logging_config import get_logger, log_operation  # structured operation logging

# Module-level logger — log operation start/complete for every detect_gaps() call
logger = get_logger("integration.data_shadow.shadow_gap_detector")


class GapDomain(Enum):
    """Domain where the expected signal is absent."""
    FOREX = "forex"
    INSURANCE = "insurance"
    CELL = "cell"
    PBB = "pbb"
    CIB = "cib"


class GapSeverity(Enum):
    """Severity of the data shadow gap."""
    INFO = "info"           # Minor gap, informational only
    LOW = "low"             # Possible miss, low confidence
    MEDIUM = "medium"       # Likely miss, worth investigating
    HIGH = "high"           # Strong signal, RM should follow up
    CRITICAL = "critical"   # Clear competitive leakage or compliance risk


@dataclass
class ShadowExpectation:
    """
    Defines what signal we expect to see for a given activity level.

    Attributes:
        domain: Domain where we expect a signal
        activity_type: CIB activity type driving the expectation
        threshold_usd: Minimum CIB activity amount to trigger expectation
        expected_signal: Description of what should be present
        weight: Importance weight for scoring (0–1)
    """
    domain: GapDomain
    activity_type: str      # "payment", "lc", "trade_finance"
    threshold_usd: float
    expected_signal: str
    weight: float = 1.0


@dataclass
class ShadowGap:
    """
    A detected data shadow gap for a specific client and domain.

    Attributes:
        gap_id: Unique gap identifier
        client_golden_id: Client identifier
        country: Country where the activity was observed
        gap_domain: Domain where the signal is absent
        expectation: The expectation that was not met
        cib_activity_usd: Size of CIB activity driving the expectation
        gap_score: Computed severity score (0–1)
        severity: Severity classification
        evidence: Supporting evidence dict
        detected_at: Detection timestamp
        recommended_action: What the RM should do
    """
    gap_id: str
    client_golden_id: str
    country: str
    gap_domain: GapDomain
    expectation: ShadowExpectation
    cib_activity_usd: float
    gap_score: float
    severity: GapSeverity
    evidence: Dict[str, Any]
    detected_at: datetime
    recommended_action: str


# ── Expectation rules ────────────────────────────────────────────────────────
# These encode domain knowledge about what signals should co-occur
# with CIB payment activity in African markets.

EXPECTATION_RULES: List[ShadowExpectation] = [
    ShadowExpectation(
        domain=GapDomain.FOREX,
        activity_type="cross_border_payment",
        threshold_usd=50_000,
        expected_signal="FX hedge or spot trade in payment currency",
        weight=0.9,
    ),
    ShadowExpectation(
        domain=GapDomain.INSURANCE,
        activity_type="cross_border_payment",
        threshold_usd=100_000,
        expected_signal="Trade credit or cargo insurance in destination country",
        weight=0.7,
    ),
    ShadowExpectation(
        domain=GapDomain.CELL,
        activity_type="payroll_payment",
        threshold_usd=25_000,
        expected_signal="Corporate SIM activations in payroll country",
        weight=0.8,
    ),
    ShadowExpectation(
        domain=GapDomain.CELL,
        activity_type="cross_border_payment",
        threshold_usd=200_000,
        expected_signal="MoMo or SIM presence in destination country",
        weight=0.6,
    ),
    ShadowExpectation(
        domain=GapDomain.PBB,
        activity_type="payroll_payment",
        threshold_usd=10_000,
        expected_signal="PBB salary accounts for payroll recipients",
        weight=0.5,
    ),
    ShadowExpectation(
        domain=GapDomain.INSURANCE,
        activity_type="asset_financing",
        threshold_usd=500_000,
        expected_signal="Asset insurance policy for financed assets",
        weight=0.85,
    ),
]


def _score_to_severity(score: float) -> GapSeverity:
    """
    Map a numeric gap score (0–1) to a GapSeverity enum value.

    Score bands:
      ≥ 0.85  → CRITICAL   (immediate RM follow-up required)
      ≥ 0.65  → HIGH       (same-week follow-up)
      ≥ 0.45  → MEDIUM     (review in next pipeline cycle)
      ≥ 0.25  → LOW        (log for tracking, no action yet)
      < 0.25  → INFO       (informational only)

    :param score: Gap score in [0.0, 1.0]
    :return: Corresponding GapSeverity value
    """
    if score >= 0.85:
        return GapSeverity.CRITICAL
    elif score >= 0.65:
        return GapSeverity.HIGH
    elif score >= 0.45:
        return GapSeverity.MEDIUM
    elif score >= 0.25:
        return GapSeverity.LOW
    else:
        return GapSeverity.INFO


class ShadowGapDetector:
    """
    We detect data shadow gaps for CIB clients.

    For each client, we look at their CIB activity and check
    whether the expected cross-domain signals are present. Where
    they are absent, we create gap records with severity scores.

    Attributes:
        expectation_rules: Rules defining expected cross-domain signals
        gaps: Detected gaps by client ID
        gap_counter: Sequential gap ID counter
    """

    def __init__(
        self,
        custom_rules: Optional[List[ShadowExpectation]] = None
    ) -> None:
        """
        Initialize the shadow gap detector.

        Args:
            custom_rules: Optional custom expectation rules
                          (supplements built-in rules)
        """
        self.expectation_rules = EXPECTATION_RULES + (custom_rules or [])
        self.gaps: Dict[str, List[ShadowGap]] = {}
        self._gap_counter = 0
        logger.info(
            f"ShadowGapDetector initialized with "
            f"{len(self.expectation_rules)} expectation rules"
        )

    def detect_gaps(
        self,
        client_golden_id: str,
        country: str,
        cib_activities: List[Dict[str, Any]],
        domain_signals: Dict[str, Any],
    ) -> List[ShadowGap]:
        """
        Detect shadow gaps for a client.

        Args:
            client_golden_id: Client golden record ID
            country: Country where CIB activity is occurring
            cib_activities: List of CIB activity dicts, each with:
                {type: str, amount_usd: float, destination_country: str}
            domain_signals: Presence signals from each domain:
                {domain_name: {signal_type: bool/int/float}}

        Returns:
            List of detected ShadowGap instances
        """
        log_operation(
            logger, "detect_gaps", "started",
            client_id=client_golden_id, country=country,
        )

        detected: List[ShadowGap] = []

        for activity in cib_activities:
            activity_type = activity.get("type", "payment")
            amount_usd = activity.get("amount_usd", 0.0)
            dest_country = activity.get("destination_country", country)

            for rule in self.expectation_rules:
                if rule.activity_type != activity_type:
                    continue
                if amount_usd < rule.threshold_usd:
                    continue

                # Check if expected signal is present
                domain_data = domain_signals.get(rule.domain.value, {})
                signal_present = self._check_signal_present(
                    rule, domain_data, dest_country, amount_usd
                )

                if not signal_present:
                    gap = self._create_gap(
                        client_golden_id=client_golden_id,
                        country=dest_country,
                        rule=rule,
                        activity=activity,
                        amount_usd=amount_usd,
                    )
                    detected.append(gap)

        if client_golden_id not in self.gaps:
            self.gaps[client_golden_id] = []
        self.gaps[client_golden_id].extend(detected)

        log_operation(
            logger, "detect_gaps", "completed",
            client_id=client_golden_id,
            gaps_detected=len(detected),
        )

        return detected

    def _check_signal_present(
        self,
        rule: ShadowExpectation,
        domain_data: Dict[str, Any],
        country: str,
        amount_usd: float,
    ) -> bool:
        """Check if the expected signal is present in domain data."""
        if rule.domain == GapDomain.FOREX:
            # Expect an active hedge or recent spot trade
            active_hedges = domain_data.get("active_hedges", 0)
            recent_spots = domain_data.get("recent_spot_trades", 0)
            return (active_hedges + recent_spots) > 0

        elif rule.domain == GapDomain.INSURANCE:
            policies = domain_data.get("active_policies", 0)
            countries_covered = domain_data.get("countries_covered", [])
            return policies > 0 and (not country or country in countries_covered)

        elif rule.domain == GapDomain.CELL:
            if rule.activity_type == "payroll_payment":
                sim_count = domain_data.get("corporate_sim_count", 0)
                return sim_count > 0
            else:
                countries_active = domain_data.get("active_countries", [])
                return country in countries_active

        elif rule.domain == GapDomain.PBB:
            linked_accounts = domain_data.get("linked_accounts", 0)
            return linked_accounts > 0

        return True  # Default: assume present if unknown

    def _create_gap(
        self,
        client_golden_id: str,
        country: str,
        rule: ShadowExpectation,
        activity: Dict[str, Any],
        amount_usd: float,
    ) -> ShadowGap:
        """
        Create a ShadowGap record for a detected absence.

        Gap score formula:
          amount_factor = min(1.0, amount_usd / (threshold × 10))
          gap_score     = rule.weight × (0.5 + 0.5 × amount_factor)

        This means:
          - At exactly the threshold, amount_factor ≈ 0.1, score ≈ weight × 0.55
          - At 10× the threshold, amount_factor = 1.0, score = rule.weight
          - Scores are bounded by rule.weight (max 1.0 if weight = 1.0)

        :param client_golden_id: Client identifier for the gap record
        :param country: Country where the absence was detected
        :param rule: The ShadowExpectation rule that was not satisfied
        :param activity: The CIB activity dict that triggered the rule check
        :param amount_usd: USD amount of the triggering activity
        :return: Populated ShadowGap record
        """
        self._gap_counter += 1
        gap_id = f"GAP-{client_golden_id}-{self._gap_counter:04d}"

        # Compute amount factor: how many times the threshold was exceeded.
        # Capped at 1.0 so very large amounts do not push score above rule.weight.
        amount_factor = min(1.0, amount_usd / (rule.threshold_usd * 10))
        # Base score is 0.5 × weight; each doubling of the threshold adds to score
        gap_score = round(rule.weight * (0.5 + 0.5 * amount_factor), 3)
        severity = _score_to_severity(gap_score)

        action_map = {
            GapDomain.FOREX: "Review FX exposure. Offer hedging solution.",
            GapDomain.INSURANCE: "Identify insurance gap. Engage broker.",
            GapDomain.CELL: "Confirm workforce in country. Offer SIM package.",
            GapDomain.PBB: "Cross-sell PBB salary accounts to employees.",
            GapDomain.CIB: "Review CIB product coverage.",
        }

        return ShadowGap(
            gap_id=gap_id,
            client_golden_id=client_golden_id,
            country=country,
            gap_domain=rule.domain,
            expectation=rule,
            cib_activity_usd=amount_usd,
            gap_score=gap_score,
            severity=severity,
            evidence={
                "activity_type": activity.get("type"),
                "amount_usd": amount_usd,
                "destination_country": country,
                "expected_signal": rule.expected_signal,
            },
            detected_at=datetime.utcnow(),
            recommended_action=action_map.get(rule.domain, "Investigate gap."),
        )

    def get_client_gaps(
        self,
        client_golden_id: str,
        min_severity: GapSeverity = GapSeverity.INFO,
    ) -> List[ShadowGap]:
        """Get gaps for a specific client filtered by minimum severity."""
        all_gaps = self.gaps.get(client_golden_id, [])
        severity_order = list(GapSeverity)
        min_idx = severity_order.index(min_severity)
        return [
            g for g in all_gaps
            if severity_order.index(g.severity) >= min_idx
        ]

    def get_top_gaps(self, limit: int = 20) -> List[ShadowGap]:
        """Get top gaps by score across all clients."""
        all_gaps = [
            g for gaps in self.gaps.values() for g in gaps
        ]
        return sorted(all_gaps, key=lambda g: g.gap_score, reverse=True)[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get gap detection statistics."""
        all_gaps = [g for gaps in self.gaps.values() for g in gaps]
        by_domain: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for gap in all_gaps:
            by_domain[gap.gap_domain.value] = by_domain.get(gap.gap_domain.value, 0) + 1
            by_severity[gap.severity.value] = by_severity.get(gap.severity.value, 0) + 1

        return {
            "total_clients_evaluated": len(self.gaps),
            "total_gaps": len(all_gaps),
            "by_domain": by_domain,
            "by_severity": by_severity,
            "critical_gap_clients": [
                cid for cid, gaps in self.gaps.items()
                if any(g.severity == GapSeverity.CRITICAL for g in gaps)
            ],
        }


if __name__ == "__main__":
    detector = ShadowGapDetector()

    cib_activities = [
        {"type": "cross_border_payment", "amount_usd": 500_000, "destination_country": "NG"},
        {"type": "payroll_payment", "amount_usd": 80_000, "destination_country": "KE"},
    ]

    domain_signals = {
        "forex": {"active_hedges": 0, "recent_spot_trades": 0},  # No hedges!
        "insurance": {"active_policies": 1, "countries_covered": ["ZA"]},  # Not in NG
        "cell": {"corporate_sim_count": 0, "active_countries": []},
        "pbb": {"linked_accounts": 0},
    }

    gaps = detector.detect_gaps("GLD-001", "NG", cib_activities, domain_signals)
    print(f"Detected {len(gaps)} gaps:")
    for g in gaps:
        print(f"  [{g.severity.value.upper()}] {g.gap_domain.value}: "
              f"{g.expectation.expected_signal} "
              f"(score={g.gap_score:.2f})")
        print(f"    → {g.recommended_action}")

    print(f"\nStats: {detector.get_statistics()}")
