"""
Kafka Producer for Cell Domain Ingestion

Usage:
    from afriflow.domains.cell.ingestion.kafka_producer import CellKafkaProducer, KafkaConfig

    cfg = KafkaConfig.from_env()
    producer = CellKafkaProducer(cfg)
    producer.batch_send(
        topic="cell.airtime.topups",
        records=[{"topup_id": "AIR-001", "country": "KE"}],
    )
    producer.flush()
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Iterable, List, Optional, Tuple

from afriflow.logging_config import get_logger

try:
    from confluent_kafka import Producer, KafkaException
except Exception:  # pragma: no cover
    Producer = None
    KafkaException = Exception

try:
    from fastavro import writer as avro_writer, parse_schema
    from io import BytesIO
except Exception:  # pragma: no cover
    avro_writer = None
    parse_schema = None
    BytesIO = None


def _setup_rotating_logger(name: str) -> Any:
    logger = get_logger(name)
    log_file = os.environ.get("AF_CELL_KAFKA_LOG_FILE", "logs/cell_kafka_producer.log")
    max_bytes = int(os.environ.get("AF_CELL_KAFKA_LOG_MAX_BYTES", "1048576"))
    backup_count = int(os.environ.get("AF_CELL_KAFKA_LOG_BACKUP_COUNT", "5"))
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("AF_CELL_KAFKA_LOG_LEVEL", "INFO"))
    return logger


@dataclass
class KafkaConfig:
    bootstrap_servers: str
    acks: str = "all"
    batch_size: int = 1000
    linger_ms: int = 5
    max_inflight: int = 5
    delivery_timeout_ms: int = 120000
    retries: int = 3
    retry_backoff_ms: int = 250
    security_protocol: Optional[str] = None
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    client_id: str = "afriflow-cell-producer"

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        return cls(
            bootstrap_servers=os.environ.get("AF_CELL_KAFKA_BOOTSTRAP", "localhost:9092"),
            acks=os.environ.get("AF_CELL_KAFKA_ACKS", "all"),
            batch_size=int(os.environ.get("AF_CELL_KAFKA_BATCH_SIZE", "1000")),
            linger_ms=int(os.environ.get("AF_CELL_KAFKA_LINGER_MS", "5")),
            max_inflight=int(os.environ.get("AF_CELL_KAFKA_MAX_INFLIGHT", "5")),
            delivery_timeout_ms=int(os.environ.get("AF_CELL_KAFKA_DELIVERY_TIMEOUT_MS", "120000")),
            retries=int(os.environ.get("AF_CELL_KAFKA_RETRIES", "3")),
            retry_backoff_ms=int(os.environ.get("AF_CELL_KAFKA_RETRY_BACKOFF_MS", "250")),
            security_protocol=os.environ.get("AF_CELL_KAFKA_SECURITY_PROTOCOL"),
            sasl_mechanism=os.environ.get("AF_CELL_KAFKA_SASL_MECHANISM"),
            sasl_username=os.environ.get("AF_CELL_KAFKA_SASL_USERNAME"),
            sasl_password=os.environ.get("AF_CELL_KAFKA_SASL_PASSWORD"),
            client_id=os.environ.get("AF_CELL_KAFKA_CLIENT_ID", "afriflow-cell-producer"),
        )

    def to_producer_config(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "acks": self.acks,
            "batch.size": self.batch_size,
            "linger.ms": self.linger_ms,
            "max.in.flight.requests.per.connection": self.max_inflight,
            "delivery.timeout.ms": self.delivery_timeout_ms,
            "client.id": self.client_id,
            "enable.idempotence": True,
            "retries": self.retries,
            "retry.backoff.ms": self.retry_backoff_ms,
        }
        if self.security_protocol:
            cfg["security.protocol"] = self.security_protocol
        if self.sasl_mechanism:
            cfg["sasl.mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            cfg["sasl.username"] = self.sasl_username
        if self.sasl_password:
            cfg["sasl.password"] = self.sasl_password
        return cfg


class CellKafkaProducer:
    def __init__(self, config: KafkaConfig) -> None:
        self.config = config
        self._logger = _setup_rotating_logger(__name__)
        self._pool_lock = threading.Lock()
        self._producer: Optional[Any] = None
        self._failed: List[Tuple[str, bytes, Optional[str]]] = []

    def _get_producer(self) -> Any:
        with self._pool_lock:
            if self._producer is None:
                if Producer is None:
                    raise RuntimeError("confluent_kafka not available")
                self._producer = Producer(self.config.to_producer_config())
            return self._producer

    def serialize(self, record: Dict[str, Any], avro_schema: Optional[Dict[str, Any]] = None) -> bytes:
        if avro_schema and avro_writer and parse_schema and BytesIO:
            parsed = parse_schema(avro_schema)
            buf = BytesIO()
            avro_writer(buf, parsed, [record])
            return buf.getvalue()
        return json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def _delivery_cb(self, err, msg) -> None:
        if err is not None:
            self._logger.error("kafka_delivery_error", extra={"error": str(err), "topic": msg.topic(), "partition": msg.partition()})
            key = msg.key().decode("utf-8") if msg.key() else None
            self._failed.append((msg.topic(), msg.value(), key))
        else:
            self._logger.debug("kafka_delivery_ok", extra={"topic": msg.topic(), "partition": msg.partition(), "offset": msg.offset()})

    def send(self, topic: str, record: Dict[str, Any], key: Optional[str] = None, avro_schema: Optional[Dict[str, Any]] = None) -> None:
        payload = self.serialize(record, avro_schema=avro_schema)
        try:
            producer = self._get_producer()
            producer.produce(topic=topic, key=key.encode("utf-8") if key else None, value=payload, on_delivery=self._delivery_cb)
            producer.poll(0)
        except KafkaException as e:
            self._logger.error("kafka_produce_exception", extra={"error": str(e)})
            self._failed.append((topic, payload, key))
        except Exception as e:
            self._logger.error("kafka_produce_unexpected", extra={"error": str(e)})
            self._failed.append((topic, payload, key))

    def batch_send(self, topic: str, records: Iterable[Dict[str, Any]], key_fn: Optional[Any] = None, avro_schema: Optional[Dict[str, Any]] = None) -> None:
        batch: List[Dict[str, Any]] = []
        for rec in records:
            batch.append(rec)
            if len(batch) >= self.config.batch_size:
                for r in batch:
                    key = key_fn(r) if key_fn else None
                    self.send(topic, r, key=key, avro_schema=avro_schema)
                batch.clear()
        for r in batch:
            key = key_fn(r) if key_fn else None
            self.send(topic, r, key=key, avro_schema=avro_schema)
        self._retry_failed()

    def _retry_failed(self) -> None:
        if not self._failed:
            return
        tries = 0
        while self._failed and tries < max(1, self.config.retries):
            pending = list(self._failed)
            self._failed.clear()
            backoff = (self.config.retry_backoff_ms / 1000.0) * (2 ** tries)
            time.sleep(backoff)
            for topic, payload, key in pending:
                try:
                    producer = self._get_producer()
                    producer.produce(topic=topic, key=key.encode("utf-8") if key else None, value=payload, on_delivery=self._delivery_cb)
                    producer.poll(0)
                except Exception as e:
                    self._logger.error("kafka_retry_error", extra={"error": str(e), "topic": topic})
                    self._failed.append((topic, payload, key))
            tries += 1
        if self._failed:
            self._logger.error("kafka_failed_records_exhausted", extra={"count": len(self._failed)})

    def flush(self, timeout: float = 10.0) -> None:
        if self._producer:
            self._producer.flush(timeout)
