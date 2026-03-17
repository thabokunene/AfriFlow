"""
Governance - Country Regulatory Registry

We maintain a registry of regulatory requirements
per country across AfriFlow's 20-country footprint.
This includes data protection laws, banking regulators,
telecom regulators, and FX control regimes.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger

logger = get_logger("governance.regulatory_registry")


class DataProtectionLevel(Enum):
    """Level of data protection regulation."""
    COMPREHENSIVE = "comprehensive"  # GDPR/POPIA-level
    MODERATE = "moderate"  # Basic data protection law
    MINIMAL = "minimal"  # Sectoral or no law
    NONE = "none"  # No data protection framework


class FXControlLevel(Enum):
    """Level of foreign exchange controls."""
    LIBERAL = "liberal"  # Minimal controls
    MODERATE = "moderate"  # Some reporting requirements
    RESTRICTIVE = "restrictive"  # Significant controls
    PROHIBITIVE = "prohibitive"  # Severe restrictions


@dataclass
class RegulatoryProfile:
    """
    Regulatory profile for a country.

    Attributes:
        country_code: ISO 3166-1 alpha-2 code
        country_name: Full country name
        data_protection_law: Name of data protection law
        data_protection_level: Level of protection
        banking_regulator: Name of banking regulator
        telecom_regulator: Name of telecom regulator
        fx_control_level: Level of FX controls
        poPIA_adequate: Whether recognized as adequate by POPIA
        notes: Additional notes
    """
    country_code: str
    country_name: str
    data_protection_law: Optional[str] = None
    data_protection_level: DataProtectionLevel = DataProtectionLevel.MINIMAL
    banking_regulator: Optional[str] = None
    telecom_regulator: Optional[str] = None
    fx_control_level: FXControlLevel = FXControlLevel.MODERATE
    popia_adequate: bool = False
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate regulatory profile."""
        if not self.country_code or len(self.country_code) != 2:
            raise ValueError("country_code must be 2 characters")


class CountryRegulatoryRegistry:
    """
    Registry of regulatory profiles by country.

    We maintain this registry to ensure compliance
    with local regulations when processing and
    transferring data across borders.

    Attributes:
        profiles: Regulatory profiles by country code
    """

    # Pre-populated regulatory profiles for AfriFlow countries
    AFRICAN_PROFILES: Dict[str, Dict[str, Any]] = {
        "ZA": {
            "country_name": "South Africa",
            "data_protection_law": "POPIA (Act 4 of 2013)",
            "data_protection_level": "comprehensive",
            "banking_regulator": "SARB Prudential Authority",
            "telecom_regulator": "ICASA",
            "fx_control_level": "moderate",
            "popia_adequate": True,
        },
        "NG": {
            "country_name": "Nigeria",
            "data_protection_law": "NDPR 2019",
            "data_protection_level": "moderate",
            "banking_regulator": "Central Bank of Nigeria",
            "telecom_regulator": "Nigerian Communications Commission",
            "fx_control_level": "restrictive",
            "popia_adequate": False,
        },
        "KE": {
            "country_name": "Kenya",
            "data_protection_law": "Data Protection Act 2019",
            "data_protection_level": "comprehensive",
            "banking_regulator": "Central Bank of Kenya",
            "telecom_regulator": "Communications Authority of Kenya",
            "fx_control_level": "moderate",
            "popia_adequate": False,
        },
        "GH": {
            "country_name": "Ghana",
            "data_protection_law": "Data Protection Act 2012",
            "data_protection_level": "moderate",
            "banking_regulator": "Bank of Ghana",
            "telecom_regulator": "National Communications Authority",
            "fx_control_level": "moderate",
            "popia_adequate": False,
        },
        "TZ": {
            "country_name": "Tanzania",
            "data_protection_law": "Personal Data Protection Act 2022",
            "data_protection_level": "moderate",
            "banking_regulator": "Bank of Tanzania",
            "telecom_regulator": "TCRA",
            "fx_control_level": "restrictive",
            "popia_adequate": False,
        },
        "UG": {
            "country_name": "Uganda",
            "data_protection_law": "Data Protection and Privacy Act 2019",
            "data_protection_level": "moderate",
            "banking_regulator": "Bank of Uganda",
            "telecom_regulator": "Uganda Communications Commission",
            "fx_control_level": "moderate",
            "popia_adequate": False,
        },
        "ZM": {
            "country_name": "Zambia",
            "data_protection_law": "Data Protection Act 2021",
            "data_protection_level": "moderate",
            "banking_regulator": "Bank of Zambia",
            "telecom_regulator": "ZICTA",
            "fx_control_level": "moderate",
            "popia_adequate": False,
        },
        "MZ": {
            "country_name": "Mozambique",
            "data_protection_law": "Data Protection Law 22/11",
            "data_protection_level": "moderate",
            "banking_regulator": "Banco Nacional de Angola",
            "telecom_regulator": "INACOM",
            "fx_control_level": "restrictive",
            "popia_adequate": False,
        },
        "CD": {
            "country_name": "Democratic Republic of Congo",
            "data_protection_law": "Draft law pending",
            "data_protection_level": "minimal",
            "banking_regulator": "Banque Centrale du Congo",
            "telecom_regulator": "ARPTC",
            "fx_control_level": "restrictive",
            "popia_adequate": False,
        },
        "AO": {
            "country_name": "Angola",
            "data_protection_law": "Data Protection Law 22/11",
            "data_protection_level": "moderate",
            "banking_regulator": "Banco Nacional de Angola",
            "telecom_regulator": "INACOM",
            "fx_control_level": "prohibitive",
            "popia_adequate": False,
        },
        "CI": {
            "country_name": "Cote d'Ivoire",
            "data_protection_law": "Law 2013-450",
            "data_protection_level": "moderate",
            "banking_regulator": "BCEAO",
            "telecom_regulator": "ARTCI",
            "fx_control_level": "liberal",
            "popia_adequate": False,
        },
        "BW": {
            "country_name": "Botswana",
            "data_protection_law": "Data Protection Act 2018",
            "data_protection_level": "comprehensive",
            "banking_regulator": "Bank of Botswana",
            "telecom_regulator": "BOCRA",
            "fx_control_level": "liberal",
            "popia_adequate": False,
        },
        "NA": {
            "country_name": "Namibia",
            "data_protection_law": "Data Protection Act pending",
            "data_protection_level": "minimal",
            "banking_regulator": "Bank of Namibia",
            "telecom_regulator": "CRAN",
            "fx_control_level": "liberal",
            "popia_adequate": False,
        },
    }

    def __init__(self) -> None:
        """Initialize the regulatory registry."""
        self.profiles: Dict[str, RegulatoryProfile] = {}
        self._load_default_profiles()
        logger.info(
            f"CountryRegulatoryRegistry initialized "
            f"with {len(self.profiles)} countries"
        )

    def _load_default_profiles(self) -> None:
        """Load default African regulatory profiles."""
        for country_code, data in self.AFRICAN_PROFILES.items():
            try:
                profile = RegulatoryProfile(
                    country_code=country_code,
                    country_name=data["country_name"],
                    data_protection_law=data.get("data_protection_law"),
                    data_protection_level=DataProtectionLevel(
                        data.get("data_protection_level", "minimal")
                    ),
                    banking_regulator=data.get("banking_regulator"),
                    telecom_regulator=data.get("telecom_regulator"),
                    fx_control_level=FXControlLevel(
                        data.get("fx_control_level", "moderate")
                    ),
                    popia_adequate=data.get("popia_adequate", False),
                )
                self.profiles[country_code] = profile
            except Exception as e:
                logger.error(
                    f"Failed to load profile for {country_code}: {e}"
                )

    def get_profile(
        self,
        country_code: str
    ) -> Optional[RegulatoryProfile]:
        """
        Get regulatory profile for a country.

        Args:
            country_code: ISO 3166-1 alpha-2 code

        Returns:
            Regulatory profile or None
        """
        return self.profiles.get(country_code.upper())

    def add_profile(
        self,
        profile: RegulatoryProfile
    ) -> None:
        """
        Add a regulatory profile.

        Args:
            profile: Regulatory profile to add
        """
        self.profiles[profile.country_code.upper()] = profile
        logger.info(f"Added profile for {profile.country_code}")

    def get_countries_by_protection_level(
        self,
        level: DataProtectionLevel
    ) -> List[str]:
        """
        Get countries by data protection level.

        Args:
            level: Protection level to filter by

        Returns:
            List of country codes
        """
        return [
            code for code, profile in self.profiles.items()
            if profile.data_protection_level == level
        ]

    def get_countries_by_fx_control(
        self,
        level: FXControlLevel
    ) -> List[str]:
        """
        Get countries by FX control level.

        Args:
            level: FX control level to filter by

        Returns:
            List of country codes
        """
        return [
            code for code, profile in self.profiles.items()
            if profile.fx_control_level == level
        ]

    def is_data_transfer_allowed(
        self,
        source_country: str,
        destination_country: str
    ) -> bool:
        """
        Check if data transfer is allowed between countries.

        Args:
            source_country: Source country code
            destination_country: Destination country code

        Returns:
            True if transfer is allowed
        """
        source = self.get_profile(source_country)
        dest = self.get_profile(destination_country)

        if not source or not dest:
            logger.warning(
                f"Missing profile for {source_country} or {destination_country}"
            )
            return False

        # Comprehensive countries can transfer to each other
        if (
            source.data_protection_level == DataProtectionLevel.COMPREHENSIVE
            and dest.data_protection_level == DataProtectionLevel.COMPREHENSIVE
        ):
            return True

        # POPIA adequate countries
        if dest.popia_adequate:
            return True

        # Default: require additional safeguards
        logger.warning(
            f"Data transfer from {source_country} to {destination_country} "
            f"may require additional safeguards"
        )
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        by_protection: Dict[str, int] = {}
        by_fx: Dict[str, int] = {}

        for profile in self.profiles.values():
            prot_level = profile.data_protection_level.value
            fx_level = profile.fx_control_level.value

            by_protection[prot_level] = by_protection.get(prot_level, 0) + 1
            by_fx[fx_level] = by_fx.get(fx_level, 0) + 1

        return {
            "total_countries": len(self.profiles),
            "by_protection_level": by_protection,
            "by_fx_control_level": by_fx,
            "popia_adequate_count": sum(
                1 for p in self.profiles.values() if p.popia_adequate
            ),
        }


if __name__ == "__main__":
    # Demo usage
    registry = CountryRegulatoryRegistry()

    # Get profile for South Africa
    za_profile = registry.get_profile("ZA")
    if za_profile:
        print(f"South Africa: {za_profile.data_protection_law}")
        print(f"FX Control: {za_profile.fx_control_level.value}")

    # Get statistics
    stats = registry.get_statistics()
    print(f"\nRegistry Statistics:")
    print(f"Total countries: {stats['total_countries']}")
    print(f"By protection level: {stats['by_protection_level']}")
