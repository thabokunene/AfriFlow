"""
Currency Event Classifier

We classify FX moves by severity tier and determine
which domains and clients are affected.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import logging

from afriflow.exceptions import CurrencyPropagationError
from afriflow.config import get_settings
from afriflow.logging_config import get_logger, log_operation
from afriflow.currency_events.constants import (
    CURRENCY_COUNTRY_MAP,
    PARALLEL_MARKET_CURRENCIES,
    COMMODITY_CORRELATIONS,
    DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE,
    DOMAIN_CELL, DOMAIN_PBB, ALL_DOMAINS
)

logger = get_logger("currency_events.classifier")


class EventTier(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

# Alias for backward compatibility
EventSeverity = EventTier


class EventType(Enum):
    DEVALUATION = "DEVALUATION"
    CAPITAL_CONTROL_CHANGE = "CAPITAL_CONTROL_CHANGE"
    CENTRAL_BANK_INTERVENTION = "CENTRAL_BANK_INTERVENTION"
    RATE_MOVE = "RATE_MOVE"
    POLICY_RATE_CHANGE = "POLICY_RATE_CHANGE"
    PARALLEL_RATE_DIVERGENCE = "PARALLEL_RATE_DIVERGENCE"
    RAPID_DEPRECIATION = "RAPID_DEPRECIATION"

# Alias for backward compatibility
EventType.PARALLEL_DIVERGENCE = EventType.PARALLEL_RATE_DIVERGENCE


@dataclass
class CurrencyEvent:
    """
    We represent a classified currency event with
    its severity, type, and propagation scope.
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
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    affected_domains: List[str] = field(
        default_factory=list
    )
    notes: str = ""

    @property
    def severity(self) -> EventTier:
        return self.event_tier

    @property
    def currency(self) -> str:
        return self.currency_code


class CurrencyEventClassifier:
    """
    We classify currency events by analyzing rate
    movements, capital control changes, and parallel
    market dynamics.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        logger.debug("CurrencyEventClassifier initialized")

    def _get_threshold(self, currency: str) -> dict:
        try:
            threshold = self.settings.get_currency_threshold(currency)
            return {
                "devaluation_pct": float(threshold.devaluation_pct),
                "rapid_depreciation_pct": float(threshold.rapid_depreciation_pct),
                "parallel_divergence_pct": float(threshold.parallel_divergence_pct),
            }
        except (AttributeError, KeyError, TypeError, ValueError) as e:
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
        if rate_before <= 0:
            raise ValueError("rate_before must be positive")

        magnitude = abs((rate_after - rate_before) / rate_before) * 100

        # Get currency-specific thresholds
        thresholds = self._get_threshold(currency)
        critical_threshold = thresholds["devaluation_pct"]
        high_threshold = thresholds["rapid_depreciation_pct"]
        medium_threshold = high_threshold * 0.6  # Scaled threshold
        parallel_critical = thresholds["parallel_divergence_pct"]

        tier = None
        event_type = EventType.RATE_MOVE

        # Determine tier based on magnitude and period
        if magnitude >= critical_threshold and period_hours <= 24:
            tier = EventTier.CRITICAL
            event_type = EventType.DEVALUATION
        elif magnitude >= high_threshold and period_hours <= 168:
            tier = EventTier.HIGH
            event_type = EventType.RAPID_DEPRECIATION
        elif magnitude >= medium_threshold and period_hours <= 720:
            tier = EventTier.MEDIUM
            event_type = EventType.RAPID_DEPRECIATION
        elif magnitude >= medium_threshold * 0.5:
            tier = EventTier.LOW
            event_type = EventType.RAPID_DEPRECIATION

        # Check parallel market divergence
        if (
            currency in PARALLEL_MARKET_CURRENCIES
            and parallel_rate_after is not None
            and rate_after > 0
        ):
            divergence = abs((parallel_rate_after - rate_after) / rate_after) * 100
            if divergence >= parallel_critical:
                tier = EventTier.CRITICAL
                event_type = EventType.PARALLEL_RATE_DIVERGENCE
            elif divergence >= parallel_critical * 0.75:
                if tier is None or tier.value not in ["CRITICAL"]:
                    tier = EventTier.HIGH
                    event_type = EventType.PARALLEL_RATE_DIVERGENCE

        if tier is None:
            return None

        affected = self._determine_affected_domains(tier)
        now = datetime.now()
        event_id = f"FXE-{currency}-{now:%Y%m%d%H%M%S}"

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
