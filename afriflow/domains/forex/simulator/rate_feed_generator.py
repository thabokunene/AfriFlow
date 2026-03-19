"""
@file rate_feed_generator.py
@description Generator for synthetic FX rate ticks, modeling unique African market dynamics such as regime changes, parallel markets, and thin liquidity.
@author Thabo Kunene
@created 2026-03-19
"""

"""
FX Rate Feed Generator

We generate realistic synthetic FX rate ticks for
African currency pairs against USD and ZAR.

African FX markets have distinct characteristics that
Western rate generators do not model:

1. Regime changes: NGN, AOA, ETB have had sudden
   official devaluations that are not gradual.
2. Parallel markets: Official and street rates diverge
   significantly in controlled economies.
3. Commodity correlation: ZMW follows copper, NGN
   follows Brent crude, GHS follows gold.
4. Thin liquidity: Large gaps between ticks during
   off-hours, wider bid-ask spreads.
5. Capital controls: Periods of FX rationing where
   official trades freeze but demand continues.

Disclaimer: This is not a sanctioned Standard Bank
Group project. It is a demonstration of concept,
domain knowledge, and technical skill built by
Thabo Kunene for portfolio purposes. All data is
simulated.
"""

# Random library for stochastic price movements using geometric Brownian motion
import random
# UUID for generating unique tick and record identifiers
import uuid
# Dataclasses for structured representation of rate ticks and market states
from dataclasses import dataclass, field
# Datetime utilities for timestamping generated rate ticks
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Dict, Iterator, List, Optional


# Base rates (approximate mid-market, vs USD).
# These serve as the initial price anchor for the simulation across African markets.
BASE_RATES_VS_USD: Dict[str, float] = {
    "ZAR": 18.50,
    "NGN": 1580.0,
    "KES": 130.0,
    "GHS": 15.5,
    "TZS": 2550.0,
    "UGX": 3750.0,
    "ZMW": 27.5,
    "MZN": 64.0,
    "AOA": 870.0,
    "XOF": 610.0,    # BCEAO – pegged to EUR, very stable
    "XAF": 610.0,    # CFA franc – also EUR-pegged
    "RWF": 1280.0,
    "ETB": 56.0,
    "MWK": 1730.0,
    "BWP": 13.8,
    "NAD": 18.5,     # Pegged 1:1 to ZAR
    "ZWL": 5800.0,   # Zimbabwe – high instability
    "CDF": 2800.0,   # DRC – moderate controls
    "SSP": 1300.0,   # South Sudan – very thin market
}

# Annualised volatility (%) per currency used to scale the random walk.
# Reflects the historical price stability or risk profile of each currency.
ANNUAL_VOLATILITY: Dict[str, float] = {
    "ZAR": 12.0,
    "NGN": 25.0,    # Structural devaluation risk
    "KES": 8.0,
    "GHS": 22.0,    # Recent debt crisis impact
    "TZS": 6.0,
    "UGX": 7.5,
    "ZMW": 18.0,
    "MZN": 14.0,
    "AOA": 20.0,
    "XOF": 3.0,     # EUR-pegged – very low vol
    "XAF": 3.0,
    "RWF": 9.0,
    "ETB": 15.0,
    "MWK": 20.0,
    "BWP": 10.0,
    "NAD": 12.0,
    "ZWL": 85.0,    # Hyperinflation-adjacent
    "CDF": 18.0,
    "SSP": 40.0,
}

# Bid-ask spread as % of mid-price (half-spread each side).
# Widening spreads reflect lower liquidity or higher transactional risk.
BID_ASK_SPREAD_PCT: Dict[str, float] = {
    "ZAR": 0.03,
    "NGN": 0.25,
    "KES": 0.08,
    "GHS": 0.30,
    "TZS": 0.12,
    "UGX": 0.15,
    "ZMW": 0.20,
    "MZN": 0.25,
    "AOA": 0.35,
    "XOF": 0.06,
    "XAF": 0.06,
    "RWF": 0.18,
    "ETB": 0.30,
    "MWK": 0.28,
    "BWP": 0.10,
    "NAD": 0.03,
    "ZWL": 1.50,
    "CDF": 0.40,
    "SSP": 0.80,
}

# Currencies with active parallel markets.
PARALLEL_MARKET_CURRENCIES = {
    "NGN", "AOA", "ETB", "ZWL", "SSP", "CDF"
}


@dataclass
class RateTick:
    """
    A single FX rate observation.

    We record the official mid, bid, ask, and where
    applicable the parallel (street) rate. The parallel
    rate is critical intelligence for clients with
    on-the-ground NGN, AOA, or ETB exposure — it tells
    you what they actually pay for USD in-country.
    """

    tick_id: str
    currency_pair: str          # e.g. "NGN/USD"
    base_currency: str
    quote_currency: str
    mid_rate: float
    bid_rate: float
    ask_rate: float
    parallel_rate: Optional[float]
    parallel_divergence_pct: Optional[float]
    tick_timestamp: str
    source: str
    is_indicative: bool = False  # True when market closed


@dataclass
class RateScenario:
    """
    A simulated FX scenario with a sequence of ticks.

    We use scenarios to test event propagation and
    impact calculations without needing live data.
    """

    scenario_id: str
    currency: str
    scenario_type: str           # NORMAL, STRESS, DEVALUATION
    ticks: List[RateTick] = field(default_factory=list)
    devaluation_event_tick: Optional[int] = None


class RateFeedGenerator:
    """
    We generate realistic synthetic FX rate feeds
    for African currency pairs.

    Usage:

        gen = RateFeedGenerator(seed=42)

        # Stream live-style ticks
        for tick in gen.stream_ticks("NGN", hours=24):
            process(tick)

        # Generate a devaluation scenario
        scenario = gen.generate_devaluation_scenario(
            "NGN", magnitude_pct=22.0
        )

        # Point-in-time snapshot across all currencies
        snapshot = gen.batch_snapshot()
    """

    SECONDS_PER_YEAR = 365.25 * 24 * 3600

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

        # We maintain current rates as mutable state so
        # each tick evolves from the previous one rather
        # than jumping to a fresh random value.
        self._current_rates: Dict[str, float] = dict(
            BASE_RATES_VS_USD
        )
        self._current_parallel: Dict[str, Optional[float]] = {
            ccy: (rate * 1.08 if ccy in PARALLEL_MARKET_CURRENCIES else None)
            for ccy, rate in BASE_RATES_VS_USD.items()
        }

    def next_tick(
        self,
        currency: str,
        interval_seconds: int = 60,
    ) -> RateTick:
        """
        We advance the rate by one tick interval and
        return the resulting RateTick.

        We model FX returns as geometric Brownian
        motion (GBM). For event currencies (ZWL, SSP)
        we add an occasional jump component to simulate
        sudden regime changes.
        """

        vol_annual = ANNUAL_VOLATILITY.get(currency, 12.0)

        # Convert annual vol to per-tick vol using
        # square-root-of-time scaling.
        vol_tick = (
            vol_annual / 100
            * (max(interval_seconds, 1) / self.SECONDS_PER_YEAR) ** 0.5
        )

        shock = random.gauss(0, 1)

        # Occasional jump-diffusion for high-risk currencies
        jump = 0.0
        if currency in {"ZWL", "SSP", "NGN", "AOA"}:
            if random.random() < 0.005:   # 0.5% chance per tick
                jump = random.uniform(0.02, 0.08)

        pct_return = vol_tick * shock + jump

        current = self._current_rates.get(
            currency, BASE_RATES_VS_USD.get(currency, 1.0)
        )
        new_rate = current * (1 + pct_return)
        # Floor at 70% of current to prevent absurd values
        new_rate = max(new_rate, current * 0.70)
        self._current_rates[currency] = new_rate

        # Parallel rate evolves with higher vol and
        # slow mean-reversion toward official rate.
        parallel = None
        parallel_divergence = None
        if currency in PARALLEL_MARKET_CURRENCIES:
            current_par = self._current_parallel.get(currency)
            if current_par is not None:
                par_shock = random.gauss(0, 1)
                par_vol = vol_tick * 1.9
                mean_revert_force = 0.002 * (new_rate - current_par)
                new_par = (
                    current_par * (1 + par_vol * par_shock)
                    + mean_revert_force
                )
                # Parallel rate never goes below official
                new_par = max(new_par, new_rate)
                self._current_parallel[currency] = new_par
                parallel = round(new_par, 4)
                parallel_divergence = round(
                    (new_par - new_rate) / new_rate * 100, 2
                )

        spread_pct = BID_ASK_SPREAD_PCT.get(currency, 0.15)
        half = new_rate * spread_pct / 100

        return RateTick(
            tick_id=f"TICK-{currency}-{uuid.uuid4().hex[:8].upper()}",
            currency_pair=f"{currency}/USD",
            base_currency=currency,
            quote_currency="USD",
            mid_rate=round(new_rate, 4),
            bid_rate=round(new_rate - half, 4),
            ask_rate=round(new_rate + half, 4),
            parallel_rate=parallel,
            parallel_divergence_pct=parallel_divergence,
            tick_timestamp=datetime.now(timezone.utc).isoformat(),
            source="simulated_rate_feed",
            is_indicative=False,
        )

    def stream_ticks(
        self,
        currency: str,
        hours: int = 24,
        interval_seconds: int = 60,
    ) -> Iterator[RateTick]:
        """
        We yield a sequence of rate ticks spanning the
        given number of hours.

        In production this feeds a Kafka producer that
        publishes to the rate_ticks topic. Here we
        yield from GBM simulation.
        """

        total_ticks = int(hours * 3600 / interval_seconds)
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        for i in range(total_ticks):
            tick = self.next_tick(currency, interval_seconds)
            tick.tick_timestamp = (
                start_time
                + timedelta(seconds=i * interval_seconds)
            ).isoformat()
            yield tick

    def generate_devaluation_scenario(
        self,
        currency: str,
        magnitude_pct: float = 20.0,
        pre_event_ticks: int = 100,
        post_event_ticks: int = 200,
    ) -> RateScenario:
        """
        We generate a scenario where the currency
        devalues sharply at a specific tick.

        African devaluations follow a pattern:
        1. Pre-event: Slow depreciation + parallel
           premium widening (market anticipates).
        2. Event: Sudden step-change (official peg
           moved or central bank window closed).
        3. Post-event: Elevated vol, partial recovery
           if devaluation is seen as credible.
        """

        scenario = RateScenario(
            scenario_id=(
                f"SCEN-{currency}-DEVAL"
                f"-{uuid.uuid4().hex[:6].upper()}"
            ),
            currency=currency,
            scenario_type="DEVALUATION",
            devaluation_event_tick=pre_event_ticks,
        )

        # Pre-event: gradual pressure build-up
        for _ in range(pre_event_ticks):
            tick = self.next_tick(currency, 3600)
            scenario.ticks.append(tick)

        # The devaluation itself: instant jump
        pre_rate = self._current_rates[currency]
        post_rate = pre_rate * (1 + magnitude_pct / 100)
        self._current_rates[currency] = post_rate

        if currency in PARALLEL_MARKET_CURRENCIES:
            # After official devaluation, parallel rate
            # typically overshoots then slowly corrects
            self._current_parallel[currency] = post_rate * 1.06

        event_tick = self.next_tick(currency, 3600)
        event_tick.mid_rate = round(post_rate, 4)
        scenario.ticks.append(event_tick)

        # Post-event: elevated vol, gradual stabilisation
        for _ in range(post_event_ticks):
            scenario.ticks.append(
                self.next_tick(currency, 3600)
            )

        return scenario

    def generate_capital_control_scenario(
        self,
        currency: str,
        restriction_ticks: int = 240,
    ) -> RateScenario:
        """
        We simulate a period of capital controls where
        the official market freezes but the parallel
        market continues depreciating.

        This is common in NGN, AOA, and ETB history.
        Official ticks are marked is_indicative=True
        to signal that no real trades are clearing.
        """

        scenario = RateScenario(
            scenario_id=(
                f"SCEN-{currency}-CC"
                f"-{uuid.uuid4().hex[:6].upper()}"
            ),
            currency=currency,
            scenario_type="CAPITAL_CONTROL",
        )

        frozen_official = self._current_rates.get(currency, 1.0)
        self._current_parallel[currency] = frozen_official * 1.25

        for _ in range(restriction_ticks):
            par = self._current_parallel.get(currency)
            if par is not None:
                drift = par * random.uniform(0.0005, 0.003)
                self._current_parallel[currency] = par + drift

            tick = self.next_tick(currency, 3600)
            # Official rate is frozen
            tick.mid_rate = round(frozen_official, 4)
            tick.bid_rate = round(frozen_official, 4)
            tick.ask_rate = round(frozen_official, 4)
            tick.is_indicative = True
            scenario.ticks.append(tick)

        return scenario

    def spot_rate(self, currency: str) -> float:
        """Return the current simulated mid-market rate."""

        return round(
            self._current_rates.get(
                currency,
                BASE_RATES_VS_USD.get(currency, 1.0),
            ),
            4,
        )

    def batch_snapshot(
        self,
        currencies: Optional[List[str]] = None,
    ) -> List[RateTick]:
        """
        We return a single tick per currency — a
        point-in-time rate snapshot.

        Useful for initialising the event propagator
        with a consistent rate base across all pairs.
        """

        if currencies is None:
            currencies = list(BASE_RATES_VS_USD.keys())

        return [self.next_tick(ccy, 60) for ccy in currencies]
