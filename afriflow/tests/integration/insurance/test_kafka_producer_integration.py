"""
Integration Tests for Insurance Kafka Producer

Tests with real Kafka broker (requires Docker).
Run with: pytest -m integration or pytest tests/integration/

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import json
import time
import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch

from afriflow.domains.insurance.ingestion.kafka_producer import (
    InsuranceKafkaProducer,
    ProducerConfig,
    PolicyMessage,
    ClaimMessage,
)


# Skip all tests in this module unless --integration is passed
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def kafka_bootstrap_servers():
    """Get Kafka bootstrap servers from environment or use Docker default."""
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


@pytest.fixture(scope="module")
def producer(kafka_bootstrap_servers):
    """Create and connect a producer for integration tests."""
    config = ProducerConfig(
        bootstrap_servers=[kafka_bootstrap_servers],
        client_id="integration-test-producer",
        retries=3,
        metrics_enabled=True,
    )
    
    producer = InsuranceKafkaProducer(config)
    producer.connect()
    
    yield producer
    
    producer.close()


@pytest.fixture(scope="module")
def consumer(kafka_bootstrap_servers):
    """Create a consumer for integration tests."""
    try:
        from kafka import KafkaConsumer
    except ImportError:
        pytest.skip("kafka-python not installed")
    
    consumer = KafkaConsumer(
        bootstrap_servers=[kafka_bootstrap_servers],
        auto_offset_reset='earliest',
        consumer_timeout_ms=5000,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    )
    
    yield consumer
    
    consumer.close()


class TestIntegrationKafkaProducer:
    """Integration tests for InsuranceKafkaProducer."""
    
    def test_connection(self, producer):
        """Test that producer can connect to Kafka."""
        assert producer._producer is not None
        
        # Verify we can get topics
        topics = producer._producer.topics()
        assert isinstance(topics, (set, dict, list))
    
    def test_send_policy(self, producer, consumer):
        """Test sending a policy message."""
        # Subscribe to topic
        consumer.subscribe(["insurance.policies.v1"])
        
        # Create and send policy
        policy = PolicyMessage(
            policy_id=f"INT-POL-{int(time.time())}",
            policy_type="group_life",
            policyholder_id="INT-EMP-001",
            insurer="Integration Test Insurance",
            country="ZA",
            currency="ZAR",
            sum_assured=500000.0,
            annual_premium=12000.0,
            inception_date="2024-01-01",
            expiry_date="2025-01-01",
            status="active",
        )
        
        future = producer.send_policy(policy)
        future.get(timeout=10)  # Wait for confirmation
        
        # Consume message
        messages = list(consumer)
        assert len(messages) > 0
        
        received = messages[0].value
        assert received['policy_id'] == policy.policy_id
        assert received['policy_type'] == 'group_life'
    
    def test_send_claim(self, producer, consumer):
        """Test sending a claim message."""
        consumer.subscribe(["insurance.claims.v1"])
        
        # Create and send claim
        claim = ClaimMessage(
            claim_id=f"INT-CLM-{int(time.time())}",
            policy_id="INT-POL-001",
            policyholder_id="INT-EMP-001",
            claim_type="death",
            claimed_amount=500000.0,
            currency="ZAR",
            country="ZA",
            incident_date="2024-01-10",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            status="pending",
        )
        
        future = producer.send_claim(claim)
        future.get(timeout=10)
        
        # Consume message
        messages = list(consumer)
        assert len(messages) > 0
        
        received = messages[0].value
        assert received['claim_id'] == claim.claim_id
        assert received['claim_type'] == 'death'
    
    def test_send_batch(self, producer, consumer):
        """Test sending batch of messages."""
        consumer.subscribe(["insurance.policies.v1", "insurance.claims.v1"])
        
        base_time = int(time.time())
        messages = [
            (
                "insurance.policies.v1",
                PolicyMessage(
                    policy_id=f"INT-BATCH-POL-{base_time}-{i}",
                    policy_type="group_life",
                    policyholder_id=f"INT-EMP-{i}",
                    insurer="Batch Test",
                    country="ZA",
                    currency="ZAR",
                    sum_assured=100000.0,
                    annual_premium=2400.0,
                    inception_date="2024-01-01",
                    expiry_date="2025-01-01",
                    status="active",
                ).to_dict(),
                f"key-{i}",
            )
            for i in range(5)
        ]
        
        result = producer.send_batch(messages)
        
        assert result['sent'] == 5
        assert result['failed'] == 0
        
        # Consume messages
        received_messages = list(consumer)
        assert len(received_messages) >= 5
    
    def test_metrics_collection(self, producer):
        """Test that metrics are properly collected."""
        # Send some messages
        for i in range(3):
            policy = PolicyMessage(
                policy_id=f"INT-MET-POL-{i}",
                policy_type="group_life",
                policyholder_id="INT-EMP-001",
                insurer="Metrics Test",
                country="ZA",
                currency="ZAR",
                sum_assured=100000.0,
            )
            future = producer.send_policy(policy)
            future.get(timeout=10)
        
        # Give metrics time to update
        time.sleep(0.5)
        
        metrics = producer.get_metrics()
        
        assert metrics['messages_sent'] >= 3
        assert metrics['success_rate'] == 100.0
        assert metrics['avg_latency_ms'] > 0
    
    def test_message_headers(self, producer, consumer):
        """Test that messages include proper headers."""
        consumer.subscribe(["insurance.policies.v1"])
        
        policy = PolicyMessage(
            policy_id=f"INT-HDR-POL-{int(time.time())}",
            policy_type="group_life",
            policyholder_id="INT-EMP-001",
            insurer="Headers Test",
            country="ZA",
            currency="ZAR",
            sum_assured=100000.0,
        )
        
        future = producer.send_policy(policy)
        future.get(timeout=10)
        
        messages = list(consumer)
        assert len(messages) > 0
        
        # Check headers
        headers = {k: v for k, v in messages[0].headers}
        assert b'content-type' in headers.values() or any(b'avro' in (v or b'') for v in headers.values())
    
    def test_retry_on_failure(self):
        """Test retry behavior on connection failure."""
        # Configure producer with unreachable broker
        config = ProducerConfig(
            bootstrap_servers=["unreachable:9092"],
            retries=1,
            request_timeout_ms=1000,
            metrics_enabled=False,
        )
        
        producer = InsuranceKafkaProducer(config)
        
        # Connection should fail
        with pytest.raises((ConnectionError, Exception)):
            producer.connect()
    
    def test_callback_execution(self, producer, consumer):
        """Test that callbacks are executed properly."""
        consumer.subscribe(["insurance.policies.v1"])
        
        success_messages = []
        error_messages = []
        
        def on_success(metadata, message):
            success_messages.append(message)
        
        def on_error(error, message):
            error_messages.append((error, message))
        
        producer.on_success(on_success)
        producer.on_error(on_error)
        
        policy = PolicyMessage(
            policy_id=f"INT-CB-POL-{int(time.time())}",
            policy_type="group_life",
            policyholder_id="INT-EMP-001",
            insurer="Callback Test",
            country="ZA",
            currency="ZAR",
            sum_assured=100000.0,
        )
        
        future = producer.send_policy(policy)
        future.get(timeout=10)
        
        # Success callback should have been called
        assert len(success_messages) == 1
        assert success_messages[0]['policy_id'] == policy.policy_id
        assert len(error_messages) == 0


class TestIntegrationSchemaValidation:
    """Integration tests for schema validation."""
    
    def test_valid_policy_schema(self, producer):
        """Test that valid policy passes schema validation."""
        policy = PolicyMessage(
            policy_id=f"INT-SCHEMA-POL-{int(time.time())}",
            policy_type="group_life",
            policyholder_id="INT-EMP-001",
            insurer="Schema Test",
            country="ZA",
            currency="ZAR",
            sum_assured=100000.0,
            annual_premium=2400.0,
            inception_date="2024-01-01",
            expiry_date="2025-01-01",
            status="active",
        )
        
        # Should not raise
        future = producer.send_policy(policy)
        future.get(timeout=10)
    
    def test_invalid_policy_missing_required(self, producer):
        """Test that invalid policy fails schema validation."""
        # Create invalid policy (missing required fields)
        invalid_policy = {
            "policy_id": "INVALID",
            # Missing required fields
        }
        
        # Should raise SchemaValidationError
        from afriflow.domains.insurance.ingestion.kafka_producer import SchemaValidationError
        
        with pytest.raises(SchemaValidationError):
            producer.send_policy(invalid_policy)


class TestIntegrationPerformance:
    """Integration tests for performance."""
    
    def test_throughput(self, producer, consumer):
        """Test message throughput."""
        consumer.subscribe(["insurance.policies.v1"])
        
        num_messages = 100
        start_time = time.time()
        
        for i in range(num_messages):
            policy = PolicyMessage(
                policy_id=f"INT-PERF-POL-{i}",
                policy_type="group_life",
                policyholder_id="INT-EMP-001",
                insurer="Performance Test",
                country="ZA",
                currency="ZAR",
                sum_assured=100000.0,
            )
            future = producer.send_policy(policy)
            future.get(timeout=10)
        
        elapsed = time.time() - start_time
        throughput = num_messages / elapsed
        
        # Should achieve at least 10 messages/second
        assert throughput > 10, f"Throughput too low: {throughput:.2f} msg/s"
        
        print(f"\nThroughput: {throughput:.2f} messages/second")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
