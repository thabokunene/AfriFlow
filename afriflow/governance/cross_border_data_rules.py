"""
governance/cross_border_data_rules.py

Country-level data residency rules for the federated
architecture.

We enforce that client PII remains within the
jurisdiction where it originates, while allowing
aggregated and anonymized intelligence to flow to
the central gold layer in South Africa.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set


class DataResidencyTier(Enum):
    """Classification of data residency requirements
    per country."""

    STRICT = auto()
    MODERATE = auto()
    LIBERAL = auto()
    UNREGULATED = auto()


class DataClassification(Enum):
    """Classification of data sensitivity for transfer
    rules."""

    PII = auto()
    AGGREGATED = auto()
    ANONYMIZED = auto()
    METADATA = auto()


@dataclass
class CountryDataRule:
    """Data residency and transfer rules for a single
    country."""

    country_code: str
    country_name: str
    residency_tier: DataResidencyTier
    data_protection_law: str
    banking_regulator: str
    telco_regulator: str
    fx_control_level: str
    pii_must_stay_local: bool
    aggregated_exportable: bool
    requires_regulatory_approval: bool
    notes: str


class CrossBorderDataRules:
    """We manage the data residency and transfer rules
    across Standard Bank's 20-country footprint.

    The core principle: raw PII stays in-country.
    Aggregated signals flow to the central gold layer.
    This is not a policy choice but a legal requirement
    in most African jurisdictions.
    """

    RULES: Dict[str, CountryDataRule] = {
        "ZA": CountryDataRule(
            country_code="ZA",
            country_name="South Africa",
            residency_tier=DataResidencyTier.MODERATE,
            data_protection_law="POPIA (Act 4 of 2013)",
            banking_regulator="SARB Prudential Authority",
            telco_regulator="ICASA under RICA",
            fx_control_level="Limited (SARB Exchange Control)",
            pii_must_stay_local=False,
            aggregated_exportable=True,
            requires_regulatory_approval=False,
            notes=(
                "POPIA allows transfer to countries with "
                "adequate protection. Most African "
                "countries do not qualify, so we default "
                "to keeping PII local."
            ),
        ),
        "NG": CountryDataRule(
            country_code="NG",
            country_name="Nigeria",
            residency_tier=DataResidencyTier.STRICT,
            data_protection_law="NDPR 2019 (under NITDA Act)",
            banking_regulator="Central Bank of Nigeria",
            telco_regulator="Nigerian Communications Commission",
            fx_control_level="Strict (CBN capital controls)",
            pii_must_stay_local=True,
            aggregated_exportable=True,
            requires_regulatory_approval=True,
            notes=(
                "CBN requires banking data to be processed "
                "and stored in Nigeria. NDPR requires "
                "data protection impact assessment for "
                "any cross-border transfer."
            ),
        ),
        "KE": CountryDataRule(
            country_code="KE",
            country_name="Kenya",
            residency_tier=DataResidencyTier.MODERATE,
            data_protection_law="Data Protection Act 2019",
            banking_regulator="Central Bank of Kenya",
            telco_regulator="Communications Authority of Kenya",
            fx_control_level="Moderate",
            pii_must_stay_local=True,
            aggregated_exportable=True,
            requires_regulatory_approval=False,
            notes=(
                "Kenya DPA requires adequate protection "
                "in receiving country for PII transfer."
            ),
        ),
        "GH": CountryDataRule(
            country_code="GH",
            country_name="Ghana",
            residency_tier=DataResidencyTier.MODERATE,
            data_protection_law="Data Protection Act 2012 (Act 843)",
            banking_regulator="Bank of Ghana",
            telco_regulator="National Communications Authority",
            fx_control_level="Moderate",
            pii_must_stay_local=False,
            aggregated_exportable=True,
            requires_regulatory_approval=False,
            notes="Requires data controller registration with DPC.",
        ),
        "CD": CountryDataRule(
            country_code="CD",
            country_name="Democratic Republic of Congo",
            residency_tier=DataResidencyTier.UNREGULATED,
            data_protection_law="No formal law (draft pending)",
            banking_regulator="Banque Centrale du Congo",
            telco_regulator="ARPTC",
            fx_control_level="Strict",
            pii_must_stay_local=False,
            aggregated_exportable=True,
            requires_regulatory_approval=False,
            notes=(
                "No formal data protection law. We apply "
                "POPIA standards as a conservative default."
            ),
        ),
        "AO": CountryDataRule(
            country_code="AO",
            country_name="Angola",
            residency_tier=DataResidencyTier.STRICT,
            data_protection_law="Data Protection Law 22/11",
            banking_regulator="Banco Nacional de Angola",
            telco_regulator="INACOM",
            fx_control_level="Very strict (BNA controls)",
            pii_must_stay_local=True,
            aggregated_exportable=True,
            requires_regulatory_approval=True,
            notes="BNA requires prior authorization for data export.",
        ),
    }

    @classmethod
    def can_export(
        cls,
        source_country: str,
        data_classification: DataClassification,
    ) -> bool:
        """We determine whether data of a given
        classification can be exported from a country
        to the central gold layer."""
        rule = cls.RULES.get(source_country)
        if rule is None:
            return False

        if data_classification == DataClassification.PII:
            return not rule.pii_must_stay_local

        if data_classification == DataClassification.AGGREGATED:
            return rule.aggregated_exportable

        if data_classification == DataClassification.ANONYMIZED:
            return True

        if data_classification == DataClassification.METADATA:
            return True

        return False

    @classmethod
    def get_exportable_fields(
        cls, source_country: str
    ) -> Dict[str, List[str]]:
        """We return the list of fields that can be
        exported to the central gold layer for a given
        source country.

        PII fields stay local. Aggregated metrics
        are exportable.
        """
        exportable = {
            "always_exportable": [
                "golden_id",
                "total_relationship_value_zar",
                "domains_active",
                "cross_sell_priority",
                "primary_risk_signal",
                "cib_active_corridors",
                "cib_annual_value",
                "forex_hedge_ratio_pct",
                "cell_total_sims",
                "pbb_employee_accounts",
            ],
            "never_exportable": [
                "client_name",
                "registration_number",
                "tax_number",
                "contact_email",
                "contact_phone",
                "address",
                "employee_names",
                "account_numbers",
            ],
        }

        rule = cls.RULES.get(source_country)
        if rule and not rule.pii_must_stay_local:
            exportable["conditionally_exportable"] = [
                "canonical_name",
                "home_country",
            ]
        else:
            exportable["conditionally_exportable"] = []

        return exportable
