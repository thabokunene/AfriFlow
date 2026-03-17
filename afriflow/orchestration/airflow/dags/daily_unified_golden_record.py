"""
Daily Unified Golden Record DAG

We run this DAG every day after all five domain refresh
DAGs (CIB, forex, cell, insurance, PBB) have completed.
Its job is to:

1. Identify clients whose data changed in any domain today
2. Re-run entity resolution for any ambiguous matches
3. Verify each domain provided fresh data for the client
4. Recompute cross-domain features: CLV, NBA score,
   churn risk, and anomaly score
5. Run consistency checks across domains
6. Write updated golden records to the gold layer
7. Invalidate the feature cache in the serving layer
8. Publish change events to Kafka for downstream consumers

Design decisions:
  - We process only clients updated today — incremental,
    not full refresh — to stay within the SLA window
  - Entity resolution runs before freshness checks because
    an unresolved entity cannot be checked for freshness
  - Feature computation depends on all four inputs
    (resolution, freshness, client list, consistency)
  - Cache invalidation and event publishing happen in
    parallel after the gold write — they are independent

SLA: Golden records must be updated within 45 minutes
of the daily domain refresh completion.

Disclaimer: This is not a sanctioned Standard Bank Group
project. Built by Thabo Kunene for portfolio purposes.
All data is simulated.
"""

# In production this imports from the Airflow library:
#   from airflow import DAG
#   from airflow.operators.python import PythonOperator
#   from airflow.utils.dates import days_ago
#
# We use plain Python here so the DAG definition is
# readable without an Airflow installation.

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# DAG metadata
# ---------------------------------------------------------------------------

DAG_ID = "daily_unified_golden_record"
SCHEDULE_INTERVAL = "@daily"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 3
SLA_MINUTES = 45


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Domain freshness SLAs — if a domain has not updated
# a client's data within this many hours, the golden
# record freshness check flags that domain as stale.
DOMAIN_FRESHNESS_HOURS: Dict[str, int] = {
    "cib":       26,   # Daily + a couple hours grace
    "forex":     26,
    "insurance": 26,
    "cell":      26,
    "pbb":       26,
}

# Cross-domain consistency check tolerances.
# E.g., CIB-reported country vs cell-inferred country
# must agree on at least this many countries.
COUNTRY_CONSISTENCY_MIN_OVERLAP = 0.70

# Kafka topic for golden record change events.
GOLDEN_RECORD_CHANGE_TOPIC = "afriflow.golden_records.changes"


# ---------------------------------------------------------------------------
# Task dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskConfig:
    task_id: str
    description: str
    retries: int = 2
    retry_delay_seconds: int = 120
    sla_minutes: Optional[int] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class DAGConfig:
    dag_id: str
    schedule_interval: str
    sla: timedelta
    max_active_runs: int
    concurrency: int
    default_args: Dict[str, Any]
    tags: List[str]
    task_dependencies: Dict[str, List[str]]


# ---------------------------------------------------------------------------
# Task functions
# ---------------------------------------------------------------------------

def load_domain_updates(
    domain_stores: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We collect the list of client golden IDs that had
    data changes in any domain in today's refresh cycle.

    This is the starting scope for the golden record
    update run. Processing only changed clients keeps
    the daily run within the 45-minute SLA.
    """

    as_of = run_date or datetime.now(timezone.utc)
    updated_clients = (
        domain_stores.get_todays_updated_clients(as_of=as_of)
        if domain_stores
        else []
    )

    print(f"[INFO] load_domain_updates: {len(updated_clients)} clients updated across domains today")
    return {"updated_clients": updated_clients, "client_count": len(updated_clients)}


def run_entity_resolution(
    domain_updates: Dict,
    entity_resolver: Any,
    **context: Any,
) -> Dict:
    """
    We re-run entity resolution for clients that have
    ambiguous matches or newly ingested aliases.

    Common resolution triggers:
    - New CIB payment with a slightly different entity name
    - New SIM activation batch under a trading name
    - Insurance policy under an abbreviated legal name

    Resolved entities are linked to their golden ID.
    Unresolvable entities are queued for manual review.
    """

    clients = domain_updates.get("updated_clients", [])
    resolved = 0
    queued_for_review = 0

    if entity_resolver:
        result = entity_resolver.resolve_ambiguous(client_ids=clients)
        resolved = result.get("resolved", 0)
        queued_for_review = result.get("queued_for_review", 0)

    print(
        f"[INFO] run_entity_resolution: "
        f"{resolved} resolved, {queued_for_review} queued for manual review"
    )
    return {"resolved": resolved, "queued_for_review": queued_for_review}


def check_golden_record_freshness(
    domain_updates: Dict,
    freshness_monitor: Any,
    **context: Any,
) -> Dict:
    """
    We verify that each domain has contributed fresh data
    for the clients being updated.

    A domain is fresh if it has updated a client's data
    within DOMAIN_FRESHNESS_HOURS[domain] hours.
    Stale domain contributions are flagged in the golden
    record metadata so downstream models can downweight
    them appropriately.
    """

    clients = domain_updates.get("updated_clients", [])
    freshness_status: Dict[str, Dict] = {}

    for domain, max_hours in DOMAIN_FRESHNESS_HOURS.items():
        if freshness_monitor:
            status = freshness_monitor.check_domain(domain, max_hours=max_hours)
            freshness_status[domain] = {
                "is_fresh": status.get("is_fresh", True),
                "staleness_hours": status.get("staleness_hours", 0),
            }
        else:
            freshness_status[domain] = {"is_fresh": True, "staleness_hours": 0}

    stale_domains = [d for d, s in freshness_status.items() if not s["is_fresh"]]

    if stale_domains:
        print(f"[WARNING] Stale domains for today's golden record update: {stale_domains}")

    print(
        f"[INFO] check_golden_record_freshness: "
        f"{len(clients)} clients, {len(stale_domains)} stale domains"
    )
    return {"freshness_status": freshness_status, "stale_domains": stale_domains}


def compute_cross_domain_features(
    domain_updates: Dict,
    resolution_result: Dict,
    freshness_result: Dict,
    feature_engine: Any,
    **context: Any,
) -> Dict:
    """
    We recompute the four core cross-domain features for
    each updated client:

    CLV (Customer Lifetime Value):
      Projected 5-year revenue across all products,
      informed by current product holdings, corridor
      activity, and comparable client benchmarks.

    NBA Score (Next Best Action):
      Top recommended action and confidence score,
      computed by the NBA model with fresh domain signals.

    Churn Risk (0–100):
      Probability of losing the primary banking mandate
      within 12 months, based on engagement decline,
      data shadow patterns, and competitor signals.

    Anomaly Score (0–100):
      Behavioural deviation from the client's own
      baseline and peer group, used to flag unusual
      activity for compliance review.
    """

    clients = domain_updates.get("updated_clients", [])
    available_domains = {
        domain
        for domain, status in freshness_result.get("freshness_status", {}).items()
        if status.get("is_fresh", True)
    }

    features = []
    if feature_engine:
        features = feature_engine.compute_cross_domain_features(
            client_ids=clients,
            available_domains=available_domains,
        )

    print(f"[INFO] compute_cross_domain_features: {len(features)} client feature sets computed")
    return {"features": features, "client_count": len(features)}


def run_consistency_checks(
    domain_updates: Dict,
    consistency_checker: Any,
    **context: Any,
) -> Dict:
    """
    We run cross-domain consistency validation.

    Checks:
    - Country overlap: countries in CIB payment corridors
      should have some overlap with cell SIM presence
    - Currency consistency: forex exposure currency mix
      should align with CIB payment currency mix
    - Headcount consistency: estimated cell headcount
      should be within 3x of CIB-reported employee count
    - Entity name consistency: names across domains
      should resolve to the same golden ID

    Inconsistencies are flagged in the golden record
    as data quality warnings, not hard failures.
    """

    clients = domain_updates.get("updated_clients", [])
    inconsistencies = []

    if consistency_checker:
        inconsistencies = consistency_checker.run_cross_domain_checks(
            client_ids=clients,
            min_country_overlap=COUNTRY_CONSISTENCY_MIN_OVERLAP,
        )

    print(
        f"[INFO] run_consistency_checks: {len(inconsistencies)} consistency issues found "
        f"across {len(clients)} clients"
    )
    return {"inconsistencies": inconsistencies, "issue_count": len(inconsistencies)}


def update_golden_records(
    feature_result: Dict,
    consistency_result: Dict,
    gold_store: Any,
    **context: Any,
) -> Dict:
    """
    We write the updated golden records to the gold layer.

    Each golden record contains:
    - Entity identity (golden_id, canonical name, aliases)
    - Domain presence flags and freshness timestamps
    - Cross-domain feature vector (CLV, NBA, churn, anomaly)
    - Data quality metadata (consistency flags, stale domains)
    - Relationship metadata (RM owner, client tier, country)
    """

    records_written = (
        gold_store.upsert_golden_records(
            features=feature_result.get("features", []),
            inconsistencies=consistency_result.get("inconsistencies", []),
        )
        if gold_store
        else 0
    )

    print(f"[INFO] update_golden_records: {records_written} golden records written to gold layer")
    return {"records_written": records_written, "layer": "gold"}


def invalidate_feature_cache(
    gold_result: Dict,
    feature_cache: Any,
    **context: Any,
) -> Dict:
    """
    We clear stale features from the serving layer cache.

    The serving layer caches golden record features for
    fast API response. After each golden record update
    we must invalidate the cache entries for updated
    clients so that the API serves fresh features.
    """

    keys_invalidated = (
        feature_cache.invalidate_batch(count=gold_result.get("records_written", 0))
        if feature_cache
        else 0
    )

    print(f"[INFO] invalidate_feature_cache: {keys_invalidated} cache keys invalidated")
    return {"keys_invalidated": keys_invalidated}


def publish_change_events(
    gold_result: Dict,
    kafka_producer: Any,
    **context: Any,
) -> Dict:
    """
    We publish golden record change events to the Kafka
    topic GOLDEN_RECORD_CHANGE_TOPIC.

    Consumers of this topic include:
    - The RM briefing service (regenerates client briefings)
    - The alert engine (checks if any alert thresholds
      have been crossed by the updated features)
    - The regulatory reporting service (logs golden record
      changes for audit trail)
    """

    events_published = 0

    if kafka_producer:
        events_published = kafka_producer.publish_change_events(
            topic=GOLDEN_RECORD_CHANGE_TOPIC,
            record_count=gold_result.get("records_written", 0),
        )

    print(
        f"[INFO] publish_change_events: {events_published} events published to "
        f"{GOLDEN_RECORD_CHANGE_TOPIC}"
    )
    return {"events_published": events_published, "topic": GOLDEN_RECORD_CHANGE_TOPIC}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   load_domain_updates
#          │
#   ┌──────┴──────────────────────┐
#   ▼                             ▼
#   run_entity_resolution   check_golden_record_freshness
#          │                           │
#          └────────────┬──────────────┘
#                        ▼
#         compute_cross_domain_features ◄── run_consistency_checks
#                        │
#                        ▼
#               update_golden_records
#                        │
#          ┌─────────────┴──────────────┐
#          ▼                            ▼
#   invalidate_feature_cache   publish_change_events
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "load_domain_updates":            [],
    "run_entity_resolution":          ["load_domain_updates"],
    "check_golden_record_freshness":  ["load_domain_updates"],
    "run_consistency_checks":         ["load_domain_updates"],
    "compute_cross_domain_features":  [
        "run_entity_resolution",
        "check_golden_record_freshness",
        "run_consistency_checks",
    ],
    "update_golden_records":          ["compute_cross_domain_features"],
    "invalidate_feature_cache":       ["update_golden_records"],
    "publish_change_events":          ["update_golden_records"],
}


# ---------------------------------------------------------------------------
# Programmatic DAG definition (Airflow SDK stub)
# ---------------------------------------------------------------------------

DAG_CONFIG = DAGConfig(
    dag_id=DAG_ID,
    schedule_interval=SCHEDULE_INTERVAL,
    sla=timedelta(minutes=SLA_MINUTES),
    max_active_runs=MAX_ACTIVE_RUNS,
    concurrency=CONCURRENCY,
    default_args={
        "owner":                    "data-engineering",
        "retries":                  2,
        "retry_delay":              timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "email_on_failure":         True,
        "email":                    ["data-engineering@afriflow.internal"],
    },
    tags=["golden-record", "daily", "cross-domain", "features", "gold", "kafka"],
    task_dependencies=TASK_DEPENDENCIES,
)
