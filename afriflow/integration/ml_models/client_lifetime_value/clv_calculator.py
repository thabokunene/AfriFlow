"""
Client Lifetime Value (CLV) Calculator

We estimate the net present value of a client relationship
across all five AfriFlow domains over a 3-year horizon.

The standard CLV formula discounts expected annual revenue
by churn probability at each time step. Our extension:

  CLV = Σ (t=1..T) [ E[Revenue_t] × P(retained_t) ] / (1+r)^t

where:
  E[Revenue_t]  = base_revenue × growth_rate^t
  P(retained_t) = (1 - annual_churn_prob)^t
  r             = cost_of_capital (12% for African operations)
  T             = 3 years

Revenue components by domain:
  CIB        : transaction fees + facility margin + trade finance
  Forex      : spread income + structuring fees
  Insurance  : premium income net of claims ratio
  Cell       : MoMo float + USSD revenue share
  PBB        : NIM on deposits + fee income

Cross-domain synergy uplift: clients active in ≥3 domains
get a 15% revenue uplift (lower CoS from consolidated servicing).

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

_COST_OF_CAPITAL = 0.12          # 12% WACC for pan-African ops
_HORIZON_YEARS = 3
_SYNERGY_THRESHOLD = 3           # domains needed for uplift
_SYNERGY_UPLIFT = 0.15           # 15% revenue uplift

# Revenue-to-AUM ratios per domain (annual)
# These are conservative estimates for a mid-tier African RM book
_DOMAIN_REVENUE_RATIOS: Dict[str, float] = {
    "cib":       0.018,   # 1.8% of facility value
    "forex":     0.0035,  # 0.35% of notional traded
    "insurance": 0.80,    # 80% of premium is net revenue (after claims)
    "cell":      0.025,   # 2.5% of MoMo transaction volume
    "pbb":       0.022,   # 2.2% of AUM (NIM + fees)
}

# Default annual growth assumptions per domain
_DOMAIN_GROWTH_RATES: Dict[str, float] = {
    "cib":       0.08,    # 8% pa — GBP/USD facility growth
    "forex":     0.06,    # 6% pa — currency volume growth
    "insurance": 0.10,    # 10% pa — Africa insurance penetration growth
    "cell":      0.15,    # 15% pa — mobile money adoption
    "pbb":       0.09,    # 9% pa — retail AUM growth
}

# Annual churn probability by churn band
_CHURN_PROB_BY_BAND: Dict[str, float] = {
    "GREEN":    0.05,
    "AMBER":    0.18,
    "RED":      0.40,
    "CRITICAL": 0.65,
}


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class DomainRevenue:
    """Estimated annual revenue from a single domain."""

    domain: str
    base_revenue_zar: float
    growth_rate: float
    aum_or_notional_zar: float
    calculation_basis: str


@dataclass
class CLVResult:
    """
    CLV calculation result for a single client.

    clv_zar         : Net present value of 3-year relationship
    annual_revenues : Year-by-year revenue projections
    domain_breakdown: Revenue breakdown by domain
    """

    client_golden_id: str
    client_name: str
    clv_zar: float
    year1_revenue_zar: float
    year2_revenue_zar: float
    year3_revenue_zar: float
    total_undiscounted_revenue_zar: float
    domain_breakdown: List[DomainRevenue]
    active_domain_count: int
    synergy_uplift_applied: bool
    churn_band: str
    annual_churn_probability: float
    data_confidence: str
    calculated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class CLVCalculator:
    """
    Calculate 3-year CLV for a client using cross-domain signals.

    Domain profiles are dicts following the AfriFlow profile contract.
    All are optional — absent domains reduce the estimate and confidence.

    Usage::

        calc = CLVCalculator()
        result = calc.calculate(
            golden_record={"golden_id": "GLD-001", "canonical_name": "Acme Ltd"},
            cib_profile={"total_facility_value_zar": 200_000_000, ...},
            forex_profile={"annual_notional_traded_zar": 50_000_000, ...},
            churn_band="AMBER",
        )
    """

    def calculate(
        self,
        golden_record: Dict,
        cib_profile: Optional[Dict] = None,
        forex_profile: Optional[Dict] = None,
        insurance_profile: Optional[Dict] = None,
        cell_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
        churn_band: str = "GREEN",
    ) -> CLVResult:
        client_id = golden_record.get("golden_id", "UNKNOWN")
        client_name = golden_record.get("canonical_name", "Unknown")

        domain_revenues = self._compute_domain_revenues(
            cib_profile, forex_profile, insurance_profile,
            cell_profile, pbb_profile
        )

        active_count = len(domain_revenues)
        synergy = active_count >= _SYNERGY_THRESHOLD
        synergy_factor = (1 + _SYNERGY_UPLIFT) if synergy else 1.0

        annual_churn = _CHURN_PROB_BY_BAND.get(churn_band, 0.05)
        retention_rates = [
            (1 - annual_churn) ** t
            for t in range(1, _HORIZON_YEARS + 1)
        ]

        year_revenues = []
        for t in range(1, _HORIZON_YEARS + 1):
            yr_revenue = sum(
                dr.base_revenue_zar * (1 + dr.growth_rate) ** t
                for dr in domain_revenues
            ) * synergy_factor
            year_revenues.append(yr_revenue)

        # Discount each year: PV = Revenue × retention × discount
        clv = sum(
            yr * retention_rates[t] / (1 + _COST_OF_CAPITAL) ** (t + 1)
            for t, yr in enumerate(year_revenues)
        )

        confidence = self._confidence(active_count)

        return CLVResult(
            client_golden_id=client_id,
            client_name=client_name,
            clv_zar=round(clv, 0),
            year1_revenue_zar=round(year_revenues[0], 0),
            year2_revenue_zar=round(year_revenues[1], 0),
            year3_revenue_zar=round(year_revenues[2], 0),
            total_undiscounted_revenue_zar=round(sum(year_revenues), 0),
            domain_breakdown=domain_revenues,
            active_domain_count=active_count,
            synergy_uplift_applied=synergy,
            churn_band=churn_band,
            annual_churn_probability=annual_churn,
            data_confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Domain revenue estimators
    # ------------------------------------------------------------------

    def _compute_domain_revenues(
        self,
        cib: Optional[Dict],
        forex: Optional[Dict],
        insurance: Optional[Dict],
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> List[DomainRevenue]:
        revenues: List[DomainRevenue] = []

        if cib:
            facility = cib.get("total_facility_value_zar", 0.0)
            rev = facility * _DOMAIN_REVENUE_RATIOS["cib"]
            revenues.append(DomainRevenue(
                domain="cib",
                base_revenue_zar=rev,
                growth_rate=_DOMAIN_GROWTH_RATES["cib"],
                aum_or_notional_zar=facility,
                calculation_basis=(
                    f"R{facility:,.0f} facility × "
                    f"{_DOMAIN_REVENUE_RATIOS['cib']*100:.1f}% revenue ratio"
                ),
            ))

        if forex:
            notional = forex.get("annual_notional_traded_zar", 0.0)
            rev = notional * _DOMAIN_REVENUE_RATIOS["forex"]
            revenues.append(DomainRevenue(
                domain="forex",
                base_revenue_zar=rev,
                growth_rate=_DOMAIN_GROWTH_RATES["forex"],
                aum_or_notional_zar=notional,
                calculation_basis=(
                    f"R{notional:,.0f} notional × "
                    f"{_DOMAIN_REVENUE_RATIOS['forex']*100:.2f}% spread"
                ),
            ))

        if insurance:
            annual_premium = insurance.get("total_annual_premium_zar", 0.0)
            rev = annual_premium * _DOMAIN_REVENUE_RATIOS["insurance"]
            revenues.append(DomainRevenue(
                domain="insurance",
                base_revenue_zar=rev,
                growth_rate=_DOMAIN_GROWTH_RATES["insurance"],
                aum_or_notional_zar=annual_premium,
                calculation_basis=(
                    f"R{annual_premium:,.0f} premium × "
                    f"{_DOMAIN_REVENUE_RATIOS['insurance']*100:.0f}% net revenue"
                ),
            ))

        if cell:
            momo_volume = cell.get("annual_momo_volume_zar", 0.0)
            rev = momo_volume * _DOMAIN_REVENUE_RATIOS["cell"]
            revenues.append(DomainRevenue(
                domain="cell",
                base_revenue_zar=rev,
                growth_rate=_DOMAIN_GROWTH_RATES["cell"],
                aum_or_notional_zar=momo_volume,
                calculation_basis=(
                    f"R{momo_volume:,.0f} MoMo volume × "
                    f"{_DOMAIN_REVENUE_RATIOS['cell']*100:.1f}% fee revenue"
                ),
            ))

        if pbb:
            aum = pbb.get("total_aum_zar", 0.0)
            rev = aum * _DOMAIN_REVENUE_RATIOS["pbb"]
            revenues.append(DomainRevenue(
                domain="pbb",
                base_revenue_zar=rev,
                growth_rate=_DOMAIN_GROWTH_RATES["pbb"],
                aum_or_notional_zar=aum,
                calculation_basis=(
                    f"R{aum:,.0f} AUM × "
                    f"{_DOMAIN_REVENUE_RATIOS['pbb']*100:.1f}% NIM + fees"
                ),
            ))

        return revenues

    def _confidence(self, active_domains: int) -> str:
        if active_domains >= 4:
            return "HIGH"
        elif active_domains >= 2:
            return "MEDIUM"
        return "LOW"
