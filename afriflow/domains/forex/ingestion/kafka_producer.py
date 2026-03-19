"""
@file kafka_producer.py
@description Kafka producer for Forex domain ingestion, providing schema validation for FX trades, rate ticks, and hedges.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Forex Kafka Producer.

We produce FX events (trades, rate ticks, hedges) to Kafka topics.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Type hinting for defining strong collection and functional contracts
from typing import Dict, Any, Optional, List
# Standard logging for operational observability and audit trails
import logging
# Standard library for JSON encoding/decoding of FX payloads
import json
# Regular expression support for schema validation of IDs and codes
import re

# Initialize module-level logger for Forex ingestion events
logger = logging.getLogger(__name__)


# Set of mandatory fields for FX trade records.
# Ensures structural integrity before streaming to trade analytics.
REQUIRED_TRADE_FIELDS = {
    "trade_id", "currency_pair", "trade_type", "direction",
    "base_amount", "quote_amount", "rate", "trade_date",
    "value_date", "client_id", "status"
}

# Set of mandatory fields for real-time rate ticks.
# Critical for high-frequency pricing and anomaly detection.
REQUIRED_RATE_FIELDS = {
    "tick_id", "currency_pair", "mid_rate", "bid_rate",
    "ask_rate", "tick_timestamp"
}

# Set of mandatory fields for FX hedging instruments.
# Used to track client risk mitigation strategies.
REQUIRED_HEDGE_FIELDS = {
    "hedge_id", "client_id", "currency_pair", "hedge_type",
    "notional_base", "strike_rate", "inception_date", "maturity_date"
}

# Regex pattern for currency pairs (e.g., 'USD/ZAR').
CURRENCY_PAIR_PATTERN = re.compile(r"^[A-Z]{3}/[A-Z]{3}$")
# Regex pattern for three-letter ISO currency codes (e.g., 'USD').
CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")
# Regex pattern for unique trade identifiers.
TRADE_ID_PATTERN = re.compile(r"^FX-[A-Z0-9]{10}$")
# Regex pattern for unique hedge identifiers.
HEDGE_ID_PATTERN = re.compile(r"^HEDGE-[A-Z0-9]{10}$")

# Permitted product types for FX trades.
VALID_TRADE_TYPES = {"SPOT", "FORWARD", "SWAP", "OPTION"}
# Permitted transaction directions.
VALID_DIRECTIONS = {"BUY", "SELL"}
# Lifecycle statuses for an FX trade.
VALID_TRADE_STATUSES = {"PENDING", "SETTLED", "FAILED", "CANCELLED"}
# Permitted hedging strategies and instrument types.
VALID_HEDGE_TYPES = {"FORWARD", "OPTION_CALL", "OPTION_PUT", "SWAP", "COLLAR"}
# Lifecycle statuses for a hedging instrument.
VALID_HEDGE_STATUSES = {"ACTIVE", "SETTLED", "TERMINATED", "EXPIRED"}


class KafkaProducerError(Exception):
    """
    Base exception for all Forex Kafka producer errors.
    """
    pass


class ValidationError(KafkaProducerError):
    """
    Exception raised when an FX event fails schema or business rule validation.
    """
    pass


class ForexKafkaProducer:
    """
    Handles the production of validated Forex events to Kafka topics.

    Supports:
    - FX trades (forex.trades)
    - Rate ticks (forex.rate_ticks)
    - Hedge instruments (forex.hedges)

    Attributes:
        topic: The target Kafka topic for the current producer instance.
        bootstrap_servers: Comma-separated list of Kafka broker addresses.
        producer: The underlying Kafka client instance.
    """

    def __init__(
        self,
        topic: str = "forex.trades",
        bootstrap_servers: str = "localhost:9092"
    ) -> None:
        """
        Initializes the Forex Kafka producer with connection and topic details.

        :param topic: Target Kafka topic. Defaults to 'forex.trades'.
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
            f"ForexKafkaProducer initialized: "
            f"topic={topic}, servers={bootstrap_servers}"
        )

    def _validate_trade(self, trade: Dict[str, Any]) -> None:
        """
        Validate FX trade data against schema requirements.

        Args:
            trade: Trade dictionary to validate

        Raises:
            ValidationError: If trade validation fails
        """
        if not isinstance(trade, dict):
            raise ValidationError("Trade must be a dictionary")

        # Check required fields
        missing_fields = REQUIRED_TRADE_FIELDS - set(trade.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        # Validate trade_id format
        trade_id = trade.get("trade_id", "")
        if not trade_id.startswith("FX-"):
            raise ValidationError(f"Invalid trade_id format: {trade_id}")

        # Validate currency pair format
        currency_pair = trade.get("currency_pair", "")
        if not CURRENCY_PAIR_PATTERN.match(currency_pair):
            raise ValidationError(f"Invalid currency_pair: {currency_pair}")

        # Validate trade type
        trade_type = trade.get("trade_type")
        if trade_type not in VALID_TRADE_TYPES:
            raise ValidationError(
                f"Invalid trade_type: {trade_type}. Must be one of {VALID_TRADE_TYPES}"
            )

        # Validate direction
        direction = trade.get("direction")
        if direction not in VALID_DIRECTIONS:
            raise ValidationError(
                f"Invalid direction: {direction}. Must be one of {VALID_DIRECTIONS}"
            )

        # Validate amount
        amount = trade.get("base_amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(f"Invalid base_amount: {amount}")

        # Validate rate
        rate = trade.get("rate")
        if not isinstance(rate, (int, float)) or rate <= 0:
            raise ValidationError(f"Invalid rate: {rate}")

        # Validate status
        status = trade.get("status")
        if status not in VALID_TRADE_STATUSES:
            raise ValidationError(
                f"Invalid status: {status}. Must be one of {VALID_TRADE_STATUSES}"
            )

        logger.debug(f"Trade validation passed: {trade_id}")

    def _validate_rate_tick(self, tick: Dict[str, Any]) -> None:
        """
        Validate rate tick data against schema requirements.

        Args:
            tick: Rate tick dictionary to validate

        Raises:
            ValidationError: If tick validation fails
        """
        if not isinstance(tick, dict):
            raise ValidationError("Rate tick must be a dictionary")

        # Check required fields
        missing_fields = REQUIRED_RATE_FIELDS - set(tick.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        # Validate currency pair format
        currency_pair = tick.get("currency_pair", "")
        if not CURRENCY_PAIR_PATTERN.match(currency_pair):
            raise ValidationError(f"Invalid currency_pair: {currency_pair}")

        # Validate rates are positive
        for rate_field in ["mid_rate", "bid_rate", "ask_rate"]:
            rate = tick.get(rate_field)
            if not isinstance(rate, (int, float)) or rate <= 0:
                raise ValidationError(f"Invalid {rate_field}: {rate}")

        # Validate bid < mid < ask
        bid = tick.get("bid_rate", 0)
        mid = tick.get("mid_rate", 0)
        ask = tick.get("ask_rate", 0)

        if not (bid < mid < ask):
            raise ValidationError(
                f"Invalid rate relationship: bid={bid}, mid={mid}, ask={ask}"
            )

        logger.debug(f"Rate tick validation passed: {tick.get('tick_id')}")

    def _validate_hedge(self, hedge: Dict[str, Any]) -> None:
        """
        Validate hedge instrument data against schema requirements.

        Args:
            hedge: Hedge dictionary to validate

        Raises:
            ValidationError: If hedge validation fails
        """
        if not isinstance(hedge, dict):
            raise ValidationError("Hedge must be a dictionary")

        # Check required fields
        missing_fields = REQUIRED_HEDGE_FIELDS - set(hedge.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        # Validate hedge_id format
        hedge_id = hedge.get("hedge_id", "")
        if not hedge_id.startswith("HEDGE-"):
            raise ValidationError(f"Invalid hedge_id format: {hedge_id}")

        # Validate currency pair format
        currency_pair = hedge.get("currency_pair", "")
        if not CURRENCY_PAIR_PATTERN.match(currency_pair):
            raise ValidationError(f"Invalid currency_pair: {currency_pair}")

        # Validate hedge type
        hedge_type = hedge.get("hedge_type")
        if hedge_type not in VALID_HEDGE_TYPES:
            raise ValidationError(
                f"Invalid hedge_type: {hedge_type}. Must be one of {VALID_HEDGE_TYPES}"
            )

        # Validate notional
        notional = hedge.get("notional_base")
        if not isinstance(notional, (int, float)) or notional <= 0:
            raise ValidationError(f"Invalid notional_base: {notional}")

        # Validate strike rate
        strike = hedge.get("strike_rate")
        if not isinstance(strike, (int, float)) or strike <= 0:
            raise ValidationError(f"Invalid strike_rate: {strike}")

        logger.debug(f"Hedge validation passed: {hedge_id}")

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

    def send_trade(
        self,
        trade: Dict[str, Any],
        key: Optional[str] = None
    ) -> None:
        """
        Send an FX trade event to Kafka.

        Args:
            trade: Trade event dictionary
            key: Optional message key

        Raises:
            ValidationError: If trade validation fails
            KafkaProducerError: If send fails
        """
        # Validate trade before sending
        self._validate_trade(trade)

        if self.producer is None:
            logger.debug(
                f"Mock send to {self.topic}: "
                f"trade_id={trade.get('trade_id', 'unknown')}"
            )
            return

        try:
            future = self.producer.send(
                self.topic,
                key=key,
                value=trade
            )

            record_metadata = future.get(timeout=10)

            logger.info(
                f"Trade sent: topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}, "
                f"trade_id={trade.get('trade_id')}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send trade {trade.get('trade_id')}: {e}"
            )
            raise KafkaProducerError(
                f"Failed to send trade: {e}"
            ) from e

    def send_rate_tick(
        self,
        tick: Dict[str, Any],
        key: Optional[str] = None
    ) -> None:
        """
        Send a rate tick event to Kafka.

        Args:
            tick: Rate tick dictionary
            key: Optional message key

        Raises:
            ValidationError: If tick validation fails
            KafkaProducerError: If send fails
        """
        self._validate_rate_tick(tick)

        if self.producer is None:
            logger.debug(
                f"Mock send to {self.topic}: "
                f"tick_id={tick.get('tick_id', 'unknown')}"
            )
            return

        try:
            future = self.producer.send(
                self.topic,
                key=key,
                value=tick
            )

            record_metadata = future.get(timeout=10)

            logger.info(
                f"Rate tick sent: topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}, "
                f"tick_id={tick.get('tick_id')}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send rate tick {tick.get('tick_id')}: {e}"
            )
            raise KafkaProducerError(
                f"Failed to send rate tick: {e}"
            ) from e

    def send_hedge(
        self,
        hedge: Dict[str, Any],
        key: Optional[str] = None
    ) -> None:
        """
        Send a hedge instrument event to Kafka.

        Args:
            hedge: Hedge dictionary
            key: Optional message key

        Raises:
            ValidationError: If hedge validation fails
            KafkaProducerError: If send fails
        """
        self._validate_hedge(hedge)

        if self.producer is None:
            logger.debug(
                f"Mock send to {self.topic}: "
                f"hedge_id={hedge.get('hedge_id', 'unknown')}"
            )
            return

        try:
            future = self.producer.send(
                self.topic,
                key=key,
                value=hedge
            )

            record_metadata = future.get(timeout=10)

            logger.info(
                f"Hedge sent: topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}, "
                f"hedge_id={hedge.get('hedge_id')}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send hedge {hedge.get('hedge_id')}: {e}"
            )
            raise KafkaProducerError(
                f"Failed to send hedge: {e}"
            ) from e

    def send_batch(
        self,
        records: List[Dict[str, Any]],
        record_type: str = "trade"
    ) -> int:
        """
        Send a batch of records.

        Args:
            records: List of record dictionaries
            record_type: Type of records ('trade', 'rate_tick', 'hedge')

        Returns:
            Number of records successfully sent
        """
        if not records:
            logger.warning("Empty batch, nothing to send")
            return 0

        sent_count = 0
        failed_count = 0

        # Select validator and sender based on record type
        validators = {
            "trade": self._validate_trade,
            "rate_tick": self._validate_rate_tick,
            "hedge": self._validate_hedge,
        }
        senders = {
            "trade": self.send_trade,
            "rate_tick": self.send_rate_tick,
            "hedge": self.send_hedge,
        }

        validator = validators.get(record_type)
        sender = senders.get(record_type)

        if not validator or not sender:
            raise ValueError(f"Unknown record_type: {record_type}")

        for idx, record in enumerate(records):
            try:
                validator(record)
                sender(record)
                sent_count += 1
            except ValidationError as e:
                failed_count += 1
                logger.error(
                    f"Validation failed for {record_type} {idx}: {e}"
                )
            except KafkaProducerError as e:
                failed_count += 1
                record_id = record.get(
                    "trade_id" or record.get("tick_id") or record.get("hedge_id")
                )
                logger.error(
                    f"Failed to send {record_type} {record_id}: {e}"
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Unexpected error for {record_type} {idx}: {e}"
                )

        if self.producer:
            self.producer.flush()

        total = len(records)
        logger.info(
            f"Batch send complete: {sent_count}/{total} sent, {failed_count} failed"
        )

        return sent_count

    def close(self) -> None:
        """Close the Kafka connection."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")
