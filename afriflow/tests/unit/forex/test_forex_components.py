"""
Unit tests for forex domain processors and simulators.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from afriflow.domains.forex.processing.flink.hedge_gap_detector import (
    Processor as HedgeGapDetector,
)
from afriflow.domains.forex.processing.flink.parallel_market_monitor import (
    Processor as ParallelMarketMonitor,
)
from afriflow.domains.forex.processing.flink.rate_anomaly_detector import (
    Processor as RateAnomalyDetector,
)
from afriflow.domains.forex.simulator.fx_trade_generator import (
    AFRICAN_CURRENCY_PAIRS,
    FXTrade,
    FXTradeGenerator,
)
from afriflow.domains.forex.simulator.hedging_simulator import (
    HedgeInstrument,
    HedgingSimulator,
)
from afriflow.domains.forex.simulator.liquidity_provider_simulator import (
    LiquidityProviderSimulator,
    LiquidityQuote,
)
from afriflow.domains.forex.simulator.order_book_simulator import (
    OrderBookLevel,
    OrderBookSimulator,
)
from afriflow.domains.forex.simulator.rate_feed_generator import RateFeedGenerator, RateTick
from afriflow.domains.forex.simulator.volatility_spike_generator import (
    VolatilitySpike,
    VolatilitySpikeGenerator,
)
from afriflow.domains.shared.interfaces import BaseProcessor, SimulatorBase


def _iso_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TestForexProcessors:
    def test_rate_anomaly_detector_rbac_and_anomaly(self) -> None:
        detector = RateAnomalyDetector()
        assert isinstance(detector, BaseProcessor)
        detector.configure()

        base = {
            "access_role": "analyst",
            "source": "unit_test",
            "currency_pair": "USD/ZAR",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for i in range(12):
            record = dict(base)
            record["rate"] = 18.0 + (i * 0.001)
            out = detector.process_sync(record)
            assert out["processed"] is True

        outlier = dict(base)
        outlier["rate"] = 30.0
        out = detector.process_sync(outlier)
        assert out["processed"] is True
        assert out["zscore"] is not None
        assert out["anomaly_type"] != "insufficient_history"
        assert isinstance(out["is_anomaly"], bool)

    def test_hedge_gap_detector_gap_status(self) -> None:
        detector = HedgeGapDetector()
        assert isinstance(detector, BaseProcessor)
        detector.configure()

        record = {
            "access_role": "analyst",
            "source": "unit_test",
            "hedge_id": "HEDGE-001",
            "client_id": "CLIENT-001",
            "currency_pair": "USD/ZAR",
            "notional_base": 100.0,
            "underlying_exposure_id": "EXP-001",
            "exposure_notional": 150.0,
        }
        out = detector.process_sync(record)
        assert out["processed"] is True
        assert out["hedge_gap_pct"] > 0
        assert out["gap_status"] in {"acceptable", "moderate_gap", "significant_gap", "perfect_hedge"}

    def test_parallel_market_monitor_premium(self) -> None:
        monitor = ParallelMarketMonitor()
        assert isinstance(monitor, BaseProcessor)
        monitor.configure()

        record = {
            "access_role": "analyst",
            "source": "unit_test",
            "currency": "NGN",
            "official_rate": 450.0,
            "parallel_rate": 650.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        out = monitor.process_sync(record)
        assert out["processed"] is True
        assert out["parallel_premium_pct"] > 0
        assert out["premium_level"] in {"minimal", "low", "moderate", "high", "critical"}


class TestForexSimulators:
    def test_fx_trade_generator(self) -> None:
        gen = FXTradeGenerator()
        assert isinstance(gen, SimulatorBase)

        trade = gen.generate_one(pair="USD/ZAR")
        assert isinstance(trade, FXTrade)
        assert trade.currency_pair == "USD/ZAR"
        assert trade.trade_type in {"spot", "forward", "swap", "option", "ndf"}
        assert trade.direction in {"buy_usd", "sell_usd"}
        assert trade.notional_usd > 0
        assert trade.rate > 0
        assert _iso_to_dt(trade.traded_at).tzinfo == timezone.utc
        assert _iso_to_dt(trade.ingested_at).tzinfo == timezone.utc

        trades = list(gen.stream(count=3, pair="USD/ZAR"))
        assert len(trades) == 3
        assert all(isinstance(t, FXTrade) for t in trades)

        with pytest.raises(ValueError):
            gen.validate_input(pair="INVALID/PAIR")

    def test_rate_feed_generator_ticks(self) -> None:
        gen = RateFeedGenerator(seed=42)
        tick = gen.next_tick("ZAR", interval_seconds=60)
        assert isinstance(tick, RateTick)
        assert tick.currency_pair == "ZAR/USD"
        assert tick.bid_rate < tick.ask_rate
        assert _iso_to_dt(tick.tick_timestamp).tzinfo == timezone.utc

        ticks = list(gen.stream_ticks("ZAR", hours=1, interval_seconds=600))
        assert len(ticks) == 6
        assert all(isinstance(t, RateTick) for t in ticks)
        scen = gen.generate_devaluation_scenario("NGN", magnitude_pct=22.0, pre_event_ticks=5, post_event_ticks=10)
        assert len(scen.ticks) == 16
        snap = gen.batch_snapshot(["ZAR", "NGN"])
        assert len(snap) == 2
        scen2 = gen.generate_capital_control_scenario("ETB", restriction_ticks=5)
        assert len(scen2.ticks) == 5

    def test_volatility_spike_generator(self) -> None:
        gen = VolatilitySpikeGenerator(seed=42)
        assert isinstance(gen, SimulatorBase)

        spike = gen.generate_one(currency_pair="USD/ZAR")
        assert isinstance(spike, VolatilitySpike)
        assert spike.currency_pair == "USD/ZAR"
        assert spike.base_vol > 0
        assert spike.spike_vol >= spike.base_vol
        assert spike.timestamp.tzinfo == timezone.utc

        spikes = list(gen.stream(count=3, currency_pair="USD/ZAR"))
        assert len(spikes) == 3

        with pytest.raises(ValueError):
            gen.validate_input(currency_pair="USD/XXX")

    def test_liquidity_provider_simulator(self) -> None:
        gen = LiquidityProviderSimulator(seed=42)
        assert isinstance(gen, SimulatorBase)

        quote = gen.generate_one(currency_pair="USD/ZAR")
        assert isinstance(quote, LiquidityQuote)
        assert quote.currency_pair == "USD/ZAR"
        assert quote.bid < quote.ask
        assert quote.timestamp.tzinfo == timezone.utc

        quotes = list(gen.stream(count=3, currency_pair="USD/ZAR"))
        assert len(quotes) == 3

        with pytest.raises(ValueError):
            gen.validate_input(currency_pair="USD/XXX")

    def test_order_book_simulator(self) -> None:
        gen = OrderBookSimulator(seed=42)
        assert isinstance(gen, SimulatorBase)

        level = gen.generate_one(currency_pair="USD/ZAR", side="bid")
        assert isinstance(level, OrderBookLevel)
        assert level.currency_pair == "USD/ZAR"
        assert level.side == "bid"
        assert level.size_musd > 0
        assert level.timestamp.tzinfo == timezone.utc

        snapshot = gen.generate_snapshot(currency_pair="USD/ZAR", levels=3)
        assert len(snapshot) == 6
        assert all(isinstance(l, OrderBookLevel) for l in snapshot)

        with pytest.raises(ValueError):
            gen.validate_input(currency_pair="USD/ZAR", side="invalid")

    def test_hedging_simulator(self) -> None:
        gen = HedgingSimulator(seed=42)
        assert isinstance(gen, SimulatorBase)

        hedge = gen.generate_one(currency_pair="USD/ZAR", notional=1000.0, tenor_days=90)
        assert isinstance(hedge, HedgeInstrument)
        assert hedge.currency_pair == "USD/ZAR"
        assert hedge.notional_base > 0
        assert hedge.inception_date.tzinfo == timezone.utc
        assert hedge.maturity_date.tzinfo == timezone.utc
        assert hedge.status in {"ACTIVE", "SETTLED", "TERMINATED", "EXPIRED"}

        hedges = list(gen.stream(count=2, currency_pair="USD/ZAR"))
        assert len(hedges) == 2

        with pytest.raises(ValueError):
            gen.validate_input(currency_pair="USD/ZAR", notional=-1)

    def test_fx_trade_pairs_constant(self) -> None:
        assert "USD/ZAR" in AFRICAN_CURRENCY_PAIRS
