"""
Informal Economy Health Index (IEHI)

The informal economy represents 30–60% of GDP across most
sub-Saharan African countries. Standard banking products
were designed for the formal sector — they miss this segment
entirely.

The IEHI scores the health and growth trajectory of the
informal economy cluster served by a corporate client,
using MoMo flows as the primary signal.

Key insight: A large employer's informal workforce (traders,
contractors, informal suppliers) transacts primarily through
MoMo. The volume, frequency, and geography of these flows
reveal the health of the informal cluster around the client —
which in turn predicts:
  - Future formal sector conversion (bankarisation rate)
  - SME lending opportunity in the supplier chain
  - Insurance micro-product demand
  - Cross-border corridor expansion

IEHI Components:
  1. MoMo velocity         — frequency of informal transactions
  2. Informal payroll reach — % of workforce paid informally
  3. Geographic spread      — informal activity in new markets
  4. Seasonal resilience    — activity maintained during lean seasons
  5. Formalisation signal  — informal clients opening bank accounts

Output: IEHI 0–100 per cluster + trajectory (GROWING/STABLE/DECLINING)

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


_COMPONENT_WEIGHTS: Dict[str, float] = {
    "momo_velocity":        0.30,
    "informal_payroll":     0.25,
    "geographic_spread":    0.20,
    "seasonal_resilience":  0.15,
    "formalisation_signal": 0.10,
}

# Trajectory thresholds (3-month change in IEHI)
_TRAJECTORY_GROWING  = +5.0
_TRAJECTORY_DECLINING = -5.0


@dataclass
class IEHIComponent:
    """One component of the Informal Economy Health Index."""

    name: str
    score: float         # 0–100
    weight: float
    description: str
    data_present: bool


@dataclass
class InformalClusterProfile:
    """Profile of the informal cluster around a corporate client."""

    estimated_informal_headcount: int
    estimated_monthly_momo_volume_zar: float
    active_momo_corridors: List[str]   # Countries with active MoMo flows
    avg_transaction_value_zar: float
    momo_enabled_pct: float


@dataclass
class IEHIResult:
    """
    Informal Economy Health Index result for a client cluster.

    iehi_score : 0–100, higher = healthier informal cluster
    trajectory : GROWING / STABLE / DECLINING
    """

    client_golden_id: str
    iehi_score: float
    trajectory: str
    trajectory_delta: float     # 3-month change in IEHI
    informal_cluster: InformalClusterProfile
    components: List[IEHIComponent]
    data_completeness: float
    opportunity_summary: str
    scored_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class InformalEconomyHealthIndexer:
    """
    Compute the Informal Economy Health Index for the informal
    cluster surrounding a corporate AfriFlow client.

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
        client_id = golden_record.get("golden_id", "UNKNOWN")

        cluster = self._build_cluster_profile(
            cell_profile, pbb_profile
        )
        components = [
            self._score_momo_velocity(cell_profile, cluster),
            self._score_informal_payroll(cell_profile, pbb_profile, cluster),
            self._score_geographic_spread(cell_profile),
            self._score_seasonal_resilience(cell_profile),
            self._score_formalisation(cell_profile, pbb_profile),
        ]

        present = [c for c in components if c.data_present]
        if not present:
            iehi = 25.0
            completeness = 0.0
        else:
            present_weight = sum(c.weight for c in present)
            completeness = present_weight
            iehi = sum(
                c.score * c.weight for c in present
            ) / present_weight

        # Trajectory
        delta = (iehi - prior_iehi_score) if prior_iehi_score is not None else 0.0
        if delta >= _TRAJECTORY_GROWING:
            trajectory = "GROWING"
        elif delta <= _TRAJECTORY_DECLINING:
            trajectory = "DECLINING"
        else:
            trajectory = "STABLE"

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
        if not cell:
            return InformalClusterProfile(
                estimated_informal_headcount=0,
                estimated_monthly_momo_volume_zar=0.0,
                active_momo_corridors=[],
                avg_transaction_value_zar=0.0,
                momo_enabled_pct=0.0,
            )

        total_employees = cell.get("estimated_employee_count", 0)
        bank_employees = (pbb or {}).get("payroll_account_count", 0)
        informal_headcount = max(total_employees - bank_employees, 0)

        momo_count = cell.get("momo_transaction_count_30d", 0)
        momo_volume = cell.get("momo_volume_30d_zar", 0.0)
        avg_val = momo_volume / momo_count if momo_count > 0 else 0.0

        momo_enabled = cell.get("momo_enabled_employee_count", 0)
        momo_pct = momo_enabled / total_employees if total_employees > 0 else 0.0

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
        name = "momo_velocity"
        weight = _COMPONENT_WEIGHTS[name]
        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No MoMo data", data_present=False
            )

        count = cell.get("momo_transaction_count_30d", 0)
        headcount = max(cluster.estimated_informal_headcount, 1)
        txn_per_head = count / headcount

        # Score: 2+ txns/person/month = healthy, 5+ = very active
        if txn_per_head >= 5:
            score = 90
        elif txn_per_head >= 3:
            score = 75
        elif txn_per_head >= 1.5:
            score = 55
        elif txn_per_head >= 0.5:
            score = 35
        else:
            score = 15

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
        name = "informal_payroll"
        weight = _COMPONENT_WEIGHTS[name]
        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        total = cell.get("estimated_employee_count", 1)
        bank = (pbb or {}).get("payroll_account_count", 0)
        informal_pct = (total - bank) / total if total > 0 else 0.0

        # High informal payroll = opportunity; score by reach
        momo_pct = cluster.momo_enabled_pct
        # If informal workers are using MoMo (even if not bank accounts)
        # that is healthy for the informal economy
        reach_score = momo_pct * 80
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
        name = "geographic_spread"
        weight = _COMPONENT_WEIGHTS[name]
        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        corridors = cell.get("active_momo_corridors", [])
        count = len(corridors)
        if count >= 5:
            score = 90
        elif count >= 3:
            score = 70
        elif count >= 2:
            score = 50
        elif count == 1:
            score = 30
        else:
            score = 10

        return IEHIComponent(
            name=name,
            score=float(score),
            weight=weight,
            description=(
                f"MoMo active in {count} corridors: "
                f"{', '.join(corridors[:4])}"
            ),
            data_present=True,
        )

    def _score_seasonal_resilience(
        self, cell: Optional[Dict]
    ) -> IEHIComponent:
        name = "seasonal_resilience"
        weight = _COMPONENT_WEIGHTS[name]
        if not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        lean_month_drop = cell.get(
            "momo_lean_season_volume_drop_pct", 0.30
        )
        # Lower drop = more resilient
        if lean_month_drop <= 0.10:
            score = 90
        elif lean_month_drop <= 0.20:
            score = 70
        elif lean_month_drop <= 0.35:
            score = 50
        elif lean_month_drop <= 0.50:
            score = 30
        else:
            score = 15

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
        name = "formalisation_signal"
        weight = _COMPONENT_WEIGHTS[name]
        if not pbb and not cell:
            return IEHIComponent(
                name=name, score=0.0, weight=weight,
                description="No data", data_present=False
            )

        # New bank account openings in past 90 days from employer cluster
        new_accounts = (pbb or {}).get(
            "new_accounts_from_employer_cluster_90d", 0
        )
        total_informal = max(
            (cell or {}).get("estimated_employee_count", 100)
            - (pbb or {}).get("payroll_account_count", 0),
            1
        )

        formalisation_rate = new_accounts / total_informal
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
        headcount = cluster.estimated_informal_headcount
        volume = cluster.estimated_monthly_momo_volume_zar
        corridors = len(cluster.active_momo_corridors)

        if iehi >= 70 and trajectory == "GROWING":
            return (
                f"Healthy and growing informal cluster: {headcount:,} workers, "
                f"R{volume:,.0f}/month MoMo volume across {corridors} corridors. "
                f"High bankarisation opportunity — recommend MoMo-to-Account "
                f"migration campaign and micro-lending pipeline."
            )
        elif iehi >= 50:
            return (
                f"Stable informal cluster: {headcount:,} workers, "
                f"R{volume:,.0f}/month. "
                f"MoMo penetration improvement would unlock NIM opportunity."
            )
        elif trajectory == "DECLINING":
            return (
                f"Declining informal cluster: {headcount:,} workers. "
                f"Monitor for employer payroll delays or workforce contraction."
            )
        else:
            return (
                f"Early-stage informal cluster: {headcount:,} workers. "
                f"Assess MoMo adoption barriers and consider incentive programme."
            )
