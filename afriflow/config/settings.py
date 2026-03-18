"""
Configuration Settings Models

We define Pydantic models for all configuration sections.
This enables validation, type safety, and clear error messages
when configuration is invalid.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RevenueEstimates(BaseModel):
    """
    Revenue estimates per domain per employee/transaction.

    Used by the data shadow module to calculate revenue
    opportunities from detected gaps.
    """

    forex_per_million_flow: float = Field(
        default=3000.0,
        description="Revenue in ZAR per R1M forex flow",
        gt=0
    )
    insurance_per_million_assets: float = Field(
        default=2000.0,
        description="Revenue in ZAR per R1M insured assets",
        gt=0
    )
    pbb_per_employee: float = Field(
        default=2500.0,
        description="Annual revenue in ZAR per employee account",
        gt=0
    )
    cell_per_sim: float = Field(
        default=150.0,
        description="Revenue in ZAR per corporate SIM",
        gt=0
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "forex_per_million_flow": 3000.0,
                "insurance_per_million_assets": 2000.0,
                "pbb_per_employee": 2500.0,
                "cell_per_sim": 150.0,
            }
        }
    }


class ExpansionThresholds(BaseModel):
    """
    Thresholds for expansion signal detection.

    Used by the expansion detector to determine when
    cross-domain evidence is sufficient to generate
    a high-confidence expansion alert.

    Attributes:
        min_cib_payments_for_signal: Minimum CIB payments to trigger signal
        min_cib_value_for_signal: Minimum CIB value in ZAR for signal
        min_sim_activations_for_signal: Minimum SIM activations for signal
        min_forex_trades_for_signal: Minimum forex trades for signal
        min_pbb_accounts_for_signal: Minimum payroll accounts for signal

    Example:
        >>> thresholds = ExpansionThresholds(
        ...     min_cib_payments_for_signal=5,
        ...     min_cib_value_for_signal=2_000_000
        ... )
    """

    min_cib_payments_for_signal: int = Field(
        default=3,
        description="Minimum CIB payments to trigger signal",
        ge=1
    )
    min_cib_value_for_signal: float = Field(
        default=1_000_000.0,
        description="Minimum CIB value in ZAR for signal",
        gt=0
    )
    min_sim_activations_for_signal: int = Field(
        default=20,
        description="Minimum SIM activations for signal",
        ge=1
    )
    min_forex_trades_for_signal: int = Field(
        default=2,
        description="Minimum forex trades for signal",
        ge=1
    )
    min_pbb_accounts_for_signal: int = Field(
        default=5,
        description="Minimum payroll accounts for signal",
        ge=1
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "min_cib_payments_for_signal": 3,
                "min_cib_value_for_signal": 1000000.0,
                "min_sim_activations_for_signal": 20,
                "min_forex_trades_for_signal": 2,
                "min_pbb_accounts_for_signal": 5,
            }
        }
    }


class ExpansionScoringWeights(BaseModel):
    """
    Scoring weights for expansion signal confidence calculation.

    Each evidence type contributes points toward the overall
    confidence score. Maximum total is 100 points.

    Attributes:
        cib_payment_base_points: Base points for CIB payments
        cib_value_per_million_points: Points per million ZAR
        sim_activation_base_points: Base points for SIM activations
        sim_per_10_activations_points: Points per 10 SIM activations
        forex_hedge_present_points: Points for forex hedging
        insurance_coverage_present_points: Points for insurance
        pbb_payroll_present_points: Points for payroll presence

    Example:
        >>> weights = ExpansionScoringWeights(
        ...     cib_payment_base_points=25,
        ...     forex_hedge_present_points=20
        ... )
    """

    cib_payment_base_points: int = Field(default=20, ge=0, le=40)
    cib_value_per_million_points: int = Field(default=10, ge=0, le=20)
    sim_activation_base_points: int = Field(default=15, ge=0, le=25)
    sim_per_10_activations_points: int = Field(default=5, ge=0, le=10)
    forex_hedge_present_points: int = Field(default=15, ge=0, le=15)
    insurance_coverage_present_points: int = Field(default=10, ge=0, le=10)
    pbb_payroll_present_points: int = Field(default=10, ge=0, le=10)

    model_config = {
        "json_schema_extra": {
            "example": {
                "cib_payment_base_points": 20,
                "cib_value_per_million_points": 10,
                "sim_activation_base_points": 15,
                "sim_per_10_activations_points": 5,
                "forex_hedge_present_points": 15,
                "insurance_coverage_present_points": 10,
                "pbb_payroll_present_points": 10,
            }
        }
    }


class ExpansionConfidenceThresholds(BaseModel):
    """
    Confidence thresholds for alert routing.

    Determines how expansion signals are prioritized
    based on their confidence scores.

    Attributes:
        min_signal_confidence: Minimum to generate any signal
        medium_priority_threshold: Threshold for medium priority
        high_priority_threshold: Threshold for high priority
        urgent_priority_threshold: Threshold for urgent priority

    Example:
        >>> thresholds = ExpansionConfidenceThresholds(
        ...     min_signal_confidence=35,
        ...     high_priority_threshold=75
        ... )
    """

    min_signal_confidence: int = Field(default=40, ge=0, le=100)
    medium_priority_threshold: int = Field(default=60, ge=0, le=100)
    high_priority_threshold: int = Field(default=80, ge=0, le=100)
    urgent_priority_threshold: int = Field(default=90, ge=0, le=100)

    model_config = {
        "json_schema_extra": {
            "example": {
                "min_signal_confidence": 40,
                "medium_priority_threshold": 60,
                "high_priority_threshold": 80,
                "urgent_priority_threshold": 90,
            }
        }
    }


class SimDeflationConfig(BaseModel):
    """
    SIM to employee deflation configuration per country.

    Used to convert raw SIM counts to estimated employee
    headcounts, accounting for multi-SIM culture in Africa.
    """

    country_code: str = Field(
        ...,
        description="ISO 3166-1 alpha-2 country code",
        pattern=r"^[A-Z]{2}$"
    )
    deflation_factor: float = Field(
        ...,
        description="Factor to multiply SIM count by",
        gt=0,
        le=1
    )
    avg_sims_per_person: float = Field(
        ...,
        description="Average SIMs per person",
        gt=0
    )
    confidence: str = Field(
        ...,
        description="Confidence level (high/medium/low)",
        pattern=r"^(high|medium|low)$"
    )
    source: str = Field(
        ...,
        description="Data source for the factor"
    )

    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate country code is uppercase."""
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "country_code": "NG",
                "deflation_factor": 0.31,
                "avg_sims_per_person": 2.8,
                "confidence": "medium",
                "source": "NCC subscriber data",
            }
        }
    }


class CurrencyThreshold(BaseModel):
    """
    Currency event detection thresholds per currency.

    Different currencies have different volatility profiles.
    We use currency-specific thresholds to avoid false alerts
    on normal volatility while catching significant moves.
    """

    devaluation_pct: float = Field(
        ...,
        description="Percentage move for devaluation event",
        gt=0
    )
    rapid_depreciation_pct: float = Field(
        ...,
        description="Percentage move for rapid depreciation",
        gt=0
    )
    parallel_divergence_pct: float = Field(
        ...,
        description="Parallel market divergence threshold",
        gt=0
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional context about the currency"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "devaluation_pct": 8.0,
                "rapid_depreciation_pct": 4.0,
                "parallel_divergence_pct": 15.0,
                "notes": "Nigeria. High volatility.",
            }
        }
    }


class SeasonalPattern(BaseModel):
    """
    Seasonal pattern for a commodity in a country.

    Used to adjust signal detection thresholds based on
    expected seasonal patterns in agricultural and
    commodity markets.
    """

    commodity: str = Field(
        ...,
        description="Commodity name"
    )
    country_code: str = Field(
        ...,
        description="ISO 3166-1 alpha-2 country code",
        pattern=r"^[A-Z]{2}$"
    )
    peak_months: List[int] = Field(
        ...,
        description="Months with peak activity (1-12)",
        ge=1,
        le=12
    )
    trough_months: List[int] = Field(
        ...,
        description="Months with low activity (1-12)",
        ge=1,
        le=12
    )
    flow_type: str = Field(
        ...,
        description="Flow type (export/import/domestic)",
        pattern=r"^(export|import|domestic)$"
    )
    expected_peak_multiplier: float = Field(
        ...,
        description="Expected volume multiplier at peak",
        gt=0
    )
    expected_trough_multiplier: float = Field(
        ...,
        description="Expected volume multiplier at trough",
        gt=0
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "commodity": "cocoa",
                "country_code": "GH",
                "peak_months": [10, 11, 12],
                "trough_months": [3, 4, 5],
                "flow_type": "export",
                "expected_peak_multiplier": 3.0,
                "expected_trough_multiplier": 0.2,
            }
        }
    }


class Settings(BaseModel):
    """
    Master settings container for all AfriFlow configuration.

    This is the single source of truth for all configurable
    values in the platform. All magic numbers should be
    replaced with settings from this class.
    """

    revenue_estimates: RevenueEstimates = Field(
        default_factory=RevenueEstimates,
        description="Revenue estimates per domain"
    )
    expansion_thresholds: ExpansionThresholds = Field(
        default_factory=ExpansionThresholds,
        description="Expansion detection thresholds"
    )
    sim_deflation: Dict[str, SimDeflationConfig] = Field(
        default_factory=dict,
        description="SIM deflation factors by country"
    )
    currency_thresholds: Dict[str, CurrencyThreshold] = Field(
        default_factory=dict,
        description="Currency event thresholds by currency"
    )
    seasonal_patterns: List[SeasonalPattern] = Field(
        default_factory=list,
        description="Seasonal patterns for commodities"
    )

    def get_sim_deflation(self, country_code: str) -> float:
        """
        Get SIM deflation factor for a country.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Deflation factor (0.0 to 1.0)

        Raises:
            KeyError: If country not found
        """
        if country_code not in self.sim_deflation:
            logger.warning(
                f"No SIM deflation factor for {country_code}, "
                f"using default 0.50"
            )
            return 0.50
        return self.sim_deflation[country_code].deflation_factor

    def get_currency_threshold(
        self,
        currency: str
    ) -> CurrencyThreshold:
        """
        Get currency event thresholds for a currency.

        Args:
            currency: ISO 4217 currency code

        Returns:
            Currency threshold configuration

        Raises:
            KeyError: If currency not found
        """
        if currency not in self.currency_thresholds:
            logger.warning(
                f"No currency threshold for {currency}, "
                f"using defaults"
            )
            return CurrencyThreshold(
                devaluation_pct=10.0,
                rapid_depreciation_pct=5.0,
                parallel_divergence_pct=20.0
            )
        return self.currency_thresholds[currency]

    model_config = {
        "json_schema_extra": {
            "example": {
                "revenue_estimates": {
                    "forex_per_million_flow": 3000.0,
                    "insurance_per_million_assets": 2000.0,
                    "pbb_per_employee": 2500.0,
                    "cell_per_sim": 150.0,
                },
                "expansion_thresholds": {
                    "min_cib_payments_for_signal": 3,
                    "min_cib_value_for_signal": 1000000.0,
                    "min_sim_activations_for_signal": 20,
                },
            }
        }
    }
