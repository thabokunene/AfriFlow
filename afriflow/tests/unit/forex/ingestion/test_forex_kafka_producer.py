from __future__ import annotations

import json
import pytest

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
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
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
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = ForexKafkaProducer()
    p.connect()
    p.send_trade(valid_trade(), key="FX-ABCDEFGHIJ")
    assert len(p.producer.sent) == 1


def test_send_tick_and_hedge(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = ForexKafkaProducer(topic="forex.rate_ticks")
    p.connect()
    p.send_rate_tick(valid_tick(), key="TICK-001")
    p.topic = "forex.hedges"
    p.send_hedge(valid_hedge(), key="HEDGE-1234567890")
    assert len(p.producer.sent) == 2


def test_send_batch_mixed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = ForexKafkaProducer()
    p.connect()
    good = valid_trade()
    bad = dict(good)
    del bad["currency_pair"]
    sent = p.send_batch([good, bad, good], record_type="trade")
    assert sent == 2


def test_close(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = ForexKafkaProducer()
    p.connect()
    p.close()
