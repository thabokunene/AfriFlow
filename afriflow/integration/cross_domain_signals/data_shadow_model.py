"""
integration/cross_domain_signals/data_shadow_model.py

Data shadow model for detecting meaningful absences
across domains.

In developed markets, missing data is an error to fix.
In African markets, the absence of expected data is
itself a signal. We compute the expected data footprint
for each client and generate intelligence from the gaps.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set


class ShadowSignalType(Enum):
    """Types of signals generated from data absences."""

    COMPETITIVE_LEAKAGE = auto()
    COMPLIANCE_CONCERN = auto()
    PRODUCT_GAP = auto()
    DATA_FEED_ISSUE = auto()
    RELATIONSHIP_OPPORTUNITY = auto()


@dataclass
class ShadowSignal:
    """A single signal generated from a data absence."""

    signal_type: ShadowSignalType
    domain: str
    country: str
    description: str
    estimated_revenue_gap_zar: float
    urgency: str
    recommended_action: str


@dataclass
class DataShadow:
    """The computed data shadow for a single client
    showing where we expect data but do not observe it."""

    golden_id: str

    expected_cell_countries: Set[str] = field(
        default_factory=set
    )
    actual_cell_countries: Set[str] = field(
        default_factory=set
    )
    missing_cell_countries: Set[str] = field(
        default_factory=set
    )

    expected_forex_currencies: Set[str] = field(
        default_factory=set
    )
    actual_forex_currencies: Set[str] = field(
        default_factory=set
    )
    missing_forex_currencies: Set[str] = field(
        default_factory=set
    )

    expected_insurance_countries: Set[str] = field(
        default_factory=set
    )
    actual_insurance_countries: Set[str] = field(
        default_factory=set
    )
    missing_insurance_countries: Set[str] = field(
        default_factory=set
    )

    expected_pbb_countries: Set[str] = field(
        default_factory=set
    )
    actual_pbb_countries: Set[str] = field(
        default_factory=set
    )
    missing_pbb_countries: Set[str] = field(
        default_factory=set
    )

    def get_signals(self) -> List[ShadowSignal]:
        """We generate actionable signals from every
        detected data absence."""
        signals = []

        COUNTRY_CURRENCY_MAP = {
            "ZA": "ZAR", "NG": "NGN", "KE": "KES",
            "GH": "GHS", "TZ": "TZS", "UG": "UGX",
            "ZM": "ZMW", "MZ": "MZN", "CD": "CDF",
            "CI": "XOF", "AO": "AOA",
        }

        for country in self.missing_forex_currencies:
            signals.append(
                ShadowSignal(
                    signal_type=(
                        ShadowSignalType.COMPETITIVE_LEAKAGE
                    ),
                    domain="forex",
                    country=country,
                    description=(
                        f"Client has CIB activity in "
                        f"{country} but no FX hedging for "
                        f"{COUNTRY_CURRENCY_MAP.get(country, country)}. "
                        f"Likely using a competitor for FX."
                    ),
                    estimated_revenue_gap_zar=500_000,
                    urgency="HIGH",
                    recommended_action=(
                        "Offer bundled FX hedging package "
                        "for this corridor."
                    ),
                )
            )

        for country in self.missing_insurance_countries:
            signals.append(
                ShadowSignal(
                    signal_type=ShadowSignalType.PRODUCT_GAP,
                    domain="insurance",
                    country=country,
                    description=(
                        f"Client has operations in "
                        f"{country} but no insurance "
                        f"coverage through Liberty or "
                        f"Standard Bank Insurance."
                    ),
                    estimated_revenue_gap_zar=200_000,
                    urgency="MEDIUM",
                    recommended_action=(
                        "Schedule insurance coverage review "
                        "with Liberty broker for "
                        f"{country} operations."
                    ),
                )
            )

        for country in self.missing_cell_countries:
            signals.append(
                ShadowSignal(
                    signal_type=(
                        ShadowSignalType.COMPLIANCE_CONCERN
                    ),
                    domain="cell",
                    country=country,
                    description=(
                        f"Client has CIB payments to "
                        f"{country} but zero MTN SIM "
                        f"presence. They may be operating "
                        f"through informal channels or "
                        f"using a competitor telco."
                    ),
                    estimated_revenue_gap_zar=100_000,
                    urgency="MEDIUM",
                    recommended_action=(
                        "Verify client operational "
                        "footprint. If using competitor "
                        "telco, propose MTN corporate "
                        "package."
                    ),
                )
            )

        for country in self.missing_pbb_countries:
            signals.append(
                ShadowSignal(
                    signal_type=(
                        ShadowSignalType.RELATIONSHIP_OPPORTUNITY
                    ),
                    domain="pbb",
                    country=country,
                    description=(
                        f"Client has employees in "
                        f"{country} (per cell data) but "
                        f"zero payroll deposits in PBB. "
                        f"Employees are banking elsewhere."
                    ),
                    estimated_revenue_gap_zar=300_000,
                    urgency="HIGH",
                    recommended_action=(
                        "Offer corporate payroll capture "
                        f"package for {country} employees."
                    ),
                )
            )

        return signals


class DataShadowModel:
    """We compute the expected data footprint for each
    client based on their known operations across
    domains, then detect and classify the gaps.

    The key insight: if CIB shows a client paying
    suppliers in Kenya, we expect to see KES in their
    forex book, Kenyan SIMs in their cell data,
    Kenyan insurance coverage, and Kenyan payroll
    deposits. Every absence is a signal.
    """

    COUNTRY_CURRENCY_MAP = {
        "ZA": "ZAR", "NG": "NGN", "KE": "KES",
        "GH": "GHS", "TZ": "TZS", "UG": "UGX",
        "ZM": "ZMW", "MZ": "MZN", "CD": "CDF",
        "CI": "XOF", "AO": "AOA", "SN": "XOF",
    }

    def compute_shadow(
        self,
        golden_id: str,
        known_operations: Dict[str, Dict],
    ) -> DataShadow:
        """We compute the data shadow by comparing what
        we observe with what we expect.

        known_operations structure:
        {
            "cib": {"countries": ["ZA", "NG", "KE"]},
            "forex": {"currencies": ["ZAR", "NGN"]},
            "cell": {"countries": ["ZA", "NG"]},
            "insurance": {"countries": ["ZA"]},
            "pbb": {"countries": ["ZA"]},
        }
        """
        cib_countries = set(
            known_operations.get("cib", {}).get(
                "countries", []
            )
        )
        forex_currencies = set(
            known_operations.get("forex", {}).get(
                "currencies", []
            )
        )
        cell_countries = set(
            known_operations.get("cell", {}).get(
                "countries", []
            )
        )
        insurance_countries = set(
            known_operations.get("insurance", {}).get(
                "countries", []
            )
        )
        pbb_countries = set(
            known_operations.get("pbb", {}).get(
                "countries", []
            )
        )

        expected_cell = cib_countries.copy()
        expected_insurance = cib_countries.copy()
        expected_pbb = cell_countries.copy()

        expected_forex_countries = set()
        for country in cib_countries:
            currency = self.COUNTRY_CURRENCY_MAP.get(country)
            if currency:
                expected_forex_countries.add(country)

        expected_forex_currencies = set()
        for country in cib_countries:
            currency = self.COUNTRY_CURRENCY_MAP.get(country)
            if currency:
                expected_forex_currencies.add(currency)

        missing_forex = expected_forex_currencies - forex_currencies
        missing_cell = expected_cell - cell_countries
        missing_insurance = expected_insurance - insurance_countries
        missing_pbb = expected_pbb - pbb_countries

        shadow = DataShadow(
            golden_id=golden_id,
            expected_cell_countries=expected_cell,
            actual_cell_countries=cell_countries,
            missing_cell_countries=missing_cell,
            expected_forex_currencies=expected_forex_currencies,
            actual_forex_currencies=forex_currencies,
            missing_forex_currencies=missing_forex,
            expected_insurance_countries=expected_insurance,
            actual_insurance_countries=insurance_countries,
            missing_insurance_countries=missing_insurance,
            expected_pbb_countries=expected_pbb,
            actual_pbb_countries=pbb_countries,
            missing_pbb_countries=missing_pbb,
        )

        return shadow
