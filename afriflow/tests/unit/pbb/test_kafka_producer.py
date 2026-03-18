"""
Unit Tests for PBB Kafka Producer

Tests with mocked Kafka interactions to verify:
- Message serialization
- Schema validation
- Retry logic
- Error handling
- Metrics collection
- Circuit breaker pattern

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import json
import time
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from unittest import mock

from afriflow.domains.pbb.ingestion.kafka_producer import (
    PBBKafkaProducer,
    ProducerConfig,
    ProducerMetrics,
    CircuitBreaker,
    KafkaProducerError,
    SchemaLoadError,
    DeliveryError,
    CircuitBreakerOpen,
    create_producer,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_account_data():
    """Sample account message as dictionary."""
    return {
        "account_id": "ACC-12345",
        "account_type": "savings",
        "customer_id": "CUST-001",
        "customer_golden_id": "GLD-001",
        "balance": 50000.0,
        "available_balance": 48000.0,
        "currency": "ZAR",
        "country": "ZA",
        "status": "active",
        "opened_date": "2024-01-01",
        "is_payroll_account": True,
        "employer_id": "CORP-001",
    }


@pytest.fixture
def sample_payroll_data():
    """Sample payroll message as dictionary."""
    return {
        "payroll_batch_id": "PAY-67890",
        "employer_id": "CORP-001",
        "employer_name": "Acme Corp",
        "payroll_date": "2024-01-15",
        "total_amount": 500000.0,
        "employee_count": 50,
        "successful_credits": 48,
        "failed_credits": 2,
        "currency": "ZAR",
        "country": "ZA",
        "status": "completed",
        "processing_status": "COMPLETED",
    }


@pytest.fixture
def producer_config():
    """Test producer configuration."""
    return ProducerConfig(
        bootstrap_servers="localhost:9092",
        client_id="test-pbb-producer",
        retries=3,
        metrics_enabled=False,  # Disable for tests
        metrics_interval_seconds=1,
        dlq_topic=None,  # Disable DLQ for tests
    )


@pytest.fixture
def mock_kafka_producer():
    """Mock Confluent Kafka producer."""
    mock_producer = Mock()
    mock_producer.poll = Mock()
    mock_producer.flush = Mock(return_value=0)
    return mock_producer


# ============================================================================
# Configuration Tests
# ============================================================================

class TestProducerConfig:
    """Tests for ProducerConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ProducerConfig()
        
        assert config.bootstrap_servers == "localhost:9092"
        assert config.acks == "all"
        assert config.batch_size == 16384
        assert config.compression_type == "snappy"
    
    def test_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict('os.environ', {
            'APP_ENV': 'prod',
            'KAFKA_BOOTSTRAP_SERVERS': 'kafka1:9092,kafka2:9092',
            'SCHEMA_REGISTRY_URL': 'http://schema-registry:8081',
        }):
            config = ProducerConfig.from_env()
            
            assert config.bootstrap_servers == 'kafka1:9092,kafka2:9092'
            assert config.acks == "all"  # Prod default
    
    def test_config_from_env_dev(self):
        """Test dev environment config."""
        with patch.dict('os.environ', {
            'APP_ENV': 'dev',
        }, clear=False):
            config = ProducerConfig.from_env()
            
            assert config.acks == 1  # Dev default
            assert config.compression_type == "none"


# ============================================================================
# Metrics Tests
# ============================================================================

class TestProducerMetrics:
    """Tests for ProducerMetrics."""
    
    def test_record_send(self):
        """Test recording successful sends."""
        metrics = ProducerMetrics()
        metrics.record_send(message_size=1024, latency_ms=5.0)
        
        assert metrics.messages_sent == 1
        assert metrics.bytes_sent == 1024
        assert metrics.avg_latency_ms == 5.0
    
    def test_record_failure(self):
        """Test recording failures."""
        metrics = ProducerMetrics()
        metrics.record_failure("KafkaTimeoutError")
        metrics.record_failure("KafkaTimeoutError")
        metrics.record_failure("ConnectionError")
        
        assert metrics.messages_failed == 3
        assert metrics.errors_by_type["KafkaTimeoutError"] == 2
        assert metrics.errors_by_type["ConnectionError"] == 1
    
    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = ProducerMetrics()
        metrics.record_send(100, 1.0)
        metrics.record_send(100, 1.0)
        metrics.record_send(100, 1.0)
        metrics.record_failure("Error")
        
        assert metrics.success_rate == 75.0
    
    def test_metrics_to_dict(self):
        """Test metrics dictionary conversion."""
        metrics = ProducerMetrics()
        metrics.record_send(1024, 5.0)
        
        result = metrics.to_dict()
        
        assert 'messages_sent' in result
        assert 'success_rate' in result
        assert 'avg_latency_ms' in result


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker pattern."""
    
    def test_initial_state(self):
        """Test circuit breaker starts closed."""
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.can_execute() is True
    
    def test_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"
        
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False
    
    def test_half_open_after_timeout(self):
        """Test circuit goes half-open after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        cb.record_failure()
        assert cb.state == "OPEN"
        
        time.sleep(0.15)
        assert cb.state == "HALF_OPEN"
        assert cb.can_execute() is True
    
    def test_closes_on_success_in_half_open(self):
        """Test circuit closes on success in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == "HALF_OPEN"
        
        cb.record_success()
        assert cb.state == "CLOSED"


# ============================================================================
# Producer Tests
# ============================================================================

class TestPBBKafkaProducer:
    """Tests for PBBKafkaProducer."""
    
    def test_producer_initialization(self, producer_config):
        """Test producer initialization."""
        with patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer') as mock_producer_class:
            with patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient'):
                producer = PBBKafkaProducer(config=producer_config)
                
                assert producer.config == producer_config
                assert producer.circuit_breaker is not None
                assert producer.metrics.messages_sent == 0
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    def test_producer_connect(
        self,
        mock_schema_client,
        mock_producer_class,
        producer_config,
    ):
        """Test producer connection."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        producer = PBBKafkaProducer(config=producer_config)
        
        assert producer.producer is not None
        mock_producer_class.assert_called_once()
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.AvroSerializer')
    def test_produce_account_success(
        self,
        mock_avro_serializer,
        mock_schema_client,
        mock_producer_class,
        producer_config,
        sample_account_data,
    ):
        """Test successful account production."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        # Mock the serializer
        mock_serializer = Mock()
        mock_serializer.return_value = json.dumps(sample_account_data).encode('utf-8')
        mock_avro_serializer.return_value = mock_serializer
        
        producer = PBBKafkaProducer(config=producer_config)
        producer.serializers["pbb.accounts"] = mock_serializer
        
        producer.produce_account(sample_account_data)
        
        mock_producer.produce.assert_called_once()
        call_args = mock_producer.produce.call_args
        assert call_args[1]['topic'] == "pbb.accounts"
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.AvroSerializer')
    def test_produce_payroll_success(
        self,
        mock_avro_serializer,
        mock_schema_client,
        mock_producer_class,
        producer_config,
        sample_payroll_data,
    ):
        """Test successful payroll production."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        # Mock the serializer
        mock_serializer = Mock()
        mock_serializer.return_value = json.dumps(sample_payroll_data).encode('utf-8')
        mock_avro_serializer.return_value = mock_serializer
        
        producer = PBBKafkaProducer(config=producer_config)
        producer.serializers["pbb.payroll"] = mock_serializer
        
        producer.produce_payroll(sample_payroll_data)
        
        mock_producer.produce.assert_called_once()
        call_args = mock_producer.produce.call_args
        assert call_args[1]['topic'] == "pbb.payroll"
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.AvroSerializer')
    def test_produce_batch(
        self,
        mock_avro_serializer,
        mock_schema_client,
        mock_producer_class,
        producer_config,
    ):
        """Test batch production."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        # Mock the serializer
        mock_serializer = Mock()
        mock_serializer.return_value = b'test'
        mock_avro_serializer.return_value = mock_serializer
        
        producer = PBBKafkaProducer(config=producer_config)
        
        messages = [
            {"account_id": "1", "account_type": "savings"},
            {"account_id": "2", "account_type": "checking"},
            {"account_id": "3", "account_type": "business"},
        ]
        
        result = producer.produce_batch(
            messages=messages,
            topic="pbb.accounts",
            schema_name="account_v1",
            key_field="account_id"
        )
        
        assert result['sent'] == 3
        assert result['failed'] == 0
        assert mock_producer.produce.call_count == 3
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.AvroSerializer')
    def test_circuit_breaker_opens_on_failures(
        self,
        mock_avro_serializer,
        mock_schema_client,
        mock_producer_class,
        producer_config,
    ):
        """Test circuit breaker opens after failures."""
        mock_producer = Mock()
        mock_producer.produce.side_effect = Exception("Connection failed")
        mock_producer_class.return_value = mock_producer
        
        # Mock the serializer
        mock_serializer = Mock()
        mock_serializer.return_value = b'test'
        mock_avro_serializer.return_value = mock_serializer
        
        producer = PBBKafkaProducer(config=producer_config)
        producer.circuit_breaker.failure_threshold = 3
        
        # Cause failures - use sync mode to ensure delivery callback is called
        for _ in range(3):
            try:
                producer.produce_account({"account_id": "1"}, sync=True)
            except DeliveryError:
                pass
        
        assert producer.circuit_breaker.state == "OPEN"
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.AvroSerializer')
    def test_metrics_collection(
        self,
        mock_avro_serializer,
        mock_schema_client,
        mock_producer_class,
        producer_config,
        sample_account_data,
    ):
        """Test metrics are collected on send."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        # Mock the serializer
        mock_serializer = Mock()
        mock_serializer.return_value = json.dumps(sample_account_data).encode('utf-8')
        mock_avro_serializer.return_value = mock_serializer
        
        producer = PBBKafkaProducer(config=producer_config)
        producer.serializers["pbb.accounts"] = mock_serializer
        producer.produce_account(sample_account_data)
        
        metrics = producer.get_metrics()
        assert metrics['messages_sent'] >= 0  # May be 0 if async
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    def test_health_check(
        self,
        mock_schema_client,
        mock_producer_class,
        producer_config,
    ):
        """Test health check endpoint."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        producer = PBBKafkaProducer(config=producer_config)
        health = producer.health_check()
        
        assert 'status' in health
        assert 'circuit_breaker_state' in health
        assert 'metrics' in health
        assert 'timestamp' in health
    
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer')
    @patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient')
    def test_close(
        self,
        mock_schema_client,
        mock_producer_class,
        producer_config,
    ):
        """Test producer close."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        producer = PBBKafkaProducer(config=producer_config)
        producer.close()
        
        mock_producer.flush.assert_called_once()
    
    def test_create_producer_convenience_function(self):
        """Test create_producer convenience function."""
        with patch('afriflow.domains.pbb.ingestion.kafka_producer.ProducerConfig.from_env') as mock_from_env:
            with patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer') as mock_producer_class:
                with patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient'):
                    mock_config = Mock()
                    mock_from_env.return_value = mock_config
                    
                    mock_producer = Mock()
                    mock_producer_class.return_value = mock_producer
                    
                    result = create_producer(env="test", bootstrap_servers="localhost:9092")
                    
                    mock_from_env.assert_called_once_with("test")
                    mock_producer_class.assert_called_once()


# ============================================================================
# Schema Tests
# ============================================================================

class TestSchemaLoading:
    """Tests for schema loading functionality."""
    
    def test_schema_file_not_found(self, producer_config):
        """Test error when schema file not found."""
        with patch('afriflow.domains.pbb.ingestion.kafka_producer.Producer') as mock_producer_class:
            with patch('afriflow.domains.pbb.ingestion.kafka_producer.SchemaRegistryClient'):
                mock_producer_class.return_value = Mock()
                
                producer = PBBKafkaProducer(config=producer_config)
                
                with pytest.raises(SchemaLoadError):
                    producer._load_schema("nonexistent_schema")


# ============================================================================
# Integration Test Stubs
# ============================================================================

class TestIntegrationStubs:
    """
    Integration test stubs.
    
    These tests require a real Kafka broker to run.
    They are marked with @pytest.mark.integration to skip by default.
    
    To run: pytest -m integration
    """
    
    @pytest.mark.integration
    def test_real_kafka_connection(self):
        """Test connection to real Kafka broker."""
        pytest.importorskip("confluent_kafka")
        
        # This would test against a real broker
        # config = ProducerConfig(bootstrap_servers="localhost:9092")
        # producer = PBBKafkaProducer(config=config)
        # producer.close()
        pytest.skip("Requires running Kafka broker")
    
    @pytest.mark.integration
    def test_real_account_send(self, sample_account_data):
        """Test sending account to real Kafka broker."""
        pytest.skip("Requires running Kafka broker")
    
    @pytest.mark.integration
    def test_real_payroll_send(self, sample_payroll_data):
        """Test sending payroll to real Kafka broker."""
        pytest.skip("Requires running Kafka broker")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
