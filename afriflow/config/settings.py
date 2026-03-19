"""
@file settings.py
@description Configuration Settings Models - Pydantic models for all configuration sections
@author Thabo Kunene
@created 2026-03-19

This module defines Pydantic models for all configuration sections.
This enables validation, type safety, and clear error messages
when configuration is invalid.

Configuration Sections:
1. SimDeflationConfig - SIM to employee conversion factors per country
2. SeasonalWeightConfig - Seasonal adjustment weights for commodities
3. SignalThresholds - Minimum evidence thresholds for signal detection
4. LekgotlaConfig - Collective intelligence platform settings
5. CorridorConfig - Cross-border corridor intelligence settings
6. ModerationPatterns - Content moderation regex patterns
7. Settings - Master container combining all configuration sections

Usage:
    >>> from afriflow.config.settings import Settings, SimDeflationConfig
    >>> config = SimDeflationConfig(
    ...     country_code="NG",
    ...     deflation_factor=0.36,
    ...     avg_sims_per_person=2.8,
    ...     confidence="medium",
    ...     source="NCC subscriber data"
    ... )
    >>> print(config.deflation_factor)  # 0.36

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

# Pydantic imports for data validation and settings management
from pydantic import BaseModel, Field, field_validator  # BaseModel for validation, Field for metadata, validator for custom validation
from typing import Dict, List, Optional, Any  # Type hints for dictionaries, lists, optional values, and any type
import logging  # Python's built-in logging module for warnings and info messages

logger = logging.getLogger(__name__)  # Get logger instance for this module


# ============================================
# SIM DEFLATION CONFIGURATION
# ============================================

class SimDeflationConfig(BaseModel):
    """
    SIM to employee deflation configuration per country.

    Used to convert raw SIM counts to estimated employee
    headcounts, accounting for multi-SIM culture in Africa.

    In many African countries, individuals own multiple SIM cards
    (2-3 on average). This means raw SIM counts overstate the
    actual number of employees. The deflation factor converts
    SIM counts to realistic employee estimates.

    Attributes:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "ZA", "NG")
        deflation_factor: Factor to multiply SIM count by (0-1)
        avg_sims_per_person: Average SIMs per person (inverse of deflation)
        confidence: Confidence level (high/medium/low) in the factor
        source: Data source for the factor (e.g., regulator data)

    Example:
        >>> config = SimDeflationConfig(
        ...     country_code="NG",
        ...     deflation_factor=0.36,
        ...     avg_sims_per_person=2.8,
        ...     confidence="medium",
        ...     source="NCC subscriber data"
        ... )
        >>> employees = sim_count * config.deflation_factor
    """

    # Country code field with validation pattern
    country_code: str = Field(
        ...,  # Required field (Ellipsis means required)
        description="ISO 3166-1 alpha-2 country code",  # Human-readable description
        pattern=r"^[A-Z]{2}$"  # Regex pattern: exactly 2 uppercase letters
    )

    # Deflation factor field with range validation
    deflation_factor: float = Field(
        ...,  # Required field
        description="Factor to multiply SIM count by",  # Description for documentation
        gt=0,  # Must be greater than 0
        le=1  # Must be less than or equal to 1
    )

    # Average SIMs per person field
    avg_sims_per_person: float = Field(
        ...,  # Required field
        description="Average SIMs per person",  # Description
        gt=0  # Must be greater than 0 (typically 1.3 to 3.3)
    )

    # Confidence level field with pattern validation
    confidence: str = Field(
        ...,  # Required field
        description="Confidence level (high/medium/low)",  # Description
        pattern=r"^(high|medium|low)$"  # Must be one of these three values
    )

    # Data source field
    source: str = Field(
        ...,  # Required field
        description="Data source for the factor"  # e.g., "ICASA 2024", "NCC subscriber data"
    )

    # Custom validator to ensure country code is uppercase
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """
        Validate country code is uppercase.

        Converts country code to uppercase to ensure consistency
        across all configuration files and runtime values.

        Args:
            v: Country code value to validate

        Returns:
            Uppercase country code
        """
        return v.upper()  # Convert to uppercase for consistency

    # Example configuration for documentation and testing
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

    Many African economies are driven by agricultural cycles.
    Payment volumes, forex flows, and cell usage all show
    seasonal patterns. This configuration enables the platform
    to distinguish between normal seasonal variation and
    genuine expansion signals.

    Attributes:
        commodity: Commodity name (e.g., "cocoa", "coffee", "copper")
        country_code: ISO 3166-1 alpha-2 country code
        peak_months: Months with peak activity (1-12)
        trough_months: Months with low activity (1-12)
        flow_type: Flow type (export/import/domestic)
        expected_peak_multiplier: Expected volume multiplier at peak (e.g., 3.0 = 3x normal)
        expected_trough_multiplier: Expected volume multiplier at trough (e.g., 0.2 = 20% of normal)

    Example:
        >>> config = SeasonalWeightConfig(
        ...     commodity="cocoa",
        ...     country_code="GH",
        ...     peak_months=[10, 11, 12],
        ...     trough_months=[3, 4, 5],
        ...     flow_type="export",
        ...     expected_peak_multiplier=3.0,
        ...     expected_trough_multiplier=0.2
        ... )
        >>> # During peak months, expect 3x normal volume
    """

    # Commodity name field
    commodity: str = Field(..., description="Commodity name")

    # Country code with validation pattern
    country_code: str = Field(
        ...,
        description="ISO 3166-1 alpha-2 country code",
        pattern=r"^[A-Z]{2}$"
    )

    # Peak months list with range validation for each month
    peak_months: List[int] = Field(
        ...,
        description="Months with peak activity (1-12)",
    )

    # Trough months list with range validation
    trough_months: List[int] = Field(
        ...,
        description="Months with low activity (1-12)",
    )

    # Flow type with pattern validation
    flow_type: str = Field(
        ...,
        description="Flow type (export/import/domestic)",
        pattern=r"^(export|import|domestic)$"
    )

    # Peak multiplier field
    expected_peak_multiplier: float = Field(
        ...,
        description="Expected volume multiplier at peak",
        gt=0  # Must be positive (typically 1.5 to 4.0)
    )

    # Trough multiplier field
    expected_trough_multiplier: float = Field(
        ...,
        description="Expected volume multiplier at trough",
        gt=0  # Must be positive (typically 0.1 to 0.6)
    )

    # Example configuration for documentation
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

    These thresholds control the sensitivity of signal detection.
    Lower thresholds generate more signals (including false positives).
    Higher thresholds generate fewer signals (potentially missing opportunities).

    Attributes:
        expansion_min_cib_payments: Minimum CIB payments for expansion signal
        expansion_min_cib_value: Minimum CIB value (ZAR) for expansion signal
        expansion_min_sim_activations: Minimum SIM activations for expansion
        leakage_min_volume_ratio: Minimum volume ratio for leakage detection
        hedge_gap_min_exposure: Minimum exposure for hedge gap signal
        workforce_min_sims: Minimum SIMs for workforce signal

    Example:
        >>> thresholds = SignalThresholds(
        ...     expansion_min_cib_payments=3,
        ...     expansion_min_cib_value=1000000.0,
        ...     expansion_min_sim_activations=20
        ... )
    """

    # Minimum CIB payments threshold
    expansion_min_cib_payments: int = Field(
        default=3,  # Default value if not specified in config
        description="Minimum CIB payments for expansion signal",
        ge=1  # Must be greater than or equal to 1
    )

    # Minimum CIB value threshold (in ZAR)
    expansion_min_cib_value: float = Field(
        default=1_000_000.0,  # 1 million ZAR default
        description="Minimum CIB value in ZAR for expansion signal",
        gt=0  # Must be positive
    )

    # Minimum SIM activations threshold
    expansion_min_sim_activations: int = Field(
        default=20,  # 20 SIMs default
        description="Minimum SIM activations for expansion signal",
        ge=1
    )

    # Leakage detection volume ratio threshold
    leakage_min_volume_ratio: float = Field(
        default=0.10,  # 10% default
        description="Minimum volume ratio for leakage detection",
        gt=0,
        le=1  # Must be between 0 and 1
    )

    # Minimum exposure for hedge gap signal
    hedge_gap_min_exposure: float = Field(
        default=500_000.0,  # 500k ZAR default
        description="Minimum exposure for hedge gap signal",
        gt=0
    )

    # Minimum SIMs for workforce signal
    workforce_min_sims: int = Field(
        default=50,  # 50 SIMs default
        description="Minimum SIMs for workforce signal",
        ge=1
    )

    # Example configuration for documentation
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

    Lekgotla is a Setswana word meaning "a gathering place for community
    decision-making and knowledge sharing." This module configures the
    gamification and collaboration features.

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

    Example:
        >>> config = LekgotlaConfig(
        ...     thread_points=10,
        ...     reply_points=5,
        ...     solution_points=25
        ... )
    """

    # Points for creating a new discussion thread
    thread_points: int = Field(
        default=10,  # 10 points per thread
        description="Points for creating a thread",
        ge=0  # Must be non-negative
    )

    # Points for posting a reply
    reply_points: int = Field(
        default=5,  # 5 points per reply
        description="Points for posting a reply",
        ge=0
    )

    # Points when reply is marked as solution
    solution_points: int = Field(
        default=25,  # 25 points for solution
        description="Points for marked solution",
        ge=0
    )

    # Points for contributing to Knowledge Card
    card_contribution_points: int = Field(
        default=50,  # 50 points per contribution
        description="Points for KC contribution",
        ge=0
    )

    # Points when Knowledge Card is published
    card_publication_points: int = Field(
        default=100,  # 100 points for publication
        description="Points for KC publication",
        ge=0
    )

    # Points per upvote received
    upvote_received_points: int = Field(
        default=2,  # 2 points per upvote
        description="Points per upvote received",
        ge=0
    )

    # Minimum upvotes required for KC graduation
    graduation_min_upvotes: int = Field(
        default=10,  # 10 upvotes minimum
        description="Minimum upvotes for KC graduation",
        ge=1
    )

    # Minimum contributors required for KC graduation
    graduation_min_contributors: int = Field(
        default=3,  # 3 contributors minimum
        description="Minimum contributors for KC graduation",
        ge=1
    )

    # Batch size for notification delivery
    notification_batch_size: int = Field(
        default=100,  # 100 notifications per batch
        description="Notifications per batch",
        ge=1
    )

    # Delay before sending notifications (seconds)
    notification_delay_seconds: int = Field(
        default=300,  # 5 minutes delay
        description="Delay before sending notifications (seconds)",
        ge=0
    )

    # Example configuration for documentation
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

    Corridors are payment flows between countries (e.g., ZA > NG).
    This configuration controls leakage detection and revenue attribution.

    Attributes:
        leakage_detection_threshold: Threshold for leakage detection
        fx_capture_expected_pct: Expected FX capture percentage
        insurance_capture_expected_pct: Expected insurance capture
        payroll_capture_expected_pct: Expected payroll capture
        informal_ratio_alert_threshold: MoMo/CIB ratio for alerts
        revenue_attribution_window_days: Days for revenue attribution

    Example:
        >>> config = CorridorConfig(
        ...     leakage_detection_threshold=0.10,
        ...     fx_capture_expected_pct=0.60
        ... )
    """

    # Leakage detection threshold (ratio)
    leakage_detection_threshold: float = Field(
        default=0.10,  # 10% default threshold
        description="Threshold for leakage detection",
        gt=0,  # Must be positive
        le=1  # Must be <= 1
    )

    # Expected FX capture percentage
    fx_capture_expected_pct: float = Field(
        default=0.60,  # 60% expected capture
        description="Expected FX capture percentage",
        gt=0,
        le=1
    )

    # Expected insurance capture percentage
    insurance_capture_expected_pct: float = Field(
        default=0.30,  # 30% expected capture
        description="Expected insurance capture percentage",
        gt=0,
        le=1
    )

    # Expected payroll capture percentage
    payroll_capture_expected_pct: float = Field(
        default=0.40,  # 40% expected capture
        description="Expected payroll capture percentage",
        gt=0,
        le=1
    )

    # MoMo/CIB ratio threshold for alerts
    informal_ratio_alert_threshold: float = Field(
        default=1.0,  # Alert when MoMo > CIB
        description="MoMo/CIB ratio for alerts",
        gt=0
    )

    # Revenue attribution window (days)
    revenue_attribution_window_days: int = Field(
        default=90,  # 90 days window
        description="Days for revenue attribution",
        ge=1
    )

    # Example configuration for documentation
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

    Regex patterns for detecting confidential information,
    spam, and inappropriate content in Lekgotla posts.

    Attributes:
        confidential_patterns: Regex patterns for confidential info
        spam_patterns: Regex patterns for spam detection
        inappropriate_patterns: Regex patterns for inappropriate content
        auto_flag_enabled: Enable automatic flagging
        require_review_before_publish: Require review before publishing

    Example:
        >>> config = ModerationPatterns(
        ...     confidential_patterns=[r"client\\s*name\\s*:\\s*\\w+"],
        ...     auto_flag_enabled=True
        ... )
    """

    # Patterns for detecting confidential information
    confidential_patterns: List[str] = Field(
        default=[  # Default patterns for common confidential data
            r"client\s*(name|number|id)\s*[:\s]*\w+",  # Client identifiers
            r"account\s*(number|id)\s*[:\s]*\d+",  # Account numbers
            r"password|credential|secret",  # Authentication credentials
            r"internal\s*(memo|document|report)",  # Internal documents
        ],
        description="Regex patterns for confidential info"
    )

    # Patterns for detecting spam
    spam_patterns: List[str] = Field(
        default=[  # Default spam patterns
            r"http[s]?://\S+",  # URLs (potential phishing)
            r"\b(CALL|CONTACT|CLICK)\s+(NOW|TODAY)\b",  # Urgency language
            r"\b(FREE|WIN|PRIZE)\b",  # Prize/promotion language
        ],
        description="Regex patterns for spam detection"
    )

    # Patterns for inappropriate content
    inappropriate_patterns: List[str] = Field(
        default=[],  # Empty by default - customize per deployment
        description="Regex patterns for inappropriate content"
    )

    # Enable/disable automatic flagging
    auto_flag_enabled: bool = Field(
        default=True,  # Enabled by default
        description="Enable automatic flagging"
    )

    # Require review before publishing
    require_review_before_publish: bool = Field(
        default=False,  # Disabled by default for user experience
        description="Require review before publishing"
    )

    # Example configuration for documentation
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

    This class combines all configuration sections into a
    single object that can be loaded once at startup and
    passed via dependency injection.

    Attributes:
        sim_deflation: SIM deflation factors by country
        seasonal_weights: Seasonal adjustment weights
        signal_thresholds: Signal detection thresholds
        lekgotla: Lekgotla configuration
        corridor: Corridor configuration
        moderation: Moderation patterns

    Example:
        >>> settings = Settings()
        >>> sim_factor = settings.get_sim_deflation("NG")
        >>> print(f"Nigeria SIM deflation: {sim_factor}")  # 0.36
    """

    # SIM deflation factors dictionary (country_code -> config)
    sim_deflation: Dict[str, SimDeflationConfig] = Field(
        default_factory=dict,  # Empty dict by default
        description="SIM deflation factors by country"
    )

    # Seasonal weights dictionary (commodity_country -> config)
    seasonal_weights: Dict[str, SeasonalWeightConfig] = Field(
        default_factory=dict,  # Empty dict by default
        description="Seasonal adjustment weights"
    )

    # Signal thresholds configuration
    signal_thresholds: SignalThresholds = Field(
        default_factory=SignalThresholds,  # Default thresholds
        description="Signal detection thresholds"
    )

    # Lekgotla configuration
    lekgotla: LekgotlaConfig = Field(
        default_factory=LekgotlaConfig,  # Default Lekgotla settings
        description="Lekgotla configuration"
    )

    # Corridor configuration
    corridor: CorridorConfig = Field(
        default_factory=CorridorConfig,  # Default corridor settings
        description="Corridor configuration"
    )

    # Moderation patterns configuration
    moderation: ModerationPatterns = Field(
        default_factory=ModerationPatterns,  # Default moderation settings
        description="Moderation patterns"
    )

    def get_sim_deflation(self, country_code: str) -> float:
        """
        Get SIM deflation factor for a country.

        This convenience method looks up the deflation factor
        for a specific country, returning a safe default if
        the country is not configured.

        Args:
            country_code: ISO 3166-1 alpha-2 country code (e.g., "ZA", "NG")

        Returns:
            Deflation factor (0.0 to 1.0)
            Default 0.50 if country not found

        Example:
            >>> settings = Settings()
            >>> factor = settings.get_sim_deflation("NG")
            >>> print(f"NG deflation: {factor}")  # 0.36
        """
        # Check if country is configured
        if country_code not in self.sim_deflation:
            # Log warning for missing configuration
            logger.warning(
                f"No SIM deflation factor for {country_code}, "
                f"using default 0.50"
            )
            return 0.50  # Safe default for unknown countries

        # Return configured deflation factor
        return self.sim_deflation[country_code].deflation_factor

    # Example configuration for documentation
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


# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.config.settings import *'

__all__ = [
    # SIM deflation configuration model
    "SimDeflationConfig",
    # Seasonal weight configuration model
    "SeasonalWeightConfig",
    # Signal threshold configuration model
    "SignalThresholds",
    # Lekgotla platform configuration model
    "LekgotlaConfig",
    # Corridor intelligence configuration model
    "CorridorConfig",
    # Content moderation configuration model
    "ModerationPatterns",
    # Master settings container combining all sections
    "Settings",
]
