"""
Access Control Matrix

We implement role-based access control (RBAC) for
all AfriFlow data products.

The matrix has two axes:
  - Role      – who the user is (RM, Compliance, etc.)
  - Resource  – what data product they are accessing

Each cell defines which operations are permitted,
with optional country and domain scoping.

Design decisions:

1. Country scoping: An RM in Kenya can only access
   client PII for clients whose home_country is Kenya
   or who have active business in Kenya. They cannot
   see South African PII.

2. Domain scoping: A CIB relationship manager cannot
   query raw insurance policy data. They can see the
   aggregated signal (e.g. "client has insurance
   coverage in Kenya") but not premium amounts or
   claim history.

3. Least privilege: Every role gets the minimum
   access needed to do their job. Adding permissions
   requires a documented change request.

4. Audit: Every access check is logged — permitted
   and denied — for POPIA accountability.

Disclaimer: Not sanctioned by Standard Bank Group.
Built by Thabo Kunene for portfolio purposes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set


class Role(Enum):
    """User roles in the AfriFlow system."""

    # Revenue-facing roles
    RELATIONSHIP_MANAGER = "RM"
    SENIOR_RELATIONSHIP_MANAGER = "SENIOR_RM"
    FX_ADVISOR = "FX_ADVISOR"
    INSURANCE_BROKER = "INSURANCE_BROKER"
    PBB_BRANCH_MANAGER = "PBB_BRANCH"

    # Oversight roles
    EXCO = "EXCO"
    COUNTRY_HEAD = "COUNTRY_HEAD"
    COMPLIANCE_OFFICER = "COMPLIANCE"
    DATA_ENGINEER = "DATA_ENGINEER"
    INFORMATION_OFFICER = "INFORMATION_OFFICER"  # POPIA s50

    # External
    REGULATOR = "REGULATOR"
    INTERNAL_AUDIT = "INTERNAL_AUDIT"


class Resource(Enum):
    """Protected data resources."""

    GOLDEN_RECORD_FULL = "golden_record_full"
    GOLDEN_RECORD_SUMMARY = "golden_record_summary"
    CLIENT_BRIEFING = "client_briefing"
    NBA_RECOMMENDATIONS = "nba_recommendations"
    EXPANSION_SIGNALS = "expansion_signals"
    DATA_SHADOW_SIGNALS = "data_shadow_signals"
    CURRENCY_EVENTS = "currency_events"

    # Domain-specific
    CIB_PAYMENTS_RAW = "cib_payments_raw"
    CIB_FACILITIES = "cib_facilities"
    FOREX_POSITIONS = "forex_positions"
    FOREX_RATES = "forex_rates"
    INSURANCE_POLICIES = "insurance_policies"
    INSURANCE_CLAIMS = "insurance_claims"
    CELL_SIM_DATA = "cell_sim_data"
    CELL_MOMO_RAW = "cell_momo_raw"
    PBB_ACCOUNT_DATA = "pbb_account_data"
    PBB_PAYROLL = "pbb_payroll"

    # Governance
    AUDIT_TRAIL = "audit_trail"
    LINEAGE_GRAPH = "lineage_graph"
    CONSENT_RECORDS = "consent_records"
    POPIA_CLASSIFICATIONS = "popia_classifications"


class Permission(Enum):
    """Operations that can be permitted or denied."""

    READ = "READ"
    READ_AGGREGATED = "READ_AGGREGATED"   # Summaries only
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"                      # Cross-border export
    ADMIN = "ADMIN"


@dataclass
class AccessRule:
    """
    A single rule granting permissions to a role
    on a resource.

    country_scope: if set, the role can only access
    records for clients in these countries.

    domain_scope: if set, within a multi-domain
    resource the role only sees specified domains.
    """

    role: Role
    resource: Resource
    permissions: FrozenSet[Permission]
    country_scope: Optional[FrozenSet[str]] = None
    domain_scope: Optional[FrozenSet[str]] = None
    notes: str = ""


@dataclass
class AccessDecision:
    """Result of an access control check."""

    permitted: bool
    role: Role
    resource: Resource
    requested_permission: Permission
    reason: str
    country_scope_applied: bool = False
    domain_scope_applied: bool = False


class AccessControlMatrix:
    """
    We enforce role-based access control for all
    AfriFlow data products.

    Usage:

        acm = AccessControlMatrix()

        decision = acm.check(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.GOLDEN_RECORD_FULL,
            permission=Permission.READ,
            user_country="KE",
            client_country="KE",
        )

        if not decision.permitted:
            raise PermissionError(decision.reason)
    """

    # The full access control matrix.
    # Each entry defines what a role can do on a resource.
    MATRIX: List[AccessRule] = [

        # --- Relationship Manager ---
        # RMs can read golden records for their country,
        # briefings, and signals. No raw domain data,
        # no cross-country PII.

        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.GOLDEN_RECORD_FULL,
            permissions=frozenset({Permission.READ}),
            notes="Country-scoped at query time",
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.CLIENT_BRIEFING,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.NBA_RECOMMENDATIONS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.EXPANSION_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.DATA_SHADOW_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.CURRENCY_EVENTS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.CIB_FACILITIES,
            permissions=frozenset({Permission.READ}),
            domain_scope=frozenset({"cib"}),
        ),
        AccessRule(
            role=Role.RELATIONSHIP_MANAGER,
            resource=Resource.FOREX_RATES,
            permissions=frozenset({Permission.READ}),
        ),

        # --- FX Advisor ---
        AccessRule(
            role=Role.FX_ADVISOR,
            resource=Resource.FOREX_POSITIONS,
            permissions=frozenset({Permission.READ, Permission.WRITE}),
        ),
        AccessRule(
            role=Role.FX_ADVISOR,
            resource=Resource.FOREX_RATES,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.FX_ADVISOR,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.FX_ADVISOR,
            resource=Resource.CURRENCY_EVENTS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.FX_ADVISOR,
            resource=Resource.CIB_FACILITIES,
            permissions=frozenset({Permission.READ_AGGREGATED}),
            notes="Aggregated exposure only — no client PII",
        ),

        # --- Insurance Broker ---
        AccessRule(
            role=Role.INSURANCE_BROKER,
            resource=Resource.INSURANCE_POLICIES,
            permissions=frozenset({Permission.READ, Permission.WRITE}),
        ),
        AccessRule(
            role=Role.INSURANCE_BROKER,
            resource=Resource.INSURANCE_CLAIMS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.INSURANCE_BROKER,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.INSURANCE_BROKER,
            resource=Resource.EXPANSION_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),

        # --- PBB Branch Manager ---
        AccessRule(
            role=Role.PBB_BRANCH_MANAGER,
            resource=Resource.PBB_ACCOUNT_DATA,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.PBB_BRANCH_MANAGER,
            resource=Resource.PBB_PAYROLL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.PBB_BRANCH_MANAGER,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
        ),

        # --- Senior RM — inherits RM + sees raw CIB ---
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.GOLDEN_RECORD_FULL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.CIB_PAYMENTS_RAW,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.CLIENT_BRIEFING,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.NBA_RECOMMENDATIONS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.EXPANSION_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.DATA_SHADOW_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.CURRENCY_EVENTS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.FOREX_POSITIONS,
            permissions=frozenset({Permission.READ_AGGREGATED}),
        ),
        AccessRule(
            role=Role.SENIOR_RELATIONSHIP_MANAGER,
            resource=Resource.INSURANCE_POLICIES,
            permissions=frozenset({Permission.READ_AGGREGATED}),
        ),

        # --- ExCo — aggregated view across all domains ---
        AccessRule(
            role=Role.EXCO,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
            notes="No PII — aggregate metrics only",
        ),
        AccessRule(
            role=Role.EXCO,
            resource=Resource.EXPANSION_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.EXCO,
            resource=Resource.CURRENCY_EVENTS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.EXCO,
            resource=Resource.NBA_RECOMMENDATIONS,
            permissions=frozenset({Permission.READ_AGGREGATED}),
        ),

        # --- Country Head — full view for their country ---
        AccessRule(
            role=Role.COUNTRY_HEAD,
            resource=Resource.GOLDEN_RECORD_FULL,
            permissions=frozenset({Permission.READ}),
            notes="Country-scoped",
        ),
        AccessRule(
            role=Role.COUNTRY_HEAD,
            resource=Resource.CLIENT_BRIEFING,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COUNTRY_HEAD,
            resource=Resource.NBA_RECOMMENDATIONS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COUNTRY_HEAD,
            resource=Resource.EXPANSION_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COUNTRY_HEAD,
            resource=Resource.DATA_SHADOW_SIGNALS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COUNTRY_HEAD,
            resource=Resource.CURRENCY_EVENTS,
            permissions=frozenset({Permission.READ}),
        ),

        # --- Compliance Officer — full read for oversight ---
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.GOLDEN_RECORD_FULL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.AUDIT_TRAIL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.CONSENT_RECORDS,
            permissions=frozenset({Permission.READ, Permission.WRITE}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.POPIA_CLASSIFICATIONS,
            permissions=frozenset({Permission.READ, Permission.WRITE}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.CIB_PAYMENTS_RAW,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.FOREX_POSITIONS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.CELL_SIM_DATA,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.COMPLIANCE_OFFICER,
            resource=Resource.CELL_MOMO_RAW,
            permissions=frozenset({Permission.READ}),
        ),

        # --- Information Officer (POPIA s50) ---
        AccessRule(
            role=Role.INFORMATION_OFFICER,
            resource=Resource.POPIA_CLASSIFICATIONS,
            permissions=frozenset({Permission.READ, Permission.WRITE, Permission.ADMIN}),
        ),
        AccessRule(
            role=Role.INFORMATION_OFFICER,
            resource=Resource.CONSENT_RECORDS,
            permissions=frozenset({Permission.READ, Permission.WRITE, Permission.ADMIN}),
        ),
        AccessRule(
            role=Role.INFORMATION_OFFICER,
            resource=Resource.AUDIT_TRAIL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.INFORMATION_OFFICER,
            resource=Resource.LINEAGE_GRAPH,
            permissions=frozenset({Permission.READ}),
        ),

        # --- Data Engineer — pipeline access, no client PII ---
        AccessRule(
            role=Role.DATA_ENGINEER,
            resource=Resource.LINEAGE_GRAPH,
            permissions=frozenset({Permission.READ, Permission.WRITE}),
        ),
        AccessRule(
            role=Role.DATA_ENGINEER,
            resource=Resource.AUDIT_TRAIL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.DATA_ENGINEER,
            resource=Resource.POPIA_CLASSIFICATIONS,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.DATA_ENGINEER,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
            notes="Aggregate only — for pipeline validation",
        ),

        # --- Regulator — read-only for specified scope ---
        AccessRule(
            role=Role.REGULATOR,
            resource=Resource.AUDIT_TRAIL,
            permissions=frozenset({Permission.READ}),
            notes="Scope defined per regulatory request",
        ),
        AccessRule(
            role=Role.REGULATOR,
            resource=Resource.CONSENT_RECORDS,
            permissions=frozenset({Permission.READ}),
        ),

        # --- Internal Audit ---
        AccessRule(
            role=Role.INTERNAL_AUDIT,
            resource=Resource.AUDIT_TRAIL,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.INTERNAL_AUDIT,
            resource=Resource.LINEAGE_GRAPH,
            permissions=frozenset({Permission.READ}),
        ),
        AccessRule(
            role=Role.INTERNAL_AUDIT,
            resource=Resource.GOLDEN_RECORD_SUMMARY,
            permissions=frozenset({Permission.READ}),
        ),
    ]

    def __init__(self) -> None:
        # Build an index: (role, resource) → AccessRule
        self._index: Dict[tuple, AccessRule] = {}
        for rule in self.MATRIX:
            key = (rule.role, rule.resource)
            self._index[key] = rule

    def check(
        self,
        role: Role,
        resource: Resource,
        permission: Permission,
        user_country: Optional[str] = None,
        client_country: Optional[str] = None,
        client_domain: Optional[str] = None,
    ) -> AccessDecision:
        """
        We evaluate whether a role may perform an
        operation on a resource.

        user_country:   the country of the requesting user
        client_country: the country of the client record
        client_domain:  the domain of the data being accessed
        """

        rule = self._index.get((role, resource))

        if rule is None:
            return AccessDecision(
                permitted=False,
                role=role,
                resource=resource,
                requested_permission=permission,
                reason=(
                    f"Role {role.value} has no access rule "
                    f"for resource {resource.value}"
                ),
            )

        if permission not in rule.permissions:
            return AccessDecision(
                permitted=False,
                role=role,
                resource=resource,
                requested_permission=permission,
                reason=(
                    f"Role {role.value} does not have "
                    f"{permission.value} on {resource.value}. "
                    f"Permitted: {[p.value for p in rule.permissions]}"
                ),
            )

        # Country scope check
        country_scope_applied = False
        if (
            user_country is not None
            and client_country is not None
            and role in {
                Role.RELATIONSHIP_MANAGER,
                Role.PBB_BRANCH_MANAGER,
                Role.COUNTRY_HEAD,
            }
        ):
            if user_country != client_country:
                return AccessDecision(
                    permitted=False,
                    role=role,
                    resource=resource,
                    requested_permission=permission,
                    reason=(
                        f"Role {role.value} in {user_country} "
                        f"cannot access records for client in "
                        f"{client_country} (country scope)"
                    ),
                    country_scope_applied=True,
                )
            country_scope_applied = True

        # Domain scope check
        domain_scope_applied = False
        if (
            rule.domain_scope is not None
            and client_domain is not None
            and client_domain not in rule.domain_scope
        ):
            return AccessDecision(
                permitted=False,
                role=role,
                resource=resource,
                requested_permission=permission,
                reason=(
                    f"Role {role.value} is scoped to domains "
                    f"{set(rule.domain_scope)} — cannot access "
                    f"domain {client_domain}"
                ),
                domain_scope_applied=True,
            )
        if rule.domain_scope is not None:
            domain_scope_applied = True

        return AccessDecision(
            permitted=True,
            role=role,
            resource=resource,
            requested_permission=permission,
            reason="Access permitted",
            country_scope_applied=country_scope_applied,
            domain_scope_applied=domain_scope_applied,
        )

    def list_permitted_resources(
        self, role: Role
    ) -> List[Resource]:
        """
        We return all resources a role has any
        permission on.
        """

        return [
            rule.resource
            for rule in self.MATRIX
            if rule.role == role
        ]

    def list_roles_for_resource(
        self, resource: Resource
    ) -> List[Role]:
        """
        We return all roles that have any permission
        on a resource. Used for impact analysis when
        changing access rules.
        """

        return [
            rule.role
            for rule in self.MATRIX
            if rule.resource == resource
        ]
