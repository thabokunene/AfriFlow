"""
Corporate SIM Activation Batch Generator

We generate realistic synthetic SIM activation events
for the cell domain.

A SIM activation batch is created when an MTN corporate
account manager activates a set of SIMs for a new or
expanding client. These events are critical intelligence:

1. New market entry signal: A burst of SIM activations
   for a corporate client in a country where they have
   no prior MTN relationship is the earliest leading
   indicator of operational expansion — it appears
   typically 1–3 months before the client announces
   market entry to their bank.

2. Workforce sizing: The number of SIMs activated,
   broken down by department, gives us a rough floor
   on headcount. Combined with the SIM deflation factor
   we can estimate total workforce in that country.

3. Departmental structure inference: A batch heavy in
   logistics SIMs suggests a distribution build-out.
   A batch heavy in sales SIMs suggests market expansion.
   A batch heavy in finance SIMs suggests back-office
   establishment (a more mature expansion phase).

Key activation types modelled:
  new_enterprise  – First-time corporate MTN customer
  sme_starter     – Small/medium business starter pack
  expansion_batch – Existing client entering new country
  replacement     – Replacing lost/damaged SIMs

Disclaimer: This is not a sanctioned Standard Bank Group
or MTN Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, List, Optional, Tuple

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Activation type profiles
# ---------------------------------------------------------------------------

ACTIVATION_PROFILES: Dict[str, Dict] = {
    "new_enterprise": {
        "min_sims": 100,
        "max_sims": 5000,
        "departments": ["sales", "logistics", "finance", "executive", "operations", "it"],
        "description": "First-time MTN corporate customer; full department rollout",
    },
    "sme_starter": {
        "min_sims": 10,
        "max_sims": 100,
        "departments": ["general"],
        "description": "Small/medium business starter pack; undifferentiated department",
    },
    "expansion_batch": {
        "min_sims": 50,
        "max_sims": 500,
        "departments": ["sales", "logistics", "operations"],
        "description": "Existing corporate client entering a new country",
    },
    "replacement": {
        "min_sims": 5,
        "max_sims": 50,
        "departments": ["general"],
        "description": "Replacement SIMs for lost/damaged/stolen devices",
    },
}

# Price plans available per activation type.
# Higher-tier plans include roaming and higher data caps.
PRICE_PLANS: Dict[str, List[str]] = {
    "new_enterprise": ["corporate_premium", "corporate_standard", "corporate_data_heavy"],
    "sme_starter":    ["sme_basic", "sme_standard"],
    "expansion_batch": ["corporate_standard", "corporate_premium"],
    "replacement":    ["corporate_standard", "sme_basic"],
}

# Major corporate operational hubs by country.
# Used to generate realistic activation locations.
COUNTRY_CITIES: Dict[str, List[str]] = {
    "ZA": ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth"],
    "NG": ["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan"],
    "KE": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"],
    "GH": ["Accra", "Kumasi", "Takoradi", "Tamale"],
    "TZ": ["Dar es Salaam", "Arusha", "Mwanza", "Dodoma"],
    "UG": ["Kampala", "Entebbe", "Jinja", "Gulu"],
    "ZM": ["Lusaka", "Ndola", "Kitwe", "Livingstone"],
    "MZ": ["Maputo", "Beira", "Nampula", "Tete"],
    "CI": ["Abidjan", "Bouaké", "Yamoussoukro"],
    "RW": ["Kigali", "Butare", "Gisenyi"],
    "ET": ["Addis Ababa", "Dire Dawa", "Gondar", "Mekele"],
    "CM": ["Douala", "Yaoundé", "Bamenda", "Bafoussam"],
}

# Department SIM weight distributions by activation type.
# Controls how SIMs are allocated across departments.
DEPARTMENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "new_enterprise": {
        "sales":      0.35,
        "logistics":  0.25,
        "operations": 0.20,
        "finance":    0.10,
        "it":         0.05,
        "executive":  0.05,
    },
    "expansion_batch": {
        "sales":      0.45,
        "logistics":  0.35,
        "operations": 0.20,
    },
    "sme_starter": {"general": 1.0},
    "replacement":  {"general": 1.0},
}

# Simulated account manager IDs per country.
ACCOUNT_MANAGER_POOLS: Dict[str, List[str]] = {
    "ZA": [f"AM-ZA-{i:04d}" for i in range(1, 21)],
    "NG": [f"AM-NG-{i:04d}" for i in range(1, 16)],
    "KE": [f"AM-KE-{i:04d}" for i in range(1, 12)],
}


@dataclass
class SIMActivation:
    """
    A single corporate SIM activation batch event.

    We publish these to the cell domain Kafka topic
    (cell.sim.activations) in Avro format. The
    corporate_client_id links this to our golden record.

    department_breakdown reveals what kind of workforce
    build-out is happening — a logistics-heavy batch
    signals a distribution expansion, which is a much
    stronger trade finance and forex signal than a pure
    sales expansion.
    """

    activation_id: str
    corporate_client_id: str
    country: str
    sim_count: int
    activation_type: str
    department_breakdown: Dict[str, int]
    location: str
    activated_at: datetime
    account_manager_id: str
    price_plan: str


class SIMActivationGenerator:
    """
    We generate realistic synthetic SIM activation batches
    for testing and demo purposes.

    Usage:

        gen = SIMActivationGenerator(seed=42)

        # Generate a single enterprise activation
        activation = gen.generate_activation(
            corporate_client_id="CLIENT-001",
            country="NG",
            activation_type="new_enterprise",
        )

        # Generate expansion batch across multiple countries
        batches = gen.generate_expansion_batch(
            corporate_client_id="CLIENT-001",
            country="ZA",
            new_countries=["NG", "KE"],
        )

        # Stream 30 days of activations
        for act in gen.stream_activations(days=30):
            publish_to_kafka(act)
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)

        # Pool of synthetic corporate client IDs
        self._client_pool: List[str] = [
            f"CORP-{uuid.uuid4().hex[:8].upper()}" for _ in range(200)
        ]

    def _department_breakdown(
        self,
        activation_type: str,
        total_sims: int,
    ) -> Dict[str, int]:
        """
        We allocate SIMs across departments using the
        weight profile for the activation type.

        We ensure the total always equals total_sims
        by allocating the remainder to the largest
        department.
        """

        weights = DEPARTMENT_WEIGHTS.get(
            activation_type,
            DEPARTMENT_WEIGHTS["sme_starter"],
        )
        departments = list(weights.keys())
        dept_weights = [weights[d] for d in departments]

        breakdown: Dict[str, int] = {}
        allocated = 0

        for i, dept in enumerate(departments[:-1]):
            count = round(total_sims * dept_weights[i])
            breakdown[dept] = max(count, 0)
            allocated += breakdown[dept]

        # Last department absorbs the remainder
        breakdown[departments[-1]] = max(total_sims - allocated, 0)

        # Filter out zero-count departments
        return {d: c for d, c in breakdown.items() if c > 0}

    def _account_manager(self, country: str) -> str:
        """
        We select a realistic account manager ID for
        the given country. For countries without a
        defined pool we generate a generic AM ID.
        """

        pool = ACCOUNT_MANAGER_POOLS.get(country)
        if pool:
            return random.choice(pool)
        return f"AM-{country}-{random.randint(1000, 9999):04d}"

    def generate_activation(
        self,
        corporate_client_id: str,
        country: str,
        activation_type: str = "new_enterprise",
        timestamp: Optional[datetime] = None,
    ) -> SIMActivation:
        """
        We generate a single SIM activation batch for
        the given corporate client and country.
        """

        if activation_type not in ACTIVATION_PROFILES:
            raise ConfigurationError(
                f"Unknown activation_type '{activation_type}'. "
                f"Valid types: {list(ACTIVATION_PROFILES.keys())}"
            )

        profile = ACTIVATION_PROFILES[activation_type]
        sim_count = random.randint(profile["min_sims"], profile["max_sims"])

        cities = COUNTRY_CITIES.get(country, ["Capital City", "Commercial Hub"])
        location = random.choice(cities)

        price_plans = PRICE_PLANS.get(activation_type, ["corporate_standard"])
        price_plan = random.choice(price_plans)

        activated_at = timestamp or datetime.now(timezone.utc)

        breakdown = self._department_breakdown(activation_type, sim_count)

        return SIMActivation(
            activation_id=f"SIM-ACT-{uuid.uuid4().hex[:10].upper()}",
            corporate_client_id=corporate_client_id,
            country=country,
            sim_count=sim_count,
            activation_type=activation_type,
            department_breakdown=breakdown,
            location=location,
            activated_at=activated_at,
            account_manager_id=self._account_manager(country),
            price_plan=price_plan,
        )

    def generate_expansion_batch(
        self,
        corporate_client_id: str,
        country: str,
        new_countries: Optional[List[str]] = None,
    ) -> List[SIMActivation]:
        """
        We generate a set of expansion activation batches
        for a corporate client moving into new countries.

        The home country gets an "expansion_batch" in case
        the client is also growing headcount domestically.
        Each new country also gets an "expansion_batch".

        This simulates the typical pattern of a corporate
        expansion: they scale up in their home market and
        simultaneously open operations in new markets.
        """

        batches = []
        target_countries = [country] + (new_countries or [])

        for target in target_countries:
            activation = self.generate_activation(
                corporate_client_id=corporate_client_id,
                country=target,
                activation_type="expansion_batch",
                timestamp=datetime.now(timezone.utc) + timedelta(
                    hours=random.randint(0, 48)
                ),
            )
            batches.append(activation)

        # Attach details using logging 'extra' to remain compatible with the
        # standard logging API and our JSON formatter.
        logger.info(
            "Generated expansion batch",
            extra={
                "corporate_client_id": corporate_client_id,
                "countries": target_countries,
                "total_sims": sum(b.sim_count for b in batches),
            },
        )
        return batches

    def stream_activations(
        self,
        days: int = 30,
        activations_per_day: Optional[int] = None,
        business_hours: Tuple[int, int] = (7, 17),
        business_hours_only: bool = True,
        off_hours_rate: float = 0.10,
    ) -> Iterator[SIMActivation]:
        """
        We yield a stream of SIM activation events
        spanning the given number of days.

        Activation volume follows a realistic weekly
        pattern — Monday and Tuesday have the highest
        activation rates as corporate account managers
        complete weekend paperwork.

        End-of-quarter months (March, June, September,
        December) have 30% higher activation volumes
        as enterprises finalise expansion budgets.
        """

        if activations_per_day is None:
            activations_per_day = 15

        bh_start, bh_end = business_hours
        if bh_start < 0 or bh_end > 23 or bh_start > bh_end:
            raise ValueError("business_hours must be a (start, end) tuple within 0..23")
        if off_hours_rate < 0.0 or off_hours_rate > 1.0:
            raise ValueError("off_hours_rate must be between 0.0 and 1.0")

        start = datetime.now(timezone.utc) - timedelta(days=days)

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)
            weekday = current_day.weekday()  # 0=Monday, 6=Sunday

            # Weekday volume multiplier
            day_multiplier = {
                0: 1.3,   # Monday
                1: 1.4,   # Tuesday
                2: 1.1,   # Wednesday
                3: 1.0,   # Thursday
                4: 0.8,   # Friday
                5: 0.2,   # Saturday
                6: 0.1,   # Sunday
            }.get(weekday, 1.0)

            # End-of-quarter boost
            if current_day.month in (3, 6, 9, 12):
                day_multiplier *= 1.30

            day_count = max(1, int(activations_per_day * day_multiplier))

            for _ in range(day_count):
                client_id = random.choice(self._client_pool)
                country = random.choice(list(COUNTRY_CITIES.keys()))
                activation_type = random.choices(
                    list(ACTIVATION_PROFILES.keys()),
                    weights=[0.20, 0.35, 0.30, 0.15],
                )[0]

                if business_hours_only:
                    hour = random.randint(bh_start, bh_end)
                else:
                    if random.random() < off_hours_rate:
                        off_hours = [h for h in range(24) if h < bh_start or h > bh_end]
                        hour = random.choice(off_hours)
                    else:
                        hour = random.randint(bh_start, bh_end)
                ts = current_day.replace(
                    hour=hour,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59),
                )

                yield self.generate_activation(
                    corporate_client_id=client_id,
                    country=country,
                    activation_type=activation_type,
                    timestamp=ts,
                )


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = SIMActivationGenerator(seed=42)

    print("=== Single Enterprise Activation (Nigeria) ===")
    act = gen.generate_activation(
        corporate_client_id="CORP-DEMO-001",
        country="NG",
        activation_type="new_enterprise",
    )
    print(f"  activation_id   : {act.activation_id}")
    print(f"  country         : {act.country}")
    print(f"  sim_count       : {act.sim_count}")
    print(f"  location        : {act.location}")
    print(f"  price_plan      : {act.price_plan}")
    print(f"  departments     : {act.department_breakdown}")

    print("\n=== Expansion Batch (ZA home + NG + KE) ===")
    batches = gen.generate_expansion_batch(
        corporate_client_id="CORP-DEMO-002",
        country="ZA",
        new_countries=["NG", "KE"],
    )
    for b in batches:
        print(f"  {b.country}: {b.sim_count} SIMs @ {b.location}")

    print("\n=== Stream (first 5 activations over 7 days) ===")
    for i, a in enumerate(gen.stream_activations(days=7)):
        print(
            f"  [{a.activated_at.date()}] {a.corporate_client_id} | "
            f"{a.country} | {a.activation_type} | {a.sim_count} SIMs"
        )
        if i >= 4:
            break
