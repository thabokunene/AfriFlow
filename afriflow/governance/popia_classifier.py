"""
POPIA Classifier

The Protection of Personal Information Act (POPIA)
is South Africa's primary data privacy law, in force
since 1 July 2021. It is broadly aligned with GDPR
but has Africa-specific provisions around:

1. Cross-border transfers to "adequate" jurisdictions
2. Special personal information (tribal origin, trade
   union membership, biometric data)
3. Financial information as a distinct category
4. Conditions for lawful processing of children's data
5. Information officer obligations for section 8

We classify every field in the AfriFlow golden record
and domain data products to:
  - Determine whether it is "personal information"
    under POPIA section 1
  - Assign a data category (standard PI, special PI,
    financial PI, or de-identified)
  - Determine the lawful basis for processing
  - Flag fields that cannot leave South Africa without
    adequate safeguards
  - Calculate per-record risk scores for privacy
    impact assessments

This classification drives:
  - Which fields can flow from country pods to the
    central hub (aggregate OK, PII stays)
  - Which fields require consent vs legitimate interest
  - What to include in section 22 breach notifications
  - FSCA reporting obligations for financial records

Disclaimer: This is not legal advice. This is a
demonstration of data engineering for compliance.
Built by Thabo Kunene for portfolio purposes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class POPIACategory(Enum):
    """
    Data categories under POPIA section 1 and
    section 26 (special personal information).
    """

    NOT_PERSONAL = "NOT_PERSONAL"
    PERSONAL = "PERSONAL"
    FINANCIAL = "FINANCIAL"
    SPECIAL_BIOMETRIC = "SPECIAL_BIOMETRIC"
    SPECIAL_HEALTH = "SPECIAL_HEALTH"
    SPECIAL_RACE_ORIGIN = "SPECIAL_RACE_ORIGIN"
    SPECIAL_TRADE_UNION = "SPECIAL_TRADE_UNION"
    SPECIAL_CRIMINAL = "SPECIAL_CRIMINAL"
    CHILDREN = "CHILDREN"
    DE_IDENTIFIED = "DE_IDENTIFIED"


class LawfulBasis(Enum):
    """
    Lawful processing conditions under POPIA
    section 11.
    """

    CONSENT = "CONSENT"
    CONTRACT = "CONTRACT"
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"
    LEGITIMATE_INTEREST = "LEGITIMATE_INTEREST"
    PUBLIC_INTEREST = "PUBLIC_INTEREST"
    VITAL_INTEREST = "VITAL_INTEREST"


class CrossBorderAdequacy(Enum):
    """
    Cross-border transfer status for a field.

    POPIA section 72 requires adequate protection
    before PI is transferred outside South Africa.
    """

    FREE_FLOW = "FREE_FLOW"          # Aggregate / de-identified
    ADEQUATE_COUNTRY = "ADEQUATE_COUNTRY"   # EC adequacy list
    SCCs_REQUIRED = "SCCs_REQUIRED"  # Standard contractual clauses
    BLOCKED = "BLOCKED"              # Cannot transfer without consent


@dataclass
class FieldClassification:
    """
    POPIA classification for a single data field.
    """

    field_name: str
    category: POPIACategory
    lawful_basis: LawfulBasis
    cross_border_status: CrossBorderAdequacy
    retention_days: int               # How long we may keep it
    can_share_internally: bool        # Across divisions
    requires_consent: bool
    section_22_notifiable: bool       # Must notify on breach
    notes: str = ""


@dataclass
class RecordClassification:
    """
    POPIA classification for a complete record
    (e.g., a golden record or domain event).
    """

    record_type: str
    record_id: str
    fields: List[FieldClassification] = field(
        default_factory=list
    )
    overall_category: POPIACategory = POPIACategory.NOT_PERSONAL
    risk_score: float = 0.0           # 0–100
    processing_permitted: bool = True
    blocking_reason: Optional[str] = None


# Master field classification registry.
# We define the POPIA status of every field that
# AfriFlow processes. New fields must be registered
# here before being added to any data product.
FIELD_REGISTRY: Dict[str, FieldClassification] = {

    # --- Golden Record fields ---

    "golden_id": FieldClassification(
        field_name="golden_id",
        category=POPIACategory.DE_IDENTIFIED,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.FREE_FLOW,
        retention_days=2555,     # 7 years (FICA requirement)
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
        notes="Synthetic identifier — not personal information",
    ),
    "canonical_name": FieldClassification(
        field_name="canonical_name",
        category=POPIACategory.PERSONAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=True,
        notes="Legal entity name — personal information for sole proprietors",
    ),
    "registration_number": FieldClassification(
        field_name="registration_number",
        category=POPIACategory.PERSONAL,
        lawful_basis=LawfulBasis.LEGAL_OBLIGATION,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=True,
        notes="CIPC/regulatory registration — required for FICA",
    ),
    "tax_number": FieldClassification(
        field_name="tax_number",
        category=POPIACategory.FINANCIAL,
        lawful_basis=LawfulBasis.LEGAL_OBLIGATION,
        cross_border_status=CrossBorderAdequacy.BLOCKED,
        retention_days=3650,     # 10 years (SARS)
        can_share_internally=False,
        requires_consent=False,
        section_22_notifiable=True,
        notes="SARS tax reference — highly sensitive, cannot cross border",
    ),
    "home_country": FieldClassification(
        field_name="home_country",
        category=POPIACategory.PERSONAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.FREE_FLOW,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
        notes="Country-level data is low-risk",
    ),
    "relationship_manager": FieldClassification(
        field_name="relationship_manager",
        category=POPIACategory.PERSONAL,
        lawful_basis=LawfulBasis.LEGITIMATE_INTEREST,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=1825,     # 5 years
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
        notes="Staff member name — internal use only",
    ),
    "total_relationship_value_zar": FieldClassification(
        field_name="total_relationship_value_zar",
        category=POPIACategory.FINANCIAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=True,
        notes="Aggregate financial value — FSCA reportable on breach",
    ),
    "data_classification": FieldClassification(
        field_name="data_classification",
        category=POPIACategory.NOT_PERSONAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.FREE_FLOW,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
    ),

    # --- CIB fields ---

    "facility_value_local": FieldClassification(
        field_name="facility_value_local",
        category=POPIACategory.FINANCIAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=True,
    ),
    "payment_amount": FieldClassification(
        field_name="payment_amount",
        category=POPIACategory.FINANCIAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=True,
    ),
    "creditor_account_number": FieldClassification(
        field_name="creditor_account_number",
        category=POPIACategory.FINANCIAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.BLOCKED,
        retention_days=2555,
        can_share_internally=False,
        requires_consent=False,
        section_22_notifiable=True,
        notes="Account numbers are highly sensitive — cannot cross border",
    ),

    # --- Cell / MoMo fields ---

    "msisdn": FieldClassification(
        field_name="msisdn",
        category=POPIACategory.PERSONAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.BLOCKED,
        retention_days=1095,     # 3 years (RICA)
        can_share_internally=False,
        requires_consent=False,
        section_22_notifiable=True,
        notes="Phone number — RICA-regulated, cannot leave country of registration",
    ),
    "sim_count": FieldClassification(
        field_name="sim_count",
        category=POPIACategory.DE_IDENTIFIED,
        lawful_basis=LawfulBasis.LEGITIMATE_INTEREST,
        cross_border_status=CrossBorderAdequacy.FREE_FLOW,
        retention_days=730,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
        notes="Aggregate SIM count — not personal information",
    ),

    # --- FX / Trade fields ---

    "forward_notional": FieldClassification(
        field_name="forward_notional",
        category=POPIACategory.FINANCIAL,
        lawful_basis=LawfulBasis.CONTRACT,
        cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
        retention_days=2555,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=True,
    ),

    # --- Aggregated / Derived fields (safe to share) ---

    "expansion_signal_score": FieldClassification(
        field_name="expansion_signal_score",
        category=POPIACategory.DE_IDENTIFIED,
        lawful_basis=LawfulBasis.LEGITIMATE_INTEREST,
        cross_border_status=CrossBorderAdequacy.FREE_FLOW,
        retention_days=365,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
        notes="Derived score — not traceable to an individual",
    ),
    "data_shadow_score": FieldClassification(
        field_name="data_shadow_score",
        category=POPIACategory.DE_IDENTIFIED,
        lawful_basis=LawfulBasis.LEGITIMATE_INTEREST,
        cross_border_status=CrossBorderAdequacy.FREE_FLOW,
        retention_days=365,
        can_share_internally=True,
        requires_consent=False,
        section_22_notifiable=False,
    ),
}

# Categories that elevate breach notification urgency
HIGH_RISK_CATEGORIES: Set[POPIACategory] = {
    POPIACategory.FINANCIAL,
    POPIACategory.SPECIAL_BIOMETRIC,
    POPIACategory.SPECIAL_HEALTH,
    POPIACategory.SPECIAL_RACE_ORIGIN,
    POPIACategory.SPECIAL_CRIMINAL,
    POPIACategory.CHILDREN,
}


class POPIAClassifier:
    """
    We classify data fields and records against the
    POPIA framework.

    Usage:

        classifier = POPIAClassifier()

        # Classify a specific field
        fc = classifier.classify_field("msisdn")

        # Classify a whole record
        rc = classifier.classify_record(
            "golden_record",
            record_id="GLD-001",
            fields=["golden_id", "canonical_name", "tax_number"]
        )

        # Check if a record can cross a border
        ok, reason = classifier.can_transfer_to_country(
            rc, destination_country="NG"
        )
    """

    # Countries with EU/UK adequacy decisions that
    # we treat as having adequate protection.
    # Transfers to these require no additional SCCs.
    ADEQUATE_COUNTRIES: Set[str] = {
        "GB", "EU", "DE", "FR", "NL", "IE",
        "CH", "NO", "IS",
    }

    def classify_field(
        self, field_name: str
    ) -> Optional[FieldClassification]:
        """
        We return the POPIA classification for a
        named field, or None if unregistered.

        Unregistered fields should be treated as
        PERSONAL by default until formally classified.
        """

        return FIELD_REGISTRY.get(field_name)

    def classify_record(
        self,
        record_type: str,
        record_id: str,
        field_names: List[str],
    ) -> RecordClassification:
        """
        We classify a full record by aggregating the
        classifications of all its fields.

        The record's overall category is the highest-
        risk category among its fields (worst-case).
        The risk score weights field sensitivity and
        count of high-risk fields.
        """

        classifications = []
        unregistered = []

        for name in field_names:
            fc = FIELD_REGISTRY.get(name)
            if fc is not None:
                classifications.append(fc)
            else:
                unregistered.append(name)
                # Default: treat as personal until classified
                classifications.append(FieldClassification(
                    field_name=name,
                    category=POPIACategory.PERSONAL,
                    lawful_basis=LawfulBasis.CONTRACT,
                    cross_border_status=CrossBorderAdequacy.SCCs_REQUIRED,
                    retention_days=1825,
                    can_share_internally=False,
                    requires_consent=False,
                    section_22_notifiable=True,
                    notes="UNREGISTERED – defaulting to PERSONAL",
                ))

        # Determine overall category (worst case)
        category_priority = [
            POPIACategory.SPECIAL_CRIMINAL,
            POPIACategory.SPECIAL_BIOMETRIC,
            POPIACategory.SPECIAL_HEALTH,
            POPIACategory.SPECIAL_RACE_ORIGIN,
            POPIACategory.SPECIAL_TRADE_UNION,
            POPIACategory.CHILDREN,
            POPIACategory.FINANCIAL,
            POPIACategory.PERSONAL,
            POPIACategory.DE_IDENTIFIED,
            POPIACategory.NOT_PERSONAL,
        ]
        present_categories = {c.category for c in classifications}
        overall = POPIACategory.NOT_PERSONAL
        for cat in category_priority:
            if cat in present_categories:
                overall = cat
                break

        # Risk score: count of high-risk fields / total
        high_risk_count = sum(
            1 for c in classifications
            if c.category in HIGH_RISK_CATEGORIES
        )
        notifiable_count = sum(
            1 for c in classifications
            if c.section_22_notifiable
        )
        risk_score = min(
            (high_risk_count * 20 + notifiable_count * 5), 100
        )

        processing_permitted = True
        blocking_reason = None
        if unregistered:
            blocking_reason = (
                f"Fields not yet POPIA-classified: "
                f"{', '.join(unregistered)}. "
                f"Register in FIELD_REGISTRY before "
                f"adding to a data product."
            )

        return RecordClassification(
            record_type=record_type,
            record_id=record_id,
            fields=classifications,
            overall_category=overall,
            risk_score=risk_score,
            processing_permitted=processing_permitted,
            blocking_reason=blocking_reason,
        )

    def can_transfer_to_country(
        self,
        record: RecordClassification,
        destination_country: str,
    ) -> Tuple:
        """
        We determine whether a record can be transferred
        to the destination country under POPIA s72.

        Returns (permitted: bool, reason: str).
        """

        blocked_fields = [
            fc for fc in record.fields
            if fc.cross_border_status == CrossBorderAdequacy.BLOCKED
        ]
        if blocked_fields:
            blocked_names = [f.field_name for f in blocked_fields]
            return (
                False,
                f"Fields {blocked_names} cannot leave South Africa. "
                f"Strip or anonymise before export.",
            )

        if destination_country in self.ADEQUATE_COUNTRIES:
            return (True, "Adequate protection — free flow permitted")

        sccs_required = [
            fc for fc in record.fields
            if fc.cross_border_status == CrossBorderAdequacy.SCCs_REQUIRED
        ]
        if sccs_required:
            return (
                True,
                f"Transfer permitted with Standard Contractual "
                f"Clauses covering {len(sccs_required)} fields.",
            )

        return (True, "No POPIA objection to transfer")

    def get_retention_policy(
        self, field_name: str
    ) -> Optional[int]:
        """
        We return the maximum retention period in days
        for the given field.
        """

        fc = FIELD_REGISTRY.get(field_name)
        return fc.retention_days if fc else None

    def fields_requiring_consent(
        self, field_names: List[str]
    ) -> List[str]:
        """
        We return which of the given fields require
        explicit consent to process.

        In practice very few fields in a B2B banking
        context require consent — most are covered by
        contract or legal obligation. But any field
        we process purely for analytics without a
        contract basis must be flagged.
        """

        return [
            name for name in field_names
            if FIELD_REGISTRY.get(name, None) is not None
            and FIELD_REGISTRY[name].requires_consent
        ]

    def breach_notification_fields(
        self, field_names: List[str]
    ) -> List[str]:
        """
        We return fields that require section 22
        notification to the Information Regulator
        and affected data subjects if breached.
        """

        return [
            name for name in field_names
            if FIELD_REGISTRY.get(name) is not None
            and FIELD_REGISTRY[name].section_22_notifiable
        ]
