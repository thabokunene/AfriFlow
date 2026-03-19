"""
@file expectation_rules.py
@description Core inference engine for cross-domain data shadow detection.
             Defines and evaluates logical rules that identify expected domain
             presence based on activity in other domains (e.g., CIB payments
             implying Forex hedging). Calculates confidence scores and revenue
             estimates for each identified gap.
@author Thabo Kunene
@created 2026-03-19
"""

# Expectation Rules Engine
#
# We define the cross-domain inference rules that
# determine what domain presence we expect for a client
# based on their known presence in other domains.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for type hinting and dictionary handling
from typing import Dict, List, Set, Optional, Any
import logging

# Platform exceptions, configuration, and logging
from afriflow.exceptions import DataShadowError
from afriflow.config import get_settings
from afriflow.logging_config import get_logger, log_operation

# Initialise a module-scoped logger for expectation rule execution
logger = get_logger("data_shadow.expectation_rules")


class ExpectationRuleEngine:
    """
    Engine responsible for applying cross-domain inference rules to identify
    potential business gaps in a client's relationship with the bank.

    The engine evaluates five primary rules:
    1. CIB → Forex: Cross-border payments imply a need for FX hedging.
    2. Cell → PBB: MTN SIM activations imply a need for payroll banking.
    3. CIB Trade Finance → Insurance: Facilities imply a need for asset coverage.
    4. CIB Growth → Cell: New payment corridors imply a need for SIM activations.
    5. CIB Supplier → Insurance: Supplier payments imply a need for commercial insurance.
    """

    def __init__(self, settings: Optional[Any] = None) -> None:
        """
        Initialise the rule engine with platform configuration.

        :param settings: Optional Settings object; defaults to global config.
        """
        # Load configuration or use platform defaults
        self.settings = settings or get_settings()
        logger.debug(
            "ExpectationRuleEngine initialized with "
            f"revenue estimates: {self.settings.revenue_estimates}"
        )

    def _get_revenue_estimate(self, estimate_type: str) -> float:
        """
        Retrieve a specific revenue multiplier from the configuration.

        :param estimate_type: Key for the estimate type (e.g., 'forex_per_million_flow').
        :return: The configured revenue estimate value.
        :raises AttributeError: If the estimate type is not found in settings.
        """
        # Pull from the revenue_estimates section of the YAML config
        estimates = self.settings.revenue_estimates
        return getattr(estimates, estimate_type)

    def compute_expectations(
        self,
        golden_id: str,
        actual_presence: Dict[str, Set[str]],
        client_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Evaluate all inference rules for a single client to identify data shadows.

        :param golden_id: Unified client identifier.
        :param actual_presence: Mapping of domain to sets of countries where active.
        :param client_metadata: Optional dictionary of domain-specific metrics.
        :return: A list of identified expectation gaps (data shadows).
        :raises DataShadowError: If input data is invalid.
        """
        # Log the start of the computation for observability
        log_operation(
            logger,
            "compute_expectations",
            "started",
            golden_id=golden_id,
            domains=list(actual_presence.keys()),
        )

        # Validation: Ensure a valid client identifier is provided
        if not golden_id:
            raise DataShadowError(
                "golden_id cannot be empty",
                details={"golden_id": golden_id}
            )

        # Validation: Ensure presence data is in the correct format
        if not isinstance(actual_presence, dict):
            raise DataShadowError(
                "actual_presence must be a dictionary",
                details={"type": type(actual_presence).__name__}
            )

        # Use empty dict if metadata is not provided
        client_metadata = client_metadata or {}
        expectations = []

        logger.debug(
            f"Computing expectations for {golden_id}: "
            f"{len(actual_presence)} domains"
        )

        # --- Rule 1: CIB → Forex (Hedging Gap) ---
        expectations.extend(
            self._rule_cib_implies_forex(
                golden_id, actual_presence,
                client_metadata
            )
        )
        # --- Rule 2: Cell → PBB (Payroll Gap) ---
        expectations.extend(
            self._rule_cell_implies_pbb(
                golden_id, actual_presence,
                client_metadata
            )
        )
        # --- Rule 3: CIB Trade Finance → Insurance (Facility Gap) ---
        expectations.extend(
            self._rule_cib_trade_finance_implies_insurance(
                golden_id, actual_presence,
                client_metadata
            )
        )
        # --- Rule 4: CIB Growth → Cell (Regional Network Gap) ---
        expectations.extend(
            self._rule_cib_implies_cell(
                golden_id, actual_presence,
                client_metadata
            )
        )
        # --- Rule 5: CIB Supplier → Insurance (Supplier Risk Gap) ---
        expectations.extend(
            self._rule_cib_supplier_implies_insurance(
                golden_id, actual_presence,
                client_metadata
            )
        )

        # Log completion and result count
        log_operation(
            logger,
            "compute_expectations",
            "completed",
            golden_id=golden_id,
            gaps_detected=len(expectations),
        )

        return expectations

    def _rule_cib_supplier_implies_insurance(
        self,
        golden_id: str,
        actual_presence: Dict[str, Set[str]],
        client_metadata: Dict
    ) -> List[Dict]:
        """
        Rule 5: If a client has supplier payments in a country, we expect
        commercial insurance coverage to mitigate supply chain risk.

        :param golden_id: Unified client identifier.
        :param actual_presence: Current domain presence mapping.
        :param client_metadata: Domain metrics dictionary.
        :return: List of identified gaps for this specific rule.
        """
        expectations = []
        # Extract CIB domain metrics
        cib_data = client_metadata.get("cib", {}) or {}
        by_country = cib_data.get("by_country", {}) or {}
        # Identify countries where the client already has insurance
        insurance_countries = actual_presence.get("insurance", set())

        # Iterate through countries where CIB payments are made
        for country, metrics in by_country.items():
            annual_value = float(metrics.get("annual_value", 0.0) or 0.0)
            payment_types = set(metrics.get("payment_types", []) or [])
            
            # If the client pays suppliers in a country but has no insurance there
            if annual_value > 0 and "SUPPLIER" in payment_types:
                if country not in insurance_countries:
                    # Record a data shadow gap
                    expectations.append({
                        "domain": "insurance",
                        "country": country,
                        "source_domain": "cib",
                        "rule_name": "CIB_SUPPLIER_IMPLIES_INSURANCE",
                        "confidence": 75.0,
                        # Estimate revenue as a % of annual supplier flow, min R500k
                        "estimated_revenue_zar": max(
                            500_000.0, annual_value * 0.02
                        ),
                        "shadow_type": "INSURANCE_GAP"
                    })

        return expectations

    def _rule_cib_implies_forex(
        self,
        golden_id: str,
        actual_presence: Dict[str, Set[str]],
        client_metadata: Dict
    ) -> List[Dict]:
        """
        Rule 1: If a client has CIB payments in a
        non-home-country currency exceeding R10M
        annually, we expect forex hedging activity
        for that currency.
        """
        expectations = []
        cib_countries = actual_presence.get("cib", set())
        forex_countries = actual_presence.get("forex", set())
        home_country = client_metadata.get("home_country", "ZA")

        # Nested data access helper
        cib_data = client_metadata.get("cib", {}) or {}
        by_country = cib_data.get("by_country", {}) or {}

        for country in cib_countries:
            if country != home_country and country not in forex_countries:
                # Try flat key first, then nested
                cib_volume = client_metadata.get(f"cib_volume_{country}")
                if cib_volume is None:
                    cib_volume = by_country.get(country, {}).get("annual_value", 10_000_000)
                
                expectations.append({
                    "domain": "forex",
                    "country": country,
                    "source_domain": "cib",
                    "rule_name": "CIB_IMPLIES_FOREX",
                    "confidence": 75.0,
                    "estimated_revenue_zar": (
                        float(cib_volume)
                        * self._get_revenue_estimate("forex_per_million_flow")
                        / 1_000_000
                    ),
                    "shadow_type": "COMPETITIVE_LEAKAGE"
                })

        return expectations

    def _rule_cell_implies_pbb(
        self,
        golden_id: str,
        actual_presence: Dict[str, Set[str]],
        client_metadata: Dict
    ) -> List[Dict]:
        """
        Rule 2: If MTN data shows corporate SIMs
        active in a country, we expect PBB payroll
        deposits for those employees.
        """
        expectations = []
        cell_countries = actual_presence.get("cell", set())
        pbb_countries = actual_presence.get("pbb", set())

        # Nested data access helper
        cell_data = client_metadata.get("cell", {}) or {}
        by_country = cell_data.get("by_country", {}) or {}

        for country in cell_countries:
            if country not in pbb_countries:
                # Try flat key first, then nested
                sim_count = client_metadata.get(f"sim_count_{country}")
                if sim_count is None:
                    sim_count = by_country.get(country, {}).get("sim_count", 100)
                
                # Only generate shadow if sim count is significant
                if sim_count < 50:
                    continue

                deflation_factor = client_metadata.get(f"deflation_{country}", 0.5)
                estimated_employees = int(sim_count * deflation_factor)

                expectations.append({
                    "domain": "pbb",
                    "country": country,
                    "source_domain": "cell",
                    "rule_name": "CELL_IMPLIES_PBB",
                    "confidence": 70.0,
                    "estimated_revenue_zar": (
                        estimated_employees
                        * self._get_revenue_estimate("pbb_per_employee")
                    ),
                    "shadow_type": "PAYROLL_CAPTURE_OPPORTUNITY"
                })

        return expectations

    def _rule_cib_trade_finance_implies_insurance(
        self,
        golden_id: str,
        actual_presence: Dict[str, Set[str]],
        client_metadata: Dict
    ) -> List[Dict]:
        """
        Rule 3: If a client has active trade finance
        facilities, we expect commercial insurance
        coverage.

        Args:
            golden_id: Unique client identifier
            actual_presence: Dict mapping domain to set of countries
            client_metadata: Additional client data

        Returns:
            List of expectation gap dictionaries
        """
        expectations = []
        cib_countries = actual_presence.get("cib", set())
        insurance_countries = actual_presence.get(
            "insurance", set()
        )

        has_trade_finance = client_metadata.get(
            "has_trade_finance", False
        )

        if not has_trade_finance:
            return expectations

        for country in cib_countries:
            if country not in insurance_countries:
                cib_volume = client_metadata.get(
                    f"cib_volume_{country}", 10_000_000
                )
                expectations.append({
                    "domain": "insurance",
                    "country": country,
                    "source_domain": "cib",
                    "rule_name": (
                        "TRADE_FINANCE_IMPLIES_INSURANCE"
                    ),
                    "confidence": 65.0,
                    "estimated_revenue_zar": (
                        cib_volume
                        * self._get_revenue_estimate(
                            "insurance_per_million_assets"
                        )
                        / 1_000_000
                    ),
                    "shadow_type": "INSURANCE_GAP"
                })

        return expectations

    def _rule_cib_implies_cell(
        self,
        golden_id: str,
        actual_presence: Dict[str, Set[str]],
        client_metadata: Dict
    ) -> List[Dict]:
        """
        Rule 4: If CIB payments to a country are growing,
        we expect cell SIM presence there within 4 to 8
        weeks.

        Args:
            golden_id: Unique client identifier
            actual_presence: Dict mapping domain to set of countries
            client_metadata: Additional client data

        Returns:
            List of expectation gap dictionaries
        """
        expectations = []
        cib_countries = actual_presence.get("cib", set())
        cell_countries = actual_presence.get(
            "cell", set()
        )

        for country in cib_countries:
            if country not in cell_countries:
                is_growing = client_metadata.get(
                    f"cib_growing_{country}", False
                )

                if is_growing:
                    cib_volume = client_metadata.get(
                        f"cib_volume_{country}", 10_000_000
                    )
                    expectations.append({
                        "domain": "cell",
                        "country": country,
                        "source_domain": "cib",
                        "rule_name": "CIB_GROWTH_IMPLIES_CELL",
                        "confidence": 60.0,
                        "estimated_revenue_zar": (
                            cib_volume
                            * self._get_revenue_estimate(
                                "cell_per_sim"
                            )
                            / 1_000_000
                        ),
                        "shadow_type": (
                            "TELCOPARTNERSHIP_OPPORTUNITY"
                        )
                    })

        return expectations
