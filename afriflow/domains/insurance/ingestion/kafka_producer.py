"""
Insurance Kafka Producer

This module provides a robust Kafka producer for the Insurance domain,
supporting Avro serialization, Schema Registry integration,
automatic retries, and Dead Letter Queue (DLQ) support.

We handle two primary event types:
1. Insurance Policies (insurance.policies)
2. Insurance Claims (insurance.claims)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import os
import json
import logging
import time
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib

from confluent_kafka import Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

from afriflow.logging_config import get_logger, log_operation
from afriflow.domains.shared.config import AppConfig, get_config


# ============================================================================
# Configuration
# ============================================================================

class Environment(Enum):
    """Supported deployment environments."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
    TEST = "test"


@dataclass
class ProducerConfig:
    """Kafka producer configuration container."""
    bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"
    client_id: str = "afriflow-insurance-producer"
    acks: Union[str, int] = "all"
    retries: int = 5
    retry_backoff_ms: int = 100
    batch_size: int = 16384
    linger_ms: int = 5
    compression_type: str = "snappy"
    enable_idempotence: bool = True
    dlq_topic: Optional[str] = "insurance.dlq"
    metrics_enabled: bool = True
    metrics_interval_seconds: int = 60
    
    @classmethod
    def from_env(cls, env: Optional[str] = None) -> 'ProducerConfig':
        """Load configuration from environment variables."""
        environment = env or os.getenv("APP_ENV", "dev")
        
        # Environment-specific defaults
        if environment == "prod":
            acks = "all"
            compression = "snappy"
            batch_size = 32768
        elif environment == "staging":
            acks = 1
            compression = "gzip"
            batch_size = 16384
        else:
            acks = 1
            compression = "none"
            batch_size = 8192
        
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            schema_registry_url=os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081"),
            client_id=f"afriflow-insurance-producer-{environment}",
            acks=acks,
            batch_size=batch_size,
            compression_type=compression,
        )


# ============================================================================
# Metrics Collection
# ============================================================================

@dataclass
class ProducerMetrics:
    """Metrics for monitoring producer performance."""
    messages_sent: int = 0
    messages_failed: int = 0
    bytes_sent: int = 0
    send_latency_sum: float = 0.0
    send_latency_count: int = 0
    retries_total: int = 0
    last_send_time: Optional[datetime] = None
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def record_send(self, message_size: int, latency_ms: float) -> None:
        """Record a successful send."""
        self.messages_sent += 1
        self.bytes_sent += message_size
        self.send_latency_sum += latency_ms
        self.send_latency_count += 1
        self.last_send_time = datetime.now()
    
    def record_failure(self, error_type: str) -> None:
        """Record a failed send."""
        self.messages_failed += 1
        self.errors_by_type[error_type] += 1
    
    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.retries_total += 1
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average send latency."""
        if self.send_latency_count == 0:
            return 0.0
        return self.send_latency_sum / self.send_latency_count
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.messages_sent + self.messages_failed
        if total == 0:
            return 100.0
        return (self.messages_sent / total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        return {
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed,
            "bytes_sent": self.bytes_sent,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "success_rate": round(self.success_rate, 2),
            "retries_total": self.retries_total,
            "errors_by_type": dict(self.errors_by_type),
            "last_send_time": self.last_send_time.isoformat() if self.last_send_time else None,
        }


# ============================================================================
# Custom Exceptions
# ============================================================================

class KafkaProducerError(Exception):
    """Base exception for Kafka producer errors."""
    pass


class SchemaLoadError(KafkaProducerError):
    """Raised when an Avro schema cannot be loaded."""
    pass


class DeliveryError(KafkaProducerError):
    """Raised when a message fails to be delivered after retries."""
    pass


class CircuitBreakerOpen(KafkaProducerError):
    """Raised when circuit breaker is open."""
    pass


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for resilient Kafka operations.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"
        self._half_open_calls = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "HALF_OPEN"
                    self._half_open_calls = 0
            return self._state
    
    def can_execute(self) -> bool:
        """Check if request can proceed."""
        state = self.state
        if state == "CLOSED":
            return True
        elif state == "HALF_OPEN":
            with self._lock:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
            return False
        return False
    
    def record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            if self._state == "HALF_OPEN":
                self._state = "CLOSED"
                self._failure_count = 0
            elif self._state == "CLOSED":
                self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self) -> None:
        """Record failed execution."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == "HALF_OPEN":
                self._state = "OPEN"
            elif self._failure_count >= self.failure_threshold:
                self._state = "OPEN"


# ============================================================================
# Main Producer Class
# ============================================================================

class InsuranceKafkaProducer:
    """
    High-performance Kafka producer for insurance events.

    Features:
    - Avro serialization with Schema Registry
    - Automatic retries with exponential backoff
    - Dead Letter Queue (DLQ) support
    - Circuit breaker pattern for resilience
    - Metrics collection and monitoring
    - Idempotent message production
    - Batch processing capabilities

    Attributes:
        producer: Confluent Kafka Producer instance.
        schema_registry_client: Client for Schema Registry.
        serializers: Dictionary of Avro serializers keyed by topic.
        dlq_topic: Optional topic for failed messages.
        circuit_breaker: Circuit breaker for resilience.
        metrics: Performance metrics container.
    """

    # Topic names
    POLICY_TOPIC = "insurance.policies"
    CLAIM_TOPIC = "insurance.claims"
    
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        schema_registry_url: Optional[str] = None,
        dlq_topic: Optional[str] = "insurance.dlq",
        conf_overrides: Optional[Dict[str, Any]] = None,
        config: Optional[ProducerConfig] = None
    ) -> None:
        """
        Initialize the Kafka producer with Avro serialization support.

        Args:
            bootstrap_servers: Kafka broker addresses.
            schema_registry_url: URL for Confluent Schema Registry.
            dlq_topic: Topic name for dead letter queue.
            conf_overrides: Optional dictionary to override default Kafka config.
            config: Optional ProducerConfig object (takes precedence over individual params).
        """
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = ProducerConfig.from_env()
            if bootstrap_servers:
                self.config.bootstrap_servers = bootstrap_servers
            if schema_registry_url:
                self.config.schema_registry_url = schema_registry_url
            if dlq_topic is not None:
                self.config.dlq_topic = dlq_topic
        
        self.bootstrap_servers = self.config.bootstrap_servers
        self.schema_registry_url = self.config.schema_registry_url
        self.dlq_topic = self.config.dlq_topic
        
        self.logger = get_logger("insurance.ingestion.kafka_producer")
        self.serializers: Dict[str, AvroSerializer] = {}
        self._schemas_cache: Dict[str, str] = {}
        
        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            half_open_max_calls=3
        )
        
        # Metrics
        self.metrics = ProducerMetrics()
        self._metrics_lock = threading.Lock()
        self._shutdown = threading.Event()
        self._metrics_thread: Optional[threading.Thread] = None
        
        # Base Kafka configuration
        producer_conf = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': self.config.client_id,
            'acks': self.config.acks,
            'retries': self.config.retries,
            'retry.backoff.ms': self.config.retry_backoff_ms,
            'linger.ms': self.config.linger_ms,
            'batch.size': self.config.batch_size,
            'compression.type': self.config.compression_type,
            'enable.idempotence': self.config.enable_idempotence,
        }

        if conf_overrides:
            producer_conf.update(conf_overrides)

        try:
            self.producer = Producer(producer_conf)
            self.schema_registry_client = SchemaRegistryClient(
                {'url': self.schema_registry_url}
            )
            self.logger.info(
                f"InsuranceKafkaProducer initialized for {self.bootstrap_servers}"
            )
            
            # Start metrics reporting if enabled
            if self.config.metrics_enabled:
                self._start_metrics_reporting()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka producer: {e}")
            raise KafkaProducerError(f"Initialization failed: {e}")

    def _start_metrics_reporting(self) -> None:
        """Start background metrics reporting thread."""
        def report_metrics():
            while not self._shutdown.is_set():
                self._shutdown.wait(self.config.metrics_interval_seconds)
                if not self._shutdown.is_set():
                    self._log_metrics()
        
        self._metrics_thread = threading.Thread(
            target=report_metrics,
            daemon=True,
            name="metrics-reporter"
        )
        self._metrics_thread.start()
    
    def _log_metrics(self) -> None:
        """Log current metrics."""
        with self._metrics_lock:
            metrics_dict = self.metrics.to_dict()
            self.logger.info(
                f"Producer metrics: "
                f"sent={metrics_dict['messages_sent']}, "
                f"failed={metrics_dict['messages_failed']}, "
                f"success_rate={metrics_dict['success_rate']}%, "
                f"avg_latency={metrics_dict['avg_latency_ms']}ms"
            )

    def _load_schema(self, schema_name: str) -> str:
        """
        Load Avro schema from file.
        
        Args:
            schema_name: Name of the schema file (without .avsc extension).
            
        Returns:
            Schema content as string.
            
        Raises:
            SchemaLoadError: If schema file cannot be loaded.
        """
        # Check cache first
        if schema_name in self._schemas_cache:
            return self._schemas_cache[schema_name]
        
        schema_path = Path(__file__).parent / "avro_schemas" / f"{schema_name}.avsc"
        if not schema_path.exists():
            raise SchemaLoadError(f"Schema file not found: {schema_path}")

        try:
            with open(schema_path, 'r') as f:
                schema_content = f.read()
                self._schemas_cache[schema_name] = schema_content
                return schema_content
        except Exception as e:
            raise SchemaLoadError(f"Failed to read schema {schema_name}: {e}")

    def _get_serializer(self, topic: str, schema_name: str) -> AvroSerializer:
        """
        Get or create an AvroSerializer for a topic.
        
        Args:
            topic: Kafka topic name.
            schema_name: Name of the Avro schema.
            
        Returns:
            AvroSerializer instance.
        """
        if topic not in self.serializers:
            schema_str = self._load_schema(schema_name)
            self.serializers[topic] = AvroSerializer(
                self.schema_registry_client,
                schema_str,
                lambda obj, ctx: obj  # Object is already a dict
            )
        return self.serializers[topic]

    def _delivery_report(
        self,
        err: Optional[KafkaError],
        msg: Any,
        obj: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> None:
        """
        Callback for message delivery reports.
        
        Args:
            err: Error object if delivery failed.
            msg: Message metadata if delivery succeeded.
            obj: Original message object for DLQ.
            start_time: Time when send was initiated for latency calculation.
        """
        if start_time:
            latency_ms = (time.time() - start_time) * 1000
            with self._metrics_lock:
                if err is None:
                    self.metrics.record_send(len(json.dumps(obj or {})), latency_ms)
                else:
                    self.metrics.record_failure(type(err).__name__)
        
        if err is not None:
            self.logger.error(f"Message delivery failed: {err}")
            self.circuit_breaker.record_failure()
            if self.dlq_topic and obj:
                self._send_to_dlq(obj, str(err))
        else:
            self.circuit_breaker.record_success()
            self.logger.debug(
                f"Message delivered to {msg.topic()} [{msg.partition()}] "
                f"at offset {msg.offset()}"
            )

    def _send_to_dlq(self, obj: Dict[str, Any], error_msg: str) -> None:
        """
        Send failed message to Dead Letter Queue.
        
        Args:
            obj: Original message object.
            error_msg: Error message describing the failure.
        """
        try:
            dlq_payload = {
                "original_message": obj,
                "error": error_msg,
                "failed_at": datetime.utcnow().isoformat(),
                "domain": "insurance"
            }
            # Send to DLQ as plain JSON (no Avro needed for DLQ usually)
            self.producer.produce(
                topic=self.dlq_topic,
                value=json.dumps(dlq_payload).encode('utf-8'),
                on_delivery=lambda err, msg: self.logger.warning(
                    f"DLQ delivery status: {err if err else 'success'}"
                )
            )
            self.logger.info(f"Message sent to DLQ topic: {self.dlq_topic}")
        except Exception as e:
            self.logger.critical(f"CRITICAL: Failed to send message to DLQ: {e}")

    def _produce_event(
        self,
        topic: str,
        schema_name: str,
        data: Dict[str, Any],
        sync: bool = False,
        key: Optional[str] = None
    ) -> None:
        """
        Generic event production internal method.
        
        Args:
            topic: Kafka topic name.
            schema_name: Name of the Avro schema.
            data: Message data dictionary.
            sync: If True, blocks until message is delivered.
            key: Optional message key for partitioning.
            
        Raises:
            CircuitBreakerOpen: If circuit breaker is open.
            DeliveryError: If message delivery fails.
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpen(
                f"Circuit breaker is OPEN. Recovery in "
                f"{self.circuit_breaker.recovery_timeout}s"
            )
        
        start_time = time.time()
        
        try:
            serializer = self._get_serializer(topic, schema_name)

            # Enrich with ingestion timestamp if missing
            if "ingested_at" not in data:
                data["ingested_at"] = datetime.utcnow().isoformat()
            
            # Generate message hash for idempotency tracking
            if "message_hash" not in data:
                content = json.dumps(data, sort_keys=True)
                data["message_hash"] = hashlib.sha256(content.encode()).hexdigest()[:16]

            self.producer.produce(
                topic=topic,
                value=serializer(data, SerializationContext(topic, MessageField.VALUE)),
                key=key.encode('utf-8') if key else None,
                on_delivery=lambda err, msg: self._delivery_report(
                    err, msg, obj=data, start_time=start_time
                )
            )

            if sync:
                self.producer.flush()
            else:
                # Serve delivery callbacks from previous asynchronous calls
                self.producer.poll(0)

        except Exception as e:
            self.logger.error(f"Failed to produce event to {topic}: {e}")
            self.circuit_breaker.record_failure()
            with self._metrics_lock:
                self.metrics.record_failure(type(e).__name__)
            if self.dlq_topic:
                self._send_to_dlq(data, str(e))
            raise DeliveryError(f"Event production failed: {e}")

    def produce_policy(
        self,
        policy_data: Dict[str, Any],
        sync: bool = False,
        key: Optional[str] = None
    ) -> None:
        """
        Produce an insurance policy event.

        Args:
            policy_data: Dictionary containing policy data.
            sync: If True, blocks until message is delivered.
            key: Optional message key for partitioning (defaults to policy_id).
            
        Example:
            >>> producer = InsuranceKafkaProducer()
            >>> producer.produce_policy({
            ...     "policy_id": "POL-12345",
            ...     "policy_type": "group_life",
            ...     "policyholder_id": "EMP-001",
            ...     "insurer": "Standard Bank Insurance",
            ...     "country": "ZA",
            ...     "sum_assured": 500000,
            ...     "annual_premium": 12000,
            ... })
        """
        topic = self.POLICY_TOPIC
        if key is None:
            key = policy_data.get("policy_id")
        self._produce_event(topic, "policy_v1", policy_data, sync, key)

    def produce_claim(
        self,
        claim_data: Dict[str, Any],
        sync: bool = False,
        key: Optional[str] = None
    ) -> None:
        """
        Produce an insurance claim event.

        Args:
            claim_data: Dictionary containing claim data.
            sync: If True, blocks until message is delivered.
            key: Optional message key for partitioning (defaults to claim_id).
            
        Example:
            >>> producer = InsuranceKafkaProducer()
            >>> producer.produce_claim({
            ...     "claim_id": "CLM-67890",
            ...     "policy_id": "POL-12345",
            ...     "claim_type": "death",
            ...     "claimed_amount": 500000,
            ...     "status": "pending",
            ... })
        """
        topic = self.CLAIM_TOPIC
        if key is None:
            key = claim_data.get("claim_id")
        self._produce_event(topic, "claim_v1", claim_data, sync, key)

    def produce_batch(
        self,
        messages: List[Dict[str, Any]],
        topic: str,
        schema_name: str,
        key_field: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Produce a batch of messages.
        
        Args:
            messages: List of message dictionaries.
            topic: Kafka topic name.
            schema_name: Name of the Avro schema.
            key_field: Optional field name to use as message key.
            
        Returns:
            Dictionary with 'sent' and 'failed' counts.
        """
        sent = 0
        failed = 0
        
        for msg in messages:
            try:
                key = msg.get(key_field) if key_field else None
                self._produce_event(topic, schema_name, msg, sync=False, key=key)
                sent += 1
            except Exception as e:
                self.logger.error(f"Batch message failed: {e}")
                failed += 1
        
        # Flush all pending messages
        self.flush()
        
        self.logger.info(f"Batch complete: {sent} sent, {failed} failed")
        return {"sent": sent, "failed": failed}

    def flush(self, timeout: float = 10.0) -> int:
        """
        Wait for all messages in the Producer queue to be delivered.
        
        Args:
            timeout: Maximum time to wait in seconds.
            
        Returns:
            Number of messages remaining in queue.
        """
        return self.producer.flush(timeout)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current producer metrics."""
        with self._metrics_lock:
            return self.metrics.to_dict()

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Dictionary with health status.
        """
        return {
            "status": "healthy" if self.circuit_breaker.state == "CLOSED" else "degraded",
            "circuit_breaker_state": self.circuit_breaker.state,
            "metrics": self.get_metrics(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def close(self) -> None:
        """Flush and close the producer."""
        self.logger.info("Closing Kafka producer...")
        self._shutdown.set()
        self.flush()
        self.logger.info("Kafka producer closed.")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_producer(
    env: Optional[str] = None,
    bootstrap_servers: Optional[str] = None,
    schema_registry_url: Optional[str] = None,
) -> InsuranceKafkaProducer:
    """
    Create and return a configured InsuranceKafkaProducer.
    
    Args:
        env: Environment name (dev, staging, prod).
        bootstrap_servers: Optional Kafka bootstrap servers.
        schema_registry_url: Optional Schema Registry URL.
        
    Returns:
        Configured InsuranceKafkaProducer instance.
    """
    config = ProducerConfig.from_env(env)
    if bootstrap_servers:
        config.bootstrap_servers = bootstrap_servers
    if schema_registry_url:
        config.schema_registry_url = schema_registry_url
    
    return InsuranceKafkaProducer(config=config)


# ============================================================================
# Main (Demo/Testing)
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Insurance Kafka Producer")
    parser.add_argument("--env", default="dev", help="Environment")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    args = parser.parse_args()
    
    # Setup logging
    from afriflow.logging_config import setup_logging
    setup_logging(level="INFO", json_format=True)
    
    if args.demo:
        # Create producer
        producer = create_producer(args.env)
        
        try:
            # Send demo policy
            policy_data = {
                "policy_id": "DEMO-POL-001",
                "policy_type": "group_life",
                "policyholder_id": "DEMO-EMP-001",
                "insurer": "Demo Insurance",
                "country": "ZA",
                "currency": "ZAR",
                "sum_assured": 500000,
                "annual_premium": 12000,
                "inception_date": "2024-01-01",
                "expiry_date": "2025-01-01",
                "status": "active",
            }
            
            producer.produce_policy(policy_data)
            print(f"Policy sent: {policy_data['policy_id']}")
            
            # Send demo claim
            claim_data = {
                "claim_id": "DEMO-CLM-001",
                "policy_id": "DEMO-POL-001",
                "claim_type": "death",
                "claimed_amount": 500000,
                "currency": "ZAR",
                "country": "ZA",
                "incident_date": "2024-06-15",
                "submitted_at": "2024-06-20",
                "status": "pending",
            }
            
            producer.produce_claim(claim_data)
            print(f"Claim sent: {claim_data['claim_id']}")
            
            # Print metrics
            time.sleep(1)
            print("\nMetrics:")
            for key, value in producer.get_metrics().items():
                print(f"  {key}: {value}")
                
        finally:
            producer.close()
    else:
        print("Insurance Kafka Producer ready.")
        print("Use --demo to run demonstration.")
