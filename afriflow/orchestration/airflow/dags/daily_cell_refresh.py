"""
Daily Cell Domain Refresh DAG

We run this DAG every day to:
1. Ingest MoMo batch transactions, SIM activations,
   and USSD session logs from MTN API feeds
2. Validate schema and pseudonymise MSISDNs per RICA
3. Apply SIM deflation factors and detect workforce growth
4. Aggregate MoMo cross-border corridors
5. Write to silver layer and detect expansion signals

Design decisions:
  - Ingest tasks run in parallel — MoMo, SIM activations,
    and USSD sessions are independent MTN data products
  - Schema validation gates all three ingest tasks together
  - Pseudonymisation runs immediately after schema validation
    as raw MSISDNs must not persist beyond the staging table
  - SIM deflation and workforce growth detection are
    sequential — deflation factors must be applied before
    headcount estimation
  - MoMo corridor aggregation is independent of the SIM
    pipeline and runs in parallel after pseudonymisation
  - Silver write consolidates all cell outputs
  - Expansion signal detection runs last as it needs the
    full silver layer picture

SLA: All cell data must be refreshed within 90 minutes.

Disclaimer: This is not a sanctioned Standard Bank Group
or MTN Group project. Built by Thabo Kunene for portfolio
purposes. All data is simulated.
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

DAG_ID = "daily_cell_refresh"
SCHEDULE_INTERVAL = "@daily"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 4
SLA_MINUTES = 90


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# RICA requires MSISDN pseudonymisation per country.
# HMAC key rotation schedule — keys rotate every 90 days.
RICA_HMAC_KEY_ROTATION_DAYS = 90

# Workforce growth alert threshold — % change in SIM
# count month-over-month that triggers an expansion signal.
WORKFORCE_GROWTH_THRESHOLD_PCT = 10.0

# MoMo corridor minimum daily volume (USD) before we
# include the corridor in the expansion signal evaluation.
CORRIDOR_MIN_VOLUME_USD = 1_000.0


# ---------------------------------------------------------------------------
# Task dataclasses
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

def ingest_momo_transactions(
    mtn_api_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull the daily MoMo transaction batch from the
    MTN API for all 20 AfriFlow countries.

    MoMo data is the richest signal in the cell domain.
    Salary batches reveal headcount. Merchant receipts
    reveal revenue. Cross-border transfers reveal trade
    corridors that CIB payments may not capture.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = mtn_api_client.pull_momo_batch(as_of=as_of) if mtn_api_client else []

    print(f"[INFO] ingest_momo_transactions: {len(records)} transactions ingested")
    return {"source": "momo", "record_count": len(records), "as_of": as_of.isoformat()}


def ingest_sim_activations(
    mtn_api_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull corporate SIM activation reports from MTN's
    enterprise customer portal.

    A burst of SIM activations for a corporate client
    in a new country is a strong leading indicator of
    workforce expansion — typically 1–3 months before
    the client formally announces market entry.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = mtn_api_client.pull_sim_activations(as_of=as_of) if mtn_api_client else []

    print(f"[INFO] ingest_sim_activations: {len(records)} activation records ingested")
    return {"source": "sim_activations", "record_count": len(records), "as_of": as_of.isoformat()}


def ingest_ussd_sessions(
    mtn_api_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull USSD session logs. USSD is the dominant
    channel for MoMo in low-smartphone-penetration markets.

    Session type distribution (airtime check vs MoMo
    transfer vs balance) is a proxy for financial
    inclusion depth in each market.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = mtn_api_client.pull_ussd_sessions(as_of=as_of) if mtn_api_client else []

    print(f"[INFO] ingest_ussd_sessions: {len(records)} USSD sessions ingested")
    return {"source": "ussd_sessions", "record_count": len(records), "as_of": as_of.isoformat()}


def validate_cell_schema(
    momo_result: Dict,
    sim_result: Dict,
    ussd_result: Dict,
    schema_registry: Any,
    **context: Any,
) -> Dict:
    """
    We validate all three cell data feeds against their
    registered Avro schemas.

    Critical fields: msisdn (not null), country (ISO2),
    timestamp (parseable), amount_local (positive for
    financial transactions).
    """

    sources = [momo_result, sim_result, ussd_result]
    total = sum(r.get("record_count", 0) for r in sources)
    violations = 0

    if schema_registry:
        violations = schema_registry.validate_cell_batch(sources)

    violation_pct = (violations / total * 100) if total > 0 else 0.0

    print(
        f"[INFO] validate_cell_schema: {total} total records, "
        f"{violations} violations ({violation_pct:.2f}%)"
    )
    return {"total_records": total, "violations": violations, "violation_pct": violation_pct}


def pseudonymise_msisdns(
    validation_result: Dict,
    pseudonymiser: Any,
    **context: Any,
) -> Dict:
    """
    We apply RICA-compliant HMAC pseudonymisation to all
    MSISDNs before they leave the staging area.

    Each country uses a separate HMAC key, rotated every
    RICA_HMAC_KEY_ROTATION_DAYS days. This ensures that
    pseudonyms cannot be de-anonymised across key periods.

    Raw MSISDNs are purged from staging immediately after
    this task completes.
    """

    records_pseudonymised = 0
    if pseudonymiser:
        result = pseudonymiser.apply_rica_hmac()
        records_pseudonymised = result.get("records_processed", 0)

    print(f"[INFO] pseudonymise_msisdns: {records_pseudonymised} MSISDNs pseudonymised")
    return {"records_pseudonymised": records_pseudonymised, "hmac_applied": True}


def compute_sim_deflation(
    pseudonymise_result: Dict,
    deflation_calculator: Any,
    **context: Any,
) -> Dict:
    """
    We apply country-specific SIM deflation factors to
    convert raw active SIM counts to headcount estimates.

    Deflation factors account for:
    - Multi-SIM behaviour (one person, multiple SIMs)
    - Dormant SIMs still registered to active accounts
    - Shared corporate SIMs (e.g. devices passed between
      shift workers)

    Deflation factors are calibrated annually using
    national census and telecom regulator data.
    """

    deflated_counts = {}
    if deflation_calculator:
        deflated_counts = deflation_calculator.apply_deflation()

    print(
        f"[INFO] compute_sim_deflation: "
        f"deflated counts for {len(deflated_counts)} client-country pairs"
    )
    return {"deflated_headcounts": deflated_counts}


def detect_workforce_growth(
    deflation_result: Dict,
    growth_detector: Any,
    **context: Any,
) -> Dict:
    """
    We compare deflated SIM counts to the prior month's
    baseline to detect significant workforce growth.

    Growth > WORKFORCE_GROWTH_THRESHOLD_PCT triggers an
    expansion signal that feeds into the NBA model.

    We also flag contractions — workforce reduction is an
    early warning of financial distress.
    """

    growth_signals = []
    contraction_signals = []

    if growth_detector:
        result = growth_detector.detect(
            deflated_headcounts=deflation_result.get("deflated_headcounts", {}),
            threshold_pct=WORKFORCE_GROWTH_THRESHOLD_PCT,
        )
        growth_signals = result.get("growth", [])
        contraction_signals = result.get("contraction", [])

    print(
        f"[INFO] detect_workforce_growth: "
        f"{len(growth_signals)} growth signals, "
        f"{len(contraction_signals)} contraction signals"
    )
    return {"growth_signals": growth_signals, "contraction_signals": contraction_signals}


def aggregate_momo_corridors(
    pseudonymise_result: Dict,
    corridor_aggregator: Any,
    **context: Any,
) -> Dict:
    """
    We build the cross-border MoMo flow summary — total
    volume and transaction count by country pair.

    MoMo corridors often precede formal banking corridors.
    A client's employees remitting from Nigeria to Ghana
    suggests a Ghana expansion is underway or imminent.

    We filter corridors below CORRIDOR_MIN_VOLUME_USD to
    exclude noise from incidental transfers.
    """

    corridors = {}
    if corridor_aggregator:
        corridors = corridor_aggregator.aggregate_momo_corridors(
            min_volume_usd=CORRIDOR_MIN_VOLUME_USD
        )

    print(f"[INFO] aggregate_momo_corridors: {len(corridors)} active corridors")
    return {"momo_corridors": corridors, "corridor_count": len(corridors)}


def update_cell_silver(
    pseudonymise_result: Dict,
    deflation_result: Dict,
    corridor_result: Dict,
    silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We write all cell domain outputs to the silver layer:
    pseudonymised MoMo transactions, deflated SIM counts,
    MoMo corridor aggregates, and USSD session summaries.
    """

    rows_written = (
        silver_store.write_cell_silver(
            pseudonymise_result, deflation_result, corridor_result
        )
        if silver_store
        else 0
    )

    print(f"[INFO] update_cell_silver: {rows_written} rows written")
    return {"rows_written": rows_written, "layer": "silver"}


def detect_expansion_signals(
    silver_result: Dict,
    growth_result: Dict,
    corridor_result: Dict,
    signal_detector: Any,
    **context: Any,
) -> Dict:
    """
    We run the cell-domain expansion signal detector across
    the consolidated silver layer.

    Expansion patterns we look for:
    - New SIM activation cluster in a country with no
      prior corporate presence
    - MoMo salary batch appearing for a new country
    - Cross-border MoMo corridor opening between a known
      corporate market and a new market
    - Workforce growth > 20% in a single month
    """

    signals = []
    if signal_detector:
        signals = signal_detector.detect_expansion(
            silver_result=silver_result,
            growth_signals=growth_result.get("growth_signals", []),
            momo_corridors=corridor_result.get("momo_corridors", {}),
        )

    print(f"[INFO] detect_expansion_signals: {len(signals)} expansion signals")
    return {"expansion_signals": signals, "signal_count": len(signals)}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   ingest_momo_transactions ─┐
#   ingest_sim_activations    ─┼─► validate_cell_schema
#   ingest_ussd_sessions      ─┘         │
#                                         ▼
#                               pseudonymise_msisdns
#                               ┌──────────┴──────────┐
#                               ▼                     ▼
#                      compute_sim_deflation  aggregate_momo_corridors
#                               │                     │
#                               ▼                     │
#                      detect_workforce_growth        │
#                               │                     │
#                               └──────────┬──────────┘
#                                          ▼
#                                 update_cell_silver
#                                          │
#                                          ▼
#                                detect_expansion_signals
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "ingest_momo_transactions":    [],
    "ingest_sim_activations":      [],
    "ingest_ussd_sessions":        [],
    "validate_cell_schema":        [
        "ingest_momo_transactions",
        "ingest_sim_activations",
        "ingest_ussd_sessions",
    ],
    "pseudonymise_msisdns":        ["validate_cell_schema"],
    "compute_sim_deflation":       ["pseudonymise_msisdns"],
    "detect_workforce_growth":     ["compute_sim_deflation"],
    "aggregate_momo_corridors":    ["pseudonymise_msisdns"],
    "update_cell_silver":          [
        "detect_workforce_growth",
        "aggregate_momo_corridors",
    ],
    "detect_expansion_signals":    ["update_cell_silver"],
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
    tags=["cell", "daily", "momo", "sim", "ussd", "expansion", "silver"],
    task_dependencies=TASK_DEPENDENCIES,
)
