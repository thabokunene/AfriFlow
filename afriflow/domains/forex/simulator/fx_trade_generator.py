"""
@file fx_trade_generator.py
@description Synthetic FX trade generator modeling African market characteristics and seasonality
@author Thabo Kunene
@created 2026-03-17
"""

"""
FX Trade Generator

We generate realistic synthetic FX trade records
for the forex domain.

African FX trading has unique characteristics:
1. NDF dominance: Many African currencies trade
   as non-deliverable forwards due to capital controls
2. Seasonal patterns: Agricultural export seasons
   create predictable USD inflow/outflow cycles
3. Central bank interventions: Sudden rate changes
   when reserves fall below critical thresholds
4. Parallel market arbitrage: Trades often hedge
   against parallel market movements
5. Liquidity fragmentation: Different liquidity
   profiles across Johannesburg, Lagos, Nairobi hubs

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

from __future__ import annotations  # allow forward-referenced type hints for dataclasses
import random  # stochastic variability for rates and notional sizes
import uuid  # unique trade identifiers generation
import logging  # operational telemetry for generation lifecycle
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone  # UTC timestamps and date arithmetic
from typing import Iterator, Optional, Dict, Any, List

from afriflow.logging_config import get_logger  # centralized JSON logging with structured context
from afriflow.domains.shared.interfaces import SimulatorBase  # base simulator contract for consistency

logger = get_logger("domains.forex.simulator.fx_trade_generator")


@dataclass
class FXTrade:
    """
    A single FX trade record.

    We publish these to the forex domain Kafka topic
    (forex.fx_trades) in Avro format.
    """

    trade_id: str
    client_id: str
    client_golden_id: Optional[str]
    trade_type: str  # spot | forward | swap | option | ndf
    currency_pair: str
    direction: str  # buy_usd | sell_usd
    notional_usd: float
    rate: float
    value_date: str
    maturity_date: Optional[str]
    is_hedge: bool
    underlying_payment_id: Optional[str]
    country: str
    traded_at: str
    ingested_at: str
    schema_version: str = "1.0"


# African currency pairs with typical characteristics
AFRICAN_CURRENCY_PAIRS = [
    "USD/ZAR", "USD/NGN", "USD/KES", "USD/GHS", "USD/TZS",
    "USD/UGX", "USD/ZMW", "USD/MZN", "USD/AOA", "USD/XOF",
    "USD/XAF", "USD/RWF", "USD/ETB", "USD/MWK", "USD/BWP",
    "USD/NAD", "USD/ZWL", "USD/CDF", "USD/SSP"
]

# Countries corresponding to currency pairs
PAIR_COUNTRIES = {
    "USD/ZAR": "South Africa", "USD/NGN": "Nigeria", "USD/KES": "Kenya",
    "USD/GHS": "Ghana", "USD/TZS": "Tanzania", "USD/UGX": "Uganda",
    "USD/ZMW": "Zambia", "USD/MZN": "Mozambique", "USD/AOA": "Angola",
    "USD/XOF": "West Africa", "USD/XAF": "Central Africa", "USD/RWF": "Rwanda",
    "USD/ETB": "Ethiopia", "USD/MWK": "Malawi", "USD/BWP": "Botswana",
    "USD/NAD": "Namibia", "USD/ZWL": "Zimbabwe", "USD/CDF": "DRC",
    "USD/SSP": "South Sudan"
}

# Currencies with NDF (Non-Deliverable Forward) markets
NDF_CURRENCIES = {"NGN", "KES", "GHS", "TZS", "UGX", "ZMW", "MZN", "AOA", "ETB", "ZWL", "CDF", "SSP"}

# Typical trade sizes by currency (USD notional)
TYPICAL_NOTIONALS = {
    "USD/ZAR": (100000, 5000000),     # Very liquid
    "USD/NGN": (50000, 1000000),      # Liquid but controlled
    "USD/KES": (25000, 500000),       # Moderate liquidity
    "USD/GHS": (25000, 300000),       # Thin but active
    "USD/TZS": (10000, 200000),       # Illiquid
    "USD/UGX": (15000, 300000),       # Illiquid
    "USD/ZMW": (20000, 400000),       # Copper-linked
    "USD/MZN": (10000, 150000),       # Very thin
    "USD/AOA": (15000, 250000),       # Controlled
    "USD/XOF": (50000, 1000000),      # EUR-pegged stable
    "USD/XAF": (50000, 1000000),      # EUR-pegged stable
    "USD/RWF": (5000, 100000),        # Very thin
    "USD/ETB": (10000, 200000),       # Controlled
    "USD/MWK": (5000, 80000),         # Very thin
    "USD/BWP": (30000, 600000),       # Diamond-linked
    "USD/NAD": (100000, 2000000),     # ZAR-pegged
    "USD/ZWL": (5000, 50000),         # Hyperinflation
    "USD/CDF": (10000, 150000),       # Mining-linked
    "USD/SSP": (5000, 50000),         # Conflict-affected
}

# Seasonal patterns for African currencies (monthly multipliers)
SEASONAL_MULTIPLIERS = {
    1: 0.8,   # January: Post-holiday lull
    2: 0.9,   # February: Quiet period
    3: 1.2,   # March: Agricultural prepayments
    4: 1.3,   # April: Export season begins
    5: 1.4,   # May: Peak export activity
    6: 1.3,   # June: Continued exports
    7: 0.7,   # July: Mid-year lull
    8: 0.8,   # August: Pre-harvest quiet
    9: 1.1,   # September: Harvest season
    10: 1.2,  # October: Export proceeds
    11: 1.0,  # November: Normal activity
    12: 0.9,  # December: Holiday slowdown
}


class FXTradeGenerator(SimulatorBase):
    """
    We generate realistic synthetic FX trades
    for testing and demo purposes.

    Usage:
        gen = FXTradeGenerator(seed=42)

        # Generate a single trade
        trade = gen.generate_one(pair="USD/NGN")

        # Stream multiple trades
        for trade in gen.stream(count=100):
            process(trade)

        # Generate hedging trades
        hedge_trades = gen.generate_hedge_trades(
            underlying_payment="PAY-123",
            currency="NGN",
            amount_usd=100000
        )
    """

    def __init__(self, config=None):
        # Use shared logger; allow config injection for deterministic seeds or environment parameters
        self.logger = logger
        super().__init__(config)

    def initialize(self, config=None) -> None:
        """
        Initialize generator with configuration.
        Notes:
        - Supports future expansion (e.g., loading seasonal calendars from YAML).
        """
        self.config = config or self.config
        self.logger.info("FX Trade Generator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters for trade generation.
        Raises ValueError when unsupported pairs/types/directions are provided.
        """
        pair = kwargs.get("pair")
        if pair and pair not in AFRICAN_CURRENCY_PAIRS:
            raise ValueError(f"Unsupported currency pair: {pair}")
        
        trade_type = kwargs.get("trade_type")
        if trade_type and trade_type not in ["spot", "forward", "swap", "option", "ndf"]:
            raise ValueError(f"Invalid trade type: {trade_type}")

        direction = kwargs.get("direction")
        if direction and direction not in ["buy_usd", "sell_usd"]:
            raise ValueError(f"Invalid direction: {direction}")

        notional = kwargs.get("notional_usd")
        if notional and notional <= 0:
            raise ValueError("Notional must be positive")

    def _get_random_rate(self, pair: str) -> float:
        """
        Generate a realistic exchange rate for the given pair.
        Combines baseline reference rates with controlled random variation.
        """
        # Base rates from the rate feed generator
        base_rates = {
            "USD/ZAR": 18.50, "USD/NGN": 1580.0, "USD/KES": 130.0,
            "USD/GHS": 15.5, "USD/TZS": 2550.0, "USD/UGX": 3750.0,
            "USD/ZMW": 27.5, "USD/MZN": 64.0, "USD/AOA": 870.0,
            "USD/XOF": 610.0, "USD/XAF": 610.0, "USD/RWF": 1280.0,
            "USD/ETB": 56.0, "USD/MWK": 1730.0, "USD/BWP": 13.8,
            "USD/NAD": 18.5, "USD/ZWL": 5800.0, "USD/CDF": 2800.0,
            "USD/SSP": 1300.0
        }
        
        base_rate = base_rates.get(pair, 100.0)
        
        # Variation captures daily market movement; higher for volatile pairs
        volatile_pairs = {"USD/ZWL", "USD/SSP", "USD/NGN", "USD/AOA", "USD/ETB"}
        max_variation = 0.05 if pair in volatile_pairs else 0.02
        
        variation = random.uniform(-max_variation, max_variation)
        return round(base_rate * (1 + variation), 4)

    def _generate_value_date(self, trade_type: str, traded_at: datetime) -> str:
        """
        Generate appropriate value date based on trade type.
        Spot: typically T+2; Forwards: chosen tenor; Swaps: short tenors.
        """
        if trade_type == "spot":
            # T+2 settlement for most currencies, T+1 for some
            settlement_days = 2
            if "ZAR" in traded_at.strftime("%A"):  # Check if traded on Friday
                settlement_days = 4  # Skip weekend
        elif trade_type == "forward":
            # 30, 60, 90 days forward
            settlement_days = random.choice([30, 60, 90])
        elif trade_type == "swap":
            # Tomorrow/next or spot/next
            settlement_days = random.choice([1, 2])
        else:  # ndf, option
            settlement_days = random.choice([30, 60, 90, 180])
        
        value_date = traded_at + timedelta(days=settlement_days)
        return value_date.strftime("%Y-%m-%d")

    def generate_one(self, **kwargs) -> FXTrade:
        """
        Generate a single FXTrade with seasonality-adjusted notional and realistic dates.
        Returns FXTrade dataclass instance.
        """
        self.validate_input(**kwargs)
        
        # Default parameters
        pair = kwargs.get("pair") or random.choice(AFRICAN_CURRENCY_PAIRS)
        country = PAIR_COUNTRIES[pair]
        
        # Determine trade type based on currency
        base_currency = pair.split("/")[1]  # e.g., ZAR in USD/ZAR
        trade_type = kwargs.get("trade_type")
        if not trade_type:
            if base_currency in NDF_CURRENCIES:
                trade_type = random.choice(["spot", "ndf", "forward"])
            else:
                trade_type = random.choice(["spot", "forward", "swap"])
        
        direction = kwargs.get("direction") or random.choice(["buy_usd", "sell_usd"])
        
        # Determine notional based on currency liquidity
        min_notional, max_notional = TYPICAL_NOTIONALS.get(pair, (10000, 500000))
        notional_usd = kwargs.get("notional_usd") or random.randint(min_notional, max_notional)
        
        # Apply seasonal multiplier to notional to reflect export/import seasonality
        current_month = datetime.now(timezone.utc).month
        seasonal_multiplier = SEASONAL_MULTIPLIERS.get(current_month, 1.0)
        notional_usd = int(notional_usd * seasonal_multiplier)
        
        # Generate rate
        rate = self._get_random_rate(pair)
        
        # Generate dates
        traded_at = kwargs.get("traded_at") or datetime.now(timezone.utc)
        if isinstance(traded_at, str):
            traded_at = datetime.fromisoformat(traded_at.replace("Z", "+00:00"))
        
        value_date = self._generate_value_date(trade_type, traded_at)
        
        # Generate maturity date for forwards/ndf contracts; swaps may not require explicit maturity here
        maturity_date = None
        if trade_type in ["forward", "ndf"]:
            maturity_days = random.choice([30, 60, 90, 180])
            maturity_dt = traded_at + timedelta(days=maturity_days)
            maturity_date = maturity_dt.strftime("%Y-%m-%d")
        
        # Client information
        client_id = kwargs.get("client_id") or f"CLIENT-{random.randint(1000, 9999)}"
        client_golden_id = kwargs.get("client_golden_id") or (f"GOLDEN-{client_id}" if random.random() > 0.3 else None)
        
        # Hedging information to link trades to underlying payments when provided
        is_hedge = kwargs.get("is_hedge", False)
        underlying_payment_id = kwargs.get("underlying_payment_id") or (f"PAY-{random.randint(10000, 99999)}" if is_hedge else None)
        
        return FXTrade(
            trade_id=f"TRADE-{uuid.uuid4().hex[:8].upper()}",
            client_id=client_id,
            client_golden_id=client_golden_id,
            trade_type=trade_type,
            currency_pair=pair,
            direction=direction,
            notional_usd=notional_usd,
            rate=rate,
            value_date=value_date,
            maturity_date=maturity_date,
            is_hedge=is_hedge,
            underlying_payment_id=underlying_payment_id,
            country=country,
            traded_at=traded_at.isoformat(),
            ingested_at=datetime.now(timezone.utc).isoformat(),
            schema_version="1.0"
        )

    def generate_hedge_trades(self, underlying_payment: str, currency: str, amount_usd: float, count: int = 1) -> List[FXTrade]:
        """
        Generate hedging trades for an underlying payment.
        Ensures valid pair selection and uses appropriate contract type by currency.
        """
        trades = []
        
        # Find appropriate currency pair
        pair = f"USD/{currency}"
        if pair not in AFRICAN_CURRENCY_PAIRS:
            # Try reverse pair
            pair = f"{currency}/USD"
            if pair not in AFRICAN_CURRENCY_PAIRS:
                raise ValueError(f"No trading pair available for currency: {currency}")
        
        for _ in range(count):
            # Hedging trades are typically forward or NDF
            trade_type = "ndf" if currency in NDF_CURRENCIES else "forward"
            
            trade = self.generate_one(
                pair=pair,
                trade_type=trade_type,
                notional_usd=amount_usd,
                is_hedge=True,
                underlying_payment_id=underlying_payment,
                direction="sell_usd"  # Typically selling USD to hedge local currency exposure
            )
            trades.append(trade)
        
        return trades

    def stream(self, count: int = 1, **kwargs) -> Iterator[FXTrade]:
        """
        Stream multiple FX trades.
        Logs begin/end of stream and yields count trades using generate_one().
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} FX trades")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} FX trades")
