"""
@file trade_finance_generator.py
@description Generator for synthetic CIB trade finance records, simulating letters of credit, guarantees, and documentary collections.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Trade Finance Record Generator

We generate realistic synthetic trade finance records
for the CIB domain.

Trade finance is a window into the real economy of
cross-border commerce. Unlike payment flows — which
record money that has already moved — trade finance
instruments record commitments about future trade:

1. Letters of Credit (LCs): A bank's guarantee to pay
   a beneficiary once shipment documents are presented.
   An LC issued today reveals that a cargo will ship
   within the next 30–90 days. This is 1–3 months of
   forward visibility into a client's trade corridors.

2. Bank Guarantees: A corporate's commitment to honour
   an obligation (performance, advance payment). A
   performance guarantee in a new country tells us the
   client has won a contract there — before any payment
   flows are visible.

3. Documentary Collections: A lower-risk alternative
   to LCs used between trusted trading partners. A
   documentary collection corridor that grows month-on-
   month signals a maturing trade relationship.

Commodity linkage is particularly powerful for the
AfriFlow signal engine: a cocoa LC from Ivory Coast
to Europe tells us not just about the corridor, but
about the sector. That client probably needs cargo
insurance, a hedge on EUR/XOF, and a warehouse
finance facility.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Standard math library for calculating transaction amounts and distributions
import math
# Random library for stochastic event generation based on market profiles
import random
# UUID for generating unique transaction and record identifiers
import uuid
# Dataclass for structured representation of trade finance records
from dataclasses import dataclass
# Datetime utilities for timestamping generated events
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Dict, Iterator, List, Optional

# Custom exception for configuration-related failures in the generator
from afriflow.exceptions import ConfigurationError
# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger

# Initialize module-level logger for the trade finance simulator
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Market profiles
# ---------------------------------------------------------------------------

# Key commodity exports by country.
# These profiles define the primary economic activities for each African market.
COMMODITY_CORRIDORS: Dict[str, List[str]] = {
    "NG": ["crude_oil", "cocoa", "sesame", "cashew"],
    "ZA": ["gold", "platinum", "coal", "manganese", "chrome"],
    "ZM": ["copper", "cobalt"],
    "GH": ["cocoa", "gold", "timber"],
    "CI": ["cocoa", "coffee", "cashew", "rubber"],
    "KE": ["tea", "coffee", "flowers", "horticulture"],
    "ET": ["coffee", "sesame", "oilseeds"],
    "TZ": ["gold", "tanzanite", "coffee", "cashew"],
    "AO": ["crude_oil", "diamonds", "iron_ore"],
    "CM": ["cocoa", "coffee", "crude_oil", "timber"],
    "MZ": ["coal", "natural_gas", "aluminium"],
    "RW": ["coffee", "tea", "minerals"],
}

# Active trade corridors: typical beneficiary countries per commodity origin.
# These destinations reflect actual global trade routes for major African exports.
COMMODITY_DESTINATIONS: Dict[str, List[str]] = {
    "crude_oil":   ["CN", "IN", "US", "NL", "SG"],
    "cocoa":       ["NL", "DE", "CH", "US", "BE"],
    "gold":        ["AE", "CH", "UK", "US", "HK"],
    "copper":      ["CN", "DE", "JP", "KR", "IN"],
    "cobalt":      ["CN", "JP", "KR", "US", "DE"],
    "coffee":      ["DE", "US", "FR", "IT", "JP"],
    "tea":         ["GB", "PK", "AE", "US", "EG"],
    "platinum":    ["JP", "DE", "US", "UK", "CH"],
    "coal":        ["IN", "CN", "PK", "MY", "JP"],
    "cashew":      ["IN", "VN", "US", "DE", "NL"],
    "sesame":      ["CN", "IN", "TK", "JP", "KR"],
    "natural_gas": ["MZ", "TZ", "AE", "IN"],
    "diamonds":    ["BE", "AE", "IN", "US"],
}

# Instrument types and their typical financial characteristics.
# Used to bias the simulation towards realistic amounts and tenors.
INSTRUMENT_CONFIGS: Dict[str, Dict] = {
    "letter_of_credit": {
        "min_amount_usd":    50_000,
        "max_amount_usd": 50_000_000,
        "tenor_days_range": (30, 180),
        "weight":            0.55,
    },
    "bank_guarantee": {
        "min_amount_usd":    25_000,
        "max_amount_usd": 20_000_000,
        "tenor_days_range": (90, 365),
        "weight":            0.25,
    },
    "documentary_collection": {
        "min_amount_usd":    10_000,
        "max_amount_usd":  5_000_000,
        "tenor_days_range": (30, 90),
        "weight":            0.20,
    },
}

# Currencies used in trade finance by corridor
TRADE_CURRENCIES = ["USD", "EUR", "GBP", "CNY", "AED"]

STATUS_WEIGHTS = {
    "issued":    0.60,
    "utilized":  0.25,
    "expired":   0.10,
    "cancelled": 0.05,
}

# Approximate USD to local currency rates
USD_RATES: Dict[str, float] = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79,
    "CNY": 7.25, "AED": 3.67,
}


@dataclass
class TradeFinanceRecord:
    """
    A single trade finance instrument record.

    We publish these to the CIB domain Kafka topic
    (cib.trade_finance.records) in Avro format.

    The commodity field links this to commodity
    market analytics and to the insurance domain
    (cargo insurance cross-sell).
    """

    tf_id: str
    record_type: str
    applicant_id: str
    beneficiary_id: str
    applicant_country: str
    beneficiary_country: str
    currency: str
    amount: float
    commodity: Optional[str]
    issue_date: datetime
    expiry_date: datetime
    status: str


class TradeFinanceGenerator:
    """
    We generate realistic synthetic trade finance records
    for testing and demo purposes.

    Usage:

        gen = TradeFinanceGenerator(seed=42)

        # Generate a single LC
        lc = gen.generate_lc(
            applicant_id="CLIENT-001",
            applicant_country="GH",
            beneficiary_country="NL",
        )

        # Generate a commodity LC
        cocoa_lc = gen.generate_commodity_lc(
            commodity="cocoa",
            origin_country="CI",
            destination_country="DE",
        )

        # Stream 30 days of trade finance records
        for record in gen.stream_trade_finance(days=30):
            publish_to_kafka(record)
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)

        # Pool of synthetic corporate client IDs
        self._client_pool: List[str] = [
            f"CORP-{uuid.uuid4().hex[:8].upper()}" for _ in range(150)
        ]

    def _amount(self, record_type: str) -> float:
        """
        We generate a realistic trade finance amount
        using a log-normal distribution within the
        configured bounds for the instrument type.
        """

        config = INSTRUMENT_CONFIGS.get(record_type, INSTRUMENT_CONFIGS["letter_of_credit"])
        min_usd = config["min_amount_usd"]
        max_usd = config["max_amount_usd"]
        mid_usd = (min_usd * max_usd) ** 0.5  # Geometric mean

        amount = math.exp(random.gauss(math.log(mid_usd), 1.2))
        return round(max(min_usd, min(amount, max_usd)), 2)

    def _tenor(self, record_type: str) -> int:
        """
        We select a realistic tenor (validity period)
        in days for the given instrument type.
        """

        config = INSTRUMENT_CONFIGS.get(record_type, INSTRUMENT_CONFIGS["letter_of_credit"])
        min_days, max_days = config["tenor_days_range"]
        return random.randint(min_days, max_days)

    def generate_lc(
        self,
        applicant_id: str,
        applicant_country: str,
        beneficiary_country: str,
        issue_date: Optional[datetime] = None,
        commodity: Optional[str] = None,
    ) -> TradeFinanceRecord:
        """
        We generate a Letter of Credit instrument.

        The applicant (importer) opens the LC at their
        bank. The beneficiary (exporter) draws on it
        when they present shipping documents.

        If commodity is None we attempt to infer a
        likely commodity from the applicant country's
        export profile.
        """

        record_type = "letter_of_credit"
        amount = self._amount(record_type)
        tenor_days = self._tenor(record_type)

        issued = issue_date or datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, 60)
        )
        expiry = issued + timedelta(days=tenor_days)

        # Infer commodity if not provided
        if commodity is None and random.random() < 0.7:
            country_commodities = COMMODITY_CORRIDORS.get(applicant_country, [])
            if country_commodities:
                commodity = random.choice(country_commodities)

        currency = random.choices(
            TRADE_CURRENCIES,
            weights=[0.55, 0.25, 0.10, 0.07, 0.03],
        )[0]

        beneficiary_id = f"BEN-{uuid.uuid4().hex[:8].upper()}"

        status = random.choices(
            list(STATUS_WEIGHTS.keys()),
            weights=list(STATUS_WEIGHTS.values()),
        )[0]

        # Log details using 'extra' to attach structured fields without breaking
        # logging API expectations.
        logger.debug(
            "Generated LC",
            extra={
                "applicant_id": applicant_id,
                "applicant_country": applicant_country,
                "beneficiary_country": beneficiary_country,
                "amount_usd": amount,
                "commodity": commodity,
            },
        )

        return TradeFinanceRecord(
            tf_id=f"TF-LC-{uuid.uuid4().hex[:10].upper()}",
            record_type=record_type,
            applicant_id=applicant_id,
            beneficiary_id=beneficiary_id,
            applicant_country=applicant_country,
            beneficiary_country=beneficiary_country,
            currency=currency,
            amount=amount,
            commodity=commodity,
            issue_date=issued,
            expiry_date=expiry,
            status=status,
        )

    def generate_bank_guarantee(
        self,
        applicant_id: str,
        country: str,
        issue_date: Optional[datetime] = None,
    ) -> TradeFinanceRecord:
        """
        We generate a Bank Guarantee instrument.

        Bank guarantees are typically domestic or
        cross-border construction, supply, and
        performance contracts. The beneficiary is
        the counterparty who demanded the guarantee.
        """

        record_type = "bank_guarantee"
        amount = self._amount(record_type)
        tenor_days = self._tenor(record_type)

        issued = issue_date or datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, 90)
        )
        expiry = issued + timedelta(days=tenor_days)

        # Guarantee beneficiary is often in the same or
        # a neighbouring country (infrastructure projects)
        neighbouring: Dict[str, List[str]] = {
            "ZA": ["NA", "MZ", "ZM", "ZW"],
            "NG": ["GH", "CM", "BJ", "NE"],
            "KE": ["TZ", "UG", "RW", "ET"],
        }
        beneficiary_country = random.choice(
            neighbouring.get(country, [country, "AE", "UK"])
        )

        return TradeFinanceRecord(
            tf_id=f"TF-BG-{uuid.uuid4().hex[:10].upper()}",
            record_type=record_type,
            applicant_id=applicant_id,
            beneficiary_id=f"BEN-{uuid.uuid4().hex[:8].upper()}",
            applicant_country=country,
            beneficiary_country=beneficiary_country,
            currency=random.choice(["USD", "EUR", "local"]),
            amount=amount,
            commodity=None,
            issue_date=issued,
            expiry_date=expiry,
            status=random.choices(
                list(STATUS_WEIGHTS.keys()),
                weights=list(STATUS_WEIGHTS.values()),
            )[0],
        )

    def generate_commodity_lc(
        self,
        commodity: str,
        origin_country: str,
        destination_country: Optional[str] = None,
    ) -> TradeFinanceRecord:
        """
        We generate a commodity-specific Letter of Credit.

        Commodity LCs tend to be larger in value and have
        tighter tenors than general trade LCs. We infer
        the destination from the commodity's typical
        export markets if not specified.
        """

        if commodity not in {
            c for comms in COMMODITY_CORRIDORS.values() for c in comms
        }:
            raise ConfigurationError(
                f"Unknown commodity '{commodity}'. "
                f"See COMMODITY_CORRIDORS for valid options."
            )

        if destination_country is None:
            destinations = COMMODITY_DESTINATIONS.get(commodity, ["US", "DE", "CN"])
            destination_country = random.choice(destinations)

        applicant_id = random.choice(self._client_pool)

        # Commodity LCs are typically larger
        config = INSTRUMENT_CONFIGS["letter_of_credit"]
        amount = math.exp(random.gauss(
            math.log(config["max_amount_usd"] * 0.3), 0.8
        ))
        amount = round(max(config["min_amount_usd"], amount), 2)

        tenor_days = random.randint(30, 90)  # Tighter tenors for commodity
        issued = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
        expiry = issued + timedelta(days=tenor_days)

        return TradeFinanceRecord(
            tf_id=f"TF-CMDTY-{uuid.uuid4().hex[:10].upper()}",
            record_type="letter_of_credit",
            applicant_id=applicant_id,
            beneficiary_id=f"BEN-{uuid.uuid4().hex[:8].upper()}",
            applicant_country=origin_country,
            beneficiary_country=destination_country,
            currency=random.choices(["USD", "EUR"], weights=[0.70, 0.30])[0],
            amount=amount,
            commodity=commodity,
            issue_date=issued,
            expiry_date=expiry,
            status=random.choices(
                list(STATUS_WEIGHTS.keys()),
                weights=list(STATUS_WEIGHTS.values()),
            )[0],
        )

    def stream_trade_finance(
        self,
        days: int = 30,
    ) -> Iterator[TradeFinanceRecord]:
        """
        We yield a stream of trade finance records
        spanning the given number of days.

        Daily volume follows a business-day pattern —
        trade finance is predominantly processed on
        weekdays. End-of-quarter sees elevated LC
        issuance as corporates finalise supply contracts.
        """

        start = datetime.now(timezone.utc) - timedelta(days=days)
        record_types = list(INSTRUMENT_CONFIGS.keys())
        type_weights = [
            INSTRUMENT_CONFIGS[t]["weight"] for t in record_types
        ]

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)
            weekday = current_day.weekday()

            if weekday >= 5:  # Weekend — minimal activity
                daily_count = random.randint(0, 2)
            else:
                daily_count = random.randint(8, 25)

            # End of quarter boost
            if current_day.month in (3, 6, 9, 12) and current_day.day >= 20:
                daily_count = int(daily_count * 1.40)

            for _ in range(daily_count):
                record_type = random.choices(record_types, weights=type_weights)[0]
                applicant_id = random.choice(self._client_pool)

                # Pick a corridor from the commodity map
                origin = random.choice(list(COMMODITY_CORRIDORS.keys()))
                commodity = random.choice(COMMODITY_CORRIDORS[origin])
                destinations = COMMODITY_DESTINATIONS.get(
                    commodity, ["US", "DE", "CN"]
                )
                destination = random.choice(destinations)

                issue_date = current_day.replace(
                    hour=random.randint(8, 17),
                    minute=random.randint(0, 59),
                )

                if record_type == "letter_of_credit":
                    yield self.generate_lc(
                        applicant_id=applicant_id,
                        applicant_country=origin,
                        beneficiary_country=destination,
                        issue_date=issue_date,
                        commodity=commodity,
                    )
                elif record_type == "bank_guarantee":
                    yield self.generate_bank_guarantee(
                        applicant_id=applicant_id,
                        country=origin,
                        issue_date=issue_date,
                    )
                else:
                    yield self.generate_lc(
                        applicant_id=applicant_id,
                        applicant_country=origin,
                        beneficiary_country=destination,
                        issue_date=issue_date,
                        commodity=commodity,
                    )


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = TradeFinanceGenerator(seed=42)

    print("=== Letter of Credit (Ghana → Netherlands) ===")
    lc = gen.generate_lc(
        applicant_id="CORP-DEMO-001",
        applicant_country="GH",
        beneficiary_country="NL",
    )
    print(f"  tf_id              : {lc.tf_id}")
    print(f"  record_type        : {lc.record_type}")
    print(f"  commodity          : {lc.commodity}")
    print(f"  amount {lc.currency:3s}          : {lc.amount:,.2f}")
    print(f"  issue → expiry     : {lc.issue_date.date()} → {lc.expiry_date.date()}")
    print(f"  status             : {lc.status}")

    print("\n=== Commodity LC (Zambia copper → China) ===")
    copper_lc = gen.generate_commodity_lc("copper", "ZM", "CN")
    print(f"  amount {copper_lc.currency:3s}          : {copper_lc.amount:,.2f}")
    print(f"  corridor           : {copper_lc.applicant_country} → {copper_lc.beneficiary_country}")

    print("\n=== Stream (first 5 records over 7 days) ===")
    for i, rec in enumerate(gen.stream_trade_finance(days=7)):
        print(
            f"  [{rec.issue_date.date()}] {rec.record_type:24s} | "
            f"{rec.applicant_country} → {rec.beneficiary_country:3s} | "
            f"{rec.currency} {rec.amount:>12,.0f} | {rec.commodity or '—'}"
        )
        if i >= 4:
            break
