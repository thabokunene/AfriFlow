"""
Weekly Outcome Feedback DAG

We run this DAG every week to close the feedback loop
between AfriFlow signals and real-world business outcomes.

The platform is only as valuable as the revenue it
generates for relationship managers. This DAG measures
whether our signals are actually driving action, and
whether actions are converting to revenue.

Without this feedback loop:
  - We cannot improve the NBA model (it needs labeled
    outcomes to learn which recommendations convert)
  - We cannot measure ROI of the platform
  - RMs have no visibility into whether following our
    signals made a difference
  - False positives accumulate and RMs stop trusting alerts

Design decisions:
  - Alert history and CRM outcomes are extracted in parallel
  - Matching runs after both are available
  - Conversion rates and revenue attribution run in parallel
    after matching — they are independent computations
  - False positive identification also runs after matching
  - Outcome registry update consolidates all results
  - Report generation depends on all analytics completing
  - RM feedback is the final personalised output

SLA: Weekly outcome report must complete within 60 minutes.

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

DAG_ID = "weekly_outcome_feedback"
SCHEDULE_INTERVAL = "@weekly"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 3
SLA_MINUTES = 60


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# CRM outcome matching window — we look for CRM activity
# within this many days of an alert being sent.
OUTCOME_MATCHING_WINDOW_DAYS = 14

# Minimum deal size (ZAR) to count as a revenue attribution
# event for the weekly report.
REVENUE_MIN_DEAL_SIZE_ZAR = 50_000.0

# False positive threshold — an alert is a false positive
# if no CRM activity was recorded within the matching window.
FALSE_POSITIVE_WINDOW_DAYS = 14

# Performance benchmark — the minimum weekly conversion
# rate below which we flag an RM for coaching.
RM_CONVERSION_RATE_BENCHMARK = 0.15


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

def extract_alert_history(
    alert_store: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull all alerts sent by AfriFlow in the last 7
    days. Each alert record includes: alert_id, type,
    golden_id, rm_id, signal_type, confidence_score,
    dispatch_timestamp, and urgency level.

    We need alert history to match against CRM outcomes —
    we attribute revenue to the alert that triggered
    the conversation.
    """

    as_of = run_date or datetime.now(timezone.utc)
    since = as_of - timedelta(days=7)
    alerts = (
        alert_store.pull_alert_history(since=since, as_of=as_of)
        if alert_store
        else []
    )

    print(f"[INFO] extract_alert_history: {len(alerts)} alerts pulled from last 7 days")
    return {"alerts": alerts, "alert_count": len(alerts), "window_days": 7}


def extract_crm_outcomes(
    crm_client: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We pull CRM outcomes from Salesforce (simulated):
    deals closed, tasks completed, meetings logged,
    and calls made.

    We pull a wider window (14 days) because some deals
    take longer to close after an alert is received.
    """

    as_of = run_date or datetime.now(timezone.utc)
    since = as_of - timedelta(days=OUTCOME_MATCHING_WINDOW_DAYS)
    outcomes = (
        crm_client.pull_crm_outcomes(since=since, as_of=as_of)
        if crm_client
        else []
    )

    print(f"[INFO] extract_crm_outcomes: {len(outcomes)} CRM outcomes pulled from last {OUTCOME_MATCHING_WINDOW_DAYS} days")
    return {"outcomes": outcomes, "outcome_count": len(outcomes)}


def match_alerts_to_outcomes(
    alert_history: Dict,
    crm_outcomes: Dict,
    outcome_matcher: Any,
    **context: Any,
) -> Dict:
    """
    We link AfriFlow alerts to subsequent CRM activity
    using golden_id + time proximity.

    Matching logic:
    - Direct match: CRM task created within 24h of alert
      for the same client → strong attribution
    - Soft match: Deal closed within 14 days of alert
      for the same client → probabilistic attribution
      (30% revenue credit given to platform)
    - No match: Alert with no subsequent CRM activity
      → classified as unactioned or false positive
    """

    matched = []
    unmatched = []

    if outcome_matcher:
        result = outcome_matcher.match(
            alerts=alert_history.get("alerts", []),
            outcomes=crm_outcomes.get("outcomes", []),
            window_days=OUTCOME_MATCHING_WINDOW_DAYS,
        )
        matched = result.get("matched", [])
        unmatched = result.get("unmatched", [])
    else:
        unmatched = alert_history.get("alerts", [])

    match_rate = len(matched) / (len(matched) + len(unmatched)) if (matched or unmatched) else 0.0

    print(
        f"[INFO] match_alerts_to_outcomes: {len(matched)} matched, "
        f"{len(unmatched)} unmatched ({match_rate:.1%} match rate)"
    )
    return {"matched": matched, "unmatched": unmatched, "match_rate": match_rate}


def compute_conversion_rates(
    match_result: Dict,
    **context: Any,
) -> Dict:
    """
    We compute conversion rates per RM and per signal type.

    Conversion = alert sent → CRM action taken within
    the matching window.

    Per-signal-type conversion helps us understand which
    signal types are most actionable. A signal type with
    < 5% conversion rate is a candidate for suppression
    or redesign.

    Per-RM conversion identifies high and low performers.
    """

    matched = match_result.get("matched", [])

    # Group by RM
    rm_stats: Dict[str, Dict] = {}
    signal_stats: Dict[str, Dict] = {}

    for alert in match_result.get("matched", []) + match_result.get("unmatched", []):
        rm_id = alert.get("rm_id", "unknown")
        signal_type = alert.get("signal_type", "unknown")
        converted = alert.get("alert_id") in {m.get("alert_id") for m in matched}

        for key, stats_dict in ((rm_id, rm_stats), (signal_type, signal_stats)):
            if key not in stats_dict:
                stats_dict[key] = {"sent": 0, "converted": 0}
            stats_dict[key]["sent"] += 1
            if converted:
                stats_dict[key]["converted"] += 1

    # Compute rates
    for stats in (rm_stats, signal_stats):
        for key in stats:
            sent = stats[key]["sent"]
            converted = stats[key]["converted"]
            stats[key]["conversion_rate"] = converted / sent if sent > 0 else 0.0

    below_benchmark = [
        rm for rm, s in rm_stats.items()
        if s["conversion_rate"] < RM_CONVERSION_RATE_BENCHMARK
    ]

    print(
        f"[INFO] compute_conversion_rates: {len(rm_stats)} RMs, "
        f"{len(below_benchmark)} below benchmark"
    )
    return {
        "rm_conversion_rates": rm_stats,
        "signal_conversion_rates": signal_stats,
        "rms_below_benchmark": below_benchmark,
    }


def compute_revenue_attribution(
    match_result: Dict,
    crm_outcomes: Dict,
    **context: Any,
) -> Dict:
    """
    We compute revenue attributed to AfriFlow signals.

    Attribution model:
    - Direct match (alert → task → deal within 7 days):
      100% of deal revenue attributed to platform
    - Soft match (alert → deal within 14 days, no task):
      30% of deal revenue attributed to platform
    - No match: 0% attribution

    We report total attributed revenue in ZAR, broken
    down by signal type and by RM.
    """

    total_attributed_zar = 0.0
    attribution_by_signal: Dict[str, float] = {}

    for match in match_result.get("matched", []):
        deal_size = match.get("deal_size_zar", 0.0)
        if deal_size < REVENUE_MIN_DEAL_SIZE_ZAR:
            continue

        attribution_pct = 1.0 if match.get("match_type") == "direct" else 0.30
        attributed = deal_size * attribution_pct
        total_attributed_zar += attributed

        signal_type = match.get("signal_type", "unknown")
        attribution_by_signal[signal_type] = (
            attribution_by_signal.get(signal_type, 0.0) + attributed
        )

    print(
        f"[INFO] compute_revenue_attribution: "
        f"ZAR {total_attributed_zar:,.0f} total attributed revenue"
    )
    return {
        "total_attributed_zar": total_attributed_zar,
        "attribution_by_signal": attribution_by_signal,
    }


def identify_false_positives(
    match_result: Dict,
    **context: Any,
) -> Dict:
    """
    We identify alerts that generated no CRM action
    within the matching window — these are potential
    false positives that erode RM trust.

    We classify false positives by likely cause:
    - Signal type with consistently low conversion
      (model improvement opportunity)
    - RM-specific non-action (coaching opportunity)
    - Client recently contacted on same topic (dedup failure)
    - Alert sent outside business hours (delivery issue)
    """

    unmatched = match_result.get("unmatched", [])
    false_positives = []

    for alert in unmatched:
        fp = {
            "alert_id": alert.get("alert_id"),
            "rm_id": alert.get("rm_id"),
            "signal_type": alert.get("signal_type"),
            "confidence_score": alert.get("confidence_score"),
            "dispatch_timestamp": alert.get("dispatch_timestamp"),
            "likely_cause": "unactioned",
        }
        false_positives.append(fp)

    fp_by_signal: Dict[str, int] = {}
    for fp in false_positives:
        signal = fp.get("signal_type", "unknown")
        fp_by_signal[signal] = fp_by_signal.get(signal, 0) + 1

    print(
        f"[INFO] identify_false_positives: {len(false_positives)} false positives, "
        f"signal breakdown: {fp_by_signal}"
    )
    return {"false_positives": false_positives, "fp_by_signal": fp_by_signal}


def update_outcome_registry(
    match_result: Dict,
    conversion_result: Dict,
    revenue_result: Dict,
    false_positive_result: Dict,
    outcome_registry: Any,
    **context: Any,
) -> Dict:
    """
    We write all weekly outcome analytics to the outcome
    registry. This registry is the training data source
    for the weekly model retrain DAG — every week's
    outcomes become next week's labeled training examples.
    """

    rows_written = (
        outcome_registry.write_weekly_outcomes(
            match_result=match_result,
            conversion_result=conversion_result,
            revenue_result=revenue_result,
            false_positive_result=false_positive_result,
        )
        if outcome_registry
        else 0
    )

    print(f"[INFO] update_outcome_registry: {rows_written} outcome records written")
    return {"rows_written": rows_written}


def generate_weekly_report(
    conversion_result: Dict,
    revenue_result: Dict,
    false_positive_result: Dict,
    report_generator: Any,
    **context: Any,
) -> Dict:
    """
    We generate the weekly platform performance summary
    for leadership and data engineering.

    Report sections:
    - Platform ROI: attributed revenue vs operational cost
    - Alert quality: conversion rates by signal type
    - False positive trends over 4-week rolling window
    - RM adoption: % of RMs acting on signals
    - Model performance: NBA accuracy, churn precision
    """

    report = {
        "dag_id": DAG_ID,
        "week_ending": datetime.now(timezone.utc).isoformat(),
        "revenue_attributed_zar": revenue_result.get("total_attributed_zar", 0.0),
        "signal_conversion_rates": conversion_result.get("signal_conversion_rates", {}),
        "false_positive_count": len(false_positive_result.get("false_positives", [])),
        "rms_below_benchmark": conversion_result.get("rms_below_benchmark", []),
    }

    if report_generator:
        report_generator.generate_and_send(report)
    else:
        print(f"[REPORT] Weekly Outcome Report: {report}")

    return {"report_generated": True, "week_ending": report["week_ending"]}


def send_rm_feedback(
    conversion_result: Dict,
    report_result: Dict,
    feedback_engine: Any,
    **context: Any,
) -> Dict:
    """
    We send individual performance feedback to each RM.

    Each RM receives a personalised summary showing:
    - Their alert conversion rate vs team benchmark
    - Top 3 signals that drove revenue this week
    - Clients actioned vs clients with pending alerts
    - One coaching tip if below benchmark

    Feedback is delivered via the CRM as a task and
    via the internal platform notification channel.
    """

    feedback_sent = 0
    rm_rates = conversion_result.get("rm_conversion_rates", {})

    for rm_id, stats in rm_rates.items():
        if feedback_engine:
            feedback_engine.send_rm_summary(
                rm_id=rm_id,
                conversion_rate=stats.get("conversion_rate", 0.0),
                benchmark=RM_CONVERSION_RATE_BENCHMARK,
                stats=stats,
            )
        feedback_sent += 1

    print(f"[INFO] send_rm_feedback: {feedback_sent} RMs received performance feedback")
    return {"feedback_sent": feedback_sent}


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   extract_alert_history ─┐
#   extract_crm_outcomes   ─┴─► match_alerts_to_outcomes
#                                         │
#                      ┌──────────────────┼──────────────┐
#                      ▼                  ▼               ▼
#         compute_conversion_rates  compute_revenue_attribution  identify_false_positives
#                      └──────────────────┬───────────────┘
#                                         ▼
#                              update_outcome_registry
#                                         │
#                                         ▼
#                              generate_weekly_report
#                                         │
#                                         ▼
#                                  send_rm_feedback
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "extract_alert_history":       [],
    "extract_crm_outcomes":        [],
    "match_alerts_to_outcomes":    ["extract_alert_history", "extract_crm_outcomes"],
    "compute_conversion_rates":    ["match_alerts_to_outcomes"],
    "compute_revenue_attribution": ["match_alerts_to_outcomes"],
    "identify_false_positives":    ["match_alerts_to_outcomes"],
    "update_outcome_registry":     [
        "compute_conversion_rates",
        "compute_revenue_attribution",
        "identify_false_positives",
    ],
    "generate_weekly_report":      ["update_outcome_registry"],
    "send_rm_feedback":            ["generate_weekly_report"],
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
    tags=["feedback", "weekly", "outcomes", "attribution", "crm", "rm"],
    task_dependencies=TASK_DEPENDENCIES,
)
