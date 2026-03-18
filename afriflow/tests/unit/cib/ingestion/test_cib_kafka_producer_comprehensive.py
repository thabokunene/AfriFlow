"""
Comprehensive Unit Tests for CIB Kafka Producer

This test suite provides comprehensive coverage for the CIB Kafka Producer module,
including validation, error handling, batch processing, and edge cases.

Test Categories:
1. Initialization Tests
2. Validation Tests (Payment Fields)
3. Connection Tests
4. Send Payment Tests
5. Batch Processing Tests
6. Error Handling Tests
7. Lifecycle Tests

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict
from unittest.mock import Mock, MagicMock, patch

import pytest

from afriflow.domains.cib.ingestion.kafka_producer import (
    CIBKafkaProducer,
    ValidationError,
    KafkaProducerError,
    REQUIRED_PAYMENT_FIELDS,
    COUNTRY_CODE_PATTERN,
    CURRENCY_CODE_PATTERN,
    STATUS_VALUES,
    PURPOSE_CODE_VALUES,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def valid_payment() -> Dict[str, Any]:
    """Provide a valid payment dictionary for testing."""
    return {
        "transaction_id": "TXN-12345-ABCDE",
        "timestamp": "2026-03-01T12:00:00Z",
        "amount": 100.50,
        "currency": "USD",
        "sender_name": "ABC Corporation Ltd",
        "sender_country": "ZA",
        "beneficiary_name": "XYZ Trading Company",
        "beneficiary_country": "NG",
        "status": "COMPLETED",
        "purpose_code": "CORT",
        "corridor": "ZA-NG",
    }


@pytest.fixture
def mock_kafka_producer_class():
    """Create a mock KafkaProducer class."""
    mock_future = Mock()
    mock_future.get.return_value = Mock(
        topic="cib.payments.v1",
        partition=0,
        offset=1
    )
    
    mock_producer = Mock()
    mock_producer.send.return_value = mock_future
    mock_producer.flush.return_value = 0
    mock_producer.close.return_value = None
    
    return mock_producer


@pytest.fixture
def producer_with_mock_kafka(mock_kafka_producer_class):
    """Create a producer with mocked Kafka connection."""
    with patch('afriflow.domains.cib.ingestion.kafka_producer.KafkaProducer') as mock_class:
        mock_class.return_value = mock_kafka_producer_class
        producer = CIBKafkaProducer()
        producer.connect()
        yield producer


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Tests for CIBKafkaProducer initialization."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        producer = CIBKafkaProducer()
        
        assert producer.topic == "cib.payments.v1"
        assert producer.bootstrap_servers == "localhost:9092"
        assert producer.producer is None
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        producer = CIBKafkaProducer(
            topic="custom.topic.v1",
            bootstrap_servers="kafka1:9092,kafka2:9092"
        )
        
        assert producer.topic == "custom.topic.v1"
        assert producer.bootstrap_servers == "kafka1:9092,kafka2:9092"
    
    def test_init_empty_topic_raises(self):
        """Test that empty topic raises ValueError."""
        with pytest.raises(ValueError, match="topic must be a non-empty string"):
            CIBKafkaProducer(topic="")
    
    def test_init_empty_bootstrap_servers_raises(self):
        """Test that empty bootstrap_servers raises ValueError."""
        with pytest.raises(ValueError, match="bootstrap_servers must be a non-empty string"):
            CIBKafkaProducer(bootstrap_servers="")
    
    def test_init_non_string_topic_raises(self):
        """Test that non-string topic raises ValueError."""
        with pytest.raises(ValueError):
            CIBKafkaProducer(topic=123)
    
    def test_init_non_string_bootstrap_servers_raises(self):
        """Test that non-string bootstrap_servers raises ValueError."""
        with pytest.raises(ValueError):
            CIBKafkaProducer(bootstrap_servers=9092)


# ============================================================================
# Validation Tests - Country Codes
# ============================================================================

class TestCountryCodeValidation:
    """Tests for country code validation."""
    
    def test_valid_country_codes(self, valid_payment):
        """Test valid country codes pass validation."""
        producer = CIBKafkaProducer()
        
        # Should not raise
        valid_payment["sender_country"] = "ZA"
        valid_payment["beneficiary_country"] = "NG"
        producer._validate_payment(valid_payment)
    
    def test_lowercase_country_code_raises(self, valid_payment):
        """Test that lowercase country code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["sender_country"] = "za"
        
        with pytest.raises(ValidationError, match="Invalid sender_country"):
            producer._validate_payment(valid_payment)
    
    def test_numeric_country_code_raises(self, valid_payment):
        """Test that numeric country code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["sender_country"] = "12"
        
        with pytest.raises(ValidationError, match="Invalid sender_country"):
            producer._validate_payment(valid_payment)
    
    def test_three_char_country_code_raises(self, valid_payment):
        """Test that 3-character country code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["sender_country"] = "ZAF"
        
        with pytest.raises(ValidationError, match="Invalid sender_country"):
            producer._validate_payment(valid_payment)
    
    def test_special_char_country_code_raises(self, valid_payment):
        """Test that country code with special chars raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["sender_country"] = "Z-A"
        
        with pytest.raises(ValidationError, match="Invalid sender_country"):
            producer._validate_payment(valid_payment)
    
    def test_empty_country_code_raises(self, valid_payment):
        """Test that empty country code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["sender_country"] = ""
        
        with pytest.raises(ValidationError):
            producer._validate_payment(valid_payment)


# ============================================================================
# Validation Tests - Currency Codes
# ============================================================================

class TestCurrencyCodeValidation:
    """Tests for currency code validation."""
    
    def test_valid_currency_codes(self, valid_payment):
        """Test valid currency codes pass validation."""
        producer = CIBKafkaProducer()
        
        for currency in ["USD", "EUR", "ZAR", "NGN", "GBP"]:
            valid_payment["currency"] = currency
            producer._validate_payment(valid_payment)
    
    def test_lowercase_currency_code_raises(self, valid_payment):
        """Test that lowercase currency code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["currency"] = "usd"
        
        with pytest.raises(ValidationError, match="Invalid currency"):
            producer._validate_payment(valid_payment)
    
    def test_two_char_currency_code_raises(self, valid_payment):
        """Test that 2-character currency code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["currency"] = "US"
        
        with pytest.raises(ValidationError, match="Invalid currency"):
            producer._validate_payment(valid_payment)
    
    def test_four_char_currency_code_raises(self, valid_payment):
        """Test that 4-character currency code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["currency"] = "USDC"
        
        with pytest.raises(ValidationError, match="Invalid currency"):
            producer._validate_payment(valid_payment)


# ============================================================================
# Validation Tests - Amount
# ============================================================================

class TestAmountValidation:
    """Tests for amount validation."""
    
    def test_valid_amounts(self, valid_payment):
        """Test valid amounts pass validation."""
        producer = CIBKafkaProducer()
        
        for amount in [0.01, 1.0, 100.50, 1000000.00]:
            valid_payment["amount"] = amount
            producer._validate_payment(valid_payment)
    
    def test_zero_amount_raises(self, valid_payment):
        """Test that zero amount raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["amount"] = 0
        
        with pytest.raises(ValidationError, match="Invalid amount"):
            producer._validate_payment(valid_payment)
    
    def test_negative_amount_raises(self, valid_payment):
        """Test that negative amount raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["amount"] = -100.50
        
        with pytest.raises(ValidationError, match="Invalid amount"):
            producer._validate_payment(valid_payment)
    
    def test_string_amount_raises(self, valid_payment):
        """Test that string amount raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["amount"] = "100.50"
        
        with pytest.raises(ValidationError, match="Invalid amount"):
            producer._validate_payment(valid_payment)
    
    def test_none_amount_raises(self, valid_payment):
        """Test that None amount raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["amount"] = None
        
        with pytest.raises(ValidationError, match="Invalid amount"):
            producer._validate_payment(valid_payment)


# ============================================================================
# Validation Tests - Status
# ============================================================================

class TestStatusValidation:
    """Tests for status validation."""
    
    def test_valid_statuses(self, valid_payment):
        """Test valid statuses pass validation."""
        producer = CIBKafkaProducer()
        
        for status in STATUS_VALUES:
            valid_payment["status"] = status
            producer._validate_payment(valid_payment)
    
    def test_invalid_status_raises(self, valid_payment):
        """Test that invalid status raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["status"] = "UNKNOWN"
        
        with pytest.raises(ValidationError, match="Invalid status"):
            producer._validate_payment(valid_payment)
    
    def test_lowercase_status_raises(self, valid_payment):
        """Test that lowercase status raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["status"] = "completed"
        
        with pytest.raises(ValidationError, match="Invalid status"):
            producer._validate_payment(valid_payment)


# ============================================================================
# Validation Tests - Purpose Code
# ============================================================================

class TestPurposeCodeValidation:
    """Tests for purpose code validation."""
    
    def test_valid_purpose_codes(self, valid_payment):
        """Test valid purpose codes pass validation."""
        producer = CIBKafkaProducer()
        
        for code in PURPOSE_CODE_VALUES:
            valid_payment["purpose_code"] = code
            producer._validate_payment(valid_payment)
    
    def test_invalid_purpose_code_raises(self, valid_payment):
        """Test that invalid purpose code raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["purpose_code"] = "INVALID"
        
        with pytest.raises(ValidationError, match="Invalid purpose_code"):
            producer._validate_payment(valid_payment)


# ============================================================================
# Validation Tests - Corridor
# ============================================================================

class TestCorridorValidation:
    """Tests for corridor validation."""
    
    def test_valid_corridor(self, valid_payment):
        """Test valid corridor passes validation."""
        producer = CIBKafkaProducer()
        valid_payment["corridor"] = "ZA-NG"
        
        # Should not raise
        producer._validate_payment(valid_payment)
    
    def test_corridor_without_dash_raises(self, valid_payment):
        """Test that corridor without dash raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["corridor"] = "ZANG"
        
        with pytest.raises(ValidationError, match="Invalid corridor format"):
            producer._validate_payment(valid_payment)
    
    def test_empty_corridor_raises(self, valid_payment):
        """Test that empty corridor raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["corridor"] = ""
        
        with pytest.raises(ValidationError, match="Invalid corridor format"):
            producer._validate_payment(valid_payment)
    
    def test_non_string_corridor_raises(self, valid_payment):
        """Test that non-string corridor raises ValidationError."""
        producer = CIBKafkaProducer()
        valid_payment["corridor"] = 123
        
        with pytest.raises(ValidationError, match="Invalid corridor format"):
            producer._validate_payment(valid_payment)


# ============================================================================
# Validation Tests - Required Fields
# ============================================================================

class TestRequiredFieldsValidation:
    """Tests for required fields validation."""
    
    def test_missing_required_fields_raises(self, valid_payment):
        """Test that missing required fields raises ValidationError."""
        producer = CIBKafkaProducer()
        
        for field in REQUIRED_PAYMENT_FIELDS:
            payment_copy = valid_payment.copy()
            del payment_copy[field]
            
            with pytest.raises(ValidationError, match="Missing required fields"):
                producer._validate_payment(payment_copy)
    
    def test_non_dict_payment_raises(self):
        """Test that non-dict payment raises ValidationError."""
        producer = CIBKafkaProducer()
        
        with pytest.raises(ValidationError, match="Payment must be a dictionary"):
            producer._validate_payment("not a dict")
        
        with pytest.raises(ValidationError, match="Payment must be a dictionary"):
            producer._validate_payment(["list"])
        
        with pytest.raises(ValidationError, match="Payment must be a dictionary"):
            producer._validate_payment(None)


# ============================================================================
# Connection Tests
# ============================================================================

class TestConnection:
    """Tests for Kafka connection."""
    
    def test_connect_import_error_mock_mode(self):
        """Test connection handles import error gracefully."""
        with patch.dict('sys.modules', {'kafka': None}):
            producer = CIBKafkaProducer()
            producer.connect()
            # Should not raise, producer stays None
            assert producer.producer is None
    
    def test_connect_success(self):
        """Test successful connection."""
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic="test", partition=0, offset=1)
        
        mock_producer = Mock()
        mock_producer.send.return_value = mock_future
        
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_producer
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            assert producer.producer is not None
            mock_class.assert_called_once()
    
    def test_connect_exception_raises(self):
        """Test that connection exception is raised."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.side_effect = Exception("Connection failed")
            
            producer = CIBKafkaProducer()
            
            with pytest.raises(Exception, match="Connection failed"):
                producer.connect()


# ============================================================================
# Send Payment Tests
# ============================================================================

class TestSendPayment:
    """Tests for send_payment method."""
    
    def test_send_payment_validation_error(self, valid_payment):
        """Test that validation error is raised for invalid payment."""
        producer = CIBKafkaProducer()
        
        # Remove required field
        del valid_payment["currency"]
        
        with pytest.raises(ValidationError):
            producer.send_payment(valid_payment)
    
    def test_send_payment_mock_mode(self, valid_payment):
        """Test send payment in mock mode (no producer)."""
        producer = CIBKafkaProducer()
        
        # Should not raise in mock mode
        producer.send_payment(valid_payment)
    
    def test_send_payment_with_key(self, valid_payment, mock_kafka_producer_class):
        """Test send payment with message key."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            producer.send_payment(valid_payment, key="test-key")
            
            mock_kafka_producer_class.send.assert_called_once()
            call_args = mock_kafka_producer_class.send.call_args
            assert call_args[1]['key'] == "test-key"
    
    def test_send_payment_logs_on_success(self, valid_payment, mock_kafka_producer_class, caplog):
        """Test that success is logged."""
        with caplog.at_level(logging.INFO):
            with patch('kafka.KafkaProducer') as mock_class:
                mock_class.return_value = mock_kafka_producer_class
                
                producer = CIBKafkaProducer()
                producer.connect()
                producer.send_payment(valid_payment)
                
                assert "Payment sent" in caplog.text


# ============================================================================
# Batch Processing Tests
# ============================================================================

class TestBatchProcessing:
    """Tests for send_batch method."""
    
    def test_send_batch_empty_list(self):
        """Test that empty batch returns 0."""
        producer = CIBKafkaProducer()
        result = producer.send_batch([])
        assert result == 0
    
    def test_send_batch_all_success(self, valid_payment, mock_kafka_producer_class):
        """Test batch with all successful sends."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            payments = [valid_payment.copy() for _ in range(5)]
            result = producer.send_batch(payments)
            
            assert result == 5
    
    def test_send_batch_mixed_results(self, valid_payment, mock_kafka_producer_class):
        """Test batch with mixed success/failure."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            good_payment = valid_payment.copy()
            bad_payment = valid_payment.copy()
            del bad_payment["currency"]  # Invalid
            
            payments = [good_payment, bad_payment, good_payment]
            result = producer.send_batch(payments)
            
            assert result == 2
    
    def test_send_batch_all_validation_failures(self, valid_payment):
        """Test batch where all payments fail validation."""
        producer = CIBKafkaProducer()
        
        bad_payment = valid_payment.copy()
        del bad_payment["currency"]
        
        payments = [bad_payment, bad_payment, bad_payment]
        result = producer.send_batch(payments)
        
        assert result == 0
    
    def test_send_batch_flushes(self, valid_payment, mock_kafka_producer_class):
        """Test that batch processing flushes the producer."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            producer.send_batch([valid_payment])
            
            mock_kafka_producer_class.flush.assert_called_once()


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_send_payment_kafka_error(self, valid_payment):
        """Test KafkaProducerError on send failure."""
        mock_future = Mock()
        mock_future.get.side_effect = Exception("Kafka error")
        
        mock_producer = Mock()
        mock_producer.send.return_value = mock_future
        
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_producer
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            with pytest.raises(KafkaProducerError, match="Kafka error"):
                producer.send_payment(valid_payment)
    
    def test_send_batch_kafka_error(self, valid_payment):
        """Test KafkaProducerError handling in batch."""
        mock_future = Mock()
        mock_future.get.side_effect = Exception("Kafka error")
        
        mock_producer = Mock()
        mock_producer.send.return_value = mock_future
        
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_producer
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            # Should not raise, should return 0 sent
            result = producer.send_batch([valid_payment])
            assert result == 0
    
    def test_send_payment_exception_chaining(self, valid_payment):
        """Test that original exception is chained."""
        mock_future = Mock()
        original_error = Exception("Original error")
        mock_future.get.side_effect = original_error
        
        mock_producer = Mock()
        mock_producer.send.return_value = mock_future
        
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_producer
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            try:
                producer.send_payment(valid_payment)
            except KafkaProducerError as e:
                assert e.__cause__ is original_error


# ============================================================================
# Lifecycle Tests
# ============================================================================

class TestLifecycle:
    """Tests for producer lifecycle."""
    
    def test_close_with_producer(self, mock_kafka_producer_class):
        """Test close with active producer."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            producer.close()
            
            mock_kafka_producer_class.close.assert_called_once()
    
    def test_close_without_producer(self):
        """Test close without active producer."""
        producer = CIBKafkaProducer()
        
        # Should not raise
        producer.close()
    
    def test_send_after_close(self, valid_payment, mock_kafka_producer_class):
        """Test sending after close."""
        with patch('afriflow.domains.cib.ingestion.kafka_producer.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            producer.close()
            
            # Should work in mock mode (producer is None)
            producer.send_payment(valid_payment)


# ============================================================================
# Pattern Tests
# ============================================================================

class TestPatterns:
    """Tests for regex patterns."""
    
    def test_country_code_pattern(self):
        """Test country code regex pattern."""
        # Valid
        assert COUNTRY_CODE_PATTERN.match("ZA")
        assert COUNTRY_CODE_PATTERN.match("NG")
        assert COUNTRY_CODE_PATTERN.match("US")
        
        # Invalid
        assert not COUNTRY_CODE_PATTERN.match("za")
        assert not COUNTRY_CODE_PATTERN.match("ZAF")
        assert not COUNTRY_CODE_PATTERN.match("12")
        assert not COUNTRY_CODE_PATTERN.match("Z-A")
    
    def test_currency_code_pattern(self):
        """Test currency code regex pattern."""
        # Valid
        assert CURRENCY_CODE_PATTERN.match("USD")
        assert CURRENCY_CODE_PATTERN.match("EUR")
        assert CURRENCY_CODE_PATTERN.match("ZAR")
        
        # Invalid
        assert not CURRENCY_CODE_PATTERN.match("usd")
        assert not CURRENCY_CODE_PATTERN.match("US")
        assert not CURRENCY_CODE_PATTERN.match("USDC")


# ============================================================================
# Integration-style Tests
# ============================================================================

class TestIntegration:
    """Integration-style tests with mocked dependencies."""
    
    def test_full_flow_valid_payment(self, valid_payment, mock_kafka_producer_class):
        """Test complete flow with valid payment."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer = CIBKafkaProducer()
            producer.connect()
            
            # Send single payment
            producer.send_payment(valid_payment)
            assert mock_kafka_producer_class.send.call_count == 1
            
            # Send batch
            producer.send_batch([valid_payment, valid_payment])
            assert mock_kafka_producer_class.send.call_count == 3
            
            # Close
            producer.close()
            mock_kafka_producer_class.close.assert_called_once()
    
    def test_multiple_producers_isolation(self, valid_payment, mock_kafka_producer_class):
        """Test that multiple producers are isolated."""
        with patch('kafka.KafkaProducer') as mock_class:
            mock_class.return_value = mock_kafka_producer_class
            
            producer1 = CIBKafkaProducer(topic="topic1")
            producer2 = CIBKafkaProducer(topic="topic2")
            
            producer1.connect()
            producer2.connect()
            
            producer1.send_payment(valid_payment)
            producer2.send_payment(valid_payment)
            
            # Verify different topics
            calls = mock_kafka_producer_class.send.call_args_list
            assert calls[0][1]['topic'] == "topic1"
            assert calls[1][1]['topic'] == "topic2"
