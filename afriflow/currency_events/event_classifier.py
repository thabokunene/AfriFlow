"""
@file event_classifier.py
@description Classifies FX market movements and central bank policy changes
             into structured currency events. Determines the severity tier
             and event type based on magnitude, time window, and parallel
             market divergence. Identifies the breadth of domain impact
             (CIB, Forex, Insurance, etc.) for each classified event.
@author Thabo Kunene
@created 2026-03-19
"""

# Currency Event Classifier
#
# We classify FX moves by severity tier and determine
# which domains and clients are affected.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data classes, enums, and dates
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import logging

# Platform-specific exceptions, configuration, and logging
from afriflow.exceptions import CurrencyPropagationError
from afriflow.config import get_settings
from afriflow.logging_config import get_logger, log_operation

# Currency event domain constants
from afriflow.currency_events.constants import (
    CURRENCY_COUNTRY_MAP,
    PARALLEL_MARKET_CURRENCIES,
    COMMODITY_CORRELATIONS,
    DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE,
    DOMAIN_CELL, DOMAIN_PBB, ALL_DOMAINS
)

# Initialise a module-scoped logger for event classification
logger = get_logger("currency_events.classifier")


class EventTier(Enum):
    """
    Categorisation of event severity based on market impact.
    """
    # Imminent and massive impact (e.g., >10% devaluation)
    CRITICAL = "CRITICAL"
    # Significant move requiring RM action within 24h
    HIGH = "HIGH"
    # Notable trend change requiring monitoring
    MEDIUM = "MEDIUM"
    # Minor fluctuation or early warning signal
    LOW = "LOW"

# Alias for backward compatibility with earlier iterations
EventSeverity = EventTier


class EventType(Enum):
    """
    Specific nature of the currency event being classified.
    """
    # Large-scale official adjustment of the peg
    DEVALUATION = "DEVALUATION"
    # Change in FX repatriation or conversion rules
    CAPITAL_CONTROL_CHANGE = "CAPITAL_CONTROL_CHANGE"
    # Central bank active in the market to defend rate
    CENTRAL_BANK_INTERVENTION = "CENTRAL_BANK_INTERVENTION"
    # Generic significant rate fluctuation
    RATE_MOVE = "RATE_MOVE"
    # Change in the benchmark interest rate
    POLICY_RATE_CHANGE = "POLICY_RATE_CHANGE"
    # Divergence between official and black market rates
    PARALLEL_RATE_DIVERGENCE = "PARALLEL_RATE_DIVERGENCE"
    # Sustained high-velocity currency slide
    RAPID_DEPRECIATION = "RAPID_DEPRECIATION"

# Alias for backward compatibility
EventType.PARALLEL_DIVERGENCE = EventType.PARALLEL_RATE_DIVERGENCE


@dataclass
class CurrencyEvent:
    """
    A structured representation of a classified currency event.

    :param event_id: Unique identifier (e.g., 'FXE-NGN-20260319...')
    :param currency_code: 3-letter ISO code of the base currency
    :param event_tier: Severity classification (CRITICAL to LOW)
    :param event_type: Nature of the event (e.g., DEVALUATION)
    :param magnitude_pct: Absolute percentage change in the rate
    :param official_rate_before: Rate prior to the event (vs ZAR)
    :param official_rate_after: Rate after the event (vs ZAR)
    :param parallel_rate_before: Parallel rate prior to event, if applicable
    :param parallel_rate_after: Parallel rate after event, if applicable
    :param trigger_source: Origin of the event detection (e.g., 'rate_feed')
    :param timestamp: ISO timestamp of when the event was classified
    :param affected_domains: List of business domains impacted by this event
    :param notes: Narrative commentary explaining the classification
    """

    event_id: str
    currency_code: str
    event_tier: EventTier
    event_type: EventType
    magnitude_pct: float
    official_rate_before: float
    official_rate_after: float
    parallel_rate_before: Optional[float] = None
    parallel_rate_after: Optional[float] = None
    trigger_source: str = "rate_feed"
    # Automatically timestamp the event object creation
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    # Default to an empty list if no specific domains are identified
    affected_domains: List[str] = field(
        default_factory=list
    )
    notes: str = ""

    @property
    def severity(self) -> EventTier:
        """
        Exposes the event tier as 'severity' for API consistency.
        """
        return self.event_tier

    @property
    def currency(self) -> str:
        """
        Exposes the currency code for easier reference.
        """
        return self.currency_code


class CurrencyEventClassifier:
    """
    Classifies FX market data into actionable business events.
    """

    def __init__(self, settings=None):
        """
        Initialise the classifier with platform settings.

        :param settings: Optional Settings object; defaults to platform global settings.
        """
        self.settings = settings or get_settings()
        logger.debug("CurrencyEventClassifier initialized")

    def _get_threshold(self, currency: str) -> dict:
        """
        Retrieve currency-specific detection thresholds from configuration.

        :param currency: The currency code to lookup.
        :return: A dictionary of threshold values.
        """
        try:
            # Attempt to pull from the 'currency_thresholds.yml' config
            threshold = self.settings.get_currency_threshold(currency)
            return {
                "devaluation_pct": float(threshold.devaluation_pct),
                "rapid_depreciation_pct": float(threshold.rapid_depreciation_pct),
                "parallel_divergence_pct": float(threshold.parallel_divergence_pct),
            }
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            # Fallback to conservative defaults if configuration is missing
            logger.warning(f"Could not load thresholds for {currency}: {e}. Using defaults.")
            return {
                "devaluation_pct": 10.0,
                "rapid_depreciation_pct": 5.0,
                "parallel_divergence_pct": 20.0,
            }

    def classify_rate_move(
        self,
        currency: str,
        rate_before: float,
        rate_after: float,
        period_hours: int,
        parallel_rate_before: Optional[float] = None,
        parallel_rate_after: Optional[float] = None,
        trigger_source: str = "rate_feed"
    ) -> Optional[CurrencyEvent]:
        """
        Analyze a rate change over a time window and classify it as an event.

        :param currency: 3-letter currency code
        :param rate_before: Mid-rate at start of period
        :param rate_after: Mid-rate at end of period
        :param period_hours: Length of the analysis window
        :param parallel_rate_before: Black market rate at start
        :param parallel_rate_after: Black market rate at end
        :param trigger_source: Label for the detector that triggered this call
        :return: A classified CurrencyEvent, or None if thresholds are not met.
        """
        # Ensure rates are valid before calculating magnitude
        if rate_before <= 0:
            raise ValueError("rate_before must be positive")

        # Calculate the absolute percentage change
        magnitude = abs((rate_after - rate_before) / rate_before) * 100

        # Load the relevant thresholds for this specific currency
        thresholds = self._get_threshold(currency)
        critical_threshold = thresholds["devaluation_pct"]
        high_threshold = thresholds["rapid_depreciation_pct"]
        medium_threshold = high_threshold * 0.6  # Calculated medium threshold
        parallel_critical = thresholds["parallel_divergence_pct"]

        tier = None
        event_type = EventType.RATE_MOVE

        # --- Decision Logic: Severity Tier Assignment ---
        # 1. CRITICAL: Massive move in a short window (e.g., >10% in 24h)
        if magnitude >= critical_threshold and period_hours <= 24:
            tier = EventTier.CRITICAL
            event_type = EventType.DEVALUATION
        # 2. HIGH: Significant slide over a week (e.g., >5% in 168h)
        elif magnitude >= high_threshold and period_hours <= 168:
            tier = EventTier.HIGH
            event_type = EventType.RAPID_DEPRECIATION
        # 3. MEDIUM: Notable trend over a month
        elif magnitude >= medium_threshold and period_hours <= 720:
            tier = EventTier.MEDIUM
            event_type = EventType.RAPID_DEPRECIATION
        # 4. LOW: Early signal of a sustained slide
        elif magnitude >= medium_threshold * 0.5:
            tier = EventTier.LOW
            event_type = EventType.RAPID_DEPRECIATION

        # --- Check for Parallel Market Divergence ---
        # This is a critical risk indicator for specific African markets (e.g., NG, ZW)
        if (
            currency in PARALLEL_MARKET_CURRENCIES
            and parallel_rate_after is not None
            and rate_after > 0
        ):
            # Calculate the spread between official and parallel rates
            divergence = abs((parallel_rate_after - rate_after) / rate_after) * 100
            # If divergence is massive, escalate to CRITICAL
            if divergence >= parallel_critical:
                tier = EventTier.CRITICAL
                event_type = EventType.PARALLEL_RATE_DIVERGENCE
            # If divergence is significant, ensure it's at least HIGH
            elif divergence >= parallel_critical * 0.75:
                if tier is None or tier.value not in ["CRITICAL"]:
                    tier = EventTier.HIGH
                    event_type = EventType.PARALLEL_RATE_DIVERGENCE

        # If no thresholds were breached, this is not an actionable event
        if tier is None:
            return None

        # Determine which business domains are impacted by an event of this tier
        affected = self._determine_affected_domains(tier)
        now = datetime.now()
        # Generate a unique event identifier
        event_id = f"FXE-{currency}-{now:%Y%m%d%H%M%S}"

        # Construct the final event record
        event = CurrencyEvent(
            event_id=event_id,
            currency_code=currency,
            event_tier=tier,
            event_type=event_type,
            magnitude_pct=round(magnitude, 4),
            official_rate_before=rate_before,
            official_rate_after=rate_after,
            parallel_rate_before=parallel_rate_before,
            parallel_rate_after=parallel_rate_after,
            trigger_source=trigger_source,
            timestamp=now.isoformat(),
            affected_domains=affected
        )
        
        logger.info(f"Classified {currency} move: {tier.value} ({magnitude:.2f}%)")
        return event

    def classify(
        self,
        currency: str,
        rate_change_pct: float,
        is_official_announcement: bool = False,
        parallel_divergence_pct: float = 0.0,
    ) -> Optional[CurrencyEvent]:
        cur = (currency or "").upper()
        mag = abs(float(rate_change_pct))
        
        # Determine period based on official announcement or just treat as 24h if official
        period = 24 if is_official_announcement else 168
        
        # Parallel market divergence check first (it often triggers events even if official rate is stable)
        if parallel_divergence_pct > 0:
            return self.classify_rate_move(
                currency=cur,
                rate_before=100.0,
                rate_after=100.0 * (1 + mag/100),
                period_hours=period,
                parallel_rate_before=100.0,
                parallel_rate_after=100.0 * (1 + parallel_divergence_pct/100)
            )

        # Large official moves are devaluations
        if is_official_announcement and mag >= 5.0:
            return self.classify_rate_move(
                currency=cur,
                rate_before=100.0,
                rate_after=100.0 * (1 + mag/100),
                period_hours=24,
                trigger_source="regulatory_announcement"
            )

        return self.classify_rate_move(
            currency=cur,
            rate_before=100.0,
            rate_after=100.0 * (1 + mag/100),
            period_hours=period
        )

    def classify_capital_control(
        self,
        currency: str,
        control_type: str,
        description: str
    ) -> CurrencyEvent:
        now = datetime.now()
        return CurrencyEvent(
            event_id=f"FXE-CC-{currency}-{now:%Y%m%d%H%M%S}",
            currency_code=currency,
            event_tier=EventTier.CRITICAL,
            event_type=EventType.CAPITAL_CONTROL_CHANGE,
            magnitude_pct=0.0,
            official_rate_before=0.0,
            official_rate_after=0.0,
            trigger_source="regulatory_announcement",
            timestamp=now.isoformat(),
            affected_domains=ALL_DOMAINS.copy(),
            notes=f"Capital control change: {control_type} - {description}"
        )

    def _determine_affected_domains(self, tier: EventTier) -> List[str]:
        if tier == EventTier.CRITICAL:
            return ALL_DOMAINS.copy()
        elif tier == EventTier.HIGH:
            return [DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE]
        elif tier == EventTier.MEDIUM:
            return [DOMAIN_CIB, DOMAIN_FOREX]
        return [DOMAIN_FOREX]
