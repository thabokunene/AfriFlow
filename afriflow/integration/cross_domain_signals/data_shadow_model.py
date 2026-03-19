"""
@file data_shadow_model.py
@description Data shadow engine for detecting meaningful data absences across domains,
    generating intelligence signals from gaps between expected and actual client footprints.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard-library imports
from dataclasses import dataclass, field  # Typed, mutable containers for shadow state
from enum import Enum, auto               # Enumerated signal-type classification
from typing import Dict, List, Set        # Type annotations


# ---------------------------------------------------------------------------
# Enumeration: classifies each detected absence into a business category
# ---------------------------------------------------------------------------

class ShadowSignalType(Enum):
    """Types of signals generated from data absences."""

    # Client is using a competitor for a product we offer in this corridor
    COMPETITIVE_LEAKAGE = auto()
    # Absence may indicate regulatory or compliance exposure
    COMPLIANCE_CONCERN = auto()
    # Client has an operational need but no product to cover it
    PRODUCT_GAP = auto()
    # Absence is likely a data pipeline failure, not a business gap
    DATA_FEED_ISSUE = auto()
    # Absence suggests a cross-sell or deepening opportunity
    RELATIONSHIP_OPPORTUNITY = auto()


# ---------------------------------------------------------------------------
# Signal dataclass: one per detected gap
# ---------------------------------------------------------------------------

@dataclass
class ShadowSignal:
    """A single signal generated from a data absence."""

    # Category of the gap driving the signal
    signal_type: ShadowSignalType
    # The domain in which the absence was detected (e.g. "forex", "cell")
    domain: str
    # ISO 3166-1 alpha-2 country code where the absence was detected
    country: str
    # Human-readable explanation of what is missing and why it matters
    description: str
    # Estimated annual revenue the gap represents, in South African Rand
    estimated_revenue_gap_zar: float
    # Priority classification: "HIGH", "MEDIUM", or "LOW"
    urgency: str
    # Specific action the RM should take to close the gap
    recommended_action: str


# ---------------------------------------------------------------------------
# Shadow record: the full absence profile for one client
# ---------------------------------------------------------------------------

@dataclass
class DataShadow:
    """The computed data shadow for a single client
    showing where we expect data but do not observe it."""

    # Unique client identifier from the golden record
    golden_id: str

    # Cell domain: expected vs actual country presence
    expected_cell_countries: Set[str] = field(
        default_factory=set
    )
    actual_cell_countries: Set[str] = field(
        default_factory=set
    )
    missing_cell_countries: Set[str] = field(
        default_factory=set
    )

    # Forex domain: expected vs actual currency coverage
    expected_forex_currencies: Set[str] = field(
        default_factory=set
    )
    actual_forex_currencies: Set[str] = field(
        default_factory=set
    )
    missing_forex_currencies: Set[str] = field(
        default_factory=set
    )

    # Insurance domain: expected vs actual country coverage
    expected_insurance_countries: Set[str] = field(
        default_factory=set
    )
    actual_insurance_countries: Set[str] = field(
        default_factory=set
    )
    missing_insurance_countries: Set[str] = field(
        default_factory=set
    )

    # PBB domain: expected vs actual payroll country presence
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
        """
        We generate actionable signals from every
        detected data absence.

        :return: List of ShadowSignal objects, one per gap detected.
                 Empty list if there are no detected absences.
        """
        signals = []

        # Lookup table: country code → primary currency code
        # Used to name the missing currency in FX leakage signals
        COUNTRY_CURRENCY_MAP = {
            "ZA": "ZAR", "NG": "NGN", "KE": "KES",
            "GH": "GHS", "TZ": "TZS", "UG": "UGX",
            "ZM": "ZMW", "MZ": "MZN", "CD": "CDF",
            "CI": "XOF", "AO": "AOA",
        }

        # --- FX leakage signals ---
        # Client pays into a country but has no FX hedging for that corridor.
        # Most likely explanation: they are using a competitor bank for FX.
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
                    # Placeholder estimate: a full corridor typically yields ~R500k p.a.
                    estimated_revenue_gap_zar=500_000,
                    urgency="HIGH",
                    recommended_action=(
                        "Offer bundled FX hedging package "
                        "for this corridor."
                    ),
                )
            )

        # --- Insurance gap signals ---
        # Client has CIB operations in a country but no insurance coverage.
        # This is both a revenue opportunity and an implicit risk concern.
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
                    # Lower estimate than FX leakage — insurance premiums are smaller
                    estimated_revenue_gap_zar=200_000,
                    urgency="MEDIUM",
                    recommended_action=(
                        "Schedule insurance coverage review "
                        "with Liberty broker for "
                        f"{country} operations."
                    ),
                )
            )

        # --- Cell presence signals ---
        # Client pays into a country but has no MTN SIM presence.
        # Could indicate informal-channel operations or competitor telco usage.
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
                    # Telco revenue per corridor is lower than banking revenue
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

        # --- PBB payroll signals ---
        # Client has employees in a country (evidenced by cell SIM activations)
        # but no payroll deposits flowing through PBB.  Employees are banking
        # with a competitor — a clear cross-sell opportunity.
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
                    # Payroll capture is high-value: salary plus transactional fees
                    estimated_revenue_gap_zar=300_000,
                    urgency="HIGH",
                    recommended_action=(
                        "Offer corporate payroll capture "
                        f"package for {country} employees."
                    ),
                )
            )

        return signals


# ---------------------------------------------------------------------------
# Model: computes the shadow for one client from their known domain footprints
# ---------------------------------------------------------------------------

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

    # Authoritative country → currency mapping used when deriving expected FX coverage
    COUNTRY_CURRENCY_MAP = {
        "ZA": "ZAR", "NG": "NGN", "KE": "KES",
        "GH": "GHS", "TZ": "TZS", "UG": "UGX",
        "ZM": "ZMW", "MZ": "MZN", "CD": "CDF",
        "CI": "XOF", "AO": "AOA", "SN": "XOF",  # Senegal also uses XOF
    }

    def compute_shadow(
        self,
        golden_id: str,
        known_operations: Dict[str, Dict],
    ) -> DataShadow:
        """
        We compute the data shadow by comparing what
        we observe with what we expect.

        known_operations structure:
        {
            "cib": {"countries": ["ZA", "NG", "KE"]},
            "forex": {"currencies": ["ZAR", "NGN"]},
            "cell": {"countries": ["ZA", "NG"]},
            "insurance": {"countries": ["ZA"]},
            "pbb": {"countries": ["ZA"]},
        }

        :param golden_id: Unique client identifier from the golden record
        :param known_operations: Dict describing each domain's observed footprint
        :return: DataShadow containing all expected, actual, and missing sets
        """
        # Extract the observed footprint for each domain
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

        # Derive expected footprints from the CIB anchor:
        # Every country the client pays into should also have Cell and Insurance
        expected_cell = cib_countries.copy()
        expected_insurance = cib_countries.copy()
        # PBB expectation is derived from Cell presence: employees need banking
        expected_pbb = cell_countries.copy()

        # Build the expected forex currency set from CIB countries
        # (only include currencies we have a known mapping for)
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

        # Set subtraction: expected minus actual = missing (the shadow)
        missing_forex = expected_forex_currencies - forex_currencies
        missing_cell = expected_cell - cell_countries
        missing_insurance = expected_insurance - insurance_countries
        missing_pbb = expected_pbb - pbb_countries

        # Assemble the full shadow record
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
