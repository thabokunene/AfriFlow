"""
@file momo_generator.py
@description Generator for synthetic Mobile Money (MoMo) transactions, simulating P2P, P2B, B2P, and cross-border flows.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Mobile Money (MoMo) Transaction Generator

We generate realistic synthetic MoMo transaction
events for the cell domain.

MoMo is not just a payment method in Africa — it is
the primary financial infrastructure for a large
portion of the population and the economic indicator
we use to track:

1. Geographic expansion: A new corporate client
   activating SIMs + seeing MoMo payroll deposits
   in a new country signals expansion before they
   tell their banker.
2. Cash flow health: MoMo merchant receipt volumes
   correlate strongly with business revenue in
   markets where formal banking penetration is low.
3. Salary cycles: End-of-month MoMo salary deposits
   let us count employees with better accuracy than
   HR data shared by the client.
4. Cross-border corridors: Remittances via MoMo
   reveal trading relationships that CIB payments
   do not capture (small suppliers, informal trade).

Key transaction types modelled:
  P2P      – Person to person (remittance, gift)
  P2B      – Person to business (merchant payment)
  B2P      – Business to person (salary, commission)
  AIRTIME  – Airtime purchase / data bundle
  CASHOUT  – Withdraw at agent
  CASHIN   – Deposit at agent
  INTL     – International transfer (cross-border)

Disclaimer: This is not a sanctioned Standard Bank
Group or MTN Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Standard math library for calculating distributions and transaction amounts
import math
# Random library for stochastic event generation based on market profiles
import random
# UUID for generating unique transaction and record identifiers
import uuid
# Dataclass for structured representation of MoMo transaction events
from dataclasses import dataclass
# Datetime utilities for timestamping generated events and simulating cycles
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Dict, Iterator, List, Optional


# Country-specific MoMo market characteristics used to bias the simulation.
# These profiles ensure that generated data reflects real-world market maturity and behavior.
MOMO_MARKET_PROFILE: Dict[str, Dict] = {
    "NG": {
        "avg_transaction_usd": 12.0,
        "daily_volume_multiplier": 1.4,
        "salary_day": 25,           # Typical 25th of month salary cycle in Nigeria
        "merchant_pct": 0.30,       # 30% of transactions are Person-to-Business
        "intl_pct": 0.08,
        "primary_corridor_to": ["GH", "CI", "CM"],
    },
    "KE": {
        "avg_transaction_usd": 18.0,  # Higher average due to M-Pesa maturity
        "daily_volume_multiplier": 1.8,
        "salary_day": 28,
        "merchant_pct": 0.45,
        "intl_pct": 0.12,
        "primary_corridor_to": ["TZ", "UG", "RW"],
    },
    "GH": {
        "avg_transaction_usd": 9.0,
        "daily_volume_multiplier": 1.0,
        "salary_day": 25,
        "merchant_pct": 0.35,
        "intl_pct": 0.07,
        "primary_corridor_to": ["CI", "NG", "BF"],
    },
    "TZ": {
        "avg_transaction_usd": 7.0,
        "daily_volume_multiplier": 0.9,
        "salary_day": 28,
        "merchant_pct": 0.28,
        "intl_pct": 0.05,
        "primary_corridor_to": ["KE", "UG", "MZ"],
    },
    "UG": {
        "avg_transaction_usd": 6.0,
        "daily_volume_multiplier": 0.8,
        "salary_day": 28,
        "merchant_pct": 0.25,
        "intl_pct": 0.09,
        "primary_corridor_to": ["KE", "RW", "CD"],
    },
    "ZM": {
        "avg_transaction_usd": 11.0,
        "daily_volume_multiplier": 0.7,
        "salary_day": 25,
        "merchant_pct": 0.30,
        "intl_pct": 0.04,
        "primary_corridor_to": ["ZA", "MZ", "MW"],
    },
    "MZ": {
        "avg_transaction_usd": 5.0,
        "daily_volume_multiplier": 0.6,
        "salary_day": 25,
        "merchant_pct": 0.22,
        "intl_pct": 0.03,
        "primary_corridor_to": ["ZA", "TZ", "ZW"],
    },
    "ZA": {
        "avg_transaction_usd": 35.0,  # Higher income
        "daily_volume_multiplier": 2.0,
        "salary_day": 25,
        "merchant_pct": 0.50,
        "intl_pct": 0.06,
        "primary_corridor_to": ["ZM", "MZ", "NA"],
    },
}

# Country to currency mapping
COUNTRY_CURRENCY: Dict[str, str] = {
    "NG": "NGN", "KE": "KES", "GH": "GHS",
    "TZ": "TZS", "UG": "UGX", "ZM": "ZMW",
    "MZ": "MZN", "ZA": "ZAR", "CI": "XOF",
    "RW": "RWF", "CM": "XAF", "CD": "CDF",
    "MW": "MWK", "NA": "NAD", "BF": "XOF",
    "ZW": "ZWL",
}

# Approximate USD to local currency
USD_RATES: Dict[str, float] = {
    "NGN": 1580.0, "KES": 130.0, "GHS": 15.5,
    "TZS": 2550.0, "UGX": 3750.0, "ZMW": 27.5,
    "MZN": 64.0, "ZAR": 18.5, "XOF": 610.0,
    "RWF": 1280.0, "XAF": 610.0, "CDF": 2800.0,
    "MWK": 1730.0, "NAD": 18.5, "ZWL": 5800.0,
}

TRANSACTION_TYPES = [
    "P2P", "P2B", "B2P", "AIRTIME", "CASHOUT", "CASHIN", "INTL"
]


@dataclass
class MomoTransaction:
    """
    A single Mobile Money transaction event.

    We publish these to the cell domain Kafka topic
    (cell.momo.transactions) in Avro format. The
    corporate_client_id links this to our golden
    record — we know the employer of B2P recipients
    from payroll registration data.
    """

    transaction_id: str
    transaction_type: str
    sender_msisdn: str          # anonymised phone number
    receiver_msisdn: str
    corporate_client_id: Optional[str]  # employer (B2P) or merchant
    country: str
    currency: str
    amount_local: float
    amount_usd: float
    transaction_timestamp: str
    channel: str                # APP, USSD, AGENT
    status: str                 # COMPLETED, FAILED, REVERSED
    is_salary_payment: bool
    is_cross_border: bool
    destination_country: Optional[str]
    agent_id: Optional[str]
    merchant_category: Optional[str]


class MomoGenerator:
    """
    We generate realistic synthetic MoMo transaction
    streams for testing and demo purposes.

    Usage:

        gen = MomoGenerator(seed=42)

        # Stream transactions for a country
        for txn in gen.stream_transactions("KE", days=30):
            publish_to_kafka(txn)

        # Generate salary payment batch
        salary_batch = gen.generate_salary_batch(
            corporate_client_id="CLIENT-001",
            country="KE",
            employee_count=850,
        )
    """

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def _msisdn(self, country: str) -> str:
        """
        We generate a synthetic but realistic MSISDN
        (mobile number) for the given country.
        Prefixes match real network operator ranges.
        """

        prefixes: Dict[str, List[str]] = {
            "NG": ["0803", "0806", "0812", "0814", "0816"],
            "KE": ["0700", "0710", "0720", "0722", "0733"],
            "GH": ["024", "025", "026", "027", "054", "055"],
            "TZ": ["0621", "0622", "0655", "0656", "0687"],
            "UG": ["039", "031", "032", "076", "077"],
            "ZM": ["096", "097", "095", "076", "077"],
            "MZ": ["84", "85", "86", "87"],
            "ZA": ["060", "061", "062", "063", "064", "065"],
        }
        country_prefixes = prefixes.get(
            country, ["070", "080", "090"]
        )
        prefix = random.choice(country_prefixes)
        suffix = "".join(
            str(random.randint(0, 9)) for _ in range(7)
        )
        return f"{prefix}{suffix}"

    def _amount(
        self,
        country: str,
        txn_type: str,
        is_salary: bool = False,
    ) -> float:
        """
        We generate a realistic transaction amount.

        Salary payments have a tighter distribution
        around the country average wage. B2P merchant
        receipts have a wider distribution with a fat
        tail for large corporate suppliers.
        """

        profile = MOMO_MARKET_PROFILE.get(country, {})
        avg_usd = profile.get("avg_transaction_usd", 10.0)
        currency = COUNTRY_CURRENCY.get(country, "USD")
        usd_rate = USD_RATES.get(currency, 1.0)

        if is_salary:
            # Salary payments cluster around country
            # average monthly wage with some dispersion
            usd_amount = random.gauss(avg_usd * 8, avg_usd * 2)
        elif txn_type == "AIRTIME":
            usd_amount = random.uniform(0.50, 5.0)
        elif txn_type in ("CASHIN", "CASHOUT"):
            usd_amount = math.exp(2.5 + 0.8 * random.gauss(0, 1))
        elif txn_type == "P2B":
            usd_amount = math.exp(2.0 + 1.0 * random.gauss(0, 1))
        elif txn_type == "INTL":
            usd_amount = math.exp(3.5 + 1.0 * random.gauss(0, 1))
        else:
            usd_amount = math.exp(
                (2.0 + avg_usd / 20) + 0.9 * random.gauss(0, 1)
            )

        usd_amount = max(usd_amount, 0.10)
        local_amount = round(usd_amount * usd_rate, 2)
        return local_amount

    def _channel(self) -> str:
        """We weight channel distribution realistically."""

        return random.choices(
            ["USSD", "APP", "AGENT"],
            weights=[0.55, 0.30, 0.15],
        )[0]

    def _merchant_category(self, txn_type: str) -> Optional[str]:
        if txn_type != "P2B":
            return None
        return random.choice([
            "GROCERY", "TRANSPORT", "UTILITY",
            "RESTAURANT", "PHARMACY", "FUEL",
            "HARDWARE", "CLOTHING", "SCHOOL_FEES",
        ])

    def generate_transaction(
        self,
        country: str,
        timestamp: Optional[datetime] = None,
        corporate_client_id: Optional[str] = None,
        force_type: Optional[str] = None,
        is_salary: bool = False,
    ) -> MomoTransaction:
        """
        We generate a single MoMo transaction for the
        given country and point in time.
        """

        profile = MOMO_MARKET_PROFILE.get(country, {})

        if force_type:
            txn_type = force_type
        elif is_salary:
            txn_type = "B2P"
        else:
            # Weight transaction type by market profile
            merchant_pct = profile.get("merchant_pct", 0.30)
            intl_pct = profile.get("intl_pct", 0.06)
            weights = [
                0.25,                   # P2P
                merchant_pct,           # P2B
                0.10,                   # B2P (non-salary)
                0.15,                   # AIRTIME
                0.10,                   # CASHOUT
                0.07,                   # CASHIN
                intl_pct,               # INTL
            ]
            txn_type = random.choices(
                TRANSACTION_TYPES, weights=weights
            )[0]

        is_cross_border = txn_type == "INTL"
        destination_country = None
        if is_cross_border:
            corridors = profile.get("primary_corridor_to", [])
            if corridors:
                destination_country = random.choice(corridors)

        currency = COUNTRY_CURRENCY.get(country, "ZAR")
        usd_rate = USD_RATES.get(currency, 1.0)
        amount_local = self._amount(country, txn_type, is_salary)
        amount_usd = round(amount_local / usd_rate, 2)

        agent_id = None
        if txn_type in ("CASHIN", "CASHOUT"):
            agent_id = f"AGT-{country}-{random.randint(1000, 9999)}"

        ts = timestamp or datetime.now(timezone.utc)

        return MomoTransaction(
            transaction_id=(
                f"MOMO-{country}-{uuid.uuid4().hex[:10].upper()}"
            ),
            transaction_type=txn_type,
            sender_msisdn=self._msisdn(country),
            receiver_msisdn=self._msisdn(
                destination_country or country
            ),
            corporate_client_id=corporate_client_id,
            country=country,
            currency=currency,
            amount_local=amount_local,
            amount_usd=amount_usd,
            transaction_timestamp=ts.isoformat(),
            channel=self._channel(),
            status=random.choices(
                ["COMPLETED", "FAILED", "REVERSED"],
                weights=[0.95, 0.04, 0.01],
            )[0],
            is_salary_payment=is_salary,
            is_cross_border=is_cross_border,
            destination_country=destination_country,
            agent_id=agent_id,
            merchant_category=self._merchant_category(txn_type),
        )

    def generate_salary_batch(
        self,
        corporate_client_id: str,
        country: str,
        employee_count: int,
        payment_date: Optional[datetime] = None,
    ) -> List[MomoTransaction]:
        """
        We generate a salary payment batch for a
        corporate client.

        These B2P transactions are the primary signal
        we use to track employee headcount in African
        markets where formal HR data is unreliable.
        We can detect workforce growth or contraction
        by monitoring salary batch size month-over-month.
        """

        ts = payment_date or datetime.now(timezone.utc)

        return [
            self.generate_transaction(
                country=country,
                timestamp=ts + timedelta(
                    seconds=random.randint(0, 7200)
                ),
                corporate_client_id=corporate_client_id,
                force_type="B2P",
                is_salary=True,
            )
            for _ in range(employee_count)
        ]

    def stream_transactions(
        self,
        country: str,
        days: int = 30,
        daily_volume: Optional[int] = None,
        corporate_client_id: Optional[str] = None,
    ) -> Iterator[MomoTransaction]:
        """
        We yield a stream of MoMo transactions spanning
        the given number of days for a country.

        Volume follows realistic intraday and monthly
        patterns:
        - Morning peak 7–9am (commute payments)
        - Lunchtime peak 12–1pm
        - Evening peak 5–7pm (end of working day)
        - End-of-month salary spike
        """

        profile = MOMO_MARKET_PROFILE.get(country, {})
        vol_multiplier = profile.get(
            "daily_volume_multiplier", 1.0
        )
        salary_day = profile.get("salary_day", 25)

        if daily_volume is None:
            daily_volume = int(200 * vol_multiplier)

        start = datetime.now(timezone.utc) - timedelta(days=days)

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)
            is_salary_day = current_day.day == salary_day

            # Salary day has 40% higher volume
            day_vol = daily_volume * (1.4 if is_salary_day else 1.0)
            day_vol = int(day_vol)

            for _ in range(day_vol):
                # Intraday hour distribution (hourly weights)
                hour = random.choices(
                    range(24),
                    weights=[
                        0.5, 0.3, 0.2, 0.2, 0.3,   # 0-4
                        0.5, 1.0, 3.0, 4.5, 3.5,   # 5-9
                        2.5, 2.0, 3.0, 2.5, 2.0,   # 10-14
                        2.0, 2.5, 4.0, 4.5, 3.5,   # 15-19
                        2.5, 2.0, 1.5, 1.0,         # 20-23
                    ],
                )[0]
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                ts = current_day.replace(
                    hour=hour, minute=minute, second=second
                )

                yield self.generate_transaction(
                    country=country,
                    timestamp=ts,
                    corporate_client_id=corporate_client_id,
                    is_salary=is_salary_day and random.random() < 0.15,
                )
