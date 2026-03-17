"""
Cell Network Usage Pattern Generator

We generate realistic synthetic voice and data usage
records for the cell domain.

Usage patterns are a rich behavioural signal:

1. Roaming events: When an employee's SIM is seen
   roaming in a country where the employer has no
   registered corporate presence, it is an early
   signal of a prospecting trip or quiet expansion.

2. Data consumption growth: A corporate SIM cluster
   showing 3x data consumption growth month-on-month
   suggests a remote working rollout or a CRM/ERP
   deployment — both are business growth signals.

3. Call pattern shifts: An increase in outgoing
   international voice calls from a corporate SIM
   cluster, particularly to a specific country,
   often precedes a formal market entry announcement.

4. Cross-border voice: Clusters of calls between
   two countries (e.g. corporate HQ in ZA calling
   employee SIMs in NG) confirm operational presence
   that payment flows may not yet reveal.

Usage types modelled:
  voice_outgoing  – Outbound call
  voice_incoming  – Inbound call
  data            – Mobile data session
  sms             – SMS (used for OTPs, banking alerts)

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
from afriflow.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Usage market profiles
# ---------------------------------------------------------------------------

# Country-level usage mix — proportion of each usage type.
USAGE_MIX: Dict[str, Dict[str, float]] = {
    "ZA": {
        "voice_outgoing": 0.20,
        "voice_incoming": 0.20,
        "data":           0.50,
        "sms":            0.10,
    },
    "NG": {
        "voice_outgoing": 0.30,
        "voice_incoming": 0.28,
        "data":           0.30,
        "sms":            0.12,
    },
    "KE": {
        "voice_outgoing": 0.25,
        "voice_incoming": 0.25,
        "data":           0.40,
        "sms":            0.10,
    },
    "GH": {
        "voice_outgoing": 0.30,
        "voice_incoming": 0.28,
        "data":           0.30,
        "sms":            0.12,
    },
    "TZ": {
        "voice_outgoing": 0.33,
        "voice_incoming": 0.32,
        "data":           0.25,
        "sms":            0.10,
    },
    "UG": {
        "voice_outgoing": 0.33,
        "voice_incoming": 0.32,
        "data":           0.25,
        "sms":            0.10,
    },
}

DEFAULT_USAGE_MIX: Dict[str, float] = {
    "voice_outgoing": 0.28,
    "voice_incoming": 0.28,
    "data":           0.32,
    "sms":            0.12,
}

# Average call duration per country (seconds).
AVG_CALL_DURATION: Dict[str, int] = {
    "ZA": 150, "NG": 200, "KE": 180, "GH": 190,
    "TZ": 170, "UG": 175, "ZM": 165, "MZ": 160,
}
DEFAULT_CALL_DURATION = 170

# Average data session size per country (MB).
AVG_DATA_SESSION_MB: Dict[str, float] = {
    "ZA": 45.0, "NG": 20.0, "KE": 30.0, "GH": 22.0,
    "TZ": 15.0, "UG": 15.0, "ZM": 18.0, "MZ": 12.0,
}
DEFAULT_DATA_SESSION_MB = 20.0

# Roaming probability per country (% of SIMs roaming
# at any given time for a corporate user pool).
ROAMING_PROBABILITY: Dict[str, float] = {
    "ZA": 0.04,   # Senior corporate staff, frequent travel
    "NG": 0.03,
    "KE": 0.05,
    "GH": 0.02,
}
DEFAULT_ROAMING_PROBABILITY = 0.02

USAGE_TYPES = ["voice_outgoing", "voice_incoming", "data", "sms"]

COUNTRY_CURRENCY: Dict[str, str] = {
    "NG": "NGN", "KE": "KES", "GH": "GHS",
    "TZ": "TZS", "UG": "UGX", "ZM": "ZMW",
    "MZ": "MZN", "ZA": "ZAR", "CI": "XOF",
    "RW": "RWF", "ET": "ETB", "CM": "XAF",
}


@dataclass
class UsageRecord:
    """
    A single cell network usage event.

    We publish these to the cell domain Kafka topic
    (cell.usage.records) in Avro format.

    Roaming records are of particular interest to the
    cross-domain signal engine — a corporate SIM seen
    roaming in a new country is an early expansion signal.
    """

    usage_id: str
    msisdn_pseudonym: str
    country: str
    usage_type: str
    duration_seconds: Optional[int]   # voice only
    data_mb: Optional[float]          # data only
    roaming: bool
    roaming_country: Optional[str]    # country where roaming occurred
    timestamp: datetime


class UsageGenerator:
    """
    We generate realistic synthetic cell network usage
    records for testing and demo purposes.

    Usage:

        gen = UsageGenerator(seed=42)

        # Generate a single usage record
        record = gen.generate_record("PSN-ZA-ABCD1234", "ZA")

        # Stream one day of usage for 1000 SIMs in Kenya
        for record in gen.stream_usage("KE", days=1, sims=1000):
            publish_to_kafka(record)
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)

    def _usage_type(self, country: str) -> str:
        """
        We sample a usage type using country-specific
        distribution weights.
        """

        mix = USAGE_MIX.get(country, DEFAULT_USAGE_MIX)
        types = list(mix.keys())
        weights = list(mix.values())
        return random.choices(types, weights=weights)[0]

    def _duration(self, country: str) -> int:
        """
        We sample a realistic call duration in seconds
        using a log-normal distribution centred on the
        country average.
        """

        avg = AVG_CALL_DURATION.get(country, DEFAULT_CALL_DURATION)
        # Log-normal: most calls short, few very long
        duration = int(random.lognormvariate(
            math.log(avg) if avg > 0 else 5.0,
            0.7,
        ))  # math imported at top of module
        return max(10, min(duration, 3600))  # 10s to 60min

    def _data_mb(self, country: str, roaming: bool) -> float:
        """
        We sample a realistic data session size.

        Roaming sessions tend to be smaller because
        users avoid large downloads on expensive
        roaming data tariffs.
        """

        avg = AVG_DATA_SESSION_MB.get(country, DEFAULT_DATA_SESSION_MB)
        if roaming:
            avg *= 0.3  # Roaming users are conservative

        mb = random.lognormvariate(
            math.log(max(avg, 0.1)),
            0.8,
        )  # math imported at top of module
        return round(max(0.1, mb), 2)

    def _is_roaming(self, country: str) -> bool:
        """
        We determine whether this SIM usage event is
        a roaming event.
        """

        prob = ROAMING_PROBABILITY.get(country, DEFAULT_ROAMING_PROBABILITY)
        return random.random() < prob

    def _roaming_country(self, home_country: str) -> str:
        """
        We select a plausible roaming country — typically
        a neighbouring country or a major business hub.
        """

        roaming_destinations: Dict[str, List[str]] = {
            "ZA": ["NA", "MZ", "ZM", "ZW", "GB", "AE"],
            "NG": ["GH", "CM", "CI", "GB", "AE"],
            "KE": ["TZ", "UG", "RW", "AE", "GB"],
            "GH": ["CI", "NG", "BF"],
            "TZ": ["KE", "UG", "MZ"],
        }
        options = roaming_destinations.get(
            home_country,
            ["AE", "GB", "US", "ZA", "NG"],
        )
        return random.choice(options)

    def generate_record(
        self,
        msisdn_pseudonym: str,
        country: str,
        timestamp: Optional[datetime] = None,
    ) -> UsageRecord:
        """
        We generate a single usage record for the given
        MSISDN and country.
        """

        if country not in COUNTRY_CURRENCY and country not in USAGE_MIX:
            logger.warning(
                "Unknown country for usage generation, using defaults",
                country=country,
            )

        usage_type = self._usage_type(country)
        roaming = self._is_roaming(country)
        roaming_country = self._roaming_country(country) if roaming else None

        duration_seconds = None
        data_mb = None

        if usage_type in ("voice_outgoing", "voice_incoming"):
            duration_seconds = self._duration(country)
        elif usage_type == "data":
            data_mb = self._data_mb(country, roaming)

        return UsageRecord(
            usage_id=f"USAGE-{country}-{uuid.uuid4().hex[:10].upper()}",
            msisdn_pseudonym=msisdn_pseudonym,
            country=country,
            usage_type=usage_type,
            duration_seconds=duration_seconds,
            data_mb=data_mb,
            roaming=roaming,
            roaming_country=roaming_country,
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    def stream_usage(
        self,
        country: str,
        days: int = 1,
        sims: int = 1_000,
    ) -> Iterator[UsageRecord]:
        """
        We yield a stream of usage records spanning the
        given days for a pool of SIMs.

        Each SIM generates an average of 8–15 usage events
        per day (realistic for a corporate device).

        Intraday volume follows the business day pattern:
        peak during working hours, low overnight.
        """

        start = datetime.now(timezone.utc) - timedelta(days=days)
        pseudonyms = [
            f"PSN-{country}-{uuid.uuid4().hex[:16].upper()}"
            for _ in range(sims)
        ]

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)

            for pseudonym in pseudonyms:
                # Each SIM generates a random number of events per day
                events_today = random.randint(5, 20)

                for _ in range(events_today):
                    hour = random.choices(
                        range(24),
                        weights=[
                            0.2, 0.1, 0.1, 0.1, 0.2,   # 0–4
                            0.4, 0.8, 2.0, 3.5, 3.0,   # 5–9
                            2.5, 2.0, 2.5, 2.5, 2.0,   # 10–14
                            2.0, 2.0, 2.5, 3.0, 2.5,   # 15–19
                            2.0, 1.5, 1.0, 0.5,         # 20–23
                        ],
                    )[0]
                    ts = current_day.replace(
                        hour=hour,
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59),
                    )
                    yield self.generate_record(
                        msisdn_pseudonym=pseudonym,
                        country=country,
                        timestamp=ts,
                    )


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = UsageGenerator(seed=42)

    print("=== Single Usage Record (South Africa) ===")
    r = gen.generate_record("PSN-ZA-DEMO0001ABCD1234", "ZA")
    print(f"  usage_id         : {r.usage_id}")
    print(f"  usage_type       : {r.usage_type}")
    print(f"  duration_seconds : {r.duration_seconds}")
    print(f"  data_mb          : {r.data_mb}")
    print(f"  roaming          : {r.roaming} -> {r.roaming_country}")

    print("\n=== First 5 records (Kenya, 50 SIMs, 1 day) ===")
    for i, rec in enumerate(gen.stream_usage("KE", days=1, sims=50)):
        print(
            f"  [{rec.timestamp.strftime('%H:%M')}] "
            f"{rec.usage_type:16s} | "
            f"roaming={rec.roaming} | "
            f"dur={rec.duration_seconds}s | "
            f"data={rec.data_mb}MB"
        )
        if i >= 4:
            break

    print("\n=== Roaming events (first 3 in Nigeria, 100 SIMs) ===")
    count = 0
    for rec in gen.stream_usage("NG", days=1, sims=100):
        if rec.roaming:
            print(
                f"  {rec.msisdn_pseudonym[:20]}... | "
                f"roaming in {rec.roaming_country}"
            )
            count += 1
            if count >= 3:
                break
