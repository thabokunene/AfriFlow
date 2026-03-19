"""
@file currency_event_alert_engine.py
@description Scans African FX market data for significant currency events and
             routes structured alerts to sales and trading desks. Detects six
             event types — rate shocks, regime changes, parallel market
             collapses, corridor illiquidity, carry opportunities, and swap
             point spikes — enriched with client impact and hedging revenue
             estimates.
@author Thabo Kunene
@created 2026-03-19
"""

# Currency Event Alert Engine
#
# Detects significant currency events across the 20 African
# markets in the AfriFlow coverage universe and routes alerts
# to the relevant sales and trading desks.
#
# Currency event types:
#   RATE_SHOCK         — Single-session move > 2× normal daily vol
#   REGIME_CHANGE      — Central bank announces devaluation/float
#   PARALLEL_COLLAPSE  — Parallel premium exceeds regulatory threshold
#   CORRIDOR_ILLIQUID  — Bid-ask spread > 5× normal = illiquid market
#   CARRY_OPPORTUNITY  — Interest rate differential creates carry trade
#   SWAP_POINTS_SPIKE  — Forward points spike = funding stress signal
#
# Events are enriched with:
#   - Client impact assessment (which clients hold this currency)
#   - Revenue opportunity sizing (hedging demand)
#   - Market commentary (plain-English trading desk note)
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for structured data, timestamps, and type hinting
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Normal daily vol (annualised / sqrt(252)) by currency pair.
# These baselines are used to identify rate shocks: a session move
# exceeding 2× the normal daily vol triggers a RATE_SHOCK event.
_NORMAL_DAILY_VOL: Dict[str, float] = {
    "NGAZAR": 0.010,   # Nigerian Naira / ZAR — moderate vol, prone to policy shocks
    "KESAZAR": 0.008,  # Kenyan Shilling / ZAR — relatively stable
    "GHSAZAR": 0.009,  # Ghanaian Cedi / ZAR — elevated after 2022 debt restructuring
    "TZSZAR": 0.007,   # Tanzanian Shilling / ZAR — managed float, low vol
    "UGXZAR": 0.009,   # Ugandan Shilling / ZAR
    "ZMWZAR": 0.012,   # Zambian Kwacha / ZAR — commodity-linked, higher vol
    "ZWLZAR": 0.030,   # Zimbabwe Dollar / ZAR — highest vol; chronic depreciation
    "MZEZAR": 0.011,   # Mozambican Metical / ZAR
    "BWPZAR": 0.005,   # Botswana Pula / ZAR — tightly managed, lowest vol
    "NADZAR": 0.004,   # Namibian Dollar / ZAR — pegged 1:1 to ZAR, minimal spread
    "ETBZAR": 0.010,   # Ethiopian Birr / ZAR — managed; parallel market significant
    "CIFZAR": 0.006,   # CFA Franc (WACU) / ZAR — pegged to EUR, low vol
    "XOFZAR": 0.006,   # CFA Franc (BCEAO) / ZAR — same peg as CIF
    "CMDZAR": 0.007,   # Central African CFA Franc / ZAR
    "AOAZAR": 0.015,   # Angolan Kwanza / ZAR — oil-dependent, elevated vol
    "MGAZAR": 0.013,   # Malagasy Ariary / ZAR
    "RWFZAR": 0.008,   # Rwandan Franc / ZAR — tightly managed by BNR
    "MURZAR": 0.005,   # Mauritian Rupee / ZAR — stable island economy
    "EGPZAR": 0.009,   # Egyptian Pound / ZAR — subject to IMF-driven adjustments
    "MWKZAR": 0.014,   # Malawian Kwacha / ZAR — frequent devaluations
}

# Parallel premium regulatory thresholds by country ISO-2 code.
# When the parallel market rate diverges from the official rate by
# more than this threshold, a PARALLEL_COLLAPSE event is triggered.
_PARALLEL_THRESHOLD: Dict[str, float] = {
    "NG": 0.15,  # Nigeria: CBN tolerates up to 15% divergence before intervention
    "EG": 0.12,  # Egypt: 12% threshold; EGP devaluation history makes this relevant
    "ZW": 0.25,  # Zimbabwe: higher threshold due to chronic dual-rate environment
    "ET": 0.18,  # Ethiopia: NBE controls; parallel premium a key risk signal
    "AO": 0.20,  # Angola: BNA threshold; Kwanza historically soft
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CurrencyEvent:
    """
    A single detected currency market event. Represents a significant move or anomaly.

    :param event_id: Unique identifier for the event
    :param event_type: Category of the event (e.g., RATE_SHOCK)
    :param currency_pair: The FX pair involved (e.g., NGN/ZAR)
    :param country: ISO-2 country code for the base currency
    :param severity: Priority level (LOW to CRITICAL)
    :param headline: Brief summary for notifications
    :param market_commentary: In-depth trading desk commentary
    :param affected_client_count: Number of clients with exposure to this pair
    :param total_client_exposure_zar: Sum of exposure in ZAR for affected clients
    :param hedging_revenue_opportunity_zar: Estimated potential revenue from hedging
    :param detected_at: Timestamp of when the event was identified
    """

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
    # Default factory ensures each event gets a unique current timestamp
    detected_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class CurrencyEventReport:
    """
    Aggregation of all currency events detected during a single market scan.

    :param events: List of detected CurrencyEvent objects
    :param scan_timestamp: When the scan was performed
    :param total_market_exposure_zar: Total exposure across all events in this report
    """

    events: List[CurrencyEvent]
    # Timestamp marking the start of the scan process
    scan_timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    # Accumulator for aggregate exposure across the entire report
    total_market_exposure_zar: float = 0.0

    @property
    def critical_events(self) -> List[CurrencyEvent]:
        """
        Filters the report to only show CRITICAL events.

        :return: A list of CurrencyEvent objects with severity 'CRITICAL'.
        """
        return [e for e in self.events if e.severity == "CRITICAL"]

    @property
    def high_events(self) -> List[CurrencyEvent]:
        """
        Filters the report to only show HIGH events.

        :return: A list of CurrencyEvent objects with severity 'HIGH'.
        """
        return [e for e in self.events if e.severity == "HIGH"]


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

class CurrencyEventAlertEngine:
    """
    Core engine responsible for scanning market data and identifying currency events.

    Iterates over live rate ticks, compares them against historical baselines and
    previous periods, and calculates client impact.
    """

    def scan(
        self,
        rate_ticks: List[Dict],
        prior_ticks: Optional[List[Dict]] = None,
        client_exposures: Optional[Dict[str, float]] = None,
    ) -> CurrencyEventReport:
        """
        Perform a full market scan for currency anomalies.

        :param rate_ticks: Current market rates and indicators
        :param prior_ticks: Rates from the previous scan for trend analysis
        :param client_exposures: Mapping of currency pairs to client exposure values
        :return: A CurrencyEventReport containing all identified events.
        """
        # Initialize defaults for optional parameters
        prior = prior_ticks or []
        exposures = client_exposures or {}
        events: List[CurrencyEvent] = []

        # Map prior ticks by currency pair for O(1) comparison lookup
        prior_map: Dict[str, Dict] = {
            t["currency_pair"]: t for t in prior if "currency_pair" in t
        }

        # Iterate over every incoming rate tick and apply all detectors
        for tick in rate_ticks:
            pair = tick.get("currency_pair", "")
            if not pair:
                continue  # Skip malformed ticks with no currency pair

            country = self._country_from_pair(pair)      # Derive ISO-2 from pair prefix
            prior_tick = prior_map.get(pair, {})          # Fetch matching prior tick, or empty
            exposure = exposures.get(pair, 0.0)           # Client exposure for this pair (ZAR)

            # --- Detector 1: Rate shock ---
            # Triggers when the intraday move exceeds 2× the normal daily vol
            event = self._detect_rate_shock(
                pair, country, tick, prior_tick, exposure
            )
            if event:
                events.append(event)

            # --- Detector 2: Parallel market collapse ---
            # Triggers when official vs parallel rate diverges beyond country threshold
            event = self._detect_parallel_collapse(
                pair, country, tick, exposure
            )
            if event:
                events.append(event)

            # --- Detector 3: Corridor illiquidity ---
            # Triggers when bid-ask spread exceeds 5× the normal 20bp benchmark
            event = self._detect_illiquidity(
                pair, country, tick, exposure
            )
            if event:
                events.append(event)

            # --- Detector 4: Swap points spike ---
            # Triggers when 3-month swap points shift >50% from prior period
            event = self._detect_swap_spike(
                pair, country, tick, prior_tick, exposure
            )
            if event:
                events.append(event)

        # Sort all detected events so trading desk sees the most critical first.
        # CRITICAL=0, HIGH=1, MEDIUM=2, LOW=3; unknown severities go to the bottom.
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        events.sort(key=lambda e: severity_order.get(e.severity, 9))

        # Sum up total ZAR exposure across all detected events for the report header
        total_exposure = sum(e.total_client_exposure_zar for e in events)

        return CurrencyEventReport(
            events=events,
            total_market_exposure_zar=total_exposure,
        )

    # ------------------------------------------------------------------
    # Event detectors
    # ------------------------------------------------------------------

    def _detect_rate_shock(
        self,
        pair: str,
        country: str,
        tick: Dict,
        prior: Dict,
        exposure: float,
    ) -> Optional[CurrencyEvent]:
        """
        Detect a rate shock: single-session move exceeding 2× normal daily vol.

        CRITICAL is triggered at 5× normal vol (exceptional move, likely news-driven).
        HIGH is triggered at 2–5× normal vol (significant but not unprecedented).

        Hedging revenue opportunity is estimated at 50% of the move × exposure,
        reflecting typical client urgency to hedge after a large dislocation.

        :param pair: Currency pair string e.g. 'NGN/ZAR'
        :param country: ISO-2 country code
        :param tick: Current rate tick dict
        :param prior: Prior period rate tick dict (may be empty)
        :param exposure: Aggregate client ZAR exposure for this pair
        :return: CurrencyEvent or None if no shock detected
        """
        # Cannot compute a move without prior data; skip silently
        if not prior:
            return None

        current = tick.get("mid_rate", 0)
        previous = prior.get("mid_rate", current)
        if not previous:
            return None  # Guard against zero-division

        # Percentage move (absolute, direction resolved separately)
        move = abs(current - previous) / previous

        # Normalise the pair key to look up its baseline vol (strip slashes/spaces)
        pair_key = pair.replace("/", "").replace(" ", "")
        normal_vol = _NORMAL_DAILY_VOL.get(pair_key, 0.010)  # Default 1% if unknown pair

        # The shock threshold is 2× the currency's normal daily vol
        if move < 2 * normal_vol:
            return None  # Move is within normal range; not a shock

        # Determine direction for the human-readable headline
        direction = "weakened" if current > previous else "strengthened"

        # Severity: CRITICAL if move is >5× normal vol; otherwise HIGH
        severity = "CRITICAL" if move > 5 * normal_vol else "HIGH"

        # Estimated hedging revenue: 50% of clients are expected to act on a shock
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
            # Estimate affected clients: one per R5m of exposure (rough heuristic)
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
        """
        Detect a parallel market collapse: official rate and parallel rate
        diverge beyond the country-specific regulatory threshold.

        Relevant for NG, EG, ZW, ET, AO where dual exchange rate systems
        create significant cross-border payment and invoice financing risk.

        CRITICAL: premium > 2× threshold (severe divergence, likely policy crisis)
        HIGH:     premium between threshold and 2× threshold

        :param pair: Currency pair string
        :param country: ISO-2 country code used to look up threshold
        :param tick: Current rate tick dict (must include 'parallel_rate')
        :param exposure: Aggregate client ZAR exposure for this pair
        :return: CurrencyEvent or None
        """
        # Only countries with a defined threshold are monitored for parallel collapse
        threshold = _PARALLEL_THRESHOLD.get(country)
        if not threshold:
            return None  # Country not in the parallel market watch list

        official = tick.get("mid_rate", 0)
        parallel = tick.get("parallel_rate")
        if not parallel or not official:
            return None  # Missing data; skip rather than raise a false alert

        # Percentage divergence between parallel and official rate
        premium = abs(parallel - official) / official

        # Only alert if premium exceeds the regulatory tolerance threshold
        if premium < threshold:
            return None

        # Double the threshold indicates a severe policy/governance crisis
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
            # One affected client per R10m of exposure (lower density than rate shock)
            affected_client_count=max(1, int(exposure / 10_000_000)),
            total_client_exposure_zar=exposure,
            # Conservative 0.5% fee opportunity on the at-risk exposure
            hedging_revenue_opportunity_zar=exposure * 0.005,
        )

    def _detect_illiquidity(
        self,
        pair: str,
        country: str,
        tick: Dict,
        exposure: float,
    ) -> Optional[CurrencyEvent]:
        """
        Detect corridor illiquidity: bid-ask spread has widened to 5× or more
        of the 20bp benchmark spread for liquid African pairs.

        Wide spreads indicate liquidity providers are pulling back, often a
        leading indicator of a larger move or market closure. Clients with
        urgent payment requirements face significant slippage.

        Severity is always HIGH (widened spread = execution risk for clients).

        :param pair: Currency pair string
        :param country: ISO-2 country code
        :param tick: Rate tick dict (must contain bid_rate, ask_rate, mid_rate)
        :param exposure: Aggregate client ZAR exposure
        :return: CurrencyEvent or None
        """
        bid = tick.get("bid_rate", 0)
        ask = tick.get("ask_rate", 0)
        mid = tick.get("mid_rate", 0)

        # All three prices are required; guard against partial data
        if not mid or not bid or not ask:
            return None

        # Spread as a fraction of mid — standard measure of market liquidity
        spread = (ask - bid) / mid

        # 20bp (0.002) is the benchmark normal spread for liquid African pairs.
        # At 5× this level (100bp), the market is considered illiquid.
        normal_spread = 0.002   # 20bp is normal for liquid African pairs

        if spread < normal_spread * 5:
            return None  # Spread within acceptable range

        return CurrencyEvent(
            event_id=f"EVT-ILLIQ-{pair.replace('/', '')}-{datetime.now().strftime('%H%M')}",
            event_type="CORRIDOR_ILLIQUID",
            currency_pair=pair,
            country=country,
            severity="HIGH",  # Illiquidity is always HIGH; never CRITICAL (not a directional move)
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
            # Estimate one affected client per R8m of exposure
            affected_client_count=max(1, int(exposure / 8_000_000)),
            total_client_exposure_zar=exposure,
            # Revenue opportunity: 30% of the widened spread applied to exposure
            # (clients will pay the spread premium to execute through the bank)
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
        """
        Detect a swap points spike: the 3-month forward points have moved more
        than 50% from the prior period.

        Swap points embed the interest rate differential between two currencies.
        A sudden spike signals a change in funding conditions, rate expectations,
        or a breakdown in covered interest parity. Severity is MEDIUM as this is
        typically a medium-term signal rather than an immediate execution risk.

        :param pair: Currency pair string
        :param country: ISO-2 country code
        :param tick: Current rate tick including 'swap_points_3m'
        :param prior: Prior period tick for comparison
        :param exposure: Aggregate client ZAR exposure
        :return: CurrencyEvent or None
        """
        current_swap = tick.get("swap_points_3m", 0)
        # Fall back to current if prior swap is not available
        prior_swap = prior.get("swap_points_3m", current_swap)

        # Cannot compute change if prior is zero (avoids division by zero)
        if not prior_swap or prior_swap == 0:
            return None

        # Absolute percentage change in swap points
        change = abs(current_swap - prior_swap) / abs(prior_swap)

        # 50% change threshold: only material moves warrant an alert
        if change < 0.50:   # Less than 50% change
            return None

        return CurrencyEvent(
            event_id=f"EVT-SWAP-{pair.replace('/', '')}-{datetime.now().strftime('%H%M')}",
            event_type="SWAP_POINTS_SPIKE",
            currency_pair=pair,
            country=country,
            severity="MEDIUM",  # Swap spikes are medium severity — monitoring signal, not crisis
            headline=(
                f"{pair} 3m swap points moved {change*100:.0f}%"
            ),
            market_commentary=(
                f"{pair} 3-month swap points changed {change*100:.0f}% "
                f"from {prior_swap:.1f} to {current_swap:.1f}. "
                f"This signals a change in funding conditions or "
                f"interest rate expectations for {country}."
            ),
            # Estimate one affected client per R15m (swap moves affect fewer clients)
            affected_client_count=max(1, int(exposure / 15_000_000)),
            total_client_exposure_zar=exposure,
            # Conservative 0.2% revenue estimate — swap spikes create repricing discussions
            hedging_revenue_opportunity_zar=exposure * 0.002,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _country_from_pair(self, pair: str) -> str:
        """
        Extract the ISO-2 country code from a currency pair string.

        Handles both slash-separated ('NGN/ZAR') and concatenated ('NGAZAR')
        formats by reading the first three characters as the base currency code.

        :param pair: Currency pair string e.g. 'NGN/ZAR' or 'NGAZAR'
        :return: Two-letter ISO country code e.g. 'NG'
        """
        if not pair:
            return "??"

        # Mapping of ISO-4217 currency codes to ISO-3166-1 alpha-2 country codes
        # Used to derive country context from the base currency of a pair
        _CURRENCY_TO_COUNTRY = {
            "NGN": "NG",   # Nigeria
            "KES": "KE",   # Kenya
            "GHS": "GH",   # Ghana
            "TZS": "TZ",   # Tanzania
            "UGX": "UG",   # Uganda
            "ZMW": "ZM",   # Zambia
            "ZWL": "ZW",   # Zimbabwe
            "MZE": "MZ",   # Mozambique
            "BWP": "BW",   # Botswana
            "NAD": "NA",   # Namibia
            "ETB": "ET",   # Ethiopia
            "XOF": "CI",   # WACU CFA — Côte d'Ivoire as proxy country
            "CIF": "CI",   # Alternative CFA code used in some feeds
            "XAF": "CM",   # Central African CFA — Cameroon as proxy
            "AOA": "AO",   # Angola
            "MGA": "MG",   # Madagascar
            "RWF": "RW",   # Rwanda
            "MUR": "MU",   # Mauritius
            "EGP": "EG",   # Egypt
            "MWK": "MW",   # Malawi
        }

        # Extract base currency: 'NGN' from 'NGN/ZAR', or first 3 chars from 'NGAZAR'
        currency = pair.split("/")[0] if "/" in pair else pair[:3].upper()
        return _CURRENCY_TO_COUNTRY.get(currency, currency[:2])
