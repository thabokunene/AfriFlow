from __future__ import annotations

import json
from typing import Any

import pytest

from afriflow.domains.cib.ingestion.kafka_producer import (
    CIBKafkaProducer,
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
    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs
        self.sent = []
        self.fail_send = False

    def send(self, topic: str, key: str | None, value: dict):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent.append((topic, key, json.dumps(value)))
        return DummyFuture(topic)

    def flush(self):
        return 0


def _valid_payment():
    return {
        "transaction_id": "TX123",
        "timestamp": "2026-03-01T12:00:00Z",
        "amount": 100.5,
        "currency": "USD",
        "sender_name": "ABC Ltd",
        "sender_country": "ZA",
        "beneficiary_name": "XYZ Ltd",
        "beneficiary_country": "NG",
        "status": "COMPLETED",
        "purpose_code": "CORT",
        "corridor": "ZA-NG",
    }


def test_init_valid():
    p = CIBKafkaProducer(topic="cib.payments.v1", bootstrap_servers="localhost:9092")
    assert p.topic == "cib.payments.v1"
    assert p.bootstrap_servers == "localhost:9092"
    assert p.producer is None


def test_init_invalid():
    with pytest.raises(ValueError):
        CIBKafkaProducer(topic="", bootstrap_servers="localhost:9092")
    with pytest.raises(ValueError):
        CIBKafkaProducer(topic="cib", bootstrap_servers="")


def test_connect_mock_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: (_ for _ in ()).throw(ImportError()) if name == "kafka" else __import__(name, *args, **kwargs))
    p = CIBKafkaProducer()
    p.connect()
    assert p.producer is None


def test_connect_real(monkeypatch: pytest.MonkeyPatch):
    class DummyKProd(DummyKafkaProducer):
        pass

    def fake_import(name, *args, **kwargs):
        if name == "kafka":
            return type("K", (), {"KafkaProducer": DummyKProd})()
        return __import__(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    p = CIBKafkaProducer()
    p.connect()
    assert isinstance(p.producer, DummyKafkaProducer)
    assert callable(p.producer.send)


def test_send_payment_validation_error():
    p = CIBKafkaProducer()
    with pytest.raises(ValidationError):
        p.send_payment({"bad": "data"})


def test_send_payment_mock_send():
    p = CIBKafkaProducer()
    p.send_payment(_valid_payment())


def test_send_payment_real_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = CIBKafkaProducer()
    p.connect()
    pm = _valid_payment()
    p.send_payment(pm, key="TX123")
    assert len(p.producer.sent) == 1


def test_send_payment_real_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = CIBKafkaProducer()
    p.connect()
    p.producer.fail_send = True
    with pytest.raises(KafkaProducerError):
        p.send_payment(_valid_payment())


def test_send_batch_mixed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs: type("K", (), {"KafkaProducer": DummyKafkaProducer})() if name == "kafka" else __import__(name, *args, **kwargs))
    p = CIBKafkaProducer()
    p.connect()
    good = _valid_payment()
    bad = dict(good)
    del bad["currency"]
    p.send_batch([good, bad, good])
    assert len(p.producer.sent) == 2
