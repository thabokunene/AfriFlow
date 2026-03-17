"""
Currency Event Alert Engine

Detects significant currency events across the 20 African
markets in the AfriFlow coverage universe and routes alerts
to the relevant sales and trading desks.

Currency event types:
  RATE_SHOCK         — Single-session move > 2× normal daily vol
  REGIME_CHANGE      — Central bank announces devaluation/float
  PARALLEL_COLLAPSE  — Parallel premium exceeds regulatory threshold
  CORRIDOR_ILLIQUID  — Bid-ask spread > 5× normal = illiquid market
  CARRY_OPPORTUNITY  — Interest rate differential creates carry trade
  SWAP_POINTS_SPIKE  — Forward points spike = funding stress signal

Events are enriched with:
  - Client impact assessment (which clients hold this currency)
  - Revenue opportunity sizing (hedging demand)
  - Market commentary (plain-English trading desk note)

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# Normal daily vol (annualised / sqrt(252)) by currency pair
# Used to detect rate shocks (2× normal daily move)
_NORMAL_DAILY_VOL: Dict[str, float] = {
    "NGAZAR": 0.010, "KESAZAR": 0.008, "GHSAZAR": 0.009,
    "TZSZAR": 0.007, "UGXZAR": 0.009, "ZMWZAR": 0.012,
    "ZWLZAR": 0.030, "MZEZAR": 0.011, "BWPZAR": 0.005,
    "NADZAR": 0.004, "ETBZAR": 0.010, "CIFZAR": 0.006,
    "XOFZAR": 0.006, "CMDZAR": 0.007, "AOAZAR": 0.015,
    "MGAZAR": 0.013, "RWFZAR": 0.008, "MURZAR": 0.005,
    "EGPZAR": 0.009, "MWKZAR": 0.014,
}

# Parallel premium regulatory thresholds
_PARALLEL_THRESHOLD: Dict[str, float] = {
    "NG": 0.15, "EG": 0.12, "ZW": 0.25,
    "ET": 0.18, "AO": 0.20,
}


@dataclass
class CurrencyEvent:
    """A single detected currency market event."""

    event_id: str
    event_type: str
    currency_pair: str
    country: str
    severity: str       # LOW / MEDIUM / HIGH / CRITICAL
    headline: str
    market_commentary: str
    affected_client_count: int
    total_client_exposure_zar: float
    hedging_revenue_opportunity_zar: float
    detected_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class CurrencyEventReport:
    """All currency events detected in the current market scan."""

    events: List[CurrencyEvent]
    scan_timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    total_market_exposure_zar: float = 0.0

    @property
    def critical_events(self) -> List[CurrencyEvent]:
        return [e for e in self.events if e.severity == "CRITICAL"]

    @property
    def high_events(self) -> List[CurrencyEvent]:
        return [e for e in self.events if e.severity == "HIGH"]


class CurrencyEventAlertEngine:
    """
    Scan rate ticks and market data for currency events.

    Usage::

        engine = CurrencyEventAlertEngine()
        report = engine.scan(
            rate_ticks=[...],          # List of current rate snapshots
            prior_ticks=[...],         # Previous period for comparison
            client_exposures=[...],    # Aggregated client exposure by pair
        )
    """

    def scan(
        self,
        rate_ticks: List[Dict],
        prior_ticks: Optional[List[Dict]] = None,
        client_exposures: Optional[Dict[str, float]] = None,
    ) -> CurrencyEventReport:
        """
        Scan market data for currency events.

        rate_ticks: list of {currency_pair, mid_rate, bid, ask,
                              parallel_rate, swap_points_3m,
                              annualised_vol, ...}
        """
        prior = prior_ticks or []
        exposures = client_exposures or {}
        events: List[CurrencyEvent] = []

        prior_map: Dict[str, Dict] = {
            t["currency_pair"]: t for t in prior if "currency_pair" in t
        }

        for tick in rate_ticks:
            pair = tick.get("currency_pair", "")
            if not pair:
                continue

            country = self._country_from_pair(pair)
            prior_tick = prior_map.get(pair, {})
            exposure = exposures.get(pair, 0.0)

            # --- Rate shock ---
            event = self._detect_rate_shock(
                pair, country, tick, prior_tick, exposure
            )
            if event:
                events.append(event)

            # --- Parallel market collapse ---
            event = self._detect_parallel_collapse(
                pair, country, tick, exposure
            )
            if event:
                events.append(event)

            # --- Corridor illiquidity ---
            event = self._detect_illiquidity(
                pair, country, tick, exposure
            )
            if event:
                events.append(event)

            # --- Swap points spike ---
            event = self._detect_swap_spike(
                pair, country, tick, prior_tick, exposure
            )
            if event:
                events.append(event)

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        events.sort(key=lambda e: severity_order.get(e.severity, 9))

        total_exposure = sum(e.total_client_exposure_zar for e in events)

        return CurrencyEventReport(
            events=events,
            total_market_exposure_zar=total_exposure,
        )

    def _detect_rate_shock(
        self,
        pair: str,
        country: str,
        tick: Dict,
        prior: Dict,
        exposure: float,
    ) -> Optional[CurrencyEvent]:
        if not prior:
            return None

        current = tick.get("mid_rate", 0)
        previous = prior.get("mid_rate", current)
        if not previous:
            return None

        move = abs(current - previous) / previous
        pair_key = pair.replace("/", "").replace(" ", "")
        normal_vol = _NORMAL_DAILY_VOL.get(pair_key, 0.010)

        if move < 2 * normal_vol:
            return None

        direction = "weakened" if current > previous else "strengthened"
        severity = "CRITICAL" if move > 5 * normal_vol else "HIGH"

        hedging_opty = exposure * move * 0.50

        return CurrencyEvent(
            event_id=f"EVT-SHOCK-{pair_key}-{datetime.now().strftime('%H%M')}",
            event_type="RATE_SHOCK",
            currency_pair=pair,
            country=country,
            severity=severity,
            headline=(
                f"{pair} {direction} {move*100:.1f}% intraday "
                f"({move/normal_vol:.1f}× normal daily vol)"
            ),
            market_commentary=(
                f"{pair} moved {move*100:.1f}% from {previous:.4f} to "
                f"{current:.4f}. This is {move/normal_vol:.1f}× the "
                f"normal daily volatility. Clients with {pair} payables "
                f"or receivables should review hedging positions."
            ),
            affected_client_count=max(1, int(exposure / 5_000_000)),
            total_client_exposure_zar=exposure,
            hedging_revenue_opportunity_zar=hedging_opty,
        )

    def _detect_parallel_collapse(
        self,
        pair: str,
        country: str,
        tick: Dict,
        exposure: float,
    ) -> Optional[CurrencyEvent]:
        threshold = _PARALLEL_THRESHOLD.get(country)
        if not threshold:
            return None

        official = tick.get("mid_rate", 0)
        parallel = tick.get("parallel_rate")
        if not parallel or not official:
            return None

        premium = abs(parallel - official) / official
        if premium < threshold:
            return None

        severity = "CRITICAL" if premium > threshold * 2 else "HIGH"

        return CurrencyEvent(
            event_id=f"EVT-PAR-{country}-{datetime.now().strftime('%H%M')}",
            event_type="PARALLEL_COLLAPSE",
            currency_pair=pair,
            country=country,
            severity=severity,
            headline=(
                f"{pair} parallel premium {premium*100:.0f}% "
                f"(threshold: {threshold*100:.0f}%)"
            ),
            market_commentary=(
                f"The {pair} parallel market is trading at "
                f"{premium*100:.1f}% premium to the official rate. "
                f"This exceeds the {threshold*100:.0f}% regulatory "
                f"threshold for {country}. Cross-border payments and "
                f"invoice financing for {country} corridors require review."
            ),
            affected_client_count=max(1, int(exposure / 10_000_000)),
            total_client_exposure_zar=exposure,
            hedging_revenue_opportunity_zar=exposure * 0.005,
        )

    def _detect_illiquidity(
        self,
        pair: str,
        country: str,
        tick: Dict,
        exposure: float,
    ) -> Optional[CurrencyEvent]:
        bid = tick.get("bid_rate", 0)
        ask = tick.get("ask_rate", 0)
        mid = tick.get("mid_rate", 0)

        if not mid or not bid or not ask:
            return None

        spread = (ask - bid) / mid
        normal_spread = 0.002   # 20bp is normal for liquid African pairs

        if spread < normal_spread * 5:
            return None

        return CurrencyEvent(
            event_id=f"EVT-ILLIQ-{pair.replace('/', '')}-{datetime.now().strftime('%H%M')}",
            event_type="CORRIDOR_ILLIQUID",
            currency_pair=pair,
            country=country,
            severity="HIGH",
            headline=(
                f"{pair} spread {spread*10000:.0f}bp "
                f"({spread/normal_spread:.0f}× normal)"
            ),
            market_commentary=(
                f"{pair} bid-ask spread widened to {spread*10000:.0f}bp, "
                f"{spread/normal_spread:.0f}× the normal {normal_spread*10000:.0f}bp. "
                f"Market is illiquid. Clients with urgent {pair} requirements "
                f"may face significant slippage."
            ),
            affected_client_count=max(1, int(exposure / 8_000_000)),
            total_client_exposure_zar=exposure,
            hedging_revenue_opportunity_zar=exposure * spread * 0.30,
        )

    def _detect_swap_spike(
        self,
        pair: str,
        country: str,
        tick: Dict,
        prior: Dict,
        exposure: float,
    ) -> Optional[CurrencyEvent]:
        current_swap = tick.get("swap_points_3m", 0)
        prior_swap = prior.get("swap_points_3m", current_swap)

        if not prior_swap or prior_swap == 0:
            return None

        change = abs(current_swap - prior_swap) / abs(prior_swap)
        if change < 0.50:   # Less than 50% change
            return None

        return CurrencyEvent(
            event_id=f"EVT-SWAP-{pair.replace('/', '')}-{datetime.now().strftime('%H%M')}",
            event_type="SWAP_POINTS_SPIKE",
            currency_pair=pair,
            country=country,
            severity="MEDIUM",
            headline=(
                f"{pair} 3m swap points moved {change*100:.0f}%"
            ),
            market_commentary=(
                f"{pair} 3-month swap points changed {change*100:.0f}% "
                f"from {prior_swap:.1f} to {current_swap:.1f}. "
                f"This signals a change in funding conditions or "
                f"interest rate expectations for {country}."
            ),
            affected_client_count=max(1, int(exposure / 15_000_000)),
            total_client_exposure_zar=exposure,
            hedging_revenue_opportunity_zar=exposure * 0.002,
        )

    def _country_from_pair(self, pair: str) -> str:
        """Extract 2-letter country code from currency pair like 'NGN/ZAR'."""
        if not pair:
            return "??"
        # Currency code → country code mapping
        _CURRENCY_TO_COUNTRY = {
            "NGN": "NG", "KES": "KE", "GHS": "GH", "TZS": "TZ",
            "UGX": "UG", "ZMW": "ZM", "ZWL": "ZW", "MZE": "MZ",
            "BWP": "BW", "NAD": "NA", "ETB": "ET", "XOF": "CI",
            "CIF": "CI", "XAF": "CM", "AOA": "AO", "MGA": "MG",
            "RWF": "RW", "MUR": "MU", "EGP": "EG", "MWK": "MW",
        }
        currency = pair.split("/")[0] if "/" in pair else pair[:3].upper()
        return _CURRENCY_TO_COUNTRY.get(currency, currency[:2])
