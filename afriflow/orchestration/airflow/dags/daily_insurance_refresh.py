"""
Daily Insurance Domain Refresh DAG

We run this DAG every day to:
1. Extract active policy records and recent claims
2. Validate schema and run domain-specific checks
3. Flag policies in free-look periods and assess
   premium affordability
4. Detect coverage gaps across PBB loan portfolios
5. Run FAIS compliance checks on advice documentation
6. Compute the renewal pipeline for next 30/60/90 days
7. Write to silver layer and send broker alerts

Design decisions:
  - Policy and claims extracts run in parallel
  - Schema validation gates all downstream work
  - Free-look and affordability checks are independent
    and run in parallel after validation
  - Coverage gap detection depends on both checks as it
    integrates loan and policy data
  - FAIS compliance is an independent regulatory check
    that runs after validation but before silver write
  - Renewal pipeline computation depends on validated
    policy data only
  - Silver write consolidates all outputs
  - Broker alerts are the final output task

SLA: All insurance data must be refreshed within 60 minutes.

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

DAG_ID = "daily_insurance_refresh"
SCHEDULE_INTERVAL = "@daily"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 3
SLA_MINUTES = 60


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Policies entering their free-look window within this
# many days are flagged for advisor follow-up.
FREE_LOOK_WINDOW_DAYS = 31

# Renewal pipeline windows — days ahead to compute.
RENEWAL_WINDOWS = [30, 60, 90]

# Premium-to-income ratio threshold above which we flag
# a policy as potentially unaffordable.
AFFORDABILITY_RATIO_THRESHOLD = 0.15


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

def extract_policy_records(
    insurance_system_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull all active insurance policies from the
    insurance system. This includes life, credit life,
    property, and business interruption policies.

    We extract: policy_id, client_id, product_type,
    premium_amount, currency, inception_date, expiry_date,
    free_look_expiry, sum_insured, and beneficiary details.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = (
        insurance_system_client.pull_active_policies(as_of=as_of)
        if insurance_system_client
        else []
    )

    print(f"[INFO] extract_policy_records: {len(records)} active policies pulled")
    return {"source": "policies", "record_count": len(records), "as_of": as_of.isoformat()}


def extract_claims_data(
    insurance_system_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull recent claims — submitted, in-process, settled,
    and rejected — from the claims management system.

    Claims data feeds the affordability model: a client
    who has recently made a large claim may have reduced
    capacity to service premiums.
    """

    as_of = run_date or datetime.now(timezone.utc)
    records = (
        insurance_system_client.pull_recent_claims(as_of=as_of)
        if insurance_system_client
        else []
    )

    print(f"[INFO] extract_claims_data: {len(records)} claims pulled")
    return {"source": "claims", "record_count": len(records), "as_of": as_of.isoformat()}


def validate_insurance_schema(
    policy_result: Dict,
    claims_result: Dict,
    schema_registry: Any,
    **context: Any,
) -> Dict:
    """
    We validate policy and claims records against their
    Avro schemas.

    Critical fields: policy_id (not null), client_id
    (must resolve to golden ID), premium_amount (positive),
    inception_date (parseable), free_look_expiry (parseable
    for recently-issued policies).
    """

    sources = [policy_result, claims_result]
    total = sum(r.get("record_count", 0) for r in sources)
    violations = 0

    if schema_registry:
        violations = schema_registry.validate_insurance_batch(sources)

    violation_pct = (violations / total * 100) if total > 0 else 0.0

    print(
        f"[INFO] validate_insurance_schema: {total} records, "
        f"{violations} violations ({violation_pct:.2f}%)"
    )
    return {"total_records": total, "violations": violations, "violation_pct": violation_pct}


def check_free_look_periods(
    validation_result: Dict,
    policy_checker: Any,
    **context: Any,
) -> Dict:
    """
    We flag policies that are within their 31-day free-look
    window — the regulatory period during which a policyholder
    may cancel and receive a full premium refund.

    Policies in the free-look window require proactive
    advisor contact to confirm the client is satisfied
    and to address any concerns before cancellation.
    """

    flagged_policies = []
    if policy_checker:
        flagged_policies = policy_checker.flag_free_look(
            window_days=FREE_LOOK_WINDOW_DAYS
        )

    print(f"[INFO] check_free_look_periods: {len(flagged_policies)} policies in free-look window")
    return {"free_look_policies": flagged_policies, "count": len(flagged_policies)}


def check_premium_affordability(
    validation_result: Dict,
    claims_result: Dict,
    affordability_engine: Any,
    **context: Any,
) -> Dict:
    """
    We run the premium affordability assessment for each
    active policy.

    We compare the annual premium to estimated household
    income (derived from PBB salary credit data where
    available, else statistical proxies).

    Policies where premium/income > AFFORDABILITY_RATIO_THRESHOLD
    are flagged for advisor review — these are at elevated
    lapse risk.
    """

    at_risk_policies = []
    if affordability_engine:
        at_risk_policies = affordability_engine.assess(
            ratio_threshold=AFFORDABILITY_RATIO_THRESHOLD,
            claims_result=claims_result,
        )

    print(
        f"[INFO] check_premium_affordability: "
        f"{len(at_risk_policies)} policies flagged as affordability risk"
    )
    return {"at_risk_policies": at_risk_policies, "count": len(at_risk_policies)}


def detect_coverage_gaps(
    free_look_result: Dict,
    affordability_result: Dict,
    gap_detector: Any,
    **context: Any,
) -> Dict:
    """
    We cross-reference PBB loan balances against insurance
    coverage to identify clients who are exposed.

    Coverage gap patterns:
    - Home loan with no property insurance
    - Vehicle finance with no comprehensive motor cover
    - Business loan with no credit life cover
    - Trade finance exposure with no cargo or political
      risk insurance

    Gaps are ranked by exposure size for broker prioritisation.
    """

    gaps = []
    if gap_detector:
        gaps = gap_detector.detect_pbb_insurance_gaps(
            free_look_result=free_look_result,
            affordability_result=affordability_result,
        )

    print(f"[INFO] detect_coverage_gaps: {len(gaps)} coverage gaps identified")
    return {"coverage_gaps": gaps, "gap_count": len(gaps)}


def run_fais_compliance(
    validation_result: Dict,
    fais_checker: Any,
    **context: Any,
) -> Dict:
    """
    We check FAIS (Financial Advisory and Intermediary
    Services Act) compliance across all insurance advice
    interactions recorded today.

    Compliance checks:
    - Advice documentation present for all replacements
    - Risk needs analysis on file for new policies
    - Disclosure documents signed within required period
    - Advisor competency certificates valid

    Non-compliant records are escalated to compliance team.
    """

    violations = []
    if fais_checker:
        violations = fais_checker.run_daily_check()

    print(f"[INFO] run_fais_compliance: {len(violations)} FAIS violations flagged")
    return {"fais_violations": violations, "violation_count": len(violations)}


def compute_renewal_pipeline(
    validation_result: Dict,
    pipeline_calculator: Any,
    **context: Any,
) -> Dict:
    """
    We compute the renewal pipeline for the next 30, 60,
    and 90 days.

    The pipeline includes: policy_id, client_id, product,
    premium_amount, renewal_date, probability_of_lapse,
    and recommended retention action.

    Lapse probability is a function of payment history,
    affordability score, and days since last advisor contact.
    """

    pipeline: Dict[str, List] = {f"{w}d": [] for w in RENEWAL_WINDOWS}

    if pipeline_calculator:
        pipeline = pipeline_calculator.compute_renewal_pipeline(
            windows_days=RENEWAL_WINDOWS
        )

    total_renewing = sum(len(v) for v in pipeline.values())
    print(
        f"[INFO] compute_renewal_pipeline: "
        f"{total_renewing} total policies across 30/60/90d windows"
    )
    return {"renewal_pipeline": pipeline, "total_renewing": total_renewing}


def update_insurance_silver(
    gap_result: Dict,
    fais_result: Dict,
    renewal_result: Dict,
    silver_store: Any,
    **context: Any,
) -> Dict:
    """
    We write all insurance domain outputs to the silver
    layer: validated policies, claims, coverage gaps,
    FAIS compliance status, and renewal pipeline.
    """

    rows_written = (
        silver_store.write_insurance_silver(gap_result, fais_result, renewal_result)
        if silver_store
        else 0
    )

    print(f"[INFO] update_insurance_silver: {rows_written} rows written")
    return {"rows_written": rows_written, "layer": "silver"}


def send_broker_alerts(
    free_look_result: Dict,
    gap_result: Dict,
    renewal_result: Dict,
    alert_engine: Any,
    **context: Any,
) -> Dict:
    """
    We send renewal and coverage gap alerts to brokers
    and advisors.

    Alert priority:
    1. Free-look policies (time-sensitive — window closes)
    2. Large coverage gaps on corporate clients
    3. High-lapse-risk renewals in the 30-day window
    4. Affordability-flagged policies requiring review
    """

    alerts_sent = 0

    if alert_engine:
        # Free-look alerts — highest urgency
        for policy in free_look_result.get("free_look_policies", []):
            alert_engine.send(
                alert_type="FREE_LOOK_EXPIRING",
                payload=policy,
                urgency="HIGH",
            )
            alerts_sent += 1

        # Coverage gap alerts
        for gap in gap_result.get("coverage_gaps", []):
            alert_engine.send(
                alert_type="COVERAGE_GAP",
                payload=gap,
                urgency="MEDIUM",
            )
            alerts_sent += 1

    print(f"[INFO] send_broker_alerts: {alerts_sent} alerts dispatched")
    return {"alerts_sent": alerts_sent}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   extract_policy_records ─┐
#   extract_claims_data     ─┴─► validate_insurance_schema
#                                         │
#                      ┌──────────────────┼──────────────────┐
#                      ▼                  ▼                   ▼
#           check_free_look_periods  check_premium_affordability  run_fais_compliance
#                      │                  │                        compute_renewal_pipeline
#                      └──────────┬───────┘
#                                 ▼
#                        detect_coverage_gaps
#                                 │
#                     ┌───────────┴──────────────┐
#                     ▼                          ▼
#           update_insurance_silver     send_broker_alerts
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "extract_policy_records":       [],
    "extract_claims_data":          [],
    "validate_insurance_schema":    ["extract_policy_records", "extract_claims_data"],
    "check_free_look_periods":      ["validate_insurance_schema"],
    "check_premium_affordability":  ["validate_insurance_schema"],
    "detect_coverage_gaps":         [
        "check_free_look_periods",
        "check_premium_affordability",
    ],
    "run_fais_compliance":          ["validate_insurance_schema"],
    "compute_renewal_pipeline":     ["validate_insurance_schema"],
    "update_insurance_silver":      [
        "detect_coverage_gaps",
        "run_fais_compliance",
        "compute_renewal_pipeline",
    ],
    "send_broker_alerts":           [
        "detect_coverage_gaps",
        "compute_renewal_pipeline",
    ],
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
    tags=["insurance", "daily", "fais", "renewal", "coverage-gaps", "silver"],
    task_dependencies=TASK_DEPENDENCIES,
)
