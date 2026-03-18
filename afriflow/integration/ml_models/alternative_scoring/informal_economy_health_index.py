"""
@file informal_economy_health_index.py
@description Computes the Informal Economy Health Index (IEHI) — a 0–100 score
             measuring the health and growth trajectory of the informal economy
             cluster surrounding a corporate AfriFlow client.
             The informal economy is 30–60% of GDP across most sub-Saharan
             African countries. MoMo transaction flows are the primary signal
             because they capture economic activity that is invisible to
             traditional banking data systems.
             Output: IEHI score + GROWING / STABLE / DECLINING trajectory +
             an opportunity summary for the relationship manager.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Component weights
# ---------------------------------------------------------------------------
# MoMo velocity dominates (0.30) because transaction frequency is the most
# direct proxy for economic activity in the informal sector.

_COMPONENT_WEIGHTS: Dict[str, float] = {
    "momo_velocity":        0.30,  # Frequency of informal MoMo transactions
    "informal_payroll":     0.25,  # Reach of MoMo payroll across informal workers
    "geographic_spread":    0.20,  # Number of active MoMo corridors
    "seasonal_resilience":  0.15,  # Volume stability across lean seasons
    "formalisation_signal": 0.10,  # New bank account openings from informal cluster
}

# Trajectory thresholds: change in IEHI score over the prior period.
# A delta >= +5 is a meaningful positive trend; <= -5 is a meaningful decline.
_TRAJECTORY_GROWING  = +5.0
_TRAJECTORY_DECLINING = -5.0


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class IEHIComponent:
    """
    One component of the Informal Economy Health Index.

    :param name:         Component key (matches _COMPONENT_WEIGHTS).
    :param score:        Component score 0–100.
    :param weight:       Fractional weight in composite.
    :param description:  Evidence summary.
    :param data_present: False if source domain data was unavailable.
    """

    name: str
    score: float         # 0–100
    weight: float
    description: str
    data_present: bool


@dataclass
class InformalClusterProfile:
    """
    Profile of the informal economic cluster surrounding a corporate client.

    Derived from the gap between total SIM-estimated headcount and the
    number of formal PBB payroll accounts — the difference approximates
    the informal workforce size.

    :param estimated_informal_headcount:       Informal workers (not banked).
    :param estimated_monthly_momo_volume_zar:  Total MoMo throughput per month.
    :param active_momo_corridors:              Country codes with active MoMo flows.
    :param avg_transaction_value_zar:          Mean per-transaction size in ZAR.
    :param momo_enabled_pct:                   Fraction of workforce with MoMo wallet.
    """

    estimated_informal_headcount: int
    estimated_monthly_momo_volume_zar: float
    active_momo_corridors: List[str]   # Countries with active MoMo flows
    avg_transaction_value_zar: float
    momo_enabled_pct: float


@dataclass
class IEHIResult:
    """
    Full Informal Economy Health Index result for a client cluster.

    iehi_score : 0–100, higher = healthier informal cluster
    trajectory : GROWING / STABLE / DECLINING (vs prior period)

    :param client_golden_id:    AfriFlow golden record identifier.
    :param iehi_score:          Composite IEHI score (0–100).
    :param trajectory:          Directional trend vs prior period.
    :param trajectory_delta:    Absolute change in IEHI vs prior score.
    :param informal_cluster:    Cluster profile derived from domain data.
    :param components:          Per-component score breakdown.
    :param data_completeness:   Fraction of domain weights covered by data.
    :param opportunity_summary: RM-facing plain-English opportunity text.
    :param scored_at:           ISO timestamp of scoring.
    """

    client_golden_id: str
    iehi_score: float
    trajectory: str
    trajectory_delta: float     # 3-month change in IEHI; 0.0 if no prior score
    informal_cluster: InformalClusterProfile
    components: List[IEHIComponent]
    data_completeness: float
    opportunity_summary: str
    scored_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------

class InformalEconomyHealthIndexer:
    """
    Compute the Informal Economy Health Index for the informal cluster
    surrounding a corporate AfriFlow client.

    Usage::

        indexer = InformalEconomyHealthIndexer()
        result = indexer.compute(
            golden_record={"golden_id": "GLD-001"},
            cell_profile={
                "momo_transaction_count_30d": 4200,
                "momo_volume_30d_zar": 8_500_000,
                "estimated_employee_count": 1200,
                ...
            },
            prior_iehi_score=None,   # if available, enables trajectory
        )
    """

    def compute(
        self,
        golden_record: Dict,
        cell_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
        cib_profile: Optional[Dict] = None,
        prior_iehi_score: Optional[float] = None,
        country: str = "ZA",
    ) -> IEHIResult:
        """
        Compute IEHI for one client.

        :param golden_record:    Mandatory golden record dict.
        :param cell_profile:     Cell/MoMo domain profile (primary signal source).
        :param pbb_profile:      PBB profile (for formal payroll account count).
        :param cib_profile:      CIB profile (reserved for future corridor signals).
        :param prior_iehi_score: Previous IEHI score for trajectory calculation.
        :param country:          ISO-2 country code for contextual adjustments.
        :return:                 IEHIResult dataclass.
        """
        client_id = golden_record.get("golden_id", "UNKNOWN")

        # Build the informal cluster profile from cell + PBB headcount gap
        cluster = self._build_cluster_profile(
            cell_profile, pbb_profile
        )

        # Score each IEHI component
        components = [
            self._score_momo_velocity(cell_profile, cluster),
            self._score_informal_payroll(cell_profile, pbb_profile, cluster),
            self._score_geographic_spread(cell_profile),
            self._score_seasonal_resilience(cell_profile),
            self._score_formalisation(cell_profile, pbb_profile),
        ]

        # Weighted composite over present components only
        present = [c for c in components if c.data_present]
        if not present:
            # No cell data at all — assign a conservative low score
            iehi = 25.0
            completeness = 0.0
        else:
            present_weight = sum(c.weight for c in present)
            completeness = present_weight
            iehi = sum(
                c.score * c.weight for c in present
            ) / present_weight  # Re-normalise over present components

        # Compute trajectory: compare current IEHI to prior period
        delta = (iehi - prior_iehi_score) if prior_iehi_score is not None else 0.0
        if delta >= _TRAJECTORY_GROWING:
            trajectory = "GROWING"
        elif delta <= _TRAJECTORY_DECLINING:
            trajectory = "DECLINING"
        else:
            trajectory = "STABLE"  # Within ±5 IEHI points — no clear trend

        # Generate a plain-English opportunity summary for the RM
        opportunity = self._opportunity_summary(iehi, trajectory, cluster)

        return IEHIResult(
            client_golden_id=client_id,
            iehi_score=round(iehi, 1),
            trajectory=trajectory,
            trajectory_delta=round(delta, 1),
            informal_cluster=cluster,
            components=components,
            data_completeness=round(completeness, 3),
            opportunity_summary=opportunity,
        )

    # ------------------------------------------------------------------
    # Cluster profile builder
    # ------------------------------------------------------------------

    def _build_cluster_profile(
        self,
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> InformalClusterProfile:
        """
        Build a profile of the informal worker cluster from the gap between
        total SIM-estimated employee count and formal PBB payroll accounts.

        :param cell: Cell profile dict.
        :param pbb:  PBB profile dict.
        :return:     InformalClusterProfile dataclass.
        """
        if not cell:
            # No cell data — return an empty cluster profile
            return InformalClusterProfile(
                estimated_informal_headcount=0,
                estimated_monthly_momo_volume_zar=0.0,
                active_momo_corridors=[],
                avg_transaction_value_zar=0.0,
                momo_enabled_pct=0.0,
            )

        # Total headcount from SIM deflation model (cell domain)
        total_employees = cell.get("estimated_employee_count", 0)

        # Number of employees with formal PBB payroll accounts
        bank_employees = (pbb or {}).get("payroll_account_count", 0)

        # Informal headcount: those without a formal bank account
        informal_headcount = max(total_employees - bank_employees, 0)

        # MoMo transaction metrics for the past 30 days
        momo_count = cell.get("momo_transaction_count_30d", 0)
        momo_volume = cell.get("momo_volume_30d_zar", 0.0)

        # Average MoMo transaction value; guard against division by zero
        avg_val = momo_volume / momo_count if momo_count > 0 else 0.0

        # MoMo wallet penetration across the full workforce
        momo_enabled = cell.get("momo_enabled_employee_count", 0)
        momo_pct = momo_enabled / total_employees if total_employees > 0 else 0.0

        # List of country codes where this client has active MoMo corridors
        corridors = cell.get("active_momo_corridors", [])

        return InformalClusterProfile(
            estimated_informal_headcount=informal_headcount,
            estimated_monthly_momo_volume_zar=momo_volume,
            active_momo_corridors=corridors,
            avg_transaction_value_zar=avg_val,
            momo_enabled_pct=momo_pct,
        )

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    def _score_momo_velocity(
        self,
        cell: Optional[Dict],
        cluster: InformalClusterProfile,
    ) -> IEHIComponent:
        """
        Score MoMo transaction velocity per informal worker.

        Velocity is measured as monthly transaction count divided by the
        estimated informal headcount.  Higher velocity = more economically
        active informal cluster.

        :param cell:    Cell profile dict.
        :param cluster: Pre-built InformalClusterProfile.
        :return:        IEHIComponent for momo_velocity.
        """
        name = "momo_velocity"
        weight = _COMPONENT_WEIGHTS[name]

        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No MoMo data", data_present=False
            )

        # Total MoMo transactions in the last 30 days
        count = cell.get("momo_transaction_count_30d", 0)

        # Avoid division by zero with a floor of 1
        headcount = max(cluster.estimated_informal_headcount, 1)

        # Per-capita transaction rate: normalised to the informal workforce
        txn_per_head = count / headcount

        # Tiered scoring: 5+ txns/person/month = very active informal economy
        if txn_per_head >= 5:
            score = 90  # Highly active informal cluster
        elif txn_per_head >= 3:
            score = 75  # Active
        elif txn_per_head >= 1.5:
            score = 55  # Moderate activity
        elif txn_per_head >= 0.5:
            score = 35  # Low activity — some engagement
        else:
            score = 15  # Near-dormant cluster

        return IEHIComponent(
            name=name,
            score=float(score),
            weight=weight,
            description=(
                f"{count} MoMo txns/month, "
                f"{txn_per_head:.1f} per informal worker"
            ),
            data_present=True,
        )

    def _score_informal_payroll(
        self,
        cell: Optional[Dict],
        pbb: Optional[Dict],
        cluster: InformalClusterProfile,
    ) -> IEHIComponent:
        """
        Score the reach of MoMo payroll within the informal workforce.

        High MoMo penetration among informal workers (even those not
        formally banked) signals a healthy, connected informal economy
        with bankarisation potential.

        :param cell:    Cell profile dict.
        :param pbb:     PBB profile dict.
        :param cluster: Pre-built InformalClusterProfile.
        :return:        IEHIComponent for informal_payroll.
        """
        name = "informal_payroll"
        weight = _COMPONENT_WEIGHTS[name]

        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        # Total and formal headcounts
        total = cell.get("estimated_employee_count", 1)
        bank = (pbb or {}).get("payroll_account_count", 0)

        # Informal fraction of the workforce (those not in PBB payroll)
        informal_pct = (total - bank) / total if total > 0 else 0.0

        # MoMo penetration rate from the cluster profile
        momo_pct = cluster.momo_enabled_pct

        # MoMo reach sub-score: 100% penetration = 80 pts
        # (even informal workers engaging digitally is a positive signal)
        reach_score = momo_pct * 80

        # Size bonus: a larger informal cluster has more opportunity mass
        # 500 informal workers = full 20 pts; scales linearly below that
        size_score = min(cluster.estimated_informal_headcount / 500 * 20, 20)

        score = min(reach_score + size_score, 100)

        return IEHIComponent(
            name=name,
            score=round(score, 1),
            weight=weight,
            description=(
                f"{informal_pct*100:.0f}% informal workforce; "
                f"{momo_pct*100:.0f}% MoMo-enabled"
            ),
            data_present=True,
        )

    def _score_geographic_spread(
        self, cell: Optional[Dict]
    ) -> IEHIComponent:
        """
        Score geographic spread of informal MoMo activity by counting
        active cross-border corridors.

        More corridors = more distributed informal trade network.

        :param cell: Cell profile dict.
        :return:     IEHIComponent for geographic_spread.
        """
        name = "geographic_spread"
        weight = _COMPONENT_WEIGHTS[name]

        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        # List of country codes (e.g. ["ZW", "MZ", "ZM"]) with active MoMo flows
        corridors = cell.get("active_momo_corridors", [])
        count = len(corridors)

        # Tiered scoring: more corridors = more geographically diverse informal economy
        if count >= 5:
            score = 90   # Well-distributed multi-country informal network
        elif count >= 3:
            score = 70   # Regional spread
        elif count >= 2:
            score = 50   # Two-country presence
        elif count == 1:
            score = 30   # Domestic only with one cross-border corridor
        else:
            score = 10   # No cross-border informal activity detected

        return IEHIComponent(
            name=name,
            score=float(score),
            weight=weight,
            description=(
                f"MoMo active in {count} corridors: "
                f"{', '.join(corridors[:4])}"  # Show at most 4 corridors in description
            ),
            data_present=True,
        )

    def _score_seasonal_resilience(
        self, cell: Optional[Dict]
    ) -> IEHIComponent:
        """
        Score the informal cluster's resilience to lean-season volume drops.

        Agricultural cycles, school-fee periods, and harvest seasons cause
        predictable MoMo volume dips across African markets.  Clusters that
        maintain high volumes despite seasonal pressure are more robust.

        :param cell: Cell profile dict.
        :return:     IEHIComponent for seasonal_resilience.
        """
        name = "seasonal_resilience"
        weight = _COMPONENT_WEIGHTS[name]

        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        # Fractional drop in MoMo volume during the leanest season month
        # Default of 0.30 (30% drop) represents a typical African lean-season impact
        lean_month_drop = cell.get(
            "momo_lean_season_volume_drop_pct", 0.30
        )

        # Inverted scoring: lower drop = more resilient = higher score
        if lean_month_drop <= 0.10:
            score = 90   # Near-flat through lean season — very resilient
        elif lean_month_drop <= 0.20:
            score = 70   # Moderate seasonal impact
        elif lean_month_drop <= 0.35:
            score = 50   # Noticeable but recoverable dip
        elif lean_month_drop <= 0.50:
            score = 30   # Significant vulnerability to seasonal pressure
        else:
            score = 15   # Severe lean-season collapse — fragile cluster

        return IEHIComponent(
            name=name,
            score=float(score),
            weight=weight,
            description=(
                f"Lean-season MoMo volume drop: {lean_month_drop*100:.0f}%"
            ),
            data_present=True,
        )

    def _score_formalisation(
        self,
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> IEHIComponent:
        """
        Score the formalisation signal: new bank account openings in the
        past 90 days from the informal cluster linked to this employer.

        Higher formalisation rate predicts future NIM growth as informal
        workers migrate from MoMo wallets to full bank accounts.

        :param cell: Cell profile dict.
        :param pbb:  PBB profile dict.
        :return:     IEHIComponent for formalisation_signal.
        """
        name = "formalisation_signal"
        weight = _COMPONENT_WEIGHTS[name]

        if not pbb and not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        # New bank accounts opened in 90 days by employees from the informal cluster
        new_accounts = (pbb or {}).get(
            "new_accounts_from_employer_cluster_90d", 0
        )

        # Estimated informal headcount (denominator for rate calculation)
        total_informal = max(
            (cell or {}).get("estimated_employee_count", 100)
            - (pbb or {}).get("payroll_account_count", 0),
            1  # Floor at 1 to avoid division by zero
        )

        # Formalisation rate: new accounts as a fraction of informal headcount
        formalisation_rate = new_accounts / total_informal

        # Score: 20% formalisation in 90 days = 100 pts
        # (factor of 500 because 0.20 × 500 = 100)
        score = min(formalisation_rate * 500, 100)

        return IEHIComponent(
            name=name,
            score=round(score, 1),
            weight=weight,
            description=(
                f"{new_accounts} new bank accounts opened in 90 days "
                f"from informal cluster ({formalisation_rate*100:.1f}% rate)"
            ),
            data_present=True,
        )

    # ------------------------------------------------------------------
    # Opportunity summary
    # ------------------------------------------------------------------

    def _opportunity_summary(
        self,
        iehi: float,
        trajectory: str,
        cluster: InformalClusterProfile,
    ) -> str:
        """
        Generate a plain-English opportunity summary for the relationship
        manager based on IEHI score, trajectory, and cluster profile.

        :param iehi:       Composite IEHI score.
        :param trajectory: GROWING / STABLE / DECLINING.
        :param cluster:    InformalClusterProfile for volume/headcount context.
        :return:           Multi-sentence opportunity narrative string.
        """
        headcount = cluster.estimated_informal_headcount
        volume = cluster.estimated_monthly_momo_volume_zar
        corridors = len(cluster.active_momo_corridors)

        # Best case: healthy and growing — recommend active bankarisation campaign
        if iehi >= 70 and trajectory == "GROWING":
            return (
                f"Healthy and growing informal cluster: {headcount:,} workers, "
                f"R{volume:,.0f}/month MoMo volume across {corridors} corridors. "
                f"High bankarisation opportunity — recommend MoMo-to-Account "
                f"migration campaign and micro-lending pipeline."
            )
        # Stable cluster — MoMo penetration improvement is the lever
        elif iehi >= 50:
            return (
                f"Stable informal cluster: {headcount:,} workers, "
                f"R{volume:,.0f}/month. "
                f"MoMo penetration improvement would unlock NIM opportunity."
            )
        # Declining cluster — flag for employer health monitoring
        elif trajectory == "DECLINING":
            return (
                f"Declining informal cluster: {headcount:,} workers. "
                f"Monitor for employer payroll delays or workforce contraction."
            )
        # Early-stage cluster — adoption barriers need investigation
        else:
            return (
                f"Early-stage informal cluster: {headcount:,} workers. "
                f"Assess MoMo adoption barriers and consider incentive programme."
            )
