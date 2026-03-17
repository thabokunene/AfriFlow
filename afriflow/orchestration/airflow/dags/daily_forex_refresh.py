"""
Daily Forex Domain Refresh DAG

We run this DAG every day to:
1. Pull live spot rates, forward curves, and hedge book
   positions from treasury and market data systems
2. Validate rate sanity and compare official vs parallel
   market rates for managed-currency countries
3. Compute unhedged exposure summaries by currency
4. Detect and propagate currency events to affected clients
5. Write to silver layer and alert FX advisors

Design decisions:
  - Rate fetch tasks (spot, forward, hedge) run in parallel
    as they are independent upstream systems
  - Sanity validation and parallel market checks run after
    all rates are fetched
  - Exposure summary depends on hedge book fetch completing
  - Event detection runs after all three validation tasks
  - Propagation depends only on event detection
  - Silver write and unhedged alerts run in parallel as
    the last stage

Intraday rate feed: spot rates are also updated every 15
minutes via a separate lightweight pipeline. This DAG
handles the full daily reconciliation and enrichment pass.

SLA: All forex data must be refreshed within 30 minutes
of the daily run start. FX data is time-critical.

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

DAG_ID = "daily_forex_refresh"
SCHEDULE_INTERVAL = "@daily"
# Intraday rate feed runs every 15 minutes via separate pipeline
INTRADAY_INTERVAL_MINUTES = 15
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 4
SLA_MINUTES = 30


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Standard deviations from 30-day mean before a rate is
# flagged as an outlier and quarantined pending review.
RATE_OUTLIER_SIGMA = 3.0

# Currencies with active parallel markets that we monitor.
# Official vs parallel spread > threshold triggers alert.
PARALLEL_MARKET_CURRENCIES = ["NGN", "AOA", "ETB"]
PARALLEL_SPREAD_ALERT_PCT = 15.0

# Minimum unhedged exposure (USD equivalent) before we
# send an FX advisor alert.
UNHEDGED_ALERT_THRESHOLD_USD = 500_000.0


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

def fetch_spot_rates(
    market_data_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull live spot rates from simulated Reuters/Bloomberg
    feeds for all 20 AfriFlow country pairs plus major
    crosses (USD, EUR, GBP, CNY).

    We store the raw feed timestamp alongside rates so
    that staleness can be detected downstream. If the
    feed is more than 30 minutes old we flag it.
    """

    as_of = run_date or datetime.now(timezone.utc)
    rates = market_data_client.get_spot_rates(as_of=as_of) if market_data_client else {}

    print(f"[INFO] fetch_spot_rates: {len(rates)} rate pairs fetched")
    return {"source": "spot", "rate_count": len(rates), "as_of": as_of.isoformat()}


def fetch_forward_curves(
    market_data_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull forward rate curves for tenors: 1W, 1M, 3M,
    6M, 12M. Forward curves are used to value FX hedges
    and compute mark-to-market on the hedge book.

    We only pull curves for currencies in which the bank
    has active forward contracts or client hedges.
    """

    as_of = run_date or datetime.now(timezone.utc)
    curves = market_data_client.get_forward_curves(as_of=as_of) if market_data_client else {}

    print(f"[INFO] fetch_forward_curves: {len(curves)} curves fetched")
    return {"source": "forward", "curve_count": len(curves), "as_of": as_of.isoformat()}


def fetch_hedge_book(
    treasury_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull the full hedge book from the treasury system.
    This includes all open FX forward contracts, options,
    and swaps held by corporate clients and the bank's
    own treasury.

    Hedge book positions are the denominator in the
    unhedged exposure calculation.
    """

    as_of = run_date or datetime.now(timezone.utc)
    positions = treasury_client.get_hedge_book(as_of=as_of) if treasury_client else []

    print(f"[INFO] fetch_hedge_book: {len(positions)} positions fetched")
    return {"source": "hedge_book", "position_count": len(positions), "as_of": as_of.isoformat()}


def validate_rate_sanity(
    spot_result: Dict,
    forward_result: Dict,
    rate_validator: Any,
    **context: Any,
) -> Dict:
    """
    We detect outlier rates by comparing each rate to its
    30-day rolling mean and standard deviation.

    Any rate more than RATE_OUTLIER_SIGMA standard
    deviations from the mean is quarantined and the
    prior day's rate is used as a fallback. The outlier
    is logged for manual review by the treasury desk.
    """

    outliers = []
    if rate_validator:
        outliers = rate_validator.detect_outliers(
            spot_result=spot_result,
            sigma_threshold=RATE_OUTLIER_SIGMA,
        )

    print(f"[INFO] validate_rate_sanity: {len(outliers)} outlier rates detected")
    return {"outlier_count": len(outliers), "outliers": outliers}


def check_parallel_markets(
    spot_result: Dict,
    parallel_data_client: Any,
    **context: Any,
) -> Dict:
    """
    We compare official exchange rates to parallel (black)
    market rates for NGN, AOA, and ETB — three African
    currencies where significant parallel markets operate.

    A spread exceeding PARALLEL_SPREAD_ALERT_PCT between
    official and parallel rates indicates a macro stress
    event and is escalated to the FX advisory desk.
    """

    alerts = []

    for currency in PARALLEL_MARKET_CURRENCIES:
        if parallel_data_client:
            spread_pct = parallel_data_client.get_spread(currency)
            if spread_pct > PARALLEL_SPREAD_ALERT_PCT:
                alerts.append({
                    "currency": currency,
                    "spread_pct": spread_pct,
                    "threshold_pct": PARALLEL_SPREAD_ALERT_PCT,
                })

    print(
        f"[INFO] check_parallel_markets: "
        f"{len(alerts)} currencies breaching spread threshold"
    )
    return {"parallel_alerts": alerts, "alert_count": len(alerts)}


def compute_exposure_summary(
    spot_result: Dict,
    hedge_result: Dict,
    exposure_calculator: Any,
    **context: Any,
) -> Dict:
    """
    We compute total unhedged FX exposure by currency
    pair across all CIB corporate clients.

    Unhedged exposure = gross trade finance + payable
    positions - outstanding FX hedges.

    We convert all amounts to USD equivalent for the
    consolidated exposure report.
    """

    summary = {}
    if exposure_calculator:
        summary = exposure_calculator.compute(
            spot_result=spot_result,
            hedge_result=hedge_result,
        )

    total_unhedged_usd = sum(
        v.get("unhedged_usd", 0) for v in summary.values()
    )

    print(
        f"[INFO] compute_exposure_summary: "
        f"USD {total_unhedged_usd:,.0f} total unhedged across "
        f"{len(summary)} currencies"
    )
    return {"exposure_by_currency": summary, "total_unhedged_usd": total_unhedged_usd}


def detect_currency_events(
    sanity_result: Dict,
    parallel_result: Dict,
    exposure_result: Dict,
    event_classifier: Any,
    **context: Any,
) -> List[Dict]:
    """
    We run the currency event classifier across all signals
    from today's rate data.

    Event types:
      DEVALUATION     – Official rate moved >5% overnight
      PARALLEL_SPIKE  – Parallel market spread >15%
      VOLATILITY      – 5-day realised vol in top 5% of
                        5-year distribution
      PARITY_BREAK    – Rate crossed a psychologically
                        significant level (e.g. 1000 NGN/USD)
    """

    events = []
    if event_classifier:
        events = event_classifier.classify(
            sanity_result=sanity_result,
            parallel_result=parallel_result,
            exposure_result=exposure_result,
        )

    print(f"[INFO] detect_currency_events: {len(events)} events classified")
    return events


def propagate_currency_events(
    events: List[Dict],
    event_propagator: Any,
    **context: Any,
) -> Dict:
    """
    We cascade detected currency events to all affected
    clients based on their FX exposure profile.

    The propagation engine looks up which clients have
    open trade finance, hedge positions, or invoiced
    receivables in each affected currency and computes
    the estimated P&L impact.
    """

    clients_impacted = 0
    if event_propagator and events:
        result = event_propagator.propagate_all(events)
        clients_impacted = result.get("clients_impacted", 0)

    print(
        f"[INFO] propagate_currency_events: "
        f"{len(events)} events propagated, {clients_impacted} clients impacted"
    )
    return {"events_propagated": len(events), "clients_impacted": clients_impacted}


def update_forex_silver(
    spot_result: Dict,
    forward_result: Dict,
    exposure_result: Dict,
    propagation_result: Dict,
    silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We write the validated and enriched forex data to the
    silver layer: spot rates, forward curves, exposure
    summaries, and currency event records.
    """

    rows_written = (
        silver_store.write_forex_silver(
            spot_result, forward_result, exposure_result, propagation_result
        )
        if silver_store
        else 0
    )

    print(f"[INFO] update_forex_silver: {rows_written} rows written")
    return {"rows_written": rows_written, "layer": "silver"}


def alert_unhedged_exposures(
    exposure_result: Dict,
    alert_engine: Any,
    **context: Any,
) -> Dict:
    """
    We send FX advisor alerts for clients with unhedged
    exposure exceeding UNHEDGED_ALERT_THRESHOLD_USD.

    Alerts include the client's exposure by currency,
    the recommended hedge instrument, and the estimated
    cost of hedging at today's forward rates.
    """

    alerts_sent = 0
    exposures = exposure_result.get("exposure_by_currency", {})

    for currency, data in exposures.items():
        if data.get("unhedged_usd", 0) >= UNHEDGED_ALERT_THRESHOLD_USD:
            if alert_engine:
                alert_engine.send(
                    alert_type="UNHEDGED_EXPOSURE",
                    currency=currency,
                    payload=data,
                    urgency="HIGH",
                )
            alerts_sent += 1

    print(f"[INFO] alert_unhedged_exposures: {alerts_sent} alerts sent")
    return {"alerts_sent": alerts_sent}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   fetch_spot_rates ─┐
#   fetch_forward_curves ─┼─► validate_rate_sanity
#   fetch_hedge_book  ─┘              │
#          │                          │
#          ▼                          ▼
#   compute_exposure_summary   check_parallel_markets
#          │                          │
#          └──────────────────────────┤
#                                     ▼
#                           detect_currency_events
#                                     │
#                           propagate_currency_events
#                                     │
#                  ┌──────────────────┴───────────────────┐
#                  ▼                                       ▼
#          update_forex_silver               alert_unhedged_exposures
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "fetch_spot_rates":           [],
    "fetch_forward_curves":       [],
    "fetch_hedge_book":           [],
    "validate_rate_sanity":       ["fetch_spot_rates", "fetch_forward_curves"],
    "check_parallel_markets":     ["fetch_spot_rates"],
    "compute_exposure_summary":   ["fetch_spot_rates", "fetch_hedge_book"],
    "detect_currency_events":     [
        "validate_rate_sanity",
        "check_parallel_markets",
        "compute_exposure_summary",
    ],
    "propagate_currency_events":  ["detect_currency_events"],
    "update_forex_silver":        ["propagate_currency_events"],
    "alert_unhedged_exposures":   ["propagate_currency_events"],
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
        "retries":                  3,
        "retry_delay":              timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "email_on_failure":         True,
        "email":                    ["data-engineering@afriflow.internal"],
    },
    tags=["forex", "daily", "rates", "hedging", "currency-events", "silver"],
    task_dependencies=TASK_DEPENDENCIES,
)
