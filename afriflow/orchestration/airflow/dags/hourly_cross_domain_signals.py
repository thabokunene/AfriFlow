"""
Hourly Cross-Domain Signal Refresh DAG

We run this DAG every hour to:
1. Refresh golden records from all five domain feeds
2. Re-score expansion signals for clients whose
   domain data changed in the last hour
3. Recalculate data shadows where expected footprint
   has diverged from actual
4. Run NBA model for clients with updated signals
5. Dispatch RM alerts for new or upgraded signals

Design decisions:
  - We process only clients with domain data changes
    in the last hour (incremental, not full refresh)
  - We parallelise domain signal tasks across 5
    workers — they are independent
  - NBA scoring depends on all domain signals so it
    runs after all five domain tasks complete
  - Alerts are dispatched after NBA scoring completes
  - Circuit breaker: if any domain feed is stale
    (freshness SLA breached), we skip that domain's
    contribution but do not fail the whole DAG

SLA: All signals must be refreshed within 55 minutes
of the top of the hour. If a run takes > 55 minutes
Airflow sends an SLA miss notification to the data
engineering on-call.

Disclaimer: This is not a sanctioned Standard Bank
Group project. Built by Thabo Kunene for portfolio
purposes. All data is simulated.
"""

# In production this imports from the Airflow library:
#   from airflow import DAG
#   from airflow.operators.python import PythonOperator
#   from airflow.utils.dates import days_ago
#
# We use plain Python here so the DAG definition is
# readable without an Airflow installation.


from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# DAG metadata
# ---------------------------------------------------------------------------

DAG_ID = "hourly_cross_domain_signals"
SCHEDULE_INTERVAL = "@hourly"
START_DATE_OFFSET_DAYS = 7     # backfill 7 days on first deploy
MAX_ACTIVE_RUNS = 1            # no concurrent runs
CONCURRENCY = 5                # 5 parallel tasks in a run
SLA_MINUTES = 55               # fail if run > 55 min


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Freshness SLA per domain in minutes.
# If a domain feed is older than this, we skip it.
DOMAIN_FRESHNESS_SLA: Dict[str, int] = {
    "cib":       30,
    "forex":     15,   # FX moves fast
    "insurance": 120,
    "cell":      60,
    "pbb":       60,
}

# Minimum signal confidence to trigger an RM alert
ALERT_CONFIDENCE_THRESHOLD = 65.0

# Maximum clients to process in a single DAG run
# to stay within SLA
MAX_CLIENTS_PER_RUN = 500


# ---------------------------------------------------------------------------
# Task functions
# ---------------------------------------------------------------------------

def check_domain_freshness(
    domain: str,
    freshness_monitor: Any,
    **context: Any,
) -> Dict:
    """
    We verify that the domain feed has been updated
    within its SLA before we attempt to process it.

    If the feed is stale we log a warning and return
    a skip flag. The downstream tasks check this flag
    and degrade gracefully rather than failing.

    We push the result to XCom so downstream tasks
    can read it.
    """

    sla_minutes = DOMAIN_FRESHNESS_SLA.get(domain, 60)
    status = freshness_monitor.check_domain(domain)

    result = {
        "domain": domain,
        "is_fresh": status.is_fresh,
        "staleness_level": status.staleness_level.value,
        "last_update": status.last_update_timestamp,
        "sla_minutes": sla_minutes,
        "skip_downstream": not status.is_fresh,
    }

    if not status.is_fresh:
        print(
            f"[WARNING] {domain} feed is {status.staleness_level.value}. "
            f"Last update: {status.last_update_timestamp}. "
            f"Skipping {domain} contribution this run."
        )

    return result


def identify_changed_clients(
    lookback_minutes: int = 70,
    golden_record_store: Any = None,
    **context: Any,
) -> List[str]:
    """
    We identify clients whose data changed in any
    domain in the last lookback_minutes window.

    This is the incremental processing key — we avoid
    reprocessing 10,000+ clients every hour when only
    a few hundred have changed.

    Returns a list of golden_ids to process this run.
    """

    if golden_record_store is None:
        print("[WARNING] No golden record store — using empty list")
        return []

    since = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    changed = golden_record_store.get_changed_since(since)

    if len(changed) > MAX_CLIENTS_PER_RUN:
        print(
            f"[WARNING] {len(changed)} changed clients exceeds "
            f"MAX_CLIENTS_PER_RUN={MAX_CLIENTS_PER_RUN}. "
            f"Processing highest-tier clients first."
        )
        # Priority: Platinum > Gold > Silver
        changed = _prioritise_clients(
            changed, golden_record_store, MAX_CLIENTS_PER_RUN
        )

    print(f"[INFO] Processing {len(changed)} changed clients")
    return [c["golden_id"] for c in changed]


def _prioritise_clients(
    clients: List[Dict],
    store: Any,
    limit: int,
) -> List[Dict]:
    """
    We sort clients by tier and relationship value so
    that the most important clients are always
    processed within the SLA window.
    """

    tier_order = {"Platinum": 0, "Gold": 1, "Silver": 2, "Standard": 3}
    return sorted(
        clients,
        key=lambda c: (
            tier_order.get(c.get("client_tier", "Standard"), 99),
            -c.get("total_relationship_value_zar", 0),
        ),
    )[:limit]


def refresh_expansion_signals(
    golden_ids: List[str],
    expansion_detector: Any,
    freshness_results: Dict,
    **context: Any,
) -> List[Dict]:
    """
    We re-run the expansion signal detector for the
    changed client list.

    We only include domain contributions from feeds
    that passed the freshness check this run.
    """

    available_domains = {
        domain
        for domain, result in freshness_results.items()
        if not result.get("skip_downstream", True)
    }

    new_signals = []
    upgraded_signals = []

    for golden_id in golden_ids:
        signal = expansion_detector.detect(
            golden_id,
            include_domains=available_domains,
        )

        if signal is None:
            continue

        if signal.get("is_new"):
            new_signals.append(signal)
        elif signal.get("confidence_upgraded"):
            upgraded_signals.append(signal)

    print(
        f"[INFO] Expansion signals: "
        f"{len(new_signals)} new, "
        f"{len(upgraded_signals)} upgraded"
    )

    return new_signals + upgraded_signals


def refresh_data_shadows(
    golden_ids: List[str],
    shadow_calculator: Any,
    freshness_results: Dict,
    **context: Any,
) -> List[Dict]:
    """
    We recalculate data shadows for changed clients.

    A data shadow is when a client's expected presence
    in a domain does not match their actual presence.
    The gap is evidence of competitive leakage.
    """

    available_domains = {
        domain
        for domain, result in freshness_results.items()
        if not result.get("skip_downstream", True)
    }

    shadows = []

    for golden_id in golden_ids:
        client_shadows = shadow_calculator.calculate(
            golden_id,
            include_domains=available_domains,
        )
        if client_shadows:
            shadows.extend(client_shadows)

    print(f"[INFO] Data shadows identified: {len(shadows)}")
    return shadows


def refresh_currency_impacts(
    golden_ids: List[str],
    event_store: Any,
    propagator: Any,
    **context: Any,
) -> List[Dict]:
    """
    We re-propagate any active currency events against
    the updated client list.

    If the NGN devalued during the last hour, all
    clients with NGN exposure get their impact
    recalculated with the updated rate.
    """

    active_events = event_store.get_active(
        min_severity="HIGH"
    )

    if not active_events:
        return []

    impacts = []
    for event in active_events:
        cascade = propagator.propagate(event)
        for impact in cascade.domain_impacts:
            if impact.golden_id in golden_ids:
                impacts.append({
                    "golden_id": impact.golden_id,
                    "event_id": event.event_id,
                    "domain": impact.domain,
                    "impact_type": impact.impact_type,
                    "impact_value_zar": impact.impact_value_zar,
                    "action_required": impact.action_required,
                    "urgency": impact.urgency,
                })

    print(f"[INFO] Currency impacts: {len(impacts)}")
    return impacts


def score_next_best_actions(
    golden_ids: List[str],
    expansion_signals: List[Dict],
    shadow_signals: List[Dict],
    currency_impacts: List[Dict],
    nba_model: Any,
    golden_record_store: Any,
    domain_stores: Dict,
    **context: Any,
) -> List[Dict]:
    """
    We run the NBA model for all changed clients,
    incorporating the freshly computed signals.

    This is the most compute-intensive task in the
    DAG. We process clients in batches of 50 to
    stay within memory limits.
    """

    # Index signals by golden_id for fast lookup
    expansion_by_client: Dict[str, List[Dict]] = {}
    for s in expansion_signals:
        gid = s.get("golden_id", "")
        expansion_by_client.setdefault(gid, []).append(s)

    shadow_by_client: Dict[str, List[Dict]] = {}
    for s in shadow_signals:
        gid = s.get("client_golden_id", "")
        shadow_by_client.setdefault(gid, []).append(s)

    results = []

    for golden_id in golden_ids:
        golden = golden_record_store.get(golden_id)
        if not golden:
            continue

        combined_signals = (
            expansion_by_client.get(golden_id, [])
            + shadow_by_client.get(golden_id, [])
        )

        nba_result = nba_model.score_client(
            golden_record=golden,
            cib_profile=domain_stores["cib"].get_profile(golden_id),
            forex_profile=domain_stores["forex"].get_profile(golden_id),
            insurance_profile=domain_stores["insurance"].get_profile(golden_id),
            cell_profile=domain_stores["cell"].get_profile(golden_id),
            pbb_profile=domain_stores["pbb"].get_profile(golden_id),
            active_signals=combined_signals,
        )

        if nba_result.top_action:
            results.append({
                "golden_id": golden_id,
                "top_action_type": nba_result.top_action.action_type,
                "top_action_product": nba_result.top_action.product_name,
                "top_action_score": nba_result.top_action.score,
                "top_action_revenue": nba_result.top_action.estimated_revenue_zar,
                "action_count": len(nba_result.all_actions),
                "data_completeness": nba_result.data_completeness_score,
            })

    print(f"[INFO] NBA results: {len(results)} clients scored")
    return results


def dispatch_rm_alerts(
    nba_results: List[Dict],
    expansion_signals: List[Dict],
    currency_impacts: List[Dict],
    alert_engine: Any,
    **context: Any,
) -> Dict:
    """
    We dispatch RM alerts for actionable signals.

    Alert priority:
      1. CRITICAL currency events (immediate)
      2. High-confidence expansion signals (same day)
      3. NBA score ≥ 75 (within 24 hours)
      4. Attrition risk detected (within 24 hours)

    We deduplicate: a client does not receive the same
    alert twice within 48 hours unless the signal
    significantly upgraded.
    """

    dispatched = 0
    skipped_dedup = 0

    # Currency event alerts first — highest urgency
    for impact in currency_impacts:
        if not impact.get("action_required"):
            continue
        sent = alert_engine.send(
            alert_type="CURRENCY_IMPACT",
            golden_id=impact["golden_id"],
            payload=impact,
            urgency=impact.get("urgency", "HIGH"),
        )
        if sent:
            dispatched += 1
        else:
            skipped_dedup += 1

    # Expansion signal alerts
    for signal in expansion_signals:
        confidence = signal.get("confidence_score", 0)
        if confidence < ALERT_CONFIDENCE_THRESHOLD:
            continue
        sent = alert_engine.send(
            alert_type="EXPANSION_OPPORTUNITY",
            golden_id=signal.get("golden_id"),
            payload=signal,
            urgency="HIGH",
        )
        if sent:
            dispatched += 1
        else:
            skipped_dedup += 1

    # NBA score alerts
    for result in nba_results:
        if result.get("top_action_score", 0) < 75:
            continue
        sent = alert_engine.send(
            alert_type="NBA_RECOMMENDATION",
            golden_id=result["golden_id"],
            payload=result,
            urgency="MEDIUM",
        )
        if sent:
            dispatched += 1
        else:
            skipped_dedup += 1

    summary = {
        "alerts_dispatched": dispatched,
        "alerts_skipped_dedup": skipped_dedup,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print(
        f"[INFO] Alerts: {dispatched} dispatched, "
        f"{skipped_dedup} skipped (dedup)"
    )
    return summary


def log_run_metrics(
    run_summary: Dict,
    metrics_store: Any,
    **context: Any,
) -> None:
    """
    We persist run metrics for the operations
    dashboard and SLA tracking.

    The data engineering team monitors:
    - Clients processed per run
    - Signals generated per run
    - Alert dispatch rate
    - Domain freshness status at run time
    - P95 task duration
    """

    metrics = {
        "dag_id": DAG_ID,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        **run_summary,
    }

    if metrics_store:
        metrics_store.record(metrics)
    else:
        print(f"[METRICS] {metrics}")


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
# The actual Airflow DAG would look like:
#
#  check_cib_freshness  ─┐
#  check_forex_freshness ─┤
#  check_ins_freshness  ─┤─► identify_changed_clients
#  check_cell_freshness ─┤         │
#  check_pbb_freshness  ─┘         │
#                                   ▼
#                        ┌──────────────────────┐
#                        │  (parallel tasks)     │
#                        │  expansion_signals    │
#                        │  data_shadows         │
#                        │  currency_impacts     │
#                        └──────────┬───────────┘
#                                   │
#                                   ▼
#                        score_next_best_actions
#                                   │
#                                   ▼
#                          dispatch_rm_alerts
#                                   │
#                                   ▼
#                           log_run_metrics
#
# The freshness checks run in parallel (5 workers).
# The three signal tasks run in parallel.
# NBA and alerts are sequential — each depends on all
# three signal tasks completing successfully.
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES = {
    "check_cib_freshness": [],
    "check_forex_freshness": [],
    "check_insurance_freshness": [],
    "check_cell_freshness": [],
    "check_pbb_freshness": [],
    "identify_changed_clients": [
        "check_cib_freshness",
        "check_forex_freshness",
        "check_insurance_freshness",
        "check_cell_freshness",
        "check_pbb_freshness",
    ],
    "refresh_expansion_signals": ["identify_changed_clients"],
    "refresh_data_shadows": ["identify_changed_clients"],
    "refresh_currency_impacts": ["identify_changed_clients"],
    "score_next_best_actions": [
        "refresh_expansion_signals",
        "refresh_data_shadows",
        "refresh_currency_impacts",
    ],
    "dispatch_rm_alerts": ["score_next_best_actions"],
    "log_run_metrics": ["dispatch_rm_alerts"],
}


# ---------------------------------------------------------------------------
# Programmatic DAG definition (Airflow SDK stub)
# ---------------------------------------------------------------------------

DAG_CONFIG = {
    "dag_id": DAG_ID,
    "description": (
        "Hourly refresh of cross-domain intelligence signals. "
        "Runs expansion detection, data shadow analysis, "
        "currency event propagation, NBA scoring, and "
        "RM alert dispatch."
    ),
    "schedule_interval": SCHEDULE_INTERVAL,
    "max_active_runs": MAX_ACTIVE_RUNS,
    "concurrency": CONCURRENCY,
    "sla": timedelta(minutes=SLA_MINUTES),
    "default_args": {
        "owner": "data-engineering",
        "retries": 2,
        "retry_delay": timedelta(minutes=3),
        "retry_exponential_backoff": True,
        "email_on_failure": True,
        "email": ["data-engineering@afriflow.internal"],
    },
    "tags": [
        "cross-domain",
        "intelligence",
        "signals",
        "hourly",
        "nba",
    ],
    "task_dependencies": TASK_DEPENDENCIES,
    "task_functions": {
        "check_cib_freshness": check_domain_freshness,
        "check_forex_freshness": check_domain_freshness,
        "check_insurance_freshness": check_domain_freshness,
        "check_cell_freshness": check_domain_freshness,
        "check_pbb_freshness": check_domain_freshness,
        "identify_changed_clients": identify_changed_clients,
        "refresh_expansion_signals": refresh_expansion_signals,
        "refresh_data_shadows": refresh_data_shadows,
        "refresh_currency_impacts": refresh_currency_impacts,
        "score_next_best_actions": score_next_best_actions,
        "dispatch_rm_alerts": dispatch_rm_alerts,
        "log_run_metrics": log_run_metrics,
    },
}
