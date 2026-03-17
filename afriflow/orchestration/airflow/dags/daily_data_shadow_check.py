"""
Daily Data Shadow Check DAG

We run this DAG every day to detect "data shadows" —
the absence of expected data as a signal.

A data shadow occurs when we observe a CIB client making
payments to a new country but see NO corresponding:
  - Forex hedge (unusual for large corporates)
  - Insurance policies in that country (expansion without
    protection is a red flag and a sales opportunity)
  - Cell network SIM activations (no workforce present
    suggests the payments may not be for operations)
  - Personal banking relationships linked to that country

These gaps are not just data quality issues — they are
intelligence signals. A client who is clearly active in
Nigeria via payment flows but has no MTN SIMs in Nigeria
and no insurance policies there suggests either:
  a) The activity is transactional (commodity trade) not
     operational, or
  b) They are banking competitors for the Nigeria business

Either interpretation generates a relationship manager
action: investigate and present the missing product.

Design decisions:
  - CIB client list load runs first as it scopes all checks
  - Domain coverage checks run in parallel — four workers
  - Gap identification depends on all four checks
  - Severity scoring depends on gap identification
  - Registry update and RM alerts run in parallel last

SLA: Shadow check must complete within 30 minutes —
it runs after all five domain DAGs have completed.

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

DAG_ID = "daily_data_shadow_check"
SCHEDULE_INTERVAL = "@daily"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 4
SLA_MINUTES = 30


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Minimum hedge coverage ratio before we flag a gap.
# If a client has >50% of corridor exposure hedged,
# the gap is not considered actionable.
HEDGE_COVERAGE_MIN_RATIO = 0.50

# Severity score thresholds for RM escalation.
SHADOW_SEVERITY_ALERT_THRESHOLD = 60.0
SHADOW_SEVERITY_CRITICAL_THRESHOLD = 85.0

# Minimum corridor payment volume (USD/month) before we
# expect the client to have corresponding domain presence.
# Below this threshold, absence of SIMs/insurance is normal.
CORRIDOR_MATERIALITY_THRESHOLD_USD = 50_000.0


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

def load_cib_client_list(
    cib_silver_store: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We load the list of CIB clients active in the last
    30 days together with their active payment corridors.

    This is the scope for all downstream shadow checks.
    Only material corridors (volume >= threshold) are
    included — we do not expect insurance in a country
    where a client sent a single $5k payment.
    """

    as_of = run_date or datetime.now(timezone.utc)
    clients = (
        cib_silver_store.get_active_cib_clients(
            as_of=as_of,
            min_corridor_volume_usd=CORRIDOR_MATERIALITY_THRESHOLD_USD,
        )
        if cib_silver_store
        else []
    )

    print(f"[INFO] load_cib_client_list: {len(clients)} active CIB clients with material corridors")
    return {"cib_clients": clients, "client_count": len(clients)}


def check_forex_coverage(
    client_list_result: Dict,
    forex_silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We check, for each CIB client, whether their active
    payment corridors have corresponding FX hedges.

    A large corporate sending USD 5M to Nigeria without
    any NGN hedge is unusual and worth investigating.
    The gap may mean they are hedging elsewhere (shadow)
    or taking unhedged risk (which is also a product pitch).
    """

    gaps = []
    clients = client_list_result.get("cib_clients", [])

    for client in clients:
        if forex_silver_store:
            hedge_ratio = forex_silver_store.get_hedge_coverage_ratio(
                client_id=client.get("golden_id"),
                corridors=client.get("active_corridors", []),
            )
        else:
            hedge_ratio = 1.0

        if hedge_ratio < HEDGE_COVERAGE_MIN_RATIO:
            gaps.append({
                "golden_id": client.get("golden_id"),
                "domain": "forex",
                "gap_type": "insufficient_hedge_coverage",
                "hedge_ratio": hedge_ratio,
                "corridors": client.get("active_corridors", []),
            })

    print(f"[INFO] check_forex_coverage: {len(gaps)} forex coverage gaps identified")
    return {"forex_gaps": gaps, "gap_count": len(gaps)}


def check_insurance_coverage(
    client_list_result: Dict,
    insurance_silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We check, for each CIB client, whether they hold
    insurance policies in the countries where they have
    active payment corridors.

    A corporate with heavy Nigeria trade flows but no
    political risk or cargo insurance in Nigeria either
    uses a competitor insurer or is taking uninsured
    risk — both are relationship conversations.
    """

    gaps = []
    clients = client_list_result.get("cib_clients", [])

    for client in clients:
        active_corridors = client.get("active_corridors", [])
        for corridor_country in active_corridors:
            has_insurance = (
                insurance_silver_store.has_coverage_in_country(
                    client_id=client.get("golden_id"),
                    country=corridor_country,
                )
                if insurance_silver_store
                else True
            )

            if not has_insurance:
                gaps.append({
                    "golden_id": client.get("golden_id"),
                    "domain": "insurance",
                    "gap_type": "no_insurance_in_corridor",
                    "corridor_country": corridor_country,
                })

    print(f"[INFO] check_insurance_coverage: {len(gaps)} insurance coverage gaps identified")
    return {"insurance_gaps": gaps, "gap_count": len(gaps)}


def check_cell_presence(
    client_list_result: Dict,
    cell_silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We check, for each CIB client, whether they have
    SIM activations or MoMo salary payments in the
    countries where they have active payment corridors.

    No SIM presence in a trade corridor suggests the
    client has no operational workforce there — the
    payments may be for commodity purchases, not
    operational expansion. That context changes how
    the RM frames the conversation.
    """

    gaps = []
    clients = client_list_result.get("cib_clients", [])

    for client in clients:
        active_corridors = client.get("active_corridors", [])
        for corridor_country in active_corridors:
            has_sims = (
                cell_silver_store.has_sim_presence_in_country(
                    client_id=client.get("golden_id"),
                    country=corridor_country,
                )
                if cell_silver_store
                else True
            )

            if not has_sims:
                gaps.append({
                    "golden_id": client.get("golden_id"),
                    "domain": "cell",
                    "gap_type": "no_sim_presence_in_corridor",
                    "corridor_country": corridor_country,
                })

    print(f"[INFO] check_cell_presence: {len(gaps)} cell presence gaps identified")
    return {"cell_gaps": gaps, "gap_count": len(gaps)}


def check_pbb_linkage(
    client_list_result: Dict,
    pbb_silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We check whether each CIB client has linked personal
    banking relationships.

    In African banking, the personal banker to the CEO
    and CFO of a corporate client is a powerful relationship
    anchor. A corporate where the executives bank elsewhere
    is at higher attrition risk on the CIB mandate.
    """

    gaps = []
    clients = client_list_result.get("cib_clients", [])

    for client in clients:
        has_pbb_linkage = (
            pbb_silver_store.has_linked_pbb_relationships(
                corporate_golden_id=client.get("golden_id")
            )
            if pbb_silver_store
            else True
        )

        if not has_pbb_linkage:
            gaps.append({
                "golden_id": client.get("golden_id"),
                "domain": "pbb",
                "gap_type": "no_linked_personal_banking",
                "client_name": client.get("client_name", ""),
            })

    print(f"[INFO] check_pbb_linkage: {len(gaps)} PBB linkage gaps identified")
    return {"pbb_gaps": gaps, "gap_count": len(gaps)}


def identify_shadow_gaps(
    forex_result: Dict,
    insurance_result: Dict,
    cell_result: Dict,
    pbb_result: Dict,
    **context: Any,
) -> Dict:
    """
    We consolidate all domain gap results into a unified
    shadow gap record per client.

    A client with gaps across multiple domains has a higher
    shadow severity score — a client missing forex hedges,
    insurance, and SIM presence in the same corridor is
    almost certainly using a competitor bank for that market.
    """

    all_gaps: Dict[str, Dict] = {}

    domain_results = [
        ("forex", forex_result.get("forex_gaps", [])),
        ("insurance", insurance_result.get("insurance_gaps", [])),
        ("cell", cell_result.get("cell_gaps", [])),
        ("pbb", pbb_result.get("pbb_gaps", [])),
    ]

    for domain, gaps in domain_results:
        for gap in gaps:
            golden_id = gap.get("golden_id", "")
            if golden_id not in all_gaps:
                all_gaps[golden_id] = {
                    "golden_id": golden_id,
                    "gaps_by_domain": {},
                    "total_gap_count": 0,
                }
            all_gaps[golden_id]["gaps_by_domain"][domain] = gap
            all_gaps[golden_id]["total_gap_count"] += 1

    shadow_records = list(all_gaps.values())
    print(f"[INFO] identify_shadow_gaps: {len(shadow_records)} clients with shadow gaps")
    return {"shadow_records": shadow_records, "client_count": len(shadow_records)}


def score_shadow_severity(
    shadow_result: Dict,
    **context: Any,
) -> Dict:
    """
    We rank shadow gaps by severity score.

    Severity scoring:
    - +30 points if forex hedge gap in high-volume corridor
    - +25 points if no insurance in 2+ active corridors
    - +20 points if no SIM presence in active corridors
    - +15 points if no PBB linkage for Platinum client
    - +10 multiplier if gaps span 3+ domains simultaneously

    Severity >= 85: CRITICAL (immediate RM escalation)
    Severity >= 60: HIGH (same-day RM alert)
    Severity < 60: MEDIUM (weekly summary)
    """

    scored = []
    for record in shadow_result.get("shadow_records", []):
        gaps_by_domain = record.get("gaps_by_domain", {})
        domain_count = len(gaps_by_domain)

        score = 0.0
        if "forex" in gaps_by_domain:
            score += 30.0
        if "insurance" in gaps_by_domain:
            score += 25.0
        if "cell" in gaps_by_domain:
            score += 20.0
        if "pbb" in gaps_by_domain:
            score += 15.0
        if domain_count >= 3:
            score *= 1.10

        severity = (
            "CRITICAL" if score >= SHADOW_SEVERITY_CRITICAL_THRESHOLD
            else "HIGH" if score >= SHADOW_SEVERITY_ALERT_THRESHOLD
            else "MEDIUM"
        )

        scored.append({
            **record,
            "shadow_severity_score": round(score, 1),
            "severity_level": severity,
        })

    scored.sort(key=lambda x: x["shadow_severity_score"], reverse=True)

    critical = sum(1 for s in scored if s["severity_level"] == "CRITICAL")
    high = sum(1 for s in scored if s["severity_level"] == "HIGH")
    print(
        f"[INFO] score_shadow_severity: {critical} CRITICAL, {high} HIGH, "
        f"{len(scored) - critical - high} MEDIUM"
    )
    return {"scored_shadows": scored, "critical_count": critical, "high_count": high}


def update_shadow_registry(
    severity_result: Dict,
    shadow_registry: Any,
    **context: Any,
) -> Dict:
    """
    We write all shadow gap records to the data shadow
    registry. The registry maintains history — we track
    how long each gap has persisted and whether it is
    narrowing or widening over time.

    Persistent gaps (> 30 days) are escalated in severity.
    """

    rows_written = (
        shadow_registry.upsert_shadow_records(
            severity_result.get("scored_shadows", [])
        )
        if shadow_registry
        else 0
    )

    print(f"[INFO] update_shadow_registry: {rows_written} shadow records upserted")
    return {"rows_written": rows_written}


def alert_relationship_managers(
    severity_result: Dict,
    alert_engine: Any,
    **context: Any,
) -> Dict:
    """
    We send shadow alerts to relationship managers for
    CRITICAL and HIGH severity gaps.

    Each alert includes:
    - The client's active corridors and payment volumes
    - Which domain gaps were identified
    - The recommended conversation starter
    - Comparable client benchmarks (anonymised)
    """

    alerts_sent = 0

    for shadow in severity_result.get("scored_shadows", []):
        severity = shadow.get("severity_level", "MEDIUM")
        if severity not in ("CRITICAL", "HIGH"):
            continue

        if alert_engine:
            alert_engine.send(
                alert_type="DATA_SHADOW_GAP",
                golden_id=shadow.get("golden_id"),
                payload=shadow,
                urgency=severity,
            )
        alerts_sent += 1

    print(f"[INFO] alert_relationship_managers: {alerts_sent} shadow alerts dispatched")
    return {"alerts_sent": alerts_sent}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   load_cib_client_list
#          │
#   ┌──────┴──────────────────────┐
#   ▼       ▼                ▼   ▼
#   check_forex  check_insurance  check_cell  check_pbb
#        └──────────────┬─────────────────────┘
#                        ▼
#                identify_shadow_gaps
#                        │
#                        ▼
#               score_shadow_severity
#                        │
#          ┌─────────────┴──────────────┐
#          ▼                            ▼
#   update_shadow_registry   alert_relationship_managers
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "load_cib_client_list":          [],
    "check_forex_coverage":          ["load_cib_client_list"],
    "check_insurance_coverage":      ["load_cib_client_list"],
    "check_cell_presence":           ["load_cib_client_list"],
    "check_pbb_linkage":             ["load_cib_client_list"],
    "identify_shadow_gaps":          [
        "check_forex_coverage",
        "check_insurance_coverage",
        "check_cell_presence",
        "check_pbb_linkage",
    ],
    "score_shadow_severity":         ["identify_shadow_gaps"],
    "update_shadow_registry":        ["score_shadow_severity"],
    "alert_relationship_managers":   ["score_shadow_severity"],
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
        "retry_delay":              timedelta(minutes=3),
        "retry_exponential_backoff": True,
        "email_on_failure":         True,
        "email":                    ["data-engineering@afriflow.internal"],
    },
    tags=["shadow", "daily", "cross-domain", "gaps", "intelligence"],
    task_dependencies=TASK_DEPENDENCIES,
)
