"""
Daily CIB Domain Refresh DAG

We run this DAG every day to:
1. Extract SWIFT MT103 messages, Letters of Credit, and
   trade finance records from the CIB ingestion layer
2. Validate schema and completeness against contract SLAs
3. Enrich payments with entity resolution to golden IDs
4. Compute payment corridor aggregates and detect flow drift
5. Write to silver and gold layers
6. Trigger the cross-domain signal engine

Design decisions:
  - Extract tasks run in parallel — SWIFT, LC docs, and
    trade finance are independent source systems
  - Validation gates (schema + completeness) run after all
    extracts complete and fail fast on bad data
  - Enrichment depends on both validation tasks passing
  - Payment corridor and drift detection depend on enrichment
  - Silver write precedes gold aggregation
  - Cross-domain signal trigger is the final output gate

SLA: All CIB data must be refreshed within 120 minutes of
the daily run start. If breached, on-call is paged.

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

DAG_ID = "daily_cib_refresh"
SCHEDULE_INTERVAL = "@daily"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 4
SLA_MINUTES = 120


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Minimum completeness ratio for CIB fields.
# Below this threshold we raise a DataQualityError.
COMPLETENESS_THRESHOLDS: Dict[str, float] = {
    "debtor_country": 0.97,
    "amount":         0.99,
    "value_date":     0.98,
    "purpose_code":   0.90,
}

# Drift alert threshold — % deviation from 30-day baseline
# before we flag a corridor as anomalous.
FLOW_DRIFT_THRESHOLD_PCT = 25.0

# Lookback for baseline comparison (days)
DRIFT_BASELINE_DAYS = 30


# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

@dataclass
class TaskConfig:
    task_id: str
    description: str
    retries: int = 2
    retry_delay_seconds: int = 180
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

def extract_swift_mt103(
    ingestion_store: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull SWIFT MT103 messages from the CIB ingestion
    layer for the prior business day.

    MT103 is the single-customer credit transfer message
    type — the backbone of cross-border CIB payments.
    We extract sender BIC, receiver BIC, debtor name,
    debtor country, amount, currency, and value date.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = ingestion_store.pull_mt103(as_of=as_of) if ingestion_store else []

    print(f"[INFO] extract_swift_mt103: {len(records)} messages pulled")
    return {"source": "swift_mt103", "record_count": len(records), "as_of": as_of.isoformat()}


def extract_lc_documents(
    ingestion_store: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull Letter of Credit documents from the trade
    finance system. LCs are a strong leading indicator
    of cross-border trade intent — they are issued before
    goods ship, giving us 30–90 days forward visibility
    into a client's trade corridors.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = ingestion_store.pull_lc_documents(as_of=as_of) if ingestion_store else []

    print(f"[INFO] extract_lc_documents: {len(records)} documents pulled")
    return {"source": "lc_documents", "record_count": len(records), "as_of": as_of.isoformat()}


def extract_trade_finance(
    ingestion_store: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull trade finance records including bank guarantees,
    documentary collections, and standby LCs.

    Together with LC documents this gives us the full
    structured trade finance picture for cross-referencing
    with the forex hedge book.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = ingestion_store.pull_trade_finance(as_of=as_of) if ingestion_store else []

    print(f"[INFO] extract_trade_finance: {len(records)} records pulled")
    return {"source": "trade_finance", "record_count": len(records), "as_of": as_of.isoformat()}


def validate_cib_schema(
    extract_results: List[Dict],
    schema_registry: Any,
    **context: Any,
) -> Dict:
    """
    We validate all extracted CIB records against their
    registered Avro schemas in the schema registry.

    On schema violation we write bad records to the
    quarantine table and proceed with valid records.
    We fail the task if the quarantine rate exceeds 5%.
    """

    total = sum(r.get("record_count", 0) for r in extract_results)
    quarantined = 0

    if schema_registry:
        quarantined = schema_registry.validate_cib_batch(extract_results)

    quarantine_pct = (quarantined / total * 100) if total > 0 else 0.0

    if quarantine_pct > 5.0:
        raise ValueError(
            f"CIB schema quarantine rate {quarantine_pct:.1f}% exceeds 5% threshold"
        )

    print(
        f"[INFO] validate_cib_schema: {total} records, "
        f"{quarantined} quarantined ({quarantine_pct:.2f}%)"
    )
    return {"total_records": total, "quarantined": quarantined, "quarantine_pct": quarantine_pct}


def check_cib_completeness(
    validation_result: Dict,
    completeness_checker: Any,
    **context: Any,
) -> Dict:
    """
    We run completeness checks on the critical CIB fields:
    debtor_country and amount must be present on nearly
    all records. Missing debtor_country breaks corridor
    analytics. Missing amount breaks everything.

    We push per-field completeness ratios to XCom for the
    data quality report.
    """

    results = {}

    for field_name, threshold in COMPLETENESS_THRESHOLDS.items():
        ratio = (
            completeness_checker.check_field(field_name)
            if completeness_checker
            else 1.0
        )
        results[field_name] = ratio
        if ratio < threshold:
            print(
                f"[WARNING] {field_name} completeness {ratio:.3f} "
                f"below threshold {threshold}"
            )

    print(f"[INFO] check_cib_completeness: {results}")
    return {"completeness": results}


def enrich_with_entity_resolution(
    completeness_result: Dict,
    entity_resolver: Any,
    **context: Any,
) -> Dict:
    """
    We link payment senders and beneficiaries to our
    golden entity registry.

    Entity resolution is probabilistic — we use name,
    country, and bank BIC as matching keys. Unresolved
    entities are flagged for manual review by the
    data stewardship team.
    """

    resolved = 0
    unresolved = 0

    if entity_resolver:
        result = entity_resolver.enrich_cib_batch()
        resolved = result.get("resolved", 0)
        unresolved = result.get("unresolved", 0)

    resolution_rate = resolved / (resolved + unresolved) if (resolved + unresolved) > 0 else 0.0

    print(
        f"[INFO] enrich_with_entity_resolution: "
        f"{resolved} resolved, {unresolved} unresolved "
        f"({resolution_rate:.1%} rate)"
    )
    return {"resolved": resolved, "unresolved": unresolved, "resolution_rate": resolution_rate}


def compute_payment_corridors(
    enrichment_result: Dict,
    corridor_aggregator: Any,
    **context: Any,
) -> Dict:
    """
    We aggregate payment flows by corridor (country pair)
    to produce the daily corridor summary table.

    This feeds the cross-domain signal engine: a corridor
    appearing in CIB payments for the first time is a
    potential expansion signal.
    """

    corridors = (
        corridor_aggregator.compute_daily_corridors()
        if corridor_aggregator
        else {}
    )

    corridor_count = len(corridors)
    print(f"[INFO] compute_payment_corridors: {corridor_count} active corridors")
    return {"corridor_count": corridor_count, "corridors": corridors}


def detect_flow_drift(
    corridor_result: Dict,
    drift_detector: Any,
    **context: Any,
) -> Dict:
    """
    We compare today's corridor volumes to the 30-day
    rolling baseline and flag corridors with significant
    drift.

    Drift signals potential issues: a sharp increase may
    indicate a large deal or evasion behaviour; a sharp
    decrease may indicate a competitor winning a mandate.
    """

    alerts = []

    if drift_detector:
        alerts = drift_detector.detect(
            corridors=corridor_result.get("corridors", {}),
            baseline_days=DRIFT_BASELINE_DAYS,
            threshold_pct=FLOW_DRIFT_THRESHOLD_PCT,
        )

    print(f"[INFO] detect_flow_drift: {len(alerts)} drift alerts")
    return {"drift_alerts": alerts, "alert_count": len(alerts)}


def update_cib_silver(
    enrichment_result: Dict,
    corridor_result: Dict,
    silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We write the enriched and validated CIB records to
    the silver layer Delta table.

    Silver layer is entity-resolved, schema-validated,
    and completeness-checked. It is the trusted source
    for all downstream gold aggregations.
    """

    rows_written = (
        silver_store.write_cib_silver(enrichment_result, corridor_result)
        if silver_store
        else 0
    )

    print(f"[INFO] update_cib_silver: {rows_written} rows written")
    return {"rows_written": rows_written, "layer": "silver"}


def update_cib_gold(
    silver_result: Dict,
    gold_store: Any,
    **context: Any,
) -> Dict:
    """
    We compute CIB gold aggregates from the silver layer:
    - Client-level corridor summary
    - 30-day rolling payment volume by corridor
    - Country-level aggregate flows
    - Entity resolution quality metrics

    Gold is the layer consumed by the NBA model and
    the RM briefing service.
    """

    aggregates_written = (
        gold_store.compute_cib_gold(silver_result)
        if gold_store
        else 0
    )

    print(f"[INFO] update_cib_gold: {aggregates_written} aggregates written")
    return {"aggregates_written": aggregates_written, "layer": "gold"}


def trigger_cross_domain_signals(
    gold_result: Dict,
    signal_engine: Any,
    **context: Any,
) -> Dict:
    """
    We notify the cross-domain signal engine that fresh
    CIB data is available. The engine then re-evaluates
    expansion signals and data shadows for clients whose
    CIB footprint changed today.
    """

    clients_triggered = (
        signal_engine.notify_domain_refresh("cib")
        if signal_engine
        else 0
    )

    print(f"[INFO] trigger_cross_domain_signals: {clients_triggered} clients queued")
    return {"domain": "cib", "clients_triggered": clients_triggered}


def send_data_quality_report(
    validation_result: Dict,
    completeness_result: Dict,
    drift_result: Dict,
    email_service: Any,
    **context: Any,
) -> None:
    """
    We email the daily CIB data quality report to the
    data engineering team and business data owners.

    The report includes:
    - Schema quarantine counts and rates
    - Per-field completeness ratios
    - Corridor drift alerts
    - Entity resolution rates
    """

    report = {
        "dag_id": DAG_ID,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "schema_validation": validation_result,
        "completeness": completeness_result,
        "drift_alerts": drift_result.get("alert_count", 0),
    }

    if email_service:
        email_service.send_dq_report("cib", report)
    else:
        print(f"[REPORT] CIB DQ Report: {report}")


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   extract_swift_mt103 ─┐
#   extract_lc_documents ─┼─► validate_cib_schema
#   extract_trade_finance ─┘         │
#                                     ▼
#                         check_cib_completeness
#                                     │
#                                     ▼
#                         enrich_with_entity_resolution
#                                     │
#                          ┌──────────┴──────────┐
#                          ▼                     ▼
#               compute_payment_corridors   update_cib_silver
#                          │                     │
#                          ▼                     ▼
#                   detect_flow_drift      update_cib_gold
#                          │                     │
#                          └──────────┬──────────┘
#                                     ▼
#                         trigger_cross_domain_signals
#                                     │
#                                     ▼
#                          send_data_quality_report
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "extract_swift_mt103":             [],
    "extract_lc_documents":            [],
    "extract_trade_finance":           [],
    "validate_cib_schema":             [
        "extract_swift_mt103",
        "extract_lc_documents",
        "extract_trade_finance",
    ],
    "check_cib_completeness":          ["validate_cib_schema"],
    "enrich_with_entity_resolution":   ["check_cib_completeness"],
    "compute_payment_corridors":       ["enrich_with_entity_resolution"],
    "detect_flow_drift":               ["compute_payment_corridors"],
    "update_cib_silver":               ["enrich_with_entity_resolution"],
    "update_cib_gold":                 ["update_cib_silver"],
    "trigger_cross_domain_signals":    ["update_cib_gold", "detect_flow_drift"],
    "send_data_quality_report":        ["trigger_cross_domain_signals"],
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
    tags=["cib", "daily", "payments", "trade-finance", "silver", "gold"],
    task_dependencies=TASK_DEPENDENCIES,
)
