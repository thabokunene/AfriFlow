"""
@file feature_store.py
@description Feature store for the Next Best Action model.
             Assembles and caches normalised feature vectors from the five
             AfriFlow domain profiles so the NBA model and SHAP explainer
             can consume a consistent, flat numeric representation.

             Each domain profile dict is mapped to a named feature vector
             entry.  Missing domains produce zero-fill entries with a
             corresponding data_present=False flag so downstream consumers
             can distinguish "zero value" from "no data".

             Feature vectors are keyed by client golden_id and are intended
             to be computed once per scoring run and passed to both
             NextBestActionModel and SHAPExplainer.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Feature metadata
# ---------------------------------------------------------------------------
# Each entry describes one slot in the flat feature vector.
# The order here is the canonical order used by the NBA model and SHAP.

_FEATURE_DEFINITIONS: List[Dict] = [
    # --- CIB features ---
    {"name": "cib_corridor_count",         "domain": "cib",       "default": 0.0},
    {"name": "cib_annual_cross_border_zar", "domain": "cib",      "default": 0.0},
    {"name": "cib_facility_utilisation",   "domain": "cib",       "default": 0.0},
    {"name": "cib_util_change_3m",         "domain": "cib",       "default": 0.0},
    {"name": "cib_inbound_payment_trend",  "domain": "cib",       "default": 0.0},
    # --- Forex features ---
    {"name": "fx_volume_trend_3m",         "domain": "forex",     "default": 0.0},
    {"name": "fx_has_active_forwards",     "domain": "forex",     "default": 0.0},
    {"name": "fx_hedge_ratio",             "domain": "forex",     "default": 0.0},
    # --- Insurance features ---
    {"name": "ins_active_policy_count",    "domain": "insurance", "default": 0.0},
    {"name": "ins_covered_country_count",  "domain": "insurance", "default": 0.0},
    {"name": "ins_days_since_renewal",     "domain": "insurance", "default": 365.0},
    # --- Cell features ---
    {"name": "cell_estimated_employees",   "domain": "cell",      "default": 0.0},
    {"name": "cell_momo_enabled_pct",      "domain": "cell",      "default": 0.0},
    {"name": "cell_momo_volume_trend_3m",  "domain": "cell",      "default": 0.0},
    {"name": "cell_ussd_session_trend_3m", "domain": "cell",      "default": 0.0},
    # --- PBB features ---
    {"name": "pbb_linked_payroll_accounts","domain": "pbb",       "default": 0.0},
    {"name": "pbb_total_aum_zar",          "domain": "pbb",       "default": 0.0},
]


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class FeatureVector:
    """
    Flat numeric feature vector for one client, assembled from domain profiles.

    :param client_golden_id:  AfriFlow golden record identifier.
    :param features:          Dict mapping feature name to float value.
    :param data_present:      Dict mapping domain name to boolean (True = data available).
    :param completeness:      Fraction of domain slots populated with real data (0–1).
    """

    client_golden_id: str
    features: Dict[str, float]     # Feature name → numeric value
    data_present: Dict[str, bool]  # Domain name → is data available
    completeness: float            # 0–1 fraction of domains with real data


# ---------------------------------------------------------------------------
# Feature store
# ---------------------------------------------------------------------------

class FeatureStore:
    """
    Assemble normalised feature vectors from AfriFlow domain profile dicts.

    The feature store is stateless — call build() for each client scoring
    run.  There is no caching in this implementation; add a dict-based
    cache keyed on golden_id if batch throughput becomes a concern.

    Usage::

        store = FeatureStore()
        fv = store.build(
            client_golden_id="GLD-001",
            cib_profile={"active_payment_corridors": ["NG", "KE"], ...},
            forex_profile={"volume_trend_3m": -0.18, ...},
        )
        # fv.features["fx_volume_trend_3m"] == -0.18
    """

    def build(
        self,
        client_golden_id: str,
        cib_profile: Optional[Dict] = None,
        forex_profile: Optional[Dict] = None,
        insurance_profile: Optional[Dict] = None,
        cell_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
    ) -> FeatureVector:
        """
        Build a FeatureVector for one client from available domain profiles.

        Missing domain profiles produce zero-filled feature slots with
        data_present=False for that domain.

        :param client_golden_id:  Client golden record identifier.
        :param cib_profile:       CIB domain profile dict.
        :param forex_profile:     Forex domain profile dict.
        :param insurance_profile: Insurance domain profile dict.
        :param cell_profile:      Cell/MoMo domain profile dict.
        :param pbb_profile:       PBB domain profile dict.
        :return:                  FeatureVector dataclass.
        """
        # Track which domains have data for the completeness fraction
        data_present = {
            "cib":       cib_profile is not None,
            "forex":     forex_profile is not None,
            "insurance": insurance_profile is not None,
            "cell":      cell_profile is not None,
            "pbb":       pbb_profile is not None,
        }

        # Compute completeness: fraction of 5 domains that have data
        completeness = sum(1 for v in data_present.values() if v) / 5.0

        # Extract each feature from the appropriate domain profile
        features: Dict[str, float] = {}

        # --- CIB features ---
        cib = cib_profile or {}
        # Number of active cross-border payment corridors
        features["cib_corridor_count"] = float(
            len(cib.get("active_payment_corridors", []))
        )
        # Annual cross-border payment value in ZAR
        features["cib_annual_cross_border_zar"] = float(
            cib.get("annual_cross_border_value_zar", 0.0)
        )
        # Current facility utilisation fraction (0–1)
        features["cib_facility_utilisation"] = float(
            cib.get("facility_utilisation_pct", 0.0)
        )
        # 3-month change in facility utilisation (negative = declining)
        features["cib_util_change_3m"] = float(
            cib.get("facility_utilization_change_pct", 0.0)
        )
        # 3-month trend in inbound payments (negative = declining)
        features["cib_inbound_payment_trend"] = float(
            cib.get("inbound_payment_trend_3m", 0.0)
        )

        # --- Forex features ---
        fx = forex_profile or {}
        # 3-month FX volume trend (negative = declining — churn signal)
        features["fx_volume_trend_3m"] = float(
            fx.get("volume_trend_3m", 0.0)
        )
        # Boolean: client has any active FX forward contracts (1.0 = yes)
        features["fx_has_active_forwards"] = float(
            fx.get("has_active_forwards", False)
        )
        # Fraction of FX exposure covered by forward hedges
        features["fx_hedge_ratio"] = float(
            fx.get("hedge_ratio", 0.0)
        )

        # --- Insurance features ---
        ins = insurance_profile or {}
        # Count of active insurance policies
        features["ins_active_policy_count"] = float(
            ins.get("active_policy_count", 0)
        )
        # Number of countries covered by insurance
        features["ins_covered_country_count"] = float(
            len(ins.get("covered_countries", []))
        )
        # Days since last policy renewal (high value = lapse risk)
        features["ins_days_since_renewal"] = float(
            ins.get("days_since_last_renewal", 365)
        )

        # --- Cell features ---
        cell = cell_profile or {}
        # Estimated total employee headcount from SIM deflation model
        features["cell_estimated_employees"] = float(
            cell.get("estimated_employee_count", 0)
        )
        # Fraction of workforce with an active MoMo wallet
        features["cell_momo_enabled_pct"] = float(
            cell.get("momo_enabled_pct", 0.0)
        )
        # 3-month MoMo volume trend (negative = declining engagement)
        features["cell_momo_volume_trend_3m"] = float(
            cell.get("momo_volume_trend_3m", 0.0)
        )
        # 3-month USSD session count trend
        features["cell_ussd_session_trend_3m"] = float(
            cell.get("ussd_session_trend_3m", 0.0)
        )

        # --- PBB features ---
        pbb = pbb_profile or {}
        # Number of employee payroll accounts linked to the employer
        features["pbb_linked_payroll_accounts"] = float(
            pbb.get("linked_payroll_accounts", 0)
        )
        # Total assets under management in ZAR
        features["pbb_total_aum_zar"] = float(
            pbb.get("total_aum_zar", 0.0)
        )

        return FeatureVector(
            client_golden_id=client_golden_id,
            features=features,
            data_present=data_present,
            completeness=completeness,
        )

    def feature_names(self) -> List[str]:
        """
        Return the ordered list of feature names in the vector.

        Used by the SHAP explainer to map shap_values indices back to
        human-readable feature names.

        :return: List of feature name strings in canonical order.
        """
        return [f["name"] for f in _FEATURE_DEFINITIONS]

    def as_list(self, fv: FeatureVector) -> List[float]:
        """
        Convert a FeatureVector to an ordered list of floats in the
        canonical feature order defined by _FEATURE_DEFINITIONS.

        Useful for passing to numerical model libraries (numpy, sklearn).

        :param fv: FeatureVector instance.
        :return:   List of float values in canonical order.
        """
        return [
            fv.features.get(f["name"], f["default"])
            for f in _FEATURE_DEFINITIONS
        ]
