"""
Daily PBB Domain Refresh DAG

We run this DAG every day to:
1. Extract PBB account balances, recent transactions,
   and loan book positions
2. Validate schema
3. Score digital channel engagement and detect salary credits
4. Flag dormant accounts (>90 days without activity)
5. Write to silver layer
6. Compute NBA scores for the PBB segment
7. Send alerts to branch staff

Design decisions:
  - Balance, transaction, and loan book extracts run
    in parallel as independent source queries
  - Schema validation gates all three
  - Digital engagement scoring and salary credit detection
    are independent analytical tasks — they run in parallel
    after validation
  - Dormancy detection also runs after validation
  - All three analytical tasks must complete before silver
    write, as the silver layer holds the consolidated view
  - NBA scoring depends on the silver write completing
  - Branch alerts are the final output task

SLA: All PBB data must be refreshed within 60 minutes.

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

DAG_ID = "daily_pbb_refresh"
SCHEDULE_INTERVAL = "@daily"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 4
SLA_MINUTES = 60


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Accounts with no debit or credit activity for longer
# than this are flagged as dormant.
DORMANCY_THRESHOLD_DAYS = 90

# Minimum salary credit amount (USD equivalent) to be
# counted as a salary detection event.
SALARY_MIN_AMOUNT_USD = 100.0

# NBA minimum score to trigger a branch staff alert.
NBA_ALERT_SCORE_THRESHOLD = 65.0


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

def extract_account_balances(
    pbb_system_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull end-of-day account balances for all active
    PBB accounts across all 20 countries.

    Balance trends feed the digital engagement model and
    are used to detect salary credits — a recurring large
    credit on a fixed day each month is the strongest
    upsell trigger in retail banking.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = (
        pbb_system_client.pull_account_balances(as_of=as_of)
        if pbb_system_client
        else []
    )

    print(f"[INFO] extract_account_balances: {len(records)} account balance records pulled")
    return {"source": "account_balances", "record_count": len(records), "as_of": as_of.isoformat()}


def extract_transactions(
    pbb_system_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull recent transactions for all PBB accounts.
    We extract: account_id, transaction_type, amount,
    currency, channel, merchant_category, and timestamp.

    Channel distribution (app vs branch vs ATM vs USSD)
    is the primary input for digital engagement scoring.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = (
        pbb_system_client.pull_recent_transactions(as_of=as_of)
        if pbb_system_client
        else []
    )

    print(f"[INFO] extract_transactions: {len(records)} transactions pulled")
    return {"source": "transactions", "record_count": len(records), "as_of": as_of.isoformat()}


def extract_loan_book(
    pbb_system_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull the PBB loan book: home loans, vehicle finance,
    personal loans, and credit cards.

    The loan book feeds the insurance coverage gap detector
    in the insurance domain DAG — we cross-reference each
    loan against the insurance policy register.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = (
        pbb_system_client.pull_loan_book(as_of=as_of)
        if pbb_system_client
        else []
    )

    print(f"[INFO] extract_loan_book: {len(records)} loan positions pulled")
    return {"source": "loan_book", "record_count": len(records), "as_of": as_of.isoformat()}


def validate_pbb_schema(
    balance_result: Dict,
    transaction_result: Dict,
    loan_result: Dict,
    schema_registry: Any,
    **context: Any,
) -> Dict:
    """
    We validate all three PBB data feeds against their
    Avro schemas.

    Critical fields: account_id (not null), client_id
    (must resolve to golden ID), amount (numeric, not null),
    currency (valid ISO 4217), timestamp (parseable).
    """

    sources = [balance_result, transaction_result, loan_result]
    total = sum(r.get("record_count", 0) for r in sources)
    violations = 0

    if schema_registry:
        violations = schema_registry.validate_pbb_batch(sources)

    violation_pct = (violations / total * 100) if total > 0 else 0.0

    print(
        f"[INFO] validate_pbb_schema: {total} records, "
        f"{violations} violations ({violation_pct:.2f}%)"
    )
    return {"total_records": total, "violations": violations, "violation_pct": violation_pct}


def compute_digital_engagement(
    validation_result: Dict,
    engagement_scorer: Any,
    **context: Any,
) -> Dict:
    """
    We score each client's digital channel engagement on
    a 0–100 scale based on their 90-day transaction history.

    The engagement score combines:
    - Proportion of transactions via digital channels
      (mobile app, internet banking, USSD)
    - Frequency of logins and transact sessions
    - Adoption of digital-only features (instant EFT,
      digital statements, biometric auth)

    Low engagement (< 30) triggers a branch outreach alert.
    High engagement (> 70) increases NBA score weighting
    for digital product cross-sells.
    """

    scored_clients = []
    if engagement_scorer:
        scored_clients = engagement_scorer.score_digital_engagement()

    print(f"[INFO] compute_digital_engagement: {len(scored_clients)} clients scored")
    return {"engagement_scores": scored_clients, "client_count": len(scored_clients)}


def detect_salary_credits(
    validation_result: Dict,
    salary_detector: Any,
    **context: Any,
) -> Dict:
    """
    We flag accounts that received a salary credit today —
    a recurring large credit that matches the pattern of
    employer payroll.

    Salary credits are the most powerful upsell trigger
    in retail banking. A client who recently received a
    salary increase is a strong candidate for home loan
    top-up, investment product, and insurance upsell.
    """

    salary_events = []
    if salary_detector:
        salary_events = salary_detector.detect_salary_credits(
            min_amount_usd=SALARY_MIN_AMOUNT_USD
        )

    print(f"[INFO] detect_salary_credits: {len(salary_events)} salary credit events detected")
    return {"salary_events": salary_events, "event_count": len(salary_events)}


def detect_dormancy(
    validation_result: Dict,
    dormancy_checker: Any,
    **context: Any,
) -> Dict:
    """
    We flag accounts dormant for more than
    DORMANCY_THRESHOLD_DAYS days.

    Dormant accounts represent both a retention risk
    (client has moved primary banking elsewhere) and a
    regulatory obligation (dormant account reporting
    requirements vary by country).

    We distinguish: newly dormant (first flag this run)
    vs persistently dormant (flagged in prior runs).
    """

    newly_dormant = []
    persistently_dormant = []

    if dormancy_checker:
        result = dormancy_checker.detect_dormancy(
            threshold_days=DORMANCY_THRESHOLD_DAYS
        )
        newly_dormant = result.get("newly_dormant", [])
        persistently_dormant = result.get("persistently_dormant", [])

    print(
        f"[INFO] detect_dormancy: {len(newly_dormant)} newly dormant, "
        f"{len(persistently_dormant)} persistently dormant"
    )
    return {
        "newly_dormant": newly_dormant,
        "persistently_dormant": persistently_dormant,
        "total_dormant": len(newly_dormant) + len(persistently_dormant),
    }


def update_pbb_silver(
    engagement_result: Dict,
    salary_result: Dict,
    dormancy_result: Dict,
    silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We write all PBB domain outputs to the silver layer:
    account balances, transactions, loan positions,
    digital engagement scores, salary events, and
    dormancy flags.
    """

    rows_written = (
        silver_store.write_pbb_silver(engagement_result, salary_result, dormancy_result)
        if silver_store
        else 0
    )

    print(f"[INFO] update_pbb_silver: {rows_written} rows written")
    return {"rows_written": rows_written, "layer": "silver"}


def score_nba(
    silver_result: Dict,
    nba_model: Any,
    **context: Any,
) -> Dict:
    """
    We compute NBA scores for all PBB segment clients
    using the latest silver layer data.

    The PBB NBA model considers:
    - Digital engagement score
    - Salary credit events (upsell trigger)
    - Current product holdings (cross-sell gaps)
    - Life stage inference (age, family status proxies)
    - Churn risk score (dormancy + competitor signals)

    Top NBA actions: home loan, vehicle finance, funeral
    cover, investment account, credit card upgrade.
    """

    scored = []
    if nba_model:
        scored = nba_model.score_pbb_segment(silver_result=silver_result)

    actionable = [s for s in scored if s.get("top_score", 0) >= NBA_ALERT_SCORE_THRESHOLD]
    print(
        f"[INFO] score_nba: {len(scored)} clients scored, "
        f"{len(actionable)} with actionable NBA"
    )
    return {"nba_scores": scored, "actionable_count": len(actionable)}


def send_branch_alerts(
    nba_result: Dict,
    dormancy_result: Dict,
    alert_engine: Any,
    **context: Any,
) -> Dict:
    """
    We send alerts to branch staff for actionable NBA
    recommendations and newly dormant accounts.

    Branch staff see a daily action list with:
    - Client name and relationship summary
    - Top NBA action and estimated revenue
    - Dormancy flag with last activity date
    - Suggested outreach channel (call, SMS, in-branch)
    """

    alerts_sent = 0

    if alert_engine:
        # NBA alerts
        for score in nba_result.get("nba_scores", []):
            if score.get("top_score", 0) >= NBA_ALERT_SCORE_THRESHOLD:
                alert_engine.send(
                    alert_type="PBB_NBA_RECOMMENDATION",
                    payload=score,
                    urgency="MEDIUM",
                )
                alerts_sent += 1

        # Dormancy alerts for newly dormant accounts
        for account in dormancy_result.get("newly_dormant", []):
            alert_engine.send(
                alert_type="PBB_DORMANCY",
                payload=account,
                urgency="LOW",
            )
            alerts_sent += 1

    print(f"[INFO] send_branch_alerts: {alerts_sent} alerts sent to branch staff")
    return {"alerts_sent": alerts_sent}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   extract_account_balances ─┐
#   extract_transactions      ─┼─► validate_pbb_schema
#   extract_loan_book         ─┘         │
#                                         │
#                      ┌──────────────────┼──────────────┐
#                      ▼                  ▼               ▼
#         compute_digital_engagement  detect_salary_credits  detect_dormancy
#                      │                  │               │
#                      └──────────────────┴───────────────┘
#                                         ▼
#                                 update_pbb_silver
#                                         │
#                                         ▼
#                                      score_nba
#                                         │
#                                         ▼
#                                  send_branch_alerts
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "extract_account_balances":    [],
    "extract_transactions":        [],
    "extract_loan_book":           [],
    "validate_pbb_schema":         [
        "extract_account_balances",
        "extract_transactions",
        "extract_loan_book",
    ],
    "compute_digital_engagement":  ["validate_pbb_schema"],
    "detect_salary_credits":       ["validate_pbb_schema"],
    "detect_dormancy":             ["validate_pbb_schema"],
    "update_pbb_silver":           [
        "compute_digital_engagement",
        "detect_salary_credits",
        "detect_dormancy",
    ],
    "score_nba":                   ["update_pbb_silver"],
    "send_branch_alerts":          ["score_nba"],
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
    tags=["pbb", "daily", "retail", "nba", "dormancy", "silver"],
    task_dependencies=TASK_DEPENDENCIES,
)
