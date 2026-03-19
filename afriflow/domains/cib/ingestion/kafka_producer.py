"""
@file kafka_producer.py
@description Kafka producer for CIB domain ingestion, providing schema validation for payment events.
@author Thabo Kunene
@created 2026-03-19
"""

"""
CIB Kafka Producer.

We produce CIB payment events to Kafka topics.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Type hinting for defining strong collection and functional contracts
from typing import Dict, Any, Optional, List
# Standard logging for operational observability and audit trails
import logging
# Standard library for JSON encoding/decoding of payment payloads
import json
# Regular expression support for schema validation of country and currency codes
import re

# Initialize module-level logger for CIB ingestion events
logger = logging.getLogger(__name__)


# Set of mandatory fields that must be present in every payment record.
# This ensures structural integrity before the data enters the streaming pipeline.
REQUIRED_PAYMENT_FIELDS = {
    "transaction_id", "timestamp", "amount", "currency",
    "sender_name", "sender_country", "beneficiary_name",
    "beneficiary_country", "status", "purpose_code", "corridor"
}

# Regex pattern for two-letter ISO country codes (e.g., 'ZA', 'NG').
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
# Regex pattern for three-letter ISO currency codes (e.g., 'ZAR', 'USD').
CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")
# Permitted lifecycle statuses for a payment transaction.
STATUS_VALUES = {"COMPLETED", "PENDING", "FAILED"}
# Standardized ISO 20022 purpose codes commonly used in CIB payments.
PURPOSE_CODE_VALUES = {"CORT", "INTC", "DIVI", "SALA", "TREA"}


class KafkaProducerError(Exception):
    """
    Base exception for all CIB Kafka producer errors.
    """
    pass


class ValidationError(KafkaProducerError):
    """
    Exception raised when a payment record fails schema or business rule validation.
    """
    pass


class CIBKafkaProducer:
    """
    Handles the production of validated CIB payment events to a Kafka topic.

    Attributes:
        topic: The target Kafka topic for payment ingestion.
        bootstrap_servers: Comma-separated list of Kafka broker addresses.
        producer: The underlying Kafka client instance.
    """

    def __init__(
        self,
        topic: str = "cib.payments.v1",
        bootstrap_servers: str = "localhost:9092"
    ) -> None:
        """
        Initializes the CIB Kafka producer with connection and topic details.

        :param topic: Target Kafka topic. Defaults to 'cib.payments.v1'.
        :param bootstrap_servers: Kafka broker connection string.
        :raises ValueError: If topic or bootstrap_servers are empty or invalid types.
        """
        if not topic or not isinstance(topic, str):
            raise ValueError("topic must be a non-empty string")
        if not bootstrap_servers or not isinstance(bootstrap_servers, str):
            raise ValueError("bootstrap_servers must be a non-empty string")

        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

        logger.info(
            f"CIBKafkaProducer initialized: "
            f"topic={topic}, servers={bootstrap_servers}"
        )

    def _validate_payment(self, payment: Dict[str, Any]) -> None:
        """
        Validates a payment record against required fields, patterns, and permitted values.

        :param payment: The payment dictionary to validate.
        :raises ValidationError: If any schema or business rule check fails.
        """
        if not isinstance(payment, dict):
            raise ValidationError("Payment must be a dictionary")

        # Structural check: Ensure all mandatory fields are present
        missing_fields = REQUIRED_PAYMENT_FIELDS - set(payment.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        # Data quality check: Validate country codes follow ISO standards
        if not COUNTRY_CODE_PATTERN.match(payment["sender_country"]):
            raise ValidationError(
                f"Invalid sender_country: {payment['sender_country']}"
            )
        if not COUNTRY_CODE_PATTERN.match(payment["beneficiary_country"]):
            raise ValidationError(
                f"Invalid beneficiary_country: {payment['beneficiary_country']}"
            )

        # Validate currency code
        if not CURRENCY_CODE_PATTERN.match(payment["currency"]):
            raise ValidationError(
                f"Invalid currency: {payment['currency']}"
            )

        # Validate amount
        amount = payment["amount"]
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(f"Invalid amount: {amount}")

        # Validate status
        if payment["status"] not in STATUS_VALUES:
            raise ValidationError(
                f"Invalid status: {payment['status']}. Must be one of {STATUS_VALUES}"
            )

        # Validate purpose code
        if payment["purpose_code"] not in PURPOSE_CODE_VALUES:
            raise ValidationError(
                f"Invalid purpose_code: {payment['purpose_code']}"
            )

        # Validate corridor format
        corridor = payment["corridor"]
        if not isinstance(corridor, str) or "-" not in corridor:
            raise ValidationError(f"Invalid corridor format: {corridor}")

        logger.debug(f"Payment validation passed: {payment.get('transaction_id')}")

    def connect(self) -> None:
        """Connect to Kafka broker."""
        try:
            from kafka import KafkaProducer

            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
            )

            logger.info("Connected to Kafka broker")

        except ImportError:
            logger.warning(
                "kafka-python not installed, running in mock mode"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def send_payment(
        self,
        payment: Dict[str, Any],
        key: Optional[str] = None
    ) -> None:
        """
        Send a payment event to Kafka.

        Args:
            payment: Payment event dictionary
            key: Optional message key

        Raises:
            ValidationError: If payment validation fails
            RuntimeError: If not connected or send fails
        """
        # Validate payment before sending
        self._validate_payment(payment)

        if self.producer is None:
            logger.debug(
                f"Mock send to {self.topic}: "
                f"{payment.get('transaction_id', 'unknown')}"
            )
            return

        try:
            future = self.producer.send(
                self.topic,
                key=key,
                value=payment
            )

            # Block for 'synchronous' sends
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Payment sent: topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}, "
                f"transaction_id={payment.get('transaction_id')}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send payment {payment.get('transaction_id')}: {e}"
            )
            raise KafkaProducerError(
                f"Failed to send payment: {e}"
            ) from e

    def send_batch(
        self,
        payments: List[Dict[str, Any]]
    ) -> int:
        """
        Send a batch of payment events.

        Args:
            payments: List of payment events

        Returns:
            Number of payments successfully sent

        Raises:
            KafkaProducerError: If batch processing fails critically
        """
        if not payments:
            logger.warning("Empty payment batch, nothing to send")
            return 0

        sent_count = 0
        failed_count = 0

        for idx, payment in enumerate(payments):
            try:
                self.send_payment(payment)
                sent_count += 1
            except ValidationError as e:
                failed_count += 1
                logger.error(
                    f"Validation failed for payment {idx}: {e}"
                )
            except KafkaProducerError as e:
                failed_count += 1
                logger.error(
                    f"Failed to send payment {payment.get('transaction_id')}: {e}"
                )

        if self.producer:
            self.producer.flush()

        total = len(payments)
        logger.info(
            f"Batch send complete: {sent_count}/{total} sent, {failed_count} failed"
        )

        if failed_count > 0:
            logger.warning(
                f"Batch had {failed_count}/{total} failures"
            )

        return sent_count

    def close(self) -> None:
        """Close the Kafka connection."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")

