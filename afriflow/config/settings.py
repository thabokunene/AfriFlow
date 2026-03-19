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

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# ============================================
# SIM DEFLATION CONFIGURATION
# ============================================

class SimDeflationConfig(BaseModel):
    """
    SIM to employee deflation configuration per country.

    Used to convert raw SIM counts to estimated employee
    headcounts, accounting for multi-SIM culture in Africa.

    Attributes:
        country_code: ISO 3166-1 alpha-2 country code
        deflation_factor: Factor to multiply SIM count by (0-1)
        avg_sims_per_person: Average SIMs per person
        confidence: Confidence level (high/medium/low)
        source: Data source for the factor
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
                "deflation_factor": 0.36,
                "avg_sims_per_person": 2.8,
                "confidence": "medium",
                "source": "NCC subscriber data",
            }
        }
    }


# ============================================
# SEASONAL WEIGHT CONFIGURATION
# ============================================

class SeasonalWeightConfig(BaseModel):
    """
    Seasonal adjustment weights per commodity.

    Used to adjust signal detection thresholds based on
    expected seasonal patterns in agricultural and
    commodity markets.

    Attributes:
        commodity: Commodity name
        country_code: ISO 3166-1 alpha-2 country code
        peak_months: Months with peak activity (1-12)
        trough_months: Months with low activity (1-12)
        flow_type: Flow type (export/import/domestic)
        expected_peak_multiplier: Expected volume multiplier at peak
        expected_trough_multiplier: Expected volume multiplier at trough
    """

    commodity: str = Field(..., description="Commodity name")
    country_code: str = Field(
        ...,
        description="ISO 3166-1 alpha-2 country code",
        pattern=r"^[A-Z]{2}$"
    )
    peak_months: List[int] = Field(
        ...,
        description="Months with peak activity (1-12)",
    )
    trough_months: List[int] = Field(
        ...,
        description="Months with low activity (1-12)",
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


# ============================================
# SIGNAL THRESHOLDS CONFIGURATION
# ============================================

class SignalThresholds(BaseModel):
    """
    Thresholds for signal detection.

    Used by signal detectors to determine when evidence
    is sufficient to generate a signal.

    Attributes:
        expansion_min_cib_payments: Minimum CIB payments for expansion signal
        expansion_min_cib_value: Minimum CIB value for expansion signal
        expansion_min_sim_activations: Minimum SIM activations for expansion
        leakage_min_volume_ratio: Minimum volume ratio for leakage detection
        hedge_gap_min_exposure: Minimum exposure for hedge gap signal
        workforce_min_sims: Minimum SIMs for workforce signal
    """

    expansion_min_cib_payments: int = Field(
        default=3,
        description="Minimum CIB payments for expansion signal",
        ge=1
    )
    expansion_min_cib_value: float = Field(
        default=1_000_000.0,
        description="Minimum CIB value in ZAR for expansion signal",
        gt=0
    )
    expansion_min_sim_activations: int = Field(
        default=20,
        description="Minimum SIM activations for expansion signal",
        ge=1
    )
    leakage_min_volume_ratio: float = Field(
        default=0.10,
        description="Minimum volume ratio for leakage detection",
        gt=0,
        le=1
    )
    hedge_gap_min_exposure: float = Field(
        default=500_000.0,
        description="Minimum exposure for hedge gap signal",
        gt=0
    )
    workforce_min_sims: int = Field(
        default=50,
        description="Minimum SIMs for workforce signal",
        ge=1
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "expansion_min_cib_payments": 3,
                "expansion_min_cib_value": 1000000.0,
                "expansion_min_sim_activations": 20,
                "leakage_min_volume_ratio": 0.10,
                "hedge_gap_min_exposure": 500000.0,
                "workforce_min_sims": 50,
            }
        }
    }


# ============================================
# LEKGOTLA CONFIGURATION
# ============================================

class LekgotlaConfig(BaseModel):
    """
    Configuration for Lekgotla collective intelligence.

    Attributes:
        thread_points: Points for creating a thread
        reply_points: Points for posting a reply
        solution_points: Points for marked solution
        card_contribution_points: Points for KC contribution
        card_publication_points: Points for KC publication
        upvote_received_points: Points per upvote received
        graduation_min_upvotes: Minimum upvotes for KC graduation
        graduation_min_contributors: Minimum contributors for KC graduation
        notification_batch_size: Notifications per batch
        notification_delay_seconds: Delay before sending notifications
    """

    thread_points: int = Field(
        default=10,
        description="Points for creating a thread",
        ge=0
    )
    reply_points: int = Field(
        default=5,
        description="Points for posting a reply",
        ge=0
    )
    solution_points: int = Field(
        default=25,
        description="Points for marked solution",
        ge=0
    )
    card_contribution_points: int = Field(
        default=50,
        description="Points for KC contribution",
        ge=0
    )
    card_publication_points: int = Field(
        default=100,
        description="Points for KC publication",
        ge=0
    )
    upvote_received_points: int = Field(
        default=2,
        description="Points per upvote received",
        ge=0
    )
    graduation_min_upvotes: int = Field(
        default=10,
        description="Minimum upvotes for KC graduation",
        ge=1
    )
    graduation_min_contributors: int = Field(
        default=3,
        description="Minimum contributors for KC graduation",
        ge=1
    )
    notification_batch_size: int = Field(
        default=100,
        description="Notifications per batch",
        ge=1
    )
    notification_delay_seconds: int = Field(
        default=300,
        description="Delay before sending notifications (seconds)",
        ge=0
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "thread_points": 10,
                "reply_points": 5,
                "solution_points": 25,
                "card_contribution_points": 50,
                "card_publication_points": 100,
                "upvote_received_points": 2,
                "graduation_min_upvotes": 10,
                "graduation_min_contributors": 3,
                "notification_batch_size": 100,
                "notification_delay_seconds": 300,
            }
        }
    }


# ============================================
# CORRIDOR CONFIGURATION
# ============================================

class CorridorConfig(BaseModel):
    """
    Configuration for corridor intelligence.

    Attributes:
        leakage_detection_threshold: Threshold for leakage detection
        fx_capture_expected_pct: Expected FX capture percentage
        insurance_capture_expected_pct: Expected insurance capture
        payroll_capture_expected_pct: Expected payroll capture
        informal_ratio_alert_threshold: MoMo/CIB ratio for alerts
        revenue_attribution_window_days: Days for revenue attribution
    """

    leakage_detection_threshold: float = Field(
        default=0.10,
        description="Threshold for leakage detection",
        gt=0,
        le=1
    )
    fx_capture_expected_pct: float = Field(
        default=0.60,
        description="Expected FX capture percentage",
        gt=0,
        le=1
    )
    insurance_capture_expected_pct: float = Field(
        default=0.30,
        description="Expected insurance capture percentage",
        gt=0,
        le=1
    )
    payroll_capture_expected_pct: float = Field(
        default=0.40,
        description="Expected payroll capture percentage",
        gt=0,
        le=1
    )
    informal_ratio_alert_threshold: float = Field(
        default=1.0,
        description="MoMo/CIB ratio for alerts",
        gt=0
    )
    revenue_attribution_window_days: int = Field(
        default=90,
        description="Days for revenue attribution",
        ge=1
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "leakage_detection_threshold": 0.10,
                "fx_capture_expected_pct": 0.60,
                "insurance_capture_expected_pct": 0.30,
                "payroll_capture_expected_pct": 0.40,
                "informal_ratio_alert_threshold": 1.0,
                "revenue_attribution_window_days": 90,
            }
        }
    }


# ============================================
# MODERATION PATTERNS
# ============================================

class ModerationPatterns(BaseModel):
    """
    Configuration for content moderation.

    Attributes:
        confidential_patterns: Regex patterns for confidential info
        spam_patterns: Regex patterns for spam detection
        inappropriate_patterns: Regex patterns for inappropriate content
        auto_flag_enabled: Enable automatic flagging
        require_review_before_publish: Require review before publishing
    """

    confidential_patterns: List[str] = Field(
        default=[
            r"client\s*(name|number|id)\s*[:\s]*\w+",
            r"account\s*(number|id)\s*[:\s]*\d+",
            r"password|credential|secret",
            r"internal\s*(memo|document|report)",
        ],
        description="Regex patterns for confidential info"
    )
    spam_patterns: List[str] = Field(
        default=[
            r"http[s]?://\S+",
            r"\b(CALL|CONTACT|CLICK)\s+(NOW|TODAY)\b",
            r"\b(FREE|WIN|PRIZE)\b",
        ],
        description="Regex patterns for spam detection"
    )
    inappropriate_patterns: List[str] = Field(
        default=[],
        description="Regex patterns for inappropriate content"
    )
    auto_flag_enabled: bool = Field(
        default=True,
        description="Enable automatic flagging"
    )
    require_review_before_publish: bool = Field(
        default=False,
        description="Require review before publishing"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "confidential_patterns": [
                    r"client\s*(name|number|id)\s*[:\s]*\w+",
                    r"account\s*(number|id)\s*[:\s]*\d+",
                ],
                "spam_patterns": [
                    r"http[s]?://\S+",
                ],
                "auto_flag_enabled": True,
                "require_review_before_publish": False,
            }
        }
    }


# ============================================
# MASTER SETTINGS
# ============================================

class Settings(BaseModel):
    """
    Master settings container for all AfriFlow configuration.

    This is the single source of truth for all configurable
    values in the platform. All magic numbers should be
    replaced with settings from this class.

    Attributes:
        sim_deflation: SIM deflation factors by country
        seasonal_weights: Seasonal adjustment weights
        signal_thresholds: Signal detection thresholds
        lekgotla: Lekgotla configuration
        corridor: Corridor configuration
        moderation: Moderation patterns
    """

    sim_deflation: Dict[str, SimDeflationConfig] = Field(
        default_factory=dict,
        description="SIM deflation factors by country"
    )
    seasonal_weights: Dict[str, SeasonalWeightConfig] = Field(
        default_factory=dict,
        description="Seasonal adjustment weights"
    )
    signal_thresholds: SignalThresholds = Field(
        default_factory=SignalThresholds,
        description="Signal detection thresholds"
    )
    lekgotla: LekgotlaConfig = Field(
        default_factory=LekgotlaConfig,
        description="Lekgotla configuration"
    )
    corridor: CorridorConfig = Field(
        default_factory=CorridorConfig,
        description="Corridor configuration"
    )
    moderation: ModerationPatterns = Field(
        default_factory=ModerationPatterns,
        description="Moderation patterns"
    )

    def get_sim_deflation(self, country_code: str) -> float:
        """
        Get SIM deflation factor for a country.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Deflation factor (0.0 to 1.0)
        """
        if country_code not in self.sim_deflation:
            logger.warning(
                f"No SIM deflation factor for {country_code}, "
                f"using default 0.50"
            )
            return 0.50
        return self.sim_deflation[country_code].deflation_factor

    model_config = {
        "json_schema_extra": {
            "example": {
                "signal_thresholds": {
                    "expansion_min_cib_payments": 3,
                    "expansion_min_cib_value": 1000000.0,
                    "expansion_min_sim_activations": 20,
                },
                "lekgotla": {
                    "thread_points": 10,
                    "reply_points": 5,
                    "solution_points": 25,
                },
            }
        }
    }


__all__ = [
    "SimDeflationConfig",
    "SeasonalWeightConfig",
    "SignalThresholds",
    "LekgotlaConfig",
    "CorridorConfig",
    "ModerationPatterns",
    "Settings",
]
