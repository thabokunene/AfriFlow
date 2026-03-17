"""
Cell Network Privacy Compliance (RICA)

We enforce privacy compliance rules specific to the
cell network domain, primarily under:

  South Africa – RICA (Regulation of Interception of
  Communications and Provision of Communication-
  Related Information Act, Act 70 of 2002)

  Nigeria – NCC Regulations on Lawful Interception
  of Communications

  Kenya – Kenya Information and Communications Act
  (KICA) and Data Retention Rules

Cell network data is uniquely sensitive because:

1. MSISDNs (mobile numbers) are quasi-identifiers —
   even without a name they can identify a person
   when combined with location or payment data.

2. MoMo transaction logs reveal behavioural patterns
   (movement, associations, income) that POPIA
   classifies as personal information.

3. Bulk SIM activation data for corporate clients
   contains employee headcounts and location data
   that must stay in-country under RICA.

4. Cross-border remittance creates a data residency
   challenge: a transaction touches two jurisdictions
   and each leg must stay in its own country pod.

Our approach:
  - Raw MSISDNs stored only in the country pod where
    the SIM is registered (RICA requirement).
  - MSISDNs pseudonymised with a country-specific
    HMAC key before they leave the pod.
  - Aggregated SIM counts and derived scores flow
    to the central hub without any MSISDN.
  - MoMo cross-border: sending leg stays in sender
    country, receiving leg stays in receiver country.
    Only anonymised corridor aggregate (count, total
    value) flows to hub.

Disclaimer: Not sanctioned by Standard Bank Group
or MTN Group. Built by Thabo Kunene for portfolio
purposes.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class RICARetentionPolicy(Enum):
    """
    Data retention categories under RICA and
    equivalent national laws.
    """

    CDR_METADATA = "CDR_METADATA"           # 3 years (RICA default)
    MOMO_TRANSACTION = "MOMO_TRANSACTION"   # 5 years (FICA)
    SIM_REGISTRATION = "SIM_REGISTRATION"   # Subscription life + 3 years
    BULK_AGGREGATE = "BULK_AGGREGATE"       # 2 years
    PSEUDONYMISED = "PSEUDONYMISED"         # 3 years


# Retention periods in days per category and country.
# Where a country has stricter requirements, we use
# the stricter rule.
RETENTION_DAYS: Dict[str, Dict[str, int]] = {
    "ZA": {
        "CDR_METADATA":     1095,   # 3 years (RICA)
        "MOMO_TRANSACTION": 1825,   # 5 years (FICA)
        "SIM_REGISTRATION": 1095,
        "BULK_AGGREGATE":    730,
        "PSEUDONYMISED":    1095,
    },
    "NG": {
        "CDR_METADATA":      730,   # NCC: 2 years
        "MOMO_TRANSACTION": 1825,
        "SIM_REGISTRATION": 1095,
        "BULK_AGGREGATE":    730,
        "PSEUDONYMISED":     730,
    },
    "KE": {
        "CDR_METADATA":      730,   # CA Kenya: 2 years
        "MOMO_TRANSACTION": 1825,
        "SIM_REGISTRATION": 1095,
        "BULK_AGGREGATE":    730,
        "PSEUDONYMISED":     730,
    },
}

DEFAULT_RETENTION: Dict[str, int] = {
    "CDR_METADATA":     1095,
    "MOMO_TRANSACTION": 1825,
    "SIM_REGISTRATION": 1095,
    "BULK_AGGREGATE":    730,
    "PSEUDONYMISED":    1095,
}

# Countries where MSISDNs may never leave in plaintext
MSISDN_STRICT_RESIDENCY = {"NG", "ZA", "KE", "GH", "TZ"}

# Countries where cross-border MoMo data sharing
# requires regulatory pre-approval
MOMO_XBORDER_APPROVAL_REQUIRED = {"NG", "AO", "ET"}


@dataclass
class MSISDNHandlingDecision:
    """Decision on how to handle an MSISDN."""

    msisdn_country: str
    purpose: str
    can_use_plaintext: bool
    must_pseudonymise: bool
    can_export: bool
    export_requires_approval: bool
    retention_days: int
    notes: str


@dataclass
class MoMoCrossBorderDecision:
    """
    Decision on how to handle data for a cross-border
    MoMo transaction.
    """

    sender_country: str
    receiver_country: str
    can_process_sender_leg_locally: bool
    can_process_receiver_leg_locally: bool
    can_share_aggregate_to_hub: bool
    requires_dual_approval: bool
    notes: str


@dataclass
class SIMDataPrivacyCheck:
    """
    Privacy assessment for a corporate SIM
    activation batch.
    """

    corporate_client_id: str
    country: str
    sim_count: int
    contains_msisdns: bool
    contains_location: bool
    processing_permitted: bool
    export_to_hub_permitted: bool
    fields_to_strip_before_export: List[str]
    retention_category: RICARetentionPolicy
    notes: str


class CellPrivacyCompliance:
    """
    We enforce RICA and equivalent cell network
    privacy regulations for AfriFlow.

    Usage:

        compliance = CellPrivacyCompliance(
            country_hmac_keys={"ZA": "secret-za-key"}
        )

        decision = compliance.msisdn_handling_decision(
            msisdn_country="NG",
            purpose="aggregate_corridor_analysis",
        )

        pseudo = compliance.pseudonymise_msisdn(
            msisdn="08031234567",
            country="NG",
        )
    """

    def __init__(
        self,
        country_hmac_keys: Optional[Dict[str, str]] = None,
    ) -> None:
        # In production: loaded from AWS Secrets Manager
        self._keys = country_hmac_keys or {}

    def msisdn_handling_decision(
        self,
        msisdn_country: str,
        purpose: str,
    ) -> MSISDNHandlingDecision:
        """
        We determine how an MSISDN from a given country
        may be handled for a specific purpose.

        Supported purposes:
          "local_processing"
          "aggregate_corridor_analysis"
          "compliance_investigation"
          "salary_matching"
        """

        strict = msisdn_country in MSISDN_STRICT_RESIDENCY
        retention = self._retention_days(msisdn_country)

        if purpose == "local_processing":
            return MSISDNHandlingDecision(
                msisdn_country=msisdn_country,
                purpose=purpose,
                can_use_plaintext=True,
                must_pseudonymise=False,
                can_export=False,
                export_requires_approval=False,
                retention_days=retention["CDR_METADATA"],
                notes="Plaintext permitted within country pod only",
            )

        if purpose == "aggregate_corridor_analysis":
            return MSISDNHandlingDecision(
                msisdn_country=msisdn_country,
                purpose=purpose,
                can_use_plaintext=False,
                must_pseudonymise=True,
                can_export=True,
                export_requires_approval=False,
                retention_days=retention["BULK_AGGREGATE"],
                notes=(
                    "MSISDN must be pseudonymised with country "
                    "HMAC key before export. Hub receives "
                    "pseudonym only, never plaintext."
                ),
            )

        if purpose == "compliance_investigation":
            return MSISDNHandlingDecision(
                msisdn_country=msisdn_country,
                purpose=purpose,
                can_use_plaintext=True,
                must_pseudonymise=False,
                can_export=not strict,
                export_requires_approval=True,
                retention_days=retention["CDR_METADATA"],
                notes=(
                    "Requires compliance officer approval. "
                    "Export to hub requires regulatory approval "
                    "if strict residency country."
                ),
            )

        if purpose == "salary_matching":
            return MSISDNHandlingDecision(
                msisdn_country=msisdn_country,
                purpose=purpose,
                can_use_plaintext=True,
                must_pseudonymise=False,
                can_export=False,
                export_requires_approval=False,
                retention_days=retention["PSEUDONYMISED"],
                notes=(
                    "Matching performed in-country pod only. "
                    "Only corporate_client_id + employee count "
                    "flows to hub."
                ),
            )

        # Unknown purpose — apply strictest policy
        return MSISDNHandlingDecision(
            msisdn_country=msisdn_country,
            purpose=purpose,
            can_use_plaintext=False,
            must_pseudonymise=True,
            can_export=False,
            export_requires_approval=True,
            retention_days=retention["CDR_METADATA"],
            notes=f"Unknown purpose '{purpose}' — applying strictest policy",
        )

    def pseudonymise_msisdn(
        self,
        msisdn: str,
        country: str,
    ) -> str:
        """
        We pseudonymise an MSISDN using a country-
        specific HMAC-SHA256 key.

        The pseudonym is deterministic (same MSISDN
        + country → same pseudonym) so we can track
        MoMo corridors without storing real numbers.

        Re-identification from the pseudonym requires
        the country HMAC key, held only in the country
        pod's secrets manager.
        """

        key = self._keys.get(country, f"demo-key-{country}")
        digest = hmac.new(
            key.encode("utf-8"),
            msisdn.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"PSN-{country}-{digest[:16].upper()}"

    def assess_sim_batch(
        self,
        corporate_client_id: str,
        country: str,
        sim_count: int,
        contains_msisdns: bool = True,
        contains_location: bool = False,
    ) -> SIMDataPrivacyCheck:
        """
        We assess whether a corporate SIM activation
        batch can be processed and/or exported to hub.
        """

        fields_to_strip: List[str] = []
        if contains_msisdns:
            fields_to_strip.append("msisdn")
        if contains_location and country in MSISDN_STRICT_RESIDENCY:
            fields_to_strip.extend([
                "cell_tower_id",
                "location_lat",
                "location_lon",
            ])

        notes = (
            f"Strip {fields_to_strip} before export. "
            f"sim_count ({sim_count}) and corporate_client_id "
            f"may flow to central hub as aggregate."
        )

        return SIMDataPrivacyCheck(
            corporate_client_id=corporate_client_id,
            country=country,
            sim_count=sim_count,
            contains_msisdns=contains_msisdns,
            contains_location=contains_location,
            processing_permitted=True,
            export_to_hub_permitted=True,
            fields_to_strip_before_export=fields_to_strip,
            retention_category=RICARetentionPolicy.SIM_REGISTRATION,
            notes=notes,
        )

    def momo_cross_border_decision(
        self,
        sender_country: str,
        receiver_country: str,
        transaction_value_usd: float = 0.0,
    ) -> MoMoCrossBorderDecision:
        """
        We determine how to handle data for a cross-
        border MoMo transaction.

        Each leg is processed in its own country pod.
        Only the anonymised corridor aggregate
        (no MSISDNs, no individual amounts) flows
        to the central hub.
        """

        requires_approval = (
            sender_country in MOMO_XBORDER_APPROVAL_REQUIRED
            or receiver_country in MOMO_XBORDER_APPROVAL_REQUIRED
        )

        notes = (
            f"Sender leg: {sender_country} pod. "
            f"Receiver leg: {receiver_country} pod. "
            f"Hub receives corridor aggregate only."
        )
        if requires_approval:
            notes += (
                " One or both countries require regulatory "
                "pre-approval for cross-border MoMo data sharing."
            )

        return MoMoCrossBorderDecision(
            sender_country=sender_country,
            receiver_country=receiver_country,
            can_process_sender_leg_locally=True,
            can_process_receiver_leg_locally=True,
            can_share_aggregate_to_hub=True,
            requires_dual_approval=requires_approval,
            notes=notes,
        )

    def get_retention_expiry(
        self,
        country: str,
        category: RICARetentionPolicy,
        record_date: Optional[datetime] = None,
    ) -> datetime:
        """
        We return the date on which a record of this
        type must be deleted or anonymised.
        """

        days = self._retention_days(country).get(
            category.value,
            DEFAULT_RETENTION.get(category.value, 1095),
        )
        base = record_date or datetime.now()
        return base + timedelta(days=days)

    def _retention_days(self, country: str) -> Dict[str, int]:
        return RETENTION_DAYS.get(country, DEFAULT_RETENTION)
