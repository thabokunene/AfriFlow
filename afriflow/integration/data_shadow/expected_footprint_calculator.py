"""
Data Shadow Model: Expected Footprint Calculator.

For each client, we calculate the data footprint we
expect to observe across all five domains based on
what we know from the domains where we have confirmed
data.

When the actual footprint diverges from the expected
footprint, we generate Data Shadow signals. These
signals can indicate competitive leakage, compliance
gaps, or data pipeline issues.

Disclaimer: This is not a sanctioned project. We
built it as a demonstration of concept, domain
knowledge, and skill.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExpectedFootprint:
    """
    The data footprint we expect for a client across
    all domains and countries.
    """

    golden_id: str
    client_name: str

    # Per country, per domain expected presence.
    # True means we expect data in this domain for
    # this country.
    expected: Dict[str, Dict[str, bool]] = field(
        default_factory=dict
    )

    # Per country, per domain actual presence.
    actual: Dict[str, Dict[str, bool]] = field(
        default_factory=dict
    )

    # Per country, per domain, the gap type if any.
    gaps: Dict[str, Dict[str, str]] = field(
        default_factory=dict
    )


class ExpectedFootprintCalculator:
    """
    We calculate what data we expect to see for each
    client across all domains and all countries.

    We derive expectations from confirmed data. For
    example, if CIB data shows R500M in payments to
    Nigeria, we expect to see forex hedging for NGN,
    insurance coverage in Nigeria, cell SIM
    activations in Nigeria, and PBB payroll accounts
    for Nigerian employees.
    """

    # We define minimum CIB corridor value (ZAR) that
    # triggers expectation of other domain presence.
    MIN_CIB_VALUE_FOR_FOREX_EXPECTATION = 5_000_000
    MIN_CIB_VALUE_FOR_INSURANCE_EXPECTATION = 10_000_000
    MIN_CIB_VALUE_FOR_CELL_EXPECTATION = 20_000_000
    MIN_CIB_VALUE_FOR_PBB_EXPECTATION = 50_000_000

    def calculate(
        self,
        golden_id: str,
        client_name: str,
        cib_corridors: Dict[str, float],
        forex_currencies: Dict[str, float],
        insurance_countries: List[str],
        cell_countries: List[str],
        pbb_countries: List[str],
    ) -> ExpectedFootprint:
        """
        Calculate the expected data footprint for a
        client and compare it to actual presence.

        We return an ExpectedFootprint object with
        gaps identified.
        """

        footprint = ExpectedFootprint(
            golden_id=golden_id,
            client_name=client_name,
        )

        # We gather all countries where we see any
        # activity.
        all_countries = set()
        all_countries.update(cib_corridors.keys())
        all_countries.update(
            self._currencies_to_countries(
                forex_currencies
            ).keys()
        )
        all_countries.update(insurance_countries)
        all_countries.update(cell_countries)
        all_countries.update(pbb_countries)

        forex_countries = self._currencies_to_countries(
            forex_currencies
        )

        for country in all_countries:
            cib_value = cib_corridors.get(country, 0)

            # We calculate expected presence per domain
            # for this country.
            expected = {}
            actual = {}
            gaps = {}

            # CIB: If we see any other domain activity
            # in this country, we expect CIB activity
            # too. But CIB is usually our primary
            # signal, so we mark it as expected if we
            # see any corridor value.
            expected["cib"] = cib_value > 0
            actual["cib"] = cib_value > 0

            # Forex: We expect hedging if CIB corridor
            # value exceeds threshold.
            expected["forex"] = (
                cib_value
                >= self.MIN_CIB_VALUE_FOR_FOREX_EXPECTATION
            )
            actual["forex"] = country in forex_countries

            # Insurance: We expect coverage if CIB
            # value is significant.
            expected["insurance"] = (
                cib_value
                >= self.MIN_CIB_VALUE_FOR_INSURANCE_EXPECTATION
            )
            actual["insurance"] = (
                country in insurance_countries
            )

            # Cell: We expect SIM presence if CIB
            # value indicates permanent operations.
            expected["cell"] = (
                cib_value
                >= self.MIN_CIB_VALUE_FOR_CELL_EXPECTATION
            )
            actual["cell"] = (
                country in cell_countries
            )

            # PBB: We expect payroll accounts if CIB
            # value indicates large workforce.
            expected["pbb"] = (
                cib_value
                >= self.MIN_CIB_VALUE_FOR_PBB_EXPECTATION
            )
            actual["pbb"] = (
                country in pbb_countries
            )

            # We identify gaps.
            for domain in [
                "cib", "forex", "insurance",
                "cell", "pbb",
            ]:
                if expected[domain] and not actual[domain]:
                    gaps[domain] = "COMPETITOR_LEAKAGE"
                elif (
                    not expected[domain]
                    and actual[domain]
                ):
                    gaps[domain] = "UNEXPECTED_PRESENCE"

            footprint.expected[country] = expected
            footprint.actual[country] = actual
            if gaps:
                footprint.gaps[country] = gaps

        return footprint

    def _currencies_to_countries(
        self,
        forex_currencies: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Convert currency codes to country codes using
        our currency map.
        """
        from domains.shared.currency_map import (
            CURRENCY_TO_COUNTRY,
        )

        result = {}
        for currency, value in forex_currencies.items():
            country = CURRENCY_TO_COUNTRY.get(currency)
            if country:
                result[country] = value
        return result
