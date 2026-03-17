"""
Feature Definitions

Defines the feature registry for the AfriFlow feature store.
Each feature has:
  - A unique name (snake_case)
  - A domain source (cib / forex / insurance / cell / pbb / cross)
  - A computation type (STREAMING / BATCH_DAILY / BATCH_WEEKLY)
  - A TTL (how long the feature value is valid)
  - A POPIA classification (PUBLIC / INTERNAL / CONFIDENTIAL)

Feature groups:
  client_financial_health  — revenue, utilisation, facility metrics
  client_geographic        — country presence, expansion signals
  client_risk              — churn score, fraud signals, anomalies
  client_digital           — digital maturity, MoMo penetration
  client_informal_economy  — IEHI, informal cluster metrics
  market_rates             — FX rates, vol surfaces, swap points

These definitions drive:
  1. Feature server materialisation schedule
  2. POPIA field classification for API masking
  3. Model feature validation (ensure inputs are fresh)

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FeatureDefinition:
    """Definition of a single feature in the feature store."""

    name: str
    domain: str            # cib / forex / insurance / cell / pbb / cross / market
    group: str             # Feature group name
    computation: str       # STREAMING / BATCH_DAILY / BATCH_WEEKLY / REALTIME
    ttl_minutes: int       # How long the feature is valid
    popia_class: str       # PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
    description: str
    default_value: object = None
    is_model_input: bool = True


# ---------------------------------------------------------------------------
# Feature registry
# ---------------------------------------------------------------------------

FEATURE_REGISTRY: List[FeatureDefinition] = [

    # ---- CIB financial health ----
    FeatureDefinition(
        name="cib_total_facility_value_zar",
        domain="cib", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Total CIB credit facility value in ZAR",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cib_facility_utilisation_pct",
        domain="cib", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Current facility utilisation as a fraction (0-1)",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cib_annual_cross_border_value_zar",
        domain="cib", group="client_geographic",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Total annual cross-border CIB payment value",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cib_active_corridor_count",
        domain="cib", group="client_geographic",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="Number of active cross-border payment corridors",
        default_value=0,
    ),
    FeatureDefinition(
        name="cib_facility_utilisation_change_3m",
        domain="cib", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="3-month change in facility utilisation (negative = declining)",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cib_inbound_payment_trend_3m",
        domain="cib", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="3-month trend in inbound CIB payment volume",
        default_value=0.0,
    ),

    # ---- Forex ----
    FeatureDefinition(
        name="forex_has_active_forwards",
        domain="forex", group="client_financial_health",
        computation="STREAMING", ttl_minutes=60,
        popia_class="CONFIDENTIAL",
        description="Whether the client has active FX forward contracts",
        default_value=False,
    ),
    FeatureDefinition(
        name="forex_hedge_ratio",
        domain="forex", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Proportion of FX exposure currently hedged (0-1)",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="forex_volume_trend_3m",
        domain="forex", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="3-month trend in FX traded notional",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="forex_annual_notional_zar",
        domain="forex", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Annual FX notional traded in ZAR equivalent",
        default_value=0.0,
    ),

    # ---- Insurance ----
    FeatureDefinition(
        name="insurance_active_policy_count",
        domain="insurance", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="Number of active insurance policies",
        default_value=0,
    ),
    FeatureDefinition(
        name="insurance_covered_countries",
        domain="insurance", group="client_geographic",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="List of countries with active coverage",
        default_value=None,
    ),
    FeatureDefinition(
        name="insurance_total_sum_assured_zar",
        domain="insurance", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Total sum assured across all policies in ZAR",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="insurance_days_since_last_renewal",
        domain="insurance", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="Days since the most recent policy renewal",
        default_value=0,
    ),

    # ---- Cell / MoMo ----
    FeatureDefinition(
        name="cell_estimated_employee_count",
        domain="cell", group="client_financial_health",
        computation="BATCH_WEEKLY", ttl_minutes=10080,
        popia_class="INTERNAL",
        description="SIM deflation-adjusted employee headcount estimate",
        default_value=0,
    ),
    FeatureDefinition(
        name="cell_momo_volume_trend_3m",
        domain="cell", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="3-month trend in MoMo transaction volume",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cell_ussd_session_trend_3m",
        domain="cell", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="3-month trend in USSD session count",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cell_active_country_count",
        domain="cell", group="client_geographic",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="Number of countries with active SIM presence",
        default_value=1,
    ),
    FeatureDefinition(
        name="cell_momo_enabled_employee_pct",
        domain="cell", group="client_digital",
        computation="BATCH_WEEKLY", ttl_minutes=10080,
        popia_class="INTERNAL",
        description="Fraction of employees using MoMo (0-1)",
        default_value=0.0,
    ),

    # ---- PBB ----
    FeatureDefinition(
        name="pbb_payroll_account_count",
        domain="pbb", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Number of payroll-linked bank accounts",
        default_value=0,
    ),
    FeatureDefinition(
        name="pbb_total_aum_zar",
        domain="pbb", group="client_financial_health",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Total PBB assets under management in ZAR",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="pbb_avg_payroll_days_late",
        domain="pbb", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="CONFIDENTIAL",
        description="Average days late for payroll runs (0 = on time)",
        default_value=0,
    ),

    # ---- Cross-domain scores ----
    FeatureDefinition(
        name="cross_churn_score",
        domain="cross", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="Cross-domain churn probability score (0-100)",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cross_nba_top_score",
        domain="cross", group="client_risk",
        computation="BATCH_DAILY", ttl_minutes=1440,
        popia_class="INTERNAL",
        description="Top NBA recommendation score (0-100)",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cross_clv_3yr_zar",
        domain="cross", group="client_financial_health",
        computation="BATCH_WEEKLY", ttl_minutes=10080,
        popia_class="CONFIDENTIAL",
        description="3-year client lifetime value estimate in ZAR",
        default_value=0.0,
    ),
    FeatureDefinition(
        name="cross_viability_score",
        domain="cross", group="client_financial_health",
        computation="BATCH_WEEKLY", ttl_minutes=10080,
        popia_class="INTERNAL",
        description="Business viability score (300-850)",
        default_value=500,
    ),
    FeatureDefinition(
        name="cross_digital_maturity_score",
        domain="cross", group="client_digital",
        computation="BATCH_WEEKLY", ttl_minutes=10080,
        popia_class="INTERNAL",
        description="Digital maturity composite score (0-100)",
        default_value=25.0,
    ),
    FeatureDefinition(
        name="cross_iehi_score",
        domain="cross", group="client_informal_economy",
        computation="BATCH_WEEKLY", ttl_minutes=10080,
        popia_class="INTERNAL",
        description="Informal Economy Health Index (0-100)",
        default_value=25.0,
    ),

    # ---- Market rate features (not client-specific) ----
    FeatureDefinition(
        name="market_ngn_zar_rate",
        domain="market", group="market_rates",
        computation="STREAMING", ttl_minutes=5,
        popia_class="PUBLIC",
        description="Current NGN/ZAR mid rate",
        default_value=None,
        is_model_input=False,
    ),
    FeatureDefinition(
        name="market_kes_zar_rate",
        domain="market", group="market_rates",
        computation="STREAMING", ttl_minutes=5,
        popia_class="PUBLIC",
        description="Current KES/ZAR mid rate",
        default_value=None,
        is_model_input=False,
    ),
]


# Lookup index for fast feature retrieval
FEATURE_INDEX: Dict[str, FeatureDefinition] = {
    f.name: f for f in FEATURE_REGISTRY
}


def get_feature(name: str) -> Optional[FeatureDefinition]:
    """Look up a feature definition by name."""
    return FEATURE_INDEX.get(name)


def features_by_domain(domain: str) -> List[FeatureDefinition]:
    """Return all features for a given domain."""
    return [f for f in FEATURE_REGISTRY if f.domain == domain]


def features_by_group(group: str) -> List[FeatureDefinition]:
    """Return all features for a given group."""
    return [f for f in FEATURE_REGISTRY if f.group == group]


def model_input_features() -> List[FeatureDefinition]:
    """Return features that are model inputs (excludes market data)."""
    return [f for f in FEATURE_REGISTRY if f.is_model_input]
