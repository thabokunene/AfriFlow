"""
@file hedging_simulator.py
@description Generator for synthetic FX hedging instruments, simulating risk management strategies for African corporate clients.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Hedging Simulator

We generate realistic synthetic FX hedging instruments
for African currency pairs.

Corporate clients in Africa use various hedging instruments
to manage FX risk:

1. Forwards: Lock in a future exchange rate. Most common
   for importers with known future USD requirements.
2. Options: Right but not obligation to exchange at a
   strike rate. Used when cash flows are uncertain.
3. Swaps: Simultaneous spot and forward. Used for
   rolling over hedges or funding in different currencies.
4. Collars: Buy put + sell call. Limits both downside
   and upside — reduces premium cost.

Hedge effectiveness is measured by comparing hedge P&L
to underlying exposure P&L. A perfect hedge has 100%
effectiveness (offsets all exposure).

Disclaimer: This is not a sanctioned Standard Bank
Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# UUID for generating unique instrument and record identifiers
import uuid
# Random library for stochastic event generation based on market profiles
import random
# Standard logging for operational telemetry and audit trails
import logging
# Dataclasses for structured representation of hedging instrument records
from dataclasses import dataclass
# Datetime utilities for timestamping and maturity calculations
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Dict, Iterator, List, Optional

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase
# Custom exception for configuration-related failures
from afriflow.exceptions import ConfigurationError

# Initialize logger for the hedging simulator namespace
logger = get_logger("domains.forex.simulator.hedging_simulator")


# Permitted instrument types for FX hedging.
HEDGE_TYPES = ["FORWARD", "OPTION_CALL", "OPTION_PUT", "SWAP", "COLLAR"]

# Permitted lifecycle statuses for a hedging instrument.
HEDGE_STATUS = ["ACTIVE", "SETTLED", "TERMINATED", "EXPIRED"]

# Common tenor durations (in days) for standard corporate banking hedges.
HEDGE_TENORS = [30, 60, 90, 180, 365]


@dataclass
class HedgeInstrument:
    """
    A single FX hedge instrument record.
    Represents a contract designed to offset currency risk.

    Attributes:
        hedge_id: Unique identifier for the hedge.
        client_id: Identifier of the corporate client.
        currency_pair: The currency pair being hedged (e.g., 'USD/ZAR').
        hedge_type: The nature of the instrument (FORWARD, OPTION, etc.).
        direction: BUY or SELL perspective of the client.
        notional_base: The face value of the hedge in the base currency.
        strike_rate: The pre-agreed exchange rate.
        current_rate: The prevailing market rate at the time of record.
        mark_to_market_usd: The current unrealized P&L of the hedge in USD.
        hedge_effectiveness_pct: Calculated percentage of exposure offset.
        inception_date: ISO timestamp when the hedge was initiated.
        maturity_date: ISO timestamp when the hedge expires.
        status: Current lifecycle state of the instrument.
        underlying_exposure_id: Optional link to the specific exposure being offset.
    """

    hedge_id: str
    client_id: str
    currency_pair: str
    hedge_type: str
    direction: str
    notional_base: float
    strike_rate: float
    current_rate: float
    mark_to_market_usd: float
    hedge_effectiveness_pct: float
    inception_date: datetime
    maturity_date: datetime
    status: str
    underlying_exposure_id: Optional[str]


class HedgingSimulator(SimulatorBase):
    """
    Generator for realistic synthetic FX hedge instruments.
    Useful for testing hedge accounting systems and risk analytics.

    Usage:
        gen = HedgingSimulator()
        hedge = gen.generate_forward("USD/ZAR", notional=1_000_000)
    """

    # Approximate spot rates used as a baseline for strike and current rate generation.
    SPOT_RATES = {
        "USD/ZAR": 18.50, "USD/NGN": 1580.0, "USD/KES": 130.0,
        "USD/GHS": 15.5, "EUR/ZAR": 20.0, "GBP/ZAR": 23.5,
    }

    def __init__(self, seed: Optional[int] = None, config=None):
        """
        Initializes the hedging simulator.

        :param seed: Optional random seed for deterministic generation.
        :param config: Optional AppConfig override.
        """
        if seed is not None:
            random.seed(seed)
        logger.info("HedgingSimulator initialized")
        super().__init__(config)

    def initialize(self, config=None) -> None:
        """Initialize the generator with default settings."""
        self._pairs = list(self.SPOT_RATES.keys())
        self._hedge_types = HEDGE_TYPES
        self._tenors = HEDGE_TENORS
        logger.info("HedgingSimulator configuration loaded")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If currency_pair is invalid or notional is malformed
        """
        pair = kwargs.get("currency_pair")
        if pair is not None and pair not in self._pairs:
            raise ValueError(f"Invalid currency_pair: {pair}")

        notional = kwargs.get("notional")
        if notional is not None:
            if not isinstance(notional, (int, float)) or notional <= 0:
                raise ValueError("notional must be a positive number")

        tenor = kwargs.get("tenor_days")
        if tenor is not None:
            if not isinstance(tenor, int) or tenor < 1 or tenor > 730:
                raise ValueError("tenor_days must be between 1 and 730")

    def _get_forward_rate(
        self,
        currency_pair: str,
        tenor_days: int,
    ) -> float:
        """
        Calculate a simulated forward rate.

        Forward rate = Spot * (1 + (rate_diff * tenor/365))
        Simplified for simulation purposes.
        """
        spot = self.SPOT_RATES.get(currency_pair, 1.0)

        # Simulated interest rate differential (annualized)
        # Positive means foreign rates higher → forward premium
        rate_diff = random.uniform(-0.03, 0.08)

        forward = spot * (1 + rate_diff * tenor_days / 365)
        return round(forward, 4)

    def _calculate_mtm(
        self,
        hedge_type: str,
        direction: str,
        strike: float,
        current: float,
        notional: float,
    ) -> float:
        """
        Calculate mark-to-market value of the hedge.

        For a BUY hedge: MTM = (current - strike) * notional
        For a SELL hedge: MTM = (strike - current) * notional
        """
        if direction == "BUY":
            mtm = (current - strike) * notional
        else:
            mtm = (strike - current) * notional

        # Options have time value — add premium adjustment
        if "OPTION" in hedge_type:
            # Simplified: add 2-5% time value
            time_value = abs(mtm) * random.uniform(0.02, 0.05)
            mtm += time_value if mtm > 0 else -time_value

        return round(mtm, 2)

    def _calculate_effectiveness(
        self,
        mtm_usd: float,
        notional: float,
        spot_change_pct: float,
    ) -> float:
        """
        Calculate hedge effectiveness percentage.

        Effectiveness = Hedge P&L / Exposure P&L * 100
        Perfect hedge = 100% (fully offsets exposure)
        """
        if spot_change_pct == 0:
            return 100.0

        exposure_pnl = notional * spot_change_pct / 100
        if exposure_pnl == 0:
            return 100.0

        effectiveness = (mtm_usd / exposure_pnl) * 100
        # Clamp to realistic range (hedges are rarely perfect)
        return round(max(0.0, min(120.0, effectiveness)), 1)

    def generate_forward(
        self,
        currency_pair: str,
        notional: float = 1_000_000,
        tenor_days: int = 90,
        client_id: Optional[str] = None,
    ) -> HedgeInstrument:
        """
        Generate a forward hedge instrument.

        Args:
            currency_pair: Currency pair to hedge
            notional: Hedge notional in base currency
            tenor_days: Days to maturity
            client_id: Optional client identifier

        Returns:
            HedgeInstrument instance
        """
        return self.generate_one(
            currency_pair=currency_pair,
            hedge_type="FORWARD",
            notional=notional,
            tenor_days=tenor_days,
            client_id=client_id,
        )

    def generate_one(self, **kwargs) -> HedgeInstrument:
        """
        Generate a single hedge instrument.

        Args:
            **kwargs: Optional overrides for hedge parameters

        Returns:
            HedgeInstrument instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

            inception_date = datetime.now(timezone.utc) - timedelta(
                days=random.randint(1, 180)
            )

            client_id = kwargs.get("client_id")
            currency_pair = kwargs.get("currency_pair") or random.choice(self._pairs)
            hedge_type = kwargs.get("hedge_type") or random.choice(self._hedge_types)
            tenor = kwargs.get("tenor_days") or random.choice(self._tenors)

            maturity_date = inception_date + timedelta(days=tenor)

            notional = kwargs.get("notional") or random.uniform(
                100_000, 10_000_000
            )
            notional = round(notional, 2)

            direction = kwargs.get("direction") or random.choice(["BUY", "SELL"])

            # Calculate strike (forward rate at inception)
            strike = self._get_forward_rate(currency_pair, tenor)

            # Current rate (simulated movement from strike)
            spot_change = random.uniform(-0.15, 0.15)  # ±15% movement
            current = strike * (1 + spot_change)
            current = round(current, 4)

            # Mark-to-market
            mtm = self._calculate_mtm(
                hedge_type, direction, strike, current, notional
            )

            # Hedge effectiveness
            effectiveness = self._calculate_effectiveness(
                mtm, notional, spot_change * 100
            )

            # Status based on maturity
            if maturity_date < datetime.now(timezone.utc):
                status = random.choice(["SETTLED", "EXPIRED"])
            elif random.random() < 0.05:
                status = "TERMINATED"
            else:
                status = "ACTIVE"

            hedge = HedgeInstrument(
                hedge_id=f"HEDGE-{uuid.uuid4().hex[:10].upper()}",
                client_id=client_id or f"CLIENT-{uuid.uuid4().hex[:8].upper()}",
                currency_pair=currency_pair,
                hedge_type=hedge_type,
                direction=direction,
                notional_base=notional,
                strike_rate=strike,
                current_rate=current,
                mark_to_market_usd=mtm,
                hedge_effectiveness_pct=effectiveness,
                inception_date=inception_date,
                maturity_date=maturity_date,
                status=status,
                underlying_exposure_id=f"EXP-{uuid.uuid4().hex[:8].upper()}",
            )

            logger.debug(
                f"Generated hedge: {hedge.hedge_id} "
                f"{currency_pair} {hedge_type} {notional:,.0f} "
                f"MTM: ${mtm:,.2f} ({effectiveness:.0f}% effective)"
            )

            return hedge

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate hedge instrument: {e}")
            raise RuntimeError(f"Hedge generation failed: {e}") from e

    def generate_batch(
        self,
        count: int,
        currency_pair: Optional[str] = None,
    ) -> List[HedgeInstrument]:
        """
        Generate a batch of hedge instruments.

        Args:
            count: Number of hedges to generate
            currency_pair: Optional fixed currency pair

        Returns:
            List of HedgeInstrument instances
        """
        if count <= 0:
            logger.warning(f"Invalid batch count: {count}")
            return []

        logger.info(f"Generating batch of {count} hedge instruments")

        hedges = [
            self.generate_one(currency_pair=currency_pair)
            for _ in range(count)
        ]

        logger.info(f"Generated {len(hedges)} hedge instruments")
        return hedges

    def stream(self, count: int = 1, **kwargs) -> Iterator[HedgeInstrument]:
        """
        Stream hedge instruments.

        Args:
            count: Number of hedges to generate
            **kwargs: Passed to generate_one

        Yields:
            HedgeInstrument instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} hedge instruments")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} hedge instruments")
