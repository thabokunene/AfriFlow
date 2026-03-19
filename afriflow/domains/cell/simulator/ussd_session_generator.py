"""
@file ussd_session_generator.py
@description Generator for synthetic USSD session events, simulating financial inclusion and service accessibility signals.
@author Thabo Kunene
@created 2026-03-19
"""

"""
USSD Session Generator

We generate realistic synthetic USSD session events
for the cell domain.

USSD (Unstructured Supplementary Service Data) is
critical infrastructure in Africa. In markets where
smartphone penetration is below 40%, USSD is the
primary interface for:

1. Mobile money transfers (MoMo)
2. Airtime and data purchases
3. Balance checks
4. Loan applications (increasingly)
5. Banking OTPs and PIN changes

USSD session patterns are valuable signals:

Session type distribution as a market maturity indicator:
  - Markets dominated by airtime_check: early-stage
    financial inclusion (cash economy)
  - Markets where momo_transfer > 30%: mature MoMo
    ecosystem (embedded in daily commerce)
  - Growing loan_enquiry sessions: emerging credit demand
    — a leading indicator for credit product rollout

Session completion rates signal UX quality:
  - Low completion rates on momo_transfer sessions
    indicate friction in the payment flow
  - Corporate clients with high USSD session volumes
    but low completion rates may be experiencing a
    technical issue — a retention risk

Disclaimer: This is not a sanctioned Standard Bank Group
or MTN Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Standard math library for calculating session durations and probabilities
import math
# Random library for stochastic event generation based on USSD code registries
import random
# UUID for generating unique session and record identifiers
import uuid
# Dataclass for structured representation of USSD session events
from dataclasses import dataclass
# Datetime utilities for timestamping generated events
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Any, Dict, Iterator, List, Optional
# AfriFlow logging utility for consistent log formatting
from afriflow.logging_config import get_logger

# Initialize module-level logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# USSD code registry per country
# ---------------------------------------------------------------------------

# Dictionary mapping ISO country codes to their respective USSD shortcodes and session types.
# These codes reflect the actual infrastructure patterns observed in major African markets.
USSD_CODES: Dict[str, Dict[str, str]] = {
    "ZA": {
        "*130#":       "airtime_check",
        "*120*321#":   "momo_transfer",
        "*120*277#":   "balance",
        "*120*3#":     "data_bundle",
        "*130*1#":     "loan_enquiry",
    },
    "NG": {
        "*556#":       "mtn_balance",
        "*600#":       "momo_transfer",
        "*461*1#":     "airtime",
        "*461*2#":     "data_bundle",
        "*573#":       "loan_enquiry",
    },
    "KE": {
        "*131#":       "airtime_check",
        "*165*1#":     "momo_transfer",
        "*234#":       "balance",
        "*234*1#":     "loan_enquiry",
        "*234*5#":     "data_bundle",
    },
    "GH": {
        "*170#":       "momo_transfer",
        "*124#":       "balance",
        "*134*1#":     "airtime_check",
        "*134*3#":     "data_bundle",
    },
    "TZ": {
        "*150*00#":    "momo_transfer",
        "*100#":       "balance",
        "*100*1#":     "airtime_check",
        "*100*4#":     "loan_enquiry",
    },
    "UG": {
        "*165*3#":     "momo_transfer",
        "*131#":       "balance",
        "*131*1#":     "airtime_check",
        "*165*5#":     "loan_enquiry",
    },
    "ZM": {
        "*321#":       "momo_transfer",
        "*200#":       "balance",
        "*200*2#":     "airtime_check",
    },
    "MZ": {
        "*150*1#":     "momo_transfer",
        "*123#":       "balance",
        "*123*1#":     "airtime_check",
    },
    "CI": {
        "*133#":       "momo_transfer",
        "*133*1#":     "balance",
        "*100#":       "airtime_check",
    },
    "RW": {
        "*182*1#":     "momo_transfer",
        "*131#":       "balance",
        "*131*1#":     "airtime_check",
    },
}

# Default codes for countries not explicitly mapped
DEFAULT_USSD_CODES: Dict[str, str] = {
    "*100#":   "airtime_check",
    "*200#":   "momo_transfer",
    "*300#":   "balance",
}

# Session type distribution by country.
# Markets with mature MoMo have higher momo_transfer share.
SESSION_TYPE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "ZA": {
        "airtime_check":  0.25,
        "momo_transfer":  0.35,
        "balance":        0.20,
        "data_bundle":    0.12,
        "loan_enquiry":   0.08,
    },
    "NG": {
        "airtime_check":  0.20,
        "momo_transfer":  0.30,
        "balance":        0.25,
        "data_bundle":    0.15,
        "loan_enquiry":   0.10,
    },
    "KE": {
        "airtime_check":  0.18,
        "momo_transfer":  0.40,
        "balance":        0.22,
        "data_bundle":    0.12,
        "loan_enquiry":   0.08,
    },
    "GH": {
        "airtime_check":  0.25,
        "momo_transfer":  0.30,
        "balance":        0.25,
        "data_bundle":    0.12,
        "loan_enquiry":   0.08,
    },
    "TZ": {
        "airtime_check":  0.30,
        "momo_transfer":  0.28,
        "balance":        0.25,
        "data_bundle":    0.12,
        "loan_enquiry":   0.05,
    },
}

DEFAULT_SESSION_WEIGHTS: Dict[str, float] = {
    "airtime_check":  0.30,
    "momo_transfer":  0.28,
    "balance":        0.25,
    "data_bundle":    0.12,
    "loan_enquiry":   0.05,
}

# Average transaction amounts (USD) for financial sessions.
SESSION_AMOUNTS_USD: Dict[str, Dict[str, float]] = {
    "momo_transfer": {
        "ZA": 25.0, "NG": 10.0, "KE": 15.0,
        "GH": 8.0,  "TZ": 6.0,  "UG": 5.0,
    },
    "loan_enquiry": {
        "ZA": 200.0, "NG": 80.0, "KE": 100.0,
        "GH": 60.0,  "TZ": 50.0,
    },
}

# Approximate USD to local currency rates
USD_RATES: Dict[str, float] = {
    "NGN": 1580.0, "KES": 130.0, "GHS": 15.5,
    "TZS": 2550.0, "UGX": 3750.0, "ZMW": 27.5,
    "MZN": 64.0,  "ZAR": 18.5,  "XOF": 610.0,
    "RWF": 1280.0,
}

COUNTRY_CURRENCY: Dict[str, str] = {
    "NG": "NGN", "KE": "KES", "GH": "GHS",
    "TZ": "TZS", "UG": "UGX", "ZM": "ZMW",
    "MZ": "MZN", "ZA": "ZAR", "CI": "XOF",
    "RW": "RWF",
}

# Session completion rates per type.
# MoMo transfers have lower completion due to PIN failures,
# balance issues, and session timeouts.
SESSION_COMPLETION_RATES: Dict[str, float] = {
    "airtime_check":  0.98,
    "momo_transfer":  0.82,
    "balance":        0.97,
    "data_bundle":    0.90,
    "loan_enquiry":   0.75,
}


@dataclass
class USSDSession:
    """
    A single USSD session event.

    We publish these to the cell domain Kafka topic
    (cell.ussd.sessions) in Avro format.

    The completed flag is important — incomplete MoMo
    transfer sessions are an early warning of UX issues
    that affect client retention.
    """

    session_id: str
    msisdn_pseudonym: str
    country: str
    ussd_code: str
    session_type: str
    duration_seconds: int
    steps_taken: int
    completed: bool
    amount_usd: Optional[float]    # None for non-financial sessions
    timestamp: datetime


class USSDSessionGenerator:
    """
    We generate realistic synthetic USSD session events
    for testing and demo purposes.

    Usage:

        gen = USSDSessionGenerator(seed=42)

        # Generate a single USSD session
        session = gen.generate_session("PSN-KE-ABCD1234", "KE")

        # Stream one day of sessions
        for session in gen.stream_sessions("NG", days=1, sessions_per_day=50000):
            publish_to_kafka(session)

        # Analyse a batch of sessions
        stats = gen.get_session_statistics(sessions)
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)

    def _session_type(self, country: str) -> str:
        """
        We sample a session type using country-specific
        distribution weights.
        """

        weights_map = SESSION_TYPE_WEIGHTS.get(country, DEFAULT_SESSION_WEIGHTS)
        types = list(weights_map.keys())
        weights = list(weights_map.values())
        return random.choices(types, weights=weights)[0]

    def _ussd_code(self, country: str, session_type: str) -> str:
        """
        We select a USSD code matching the session type
        for the given country.
        """

        codes = USSD_CODES.get(country, DEFAULT_USSD_CODES)
        matching = [code for code, stype in codes.items() if stype == session_type]

        if matching:
            return random.choice(matching)

        # Fallback: return any code for the country
        return random.choice(list(codes.keys())) if codes else "*100#"

    def _duration_and_steps(self, session_type: str, completed: bool) -> tuple[int, int]:
        """
        We generate realistic session duration and step count.

        Incomplete sessions have fewer steps and shorter
        duration — the user abandoned early.
        """

        base_steps = {
            "airtime_check":  3,
            "momo_transfer":  7,
            "balance":        2,
            "data_bundle":    5,
            "loan_enquiry":   6,
        }.get(session_type, 4)

        base_duration = {
            "airtime_check":  15,
            "momo_transfer":  90,
            "balance":        10,
            "data_bundle":    45,
            "loan_enquiry":   120,
        }.get(session_type, 30)

        if completed:
            steps = base_steps + random.randint(0, 2)
            duration = int(base_duration * random.uniform(0.8, 1.5))
        else:
            steps = random.randint(1, max(1, base_steps - 2))
            duration = int(base_duration * random.uniform(0.2, 0.6))

        return max(5, duration), max(1, steps)

    def _amount(self, session_type: str, country: str) -> Optional[float]:
        """
        We generate a transaction amount for financial
        sessions. Non-financial sessions return None.
        """

        if session_type not in ("momo_transfer", "loan_enquiry"):
            return None

        avg_usd = SESSION_AMOUNTS_USD.get(session_type, {}).get(country, 10.0)
        usd_amount = random.lognormvariate(
            math.log(max(avg_usd, 0.1)), 0.7
        )
        return round(max(0.5, usd_amount), 2)

    def generate_session(
        self,
        msisdn_pseudonym: str,
        country: str,
        timestamp: Optional[datetime] = None,
        force_type: Optional[str] = None,
    ) -> USSDSession:
        """
        We generate a single USSD session for the given
        MSISDN and country.
        """

        session_type = force_type or self._session_type(country)
        completion_rate = SESSION_COMPLETION_RATES.get(session_type, 0.90)
        completed = random.random() < completion_rate

        duration, steps = self._duration_and_steps(session_type, completed)
        amount_usd = self._amount(session_type, country) if completed else None

        return USSDSession(
            session_id=f"USSD-{country}-{uuid.uuid4().hex[:10].upper()}",
            msisdn_pseudonym=msisdn_pseudonym,
            country=country,
            ussd_code=self._ussd_code(country, session_type),
            session_type=session_type,
            duration_seconds=duration,
            steps_taken=steps,
            completed=completed,
            amount_usd=amount_usd,
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    def stream_sessions(
        self,
        country: str,
        days: int = 1,
        sessions_per_day: int = 50_000,
    ) -> Iterator[USSDSession]:
        """
        We yield a stream of USSD sessions for the given
        country spanning the requested days.

        USSD volume peaks in the early morning (people
        checking balances before commuting) and at
        end-of-day (payroll confirmations, transfers).

        Salary days see a 60% spike in momo_transfer
        sessions as workers receive and redistribute wages.
        """

        start = datetime.now(timezone.utc) - timedelta(days=days)
        salary_days = {25, 26, 27, 28, 29, 30}  # End-of-month window

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)
            is_salary_day = current_day.day in salary_days

            day_vol = int(sessions_per_day * (1.6 if is_salary_day else 1.0))

            for _ in range(day_vol):
                hour = random.choices(
                    range(24),
                    weights=[
                        0.5, 0.3, 0.2, 0.2, 0.3,   # 0–4
                        1.5, 3.0, 4.0, 3.5, 2.5,   # 5–9
                        2.0, 1.5, 2.0, 2.0, 1.8,   # 10–14
                        2.0, 2.5, 4.5, 4.0, 3.5,   # 15–19
                        3.0, 2.0, 1.5, 0.8,         # 20–23
                    ],
                )[0]

                ts = current_day.replace(
                    hour=hour,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59),
                )

                pseudonym = f"PSN-{country}-{uuid.uuid4().hex[:16].upper()}"

                # On salary days bias toward momo_transfer
                force_type = None
                if is_salary_day and random.random() < 0.40:
                    force_type = "momo_transfer"

                yield self.generate_session(
                    msisdn_pseudonym=pseudonym,
                    country=country,
                    timestamp=ts,
                    force_type=force_type,
                )

    def get_session_statistics(
        self,
        sessions: List[USSDSession],
    ) -> Dict[str, Any]:
        """
        We compute summary statistics for a list of
        USSD sessions.

        Returns per-type counts, completion rates,
        average duration, and total transaction volume.
        """

        if not sessions:
            return {"total": 0}

        type_counts: Dict[str, int] = {}
        type_completed: Dict[str, int] = {}
        type_amounts: Dict[str, List[float]] = {}
        total_duration = 0

        for session in sessions:
            stype = session.session_type
            type_counts[stype] = type_counts.get(stype, 0) + 1
            if session.completed:
                type_completed[stype] = type_completed.get(stype, 0) + 1
            if session.amount_usd is not None:
                type_amounts.setdefault(stype, []).append(session.amount_usd)
            total_duration += session.duration_seconds

        stats: Dict[str, Any] = {
            "total": len(sessions),
            "completed": sum(1 for s in sessions if s.completed),
            "overall_completion_rate": (
                sum(1 for s in sessions if s.completed) / len(sessions)
            ),
            "avg_duration_seconds": total_duration / len(sessions),
            "by_type": {},
        }

        for stype, count in type_counts.items():
            amounts = type_amounts.get(stype, [])
            stats["by_type"][stype] = {
                "count": count,
                "completion_rate": type_completed.get(stype, 0) / count,
                "total_volume_usd": sum(amounts),
                "avg_amount_usd": sum(amounts) / len(amounts) if amounts else None,
            }

        return stats


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = USSDSessionGenerator(seed=42)

    print("=== Single USSD Session (Kenya) ===")
    s = gen.generate_session("PSN-KE-DEMO0001ABCD1234", "KE")
    print(f"  session_id       : {s.session_id}")
    print(f"  ussd_code        : {s.ussd_code}")
    print(f"  session_type     : {s.session_type}")
    print(f"  duration_seconds : {s.duration_seconds}")
    print(f"  steps_taken      : {s.steps_taken}")
    print(f"  completed        : {s.completed}")
    print(f"  amount_usd       : {s.amount_usd}")

    print("\n=== Stream (first 5 sessions, Nigeria) ===")
    for i, session in enumerate(gen.stream_sessions("NG", days=1, sessions_per_day=200)):
        print(
            f"  [{session.timestamp.strftime('%H:%M')}] "
            f"{session.session_type:16s} | "
            f"completed={session.completed} | "
            f"steps={session.steps_taken} | "
            f"USD {session.amount_usd}"
        )
        if i >= 4:
            break

    print("\n=== Statistics (1000 sessions, Ghana) ===")
    batch = list(gen.stream_sessions("GH", days=1, sessions_per_day=1000))
    batch = batch[:1000]
    stats = gen.get_session_statistics(batch)
    print(f"  total                  : {stats['total']}")
    print(f"  overall_completion_rate: {stats['overall_completion_rate']:.1%}")
    print(f"  avg_duration_seconds   : {stats['avg_duration_seconds']:.0f}s")
    for stype, s in stats.get("by_type", {}).items():
        print(
            f"  {stype:18s}: {s['count']:5d} sessions, "
            f"{s['completion_rate']:.0%} completion"
        )
