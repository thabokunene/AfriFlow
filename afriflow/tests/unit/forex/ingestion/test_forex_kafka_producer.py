from __future__ import annotations

import json
import pytest
from itertools import product

from afriflow.domains.forex.ingestion.kafka_producer import (
    ForexKafkaProducer,
    ValidationError,
    KafkaProducerError,
)


class DummyFuture:
    def __init__(self, topic: str):
        self._topic = topic

    def get(self, timeout: float):
        return type(
            "RM",
            (),
            {
                "topic": self._topic,
                "partition": 0,
                "offset": 1,
            },
        )()


class DummyKafkaProducer:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.sent = []
        self.fail_send = False

    def send(self, topic: str, key, value):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent.append((topic, key, json.dumps(value)))
        return DummyFuture(topic)

    def flush(self):
        return 0

    def close(self):
        return 0


def valid_trade():
    return {
        "trade_id": "FX-ABCDEFGHIJ",
        "currency_pair": "USD/ZAR",
        "trade_type": "SPOT",
        "direction": "BUY",
        "base_amount": 1000.0,
        "quote_amount": 18500.0,
        "rate": 18.5,
        "trade_date": "2026-03-01",
        "value_date": "2026-03-03",
        "client_id": "CLIENT-1",
        "status": "PENDING",
    }


def valid_tick():
    return {
        "tick_id": "TICK-001",
        "currency_pair": "USD/ZAR",
        "mid_rate": 18.50,
        "bid_rate": 18.49,
        "ask_rate": 18.51,
        "tick_timestamp": "2026-03-01T12:00:00Z",
    }


def valid_hedge():
    return {
        "hedge_id": "HEDGE-1234567890",
        "client_id": "CLIENT-1",
        "currency_pair": "USD/ZAR",
        "hedge_type": "FORWARD",
        "notional_base": 100000.0,
        "strike_rate": 18.0,
        "inception_date": "2026-02-01",
        "maturity_date": "2026-06-01",
    }


def test_init_valid():
    p = ForexKafkaProducer(topic="forex.trades", bootstrap_servers="localhost:9092")
    assert p.topic == "forex.trades"
    assert p.bootstrap_servers == "localhost:9092"
    assert p.producer is None


def test_init_invalid():
    with pytest.raises(ValueError):
        ForexKafkaProducer(topic="", bootstrap_servers="localhost:9092")
    with pytest.raises(ValueError):
        ForexKafkaProducer(topic="forex.trades", bootstrap_servers="")


def test_connect_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: (_ for _ in ()).throw(ImportError()) if name == "kafka" else __import__(name, *args, **kwargs))
    p = ForexKafkaProducer()
    p.connect()
    assert p.producer is None


def test_connect_real(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    assert isinstance(p.producer, DummyKafkaProducer)


def test_send_trade_validation_error():
    p = ForexKafkaProducer()
    with pytest.raises(ValidationError):
        p.send_trade({"bad": "trade"})


def test_send_trade_mock():
    p = ForexKafkaProducer()
    p.send_trade(valid_trade())


def test_send_trade_real_success(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    p.send_trade(valid_trade(), key="FX-ABCDEFGHIJ")
    assert len(p.producer.sent) == 1


def test_send_tick_and_hedge(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer(topic="forex.rate_ticks")
    p.connect()
    p.send_rate_tick(valid_tick(), key="TICK-001")
    p.topic = "forex.hedges"
    p.send_hedge(valid_hedge(), key="HEDGE-1234567890")
    assert len(p.producer.sent) == 2


def test_send_batch_mixed(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    good = valid_trade()
    bad = dict(good)
    del bad["currency_pair"]
    sent = p.send_batch([good, bad, good], record_type="trade")
    assert sent == 2


def test_close(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    p.close()


@pytest.mark.parametrize(
    "trade_type,currency_pair,base_amount,rate,status",
    [
        ("SPOT", "USD/ZAR", 1000.0, 18.5, "PENDING"),
        ("FORWARD", "EUR/NGN", 5000.0, 1200.0, "SETTLED"),
        ("SWAP", "GBP/ZAR", 2500.0, 23.0, "FAILED"),
        ("OPTION", "USD/ZMW", 1500.0, 20.1, "CANCELLED"),
        ("SPOT", "USD/ZAR", 0.01, 0.0001, "PENDING"),  # boundary amounts/rates
    ],
)
def test_param_batch_trade_types(monkeypatch: pytest.MonkeyPatch, trade_type, currency_pair, base_amount, rate, status):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t["trade_type"] = trade_type
    t["currency_pair"] = currency_pair
    t["base_amount"] = max(base_amount, 0.01)
    t["rate"] = max(rate, 0.0001)
    t["status"] = status if status in {"PENDING", "SETTLED", "FAILED", "CANCELLED"} else "PENDING"
    sent = p.send_batch([t], record_type="trade")
    assert sent == 1


@pytest.mark.parametrize(
    "currency_pair,dates,notional",
    [
        ("USD/ZAR", ("2026-03-01", "2026-03-03"), 1000.0),
        ("EUR/NGN", ("2026-04-10", "2026-04-20"), 50000.0),
        ("GBP/ZAR", ("2026-05-15", "2026-05-25"), 250000.0),
    ],
)
def test_trade_matrix(monkeypatch: pytest.MonkeyPatch, currency_pair, dates, notional):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t["currency_pair"] = currency_pair
    t["trade_date"] = dates[0]
    t["value_date"] = dates[1]
    t["base_amount"] = notional
    assert p.send_batch([t], record_type="trade") == 1


@pytest.mark.parametrize("bad_field", ["currency_pair", "trade_type", "direction", "base_amount", "rate", "status"])
def test_trade_edge_cases_nulls(monkeypatch: pytest.MonkeyPatch, bad_field):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t[bad_field] = None
    sent = p.send_batch([t], record_type="trade")
    assert sent == 0


def test_invalid_trade_type(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t["trade_type"] = "NDF"
    assert p.send_batch([t], record_type="trade") == 0


def test_invalid_direction(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t["direction"] = "HOLD"
    assert p.send_batch([t], record_type="trade") == 0


def test_invalid_amount_and_rate(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t["base_amount"] = -1
    t["rate"] = 0
    assert p.send_batch([t], record_type="trade") == 0


def test_invalid_status(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    t = valid_trade()
    t["status"] = "UNKNOWN"
    assert p.send_batch([t], record_type="trade") == 0


def test_tick_invalid_relationship(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer(topic="forex.rate_ticks")
    p.connect()
    tick = valid_tick()
    tick["bid_rate"] = 20.0
    tick["mid_rate"] = 19.0
    tick["ask_rate"] = 18.0
    assert p.send_batch([tick], record_type="rate_tick") == 0


def test_hedge_invalid_type(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer(topic="forex.hedges")
    p.connect()
    hedge = valid_hedge()
    hedge["hedge_type"] = "BADTYPE"
    assert p.send_batch([hedge], record_type="hedge") == 0


def test_unknown_record_type_raises():
    p = ForexKafkaProducer()
    with pytest.raises(ValueError):
        p.send_batch([valid_trade()], record_type="unknown")


def test_send_failure_paths(monkeypatch: pytest.MonkeyPatch):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer()
    p.connect()
    assert isinstance(p.producer, DummyKafkaProducer)
    p.producer.fail_send = True
    with pytest.raises(KafkaProducerError):
        p.send_trade(valid_trade())
    with pytest.raises(KafkaProducerError):
        p.send_rate_tick(valid_tick())
    with pytest.raises(KafkaProducerError):
        p.send_hedge(valid_hedge())


@pytest.mark.parametrize(
    "hedge_type,currency_pair,notional,strike",
    [
        ("FORWARD", "USD/ZAR", 1000.0, 18.5),
        ("OPTION_CALL", "EUR/NGN", 50000.0, 1200.0),
        ("OPTION_PUT", "GBP/ZAR", 2500.0, 23.0),
        ("SWAP", "USD/ZMW", 1500.0, 20.1),
        ("COLLAR", "USD/ZAR", 0.01, 0.0001),  # boundary values
    ],
)
def test_param_batch_hedge_types(monkeypatch: pytest.MonkeyPatch, hedge_type, currency_pair, notional, strike):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer(topic="forex.hedges")
    p.connect()
    h = valid_hedge()
    h["hedge_type"] = hedge_type
    h["currency_pair"] = currency_pair
    h["notional_base"] = max(notional, 0.01)
    h["strike_rate"] = max(strike, 0.0001)
    assert p.send_batch([h], record_type="hedge") == 1


@pytest.mark.parametrize(
    "currency_pair,mid,bid,ask",
    [
        ("USD/ZAR", 18.50, 18.49, 18.51),
        ("EUR/NGN", 1200.0, 1199.0, 1201.0),
        ("GBP/ZAR", 23.0, 22.99, 23.01),
    ],
)
def test_param_batch_rate_ticks(monkeypatch: pytest.MonkeyPatch, currency_pair, mid, bid, ask):
    orig_import = __import__
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})()
        if name == "kafka"
        else orig_import(name, *args, **kwargs),
    )
    p = ForexKafkaProducer(topic="forex.rate_ticks")
    p.connect()
    tick = valid_tick()
    tick["currency_pair"] = currency_pair
    tick["mid_rate"] = mid
    tick["bid_rate"] = bid
    tick["ask_rate"] = ask
    assert p.send_batch([tick], record_type="rate_tick") == 1
