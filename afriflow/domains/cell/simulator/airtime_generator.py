"""
Airtime Top-Up Pattern Generator

We generate realistic synthetic airtime purchase events
for the cell domain.

Airtime top-ups are far more than a telecom metric.
In African markets, airtime purchasing behaviour is a
robust proxy for individual disposable income and
financial health:

1. Top-up frequency: A corporate employee making multiple
   small top-ups (< USD 1) per week signals financial
   stress — they cannot afford a larger bundle. A single
   monthly large top-up signals stable income.

2. Bundle vs scratch card: Migration from scratch card
   purchases (via agent channel) to monthly bundle
   subscriptions (via mobile app) correlates with
   upward income mobility — a banking cross-sell signal.

3. Corporate bulk airtime: When a company buys bulk
   airtime for employees, the purchase amount is a
   floor on their active workforce size. A corporate
   that increased its bulk airtime purchase by 30%
   month-on-month likely hired 30% more staff.

4. Channel migration: Employees moving from USSD airtime
   to app-based purchase indicates smartphone adoption —
   a leading indicator for digital banking readiness
   and financial product uptake.

Disclaimer: This is not a sanctioned Standard Bank Group
or MTN Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

import math
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, List, Optional

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Market profiles
# ---------------------------------------------------------------------------

# Country-specific airtime amount buckets in USD.
# Buckets reflect actual denomination availability.
TOPUP_AMOUNTS_USD: Dict[str, List[float]] = {
    "ZA": [1.0, 2.5, 5.0, 10.0, 20.0, 50.0],
    "NG": [0.5, 1.0, 2.0, 5.0, 10.0],
    "KE": [0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
    "GH": [0.5, 1.0, 2.0, 5.0, 10.0],
    "TZ": [0.25, 0.5, 1.0, 2.0, 5.0],
    "UG": [0.25, 0.5, 1.0, 2.0, 5.0],
    "ZM": [0.5, 1.0, 2.0, 5.0, 10.0],
    "MZ": [0.25, 0.5, 1.0, 2.0, 5.0],
    "CI": [0.5, 1.0, 2.0, 5.0, 10.0],
    "RW": [0.25, 0.5, 1.0, 2.0, 5.0],
    "ET": [0.25, 0.5, 1.0, 2.0],
    "CM": [0.5, 1.0, 2.0, 5.0],
}

# Default buckets for countries without a specific profile
DEFAULT_TOPUP_AMOUNTS_USD = [0.5, 1.0, 2.0, 5.0, 10.0]

# Top-up amount weight distributions — smaller amounts
# are more frequent in markets with lower income.
# Weights are indexed to match TOPUP_AMOUNTS_USD buckets.
TOPUP_AMOUNT_WEIGHTS: Dict[str, List[float]] = {
    "ZA": [0.10, 0.20, 0.30, 0.25, 0.10, 0.05],
    "NG": [0.25, 0.35, 0.25, 0.10, 0.05],
    "KE": [0.20, 0.30, 0.25, 0.15, 0.07, 0.03],
    "GH": [0.25, 0.35, 0.25, 0.10, 0.05],
    "TZ": [0.35, 0.30, 0.20, 0.10, 0.05],
    "UG": [0.35, 0.30, 0.20, 0.10, 0.05],
}

# Channel distribution for individual top-ups.
# Sum must equal 1.0.
CHANNEL_WEIGHTS: Dict[str, float] = {
    "ussd":         0.45,
    "mobile_app":   0.25,
    "agent":        0.25,
    "bank_transfer": 0.05,
}

# Approximate USD to local currency rates.
# Matches the rates in momo_generator.py for consistency.
USD_RATES: Dict[str, float] = {
    "NGN": 1580.0, "KES": 130.0, "GHS": 15.5,
    "TZS": 2550.0, "UGX": 3750.0, "ZMW": 27.5,
    "MZN": 64.0,  "ZAR": 18.5,  "XOF": 610.0,
    "RWF": 1280.0, "ETB": 56.0,  "XAF": 610.0,
}

COUNTRY_CURRENCY: Dict[str, str] = {
    "NG": "NGN", "KE": "KES", "GH": "GHS",
    "TZ": "TZS", "UG": "UGX", "ZM": "ZMW",
    "MZ": "MZN", "ZA": "ZAR", "CI": "XOF",
    "RW": "RWF", "ET": "ETB", "CM": "XAF",
}


@dataclass
class AirtimeTopUp:
    """
    A single airtime top-up event.

    We publish these to the cell domain Kafka topic
    (cell.airtime.topups) in Avro format. When
    is_corporate_airtime is True the purchase represents
    a bulk purchase by an employer — the msisdn_pseudonym
    is the corporate account holder, not an individual.
    """

    topup_id: str
    msisdn_pseudonym: str
    country: str
    amount_local: float
    amount_usd: float
    channel: str
    timestamp: datetime
    is_corporate_airtime: bool


class AirtimeGenerator:
    """
    We generate realistic synthetic airtime top-up
    streams for testing and demo purposes.

    Usage:

        gen = AirtimeGenerator(seed=42)

        # Generate a single top-up
        topup = gen.generate_topup(country="KE")

        # Stream top-ups for Kenya over 30 days
        for topup in gen.stream_topups("KE", days=30, daily_count=10000):
            publish_to_kafka(topup)

        # Generate corporate bulk airtime purchase
        bulk = gen.generate_corporate_bulk(
            corporate_client_id="CORP-001",
            country="NG",
            employee_count=500,
        )
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)

    def _pseudonym(self, country: str) -> str:
        """
        We generate a RICA-pseudonymised MSISDN token.
        In production this would be HMAC-SHA256 of the
        real MSISDN. Here we generate a realistic-looking
        pseudonym token.
        """
        return f"PSN-{country}-{uuid.uuid4().hex[:16].upper()}"

    def _amount(self, country: str, is_corporate: bool = False) -> float:
        """
        We select a realistic top-up amount for the
        given country.

        Corporate bulk purchases use a different
        distribution — they are typically larger amounts
        representing fleet-level allocations.
        """

        if is_corporate:
            # Corporate bulk: log-normal around USD 500–5000
            usd_amount = math.exp(random.gauss(6.5, 0.8))
            usd_amount = max(min(usd_amount, 10_000.0), 100.0)
        else:
            amounts = TOPUP_AMOUNTS_USD.get(country, DEFAULT_TOPUP_AMOUNTS_USD)
            weights = TOPUP_AMOUNT_WEIGHTS.get(country, None)
            usd_amount = random.choices(amounts, weights=weights)[0]
            # Add small random jitter to avoid purely discrete distribution
            usd_amount *= random.uniform(0.95, 1.05)

        currency = COUNTRY_CURRENCY.get(country, "USD")
        usd_rate = USD_RATES.get(currency, 1.0)
        local_amount = round(usd_amount * usd_rate, 2)

        return local_amount

    def _channel(self, is_corporate: bool = False) -> str:
        """
        We weight channel distribution. Corporate bulk
        purchases overwhelmingly go via bank_transfer
        or the corporate mobile app.
        """

        if is_corporate:
            return random.choices(
                ["bank_transfer", "mobile_app", "agent"],
                weights=[0.65, 0.30, 0.05],
            )[0]

        channels = list(CHANNEL_WEIGHTS.keys())
        weights = list(CHANNEL_WEIGHTS.values())
        return random.choices(channels, weights=weights)[0]

    def generate_topup(
        self,
        country: str,
        msisdn_pseudonym: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        is_corporate_airtime: bool = False,
    ) -> AirtimeTopUp:
        """
        We generate a single airtime top-up event for
        the given country.
        """

        if country not in COUNTRY_CURRENCY:
            raise ConfigurationError(
                f"Country '{country}' not in COUNTRY_CURRENCY map. "
                f"Supported: {list(COUNTRY_CURRENCY.keys())}"
            )

        currency = COUNTRY_CURRENCY[country]
        usd_rate = USD_RATES.get(currency, 1.0)

        amount_local = self._amount(country, is_corporate=is_corporate_airtime)
        amount_usd = round(amount_local / usd_rate, 4)

        return AirtimeTopUp(
            topup_id=f"AIRTIME-{country}-{uuid.uuid4().hex[:10].upper()}",
            msisdn_pseudonym=msisdn_pseudonym or self._pseudonym(country),
            country=country,
            amount_local=amount_local,
            amount_usd=amount_usd,
            channel=self._channel(is_corporate=is_corporate_airtime),
            timestamp=timestamp or datetime.now(timezone.utc),
            is_corporate_airtime=is_corporate_airtime,
        )

    def stream_topups(
        self,
        country: str,
        days: int = 30,
        daily_count: int = 10_000,
        month_end_start_day: int = 25,
        month_end_boost_factor: float = 1.3,
    ) -> Iterator[AirtimeTopUp]:
        """
        We yield a stream of airtime top-ups for the
        given country spanning the requested days.

        Volume follows realistic intraday patterns:
        - Morning commute peak (7–9am)
        - Lunch peak (12–1pm)
        - Evening peak (5–7pm)
        - Low volume overnight

        Month-end sees a spike as salary recipients
        make larger bundle purchases.
        """

        if month_end_start_day < 1 or month_end_start_day > 31:
            raise ValueError("month_end_start_day must be between 1 and 31")
        if month_end_boost_factor < 1.0:
            raise ValueError("month_end_boost_factor must be >= 1.0")

        start = datetime.now(timezone.utc) - timedelta(days=days)

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)
            is_month_end = current_day.day >= month_end_start_day

            day_vol = int(daily_count * (month_end_boost_factor if is_month_end else 1.0))

            for _ in range(day_vol):
                hour = random.choices(
                    range(24),
                    weights=[
                        0.3, 0.2, 0.2, 0.2, 0.3,   # 0–4
                        0.5, 0.8, 2.5, 3.5, 2.5,   # 5–9
                        2.0, 1.5, 2.5, 2.0, 1.5,   # 10–14
                        1.5, 2.0, 3.5, 3.5, 3.0,   # 15–19
                        2.5, 1.5, 1.0, 0.5,         # 20–23
                    ],
                )[0]

                ts = current_day.replace(
                    hour=hour,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59),
                )

                yield self.generate_topup(
                    country=country,
                    timestamp=ts,
                    is_corporate_airtime=False,
                )

    def generate_corporate_bulk(
        self,
        corporate_client_id: str,
        country: str,
        employee_count: int,
    ) -> List[AirtimeTopUp]:
        """
        We generate a corporate bulk airtime purchase
        event. Corporate clients buy airtime in bulk
        for their employees — a single purchase covers
        the monthly airtime allowance for the fleet.

        The purchase amount scales approximately linearly
        with employee_count but with some variance.
        """

        # Number of bulk purchase transactions — large
        # corporates may split across multiple accounts
        num_transactions = max(1, employee_count // 200)

        # Use logging 'extra' to attach structured fields safely. Passing arbitrary
        # keyword args to logger methods is not supported by the standard logging API
        # and can raise a TypeError on some handlers. Using 'extra' maintains context
        # and works with our JSONFormatter.
        logger.info(
            "Generating corporate bulk airtime",
            extra={
                "corporate_client_id": corporate_client_id,
                "country": country,
                "employee_count": employee_count,
                "transactions": num_transactions,
            },
        )

        return [
            self.generate_topup(
                country=country,
                msisdn_pseudonym=f"CORP-{corporate_client_id}-{i:04d}",
                is_corporate_airtime=True,
            )
            for i in range(num_transactions)
        ]


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = AirtimeGenerator(seed=42)

    print("=== Single Top-Up (Kenya) ===")
    t = gen.generate_topup("KE")
    print(f"  topup_id     : {t.topup_id}")
    print(f"  amount_usd   : {t.amount_usd}")
    print(f"  amount_local : {t.amount_local} KES")
    print(f"  channel      : {t.channel}")

    print("\n=== Corporate Bulk (Nigeria, 300 employees) ===")
    bulk = gen.generate_corporate_bulk("CORP-DEMO-001", "NG", employee_count=300)
    total_usd = sum(b.amount_usd for b in bulk)
    print(f"  {len(bulk)} transaction(s), total USD {total_usd:,.2f}")

    print("\n=== Stream (first 5 top-ups over 7 days, Kenya) ===")
    for i, topup in enumerate(gen.stream_topups("KE", days=7, daily_count=100)):
        print(
            f"  [{topup.timestamp.strftime('%Y-%m-%d %H:%M')}] "
            f"{topup.channel:12s} | USD {topup.amount_usd:.2f}"
        )
        if i >= 4:
            break
