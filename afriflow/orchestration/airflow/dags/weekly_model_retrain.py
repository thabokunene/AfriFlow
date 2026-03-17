"""
Weekly Model Retrain DAG

We run this DAG every week to:
1. Extract labeled training data from the outcome tracker
2. Check for feature and model performance drift
3. Retrain the churn, NBA, and CLV models on fresh data
4. Validate new models on a holdout window
5. Shadow-deploy new models alongside production models
6. Promote new models if they exceed the performance
   threshold over the shadow period
7. Log model versions and metrics to the registry

Design decisions:
  - Training data extraction runs first — all retrain tasks
    depend on fresh labeled data being available
  - Feature drift and model performance checks run in
    parallel after extraction — they are independent
    diagnostics that inform whether retraining is urgent
  - The three model retrains run in parallel as they are
    independent models with separate feature sets
  - All three retrain tasks must complete before holdout
    validation, which tests the combined model set
  - Shadow deploy runs after validation passes
  - Promotion is a gated step — only models that beat
    the production baseline during shadow are promoted
  - Model registry update is the final audit log step

SLA: Full retrain pipeline must complete within 240 minutes.

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

DAG_ID = "weekly_model_retrain"
SCHEDULE_INTERVAL = "@weekly"
START_DATE_OFFSET_DAYS = 7
MAX_ACTIVE_RUNS = 1
CONCURRENCY = 3
SLA_MINUTES = 240


# ---------------------------------------------------------------------------
# Task configuration
# ---------------------------------------------------------------------------

# Minimum labeled outcome records required to trigger
# a retrain. Below this threshold we skip retraining
# and carry forward the current production model.
MIN_TRAINING_RECORDS = 500

# Feature drift alert threshold — Jensen-Shannon
# divergence above this value triggers a retraining
# urgency flag.
FEATURE_DRIFT_JS_THRESHOLD = 0.15

# Model performance degradation threshold.
# If current AUC drops below (baseline - threshold),
# we flag the model as degraded.
PERFORMANCE_DEGRADATION_THRESHOLD = 0.03

# Shadow deploy duration before promotion eligibility.
SHADOW_DEPLOY_HOURS = 24

# Minimum improvement over production model required
# to promote a new model.
PROMOTION_MIN_IMPROVEMENT = 0.01


# ---------------------------------------------------------------------------
# Task dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskConfig:
    task_id: str
    description: str
    retries: int = 1
    retry_delay_seconds: int = 300
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

def extract_training_data(
    outcome_tracker: Any,
    run_date: Optional[datetime] = None,
    **context: Any,
) -> Dict:
    """
    We extract labeled outcome records from the outcome
    tracker — this is the ground truth for model training.

    Outcome records include:
    - Alert sent, action taken, revenue attributed (NBA)
    - Client churned / retained (churn model)
    - Actual vs predicted CLV (CLV model)

    We require MIN_TRAINING_RECORDS outcomes before
    triggering a retrain. If the count is too low we
    log a warning and skip training this week.
    """

    as_of = run_date or datetime.now(timezone.utc)
    training_data = (
        outcome_tracker.extract_labeled_outcomes(as_of=as_of)
        if outcome_tracker
        else {}
    )

    record_count = training_data.get("total_records", 0)
    sufficient = record_count >= MIN_TRAINING_RECORDS

    if not sufficient:
        print(
            f"[WARNING] Only {record_count} labeled records available. "
            f"Minimum {MIN_TRAINING_RECORDS} required. Skipping retrain."
        )

    print(f"[INFO] extract_training_data: {record_count} labeled records extracted")
    return {
        "training_data": training_data,
        "record_count": record_count,
        "sufficient_for_training": sufficient,
    }


def compute_feature_drift(
    training_data: Dict,
    drift_detector: Any,
    **context: Any,
) -> Dict:
    """
    We check whether the feature distributions in the
    new training window have drifted significantly from
    the previous training window.

    We use Jensen-Shannon divergence as the drift metric.
    Drift above FEATURE_DRIFT_JS_THRESHOLD triggers an
    urgent retrain recommendation — the model is likely
    making predictions on out-of-distribution data.
    """

    drift_scores: Dict[str, float] = {}
    urgent = False

    if drift_detector:
        drift_scores = drift_detector.compute_js_divergence(
            training_data=training_data.get("training_data", {})
        )
        urgent = any(v > FEATURE_DRIFT_JS_THRESHOLD for v in drift_scores.values())

    print(
        f"[INFO] compute_feature_drift: {len(drift_scores)} features checked, "
        f"urgent={'YES' if urgent else 'NO'}"
    )
    return {"drift_scores": drift_scores, "drift_urgent": urgent}


def check_model_performance(
    training_data: Dict,
    model_evaluator: Any,
    **context: Any,
) -> Dict:
    """
    We evaluate current production model performance
    on the recent holdout window (last 30 days).

    We compare current AUC to the baseline AUC recorded
    at the last promotion event. If the gap exceeds
    PERFORMANCE_DEGRADATION_THRESHOLD we flag the model
    as degraded and mark retrain as urgent.
    """

    performance: Dict[str, Dict] = {}
    any_degraded = False

    for model_name in ("churn", "nba", "clv"):
        if model_evaluator:
            result = model_evaluator.evaluate(
                model_name=model_name,
                holdout_data=training_data.get("training_data", {}),
            )
            performance[model_name] = result
            if result.get("degraded", False):
                any_degraded = True
        else:
            performance[model_name] = {"auc": 0.0, "degraded": False}

    print(
        f"[INFO] check_model_performance: {len(performance)} models evaluated, "
        f"any_degraded={any_degraded}"
    )
    return {"model_performance": performance, "any_degraded": any_degraded}


def retrain_churn_model(
    training_data: Dict,
    model_trainer: Any,
    **context: Any,
) -> Dict:
    """
    We retrain the churn prediction model on fresh data.

    The churn model uses a gradient boosted classifier
    with cross-domain features: engagement decline,
    data shadow score, product holding changes, and
    competitor signal proxies.

    Per-country models are calibrated separately as
    churn drivers differ significantly across markets.
    """

    if not training_data.get("sufficient_for_training", False):
        print("[INFO] retrain_churn_model: skipped (insufficient training data)")
        return {"model": "churn", "skipped": True}

    model_artifact = (
        model_trainer.retrain(
            model_name="churn",
            data=training_data.get("training_data", {}),
        )
        if model_trainer
        else {}
    )

    auc = model_artifact.get("validation_auc", 0.0)
    print(f"[INFO] retrain_churn_model: new model AUC={auc:.4f}")
    return {"model": "churn", "artifact": model_artifact, "validation_auc": auc, "skipped": False}


def retrain_nba_model(
    training_data: Dict,
    model_trainer: Any,
    **context: Any,
) -> Dict:
    """
    We update NBA action weights based on recent outcome
    data — which recommendations led to accepted actions
    and which were ignored.

    The NBA model is a contextual bandit. We update the
    reward weights per action type and per country using
    Thompson sampling on the observed conversion rates.
    """

    if not training_data.get("sufficient_for_training", False):
        print("[INFO] retrain_nba_model: skipped (insufficient training data)")
        return {"model": "nba", "skipped": True}

    model_artifact = (
        model_trainer.retrain(
            model_name="nba",
            data=training_data.get("training_data", {}),
        )
        if model_trainer
        else {}
    )

    precision = model_artifact.get("top1_precision", 0.0)
    print(f"[INFO] retrain_nba_model: new model top-1 precision={precision:.4f}")
    return {"model": "nba", "artifact": model_artifact, "top1_precision": precision, "skipped": False}


def retrain_clv_model(
    training_data: Dict,
    model_trainer: Any,
    **context: Any,
) -> Dict:
    """
    We update CLV parameters per country using a
    Pareto/NBD model for transaction frequency and a
    gamma-gamma model for monetary value.

    CLV is recomputed quarterly for deep recalibration
    but the weekly run updates the country-level
    multipliers that account for macroeconomic shifts.
    """

    if not training_data.get("sufficient_for_training", False):
        print("[INFO] retrain_clv_model: skipped (insufficient training data)")
        return {"model": "clv", "skipped": True}

    model_artifact = (
        model_trainer.retrain(
            model_name="clv",
            data=training_data.get("training_data", {}),
        )
        if model_trainer
        else {}
    )

    mape = model_artifact.get("mape", 0.0)
    print(f"[INFO] retrain_clv_model: new model MAPE={mape:.4f}")
    return {"model": "clv", "artifact": model_artifact, "mape": mape, "skipped": False}


def validate_new_models(
    churn_result: Dict,
    nba_result: Dict,
    clv_result: Dict,
    model_validator: Any,
    **context: Any,
) -> Dict:
    """
    We run holdout validation on the last 30 days for
    all three new models.

    Validation checks:
    - AUC/precision above minimum threshold
    - No significant calibration errors
    - Performance does not degrade for any country subgroup
    - Predictions are not biased by protected attributes
    """

    validation_results = {}
    all_passed = True

    for result in (churn_result, nba_result, clv_result):
        model = result.get("model", "unknown")
        if result.get("skipped", False):
            validation_results[model] = {"passed": True, "skipped": True}
            continue

        if model_validator:
            vr = model_validator.validate_holdout(model_name=model, artifact=result.get("artifact"))
            passed = vr.get("passed", True)
        else:
            passed = True
            vr = {"passed": True}

        validation_results[model] = vr
        if not passed:
            all_passed = False
            print(f"[WARNING] validate_new_models: {model} failed holdout validation")

    print(f"[INFO] validate_new_models: all_passed={all_passed}")
    return {"validation_results": validation_results, "all_passed": all_passed}


def shadow_deploy(
    validation_result: Dict,
    deployment_manager: Any,
    **context: Any,
) -> Dict:
    """
    We run new and old models in parallel for
    SHADOW_DEPLOY_HOURS hours.

    During shadow deploy:
    - Production predictions come from the current model
    - Shadow predictions come from the new model
    - Both are logged for comparison
    - No RMs receive alerts based on shadow model output

    After shadow deploy completes the promote_models task
    compares shadow vs production performance.
    """

    if not validation_result.get("all_passed", False):
        print("[INFO] shadow_deploy: skipped (validation failed)")
        return {"deployed": False, "reason": "validation_failed"}

    shadow_ids = {}
    if deployment_manager:
        shadow_ids = deployment_manager.shadow_deploy_all(
            validation_results=validation_result.get("validation_results", {}),
            shadow_hours=SHADOW_DEPLOY_HOURS,
        )

    print(f"[INFO] shadow_deploy: {len(shadow_ids)} models deployed in shadow mode")
    return {"deployed": True, "shadow_ids": shadow_ids, "shadow_hours": SHADOW_DEPLOY_HOURS}


def promote_models(
    shadow_result: Dict,
    deployment_manager: Any,
    **context: Any,
) -> Dict:
    """
    We promote models from shadow to production if their
    shadow performance exceeds the current production
    model by at least PROMOTION_MIN_IMPROVEMENT.

    Promotion is model-by-model — a new churn model can
    be promoted while the NBA model is held in shadow if
    NBA performance is not sufficiently better.
    """

    if not shadow_result.get("deployed", False):
        print("[INFO] promote_models: skipped (no shadow deployment)")
        return {"promoted_models": [], "held_models": []}

    promoted = []
    held = []

    if deployment_manager:
        result = deployment_manager.evaluate_and_promote(
            shadow_ids=shadow_result.get("shadow_ids", {}),
            min_improvement=PROMOTION_MIN_IMPROVEMENT,
        )
        promoted = result.get("promoted", [])
        held = result.get("held", [])

    print(f"[INFO] promote_models: {len(promoted)} promoted, {len(held)} held in shadow")
    return {"promoted_models": promoted, "held_models": held}


def update_model_registry(
    churn_result: Dict,
    nba_result: Dict,
    clv_result: Dict,
    validation_result: Dict,
    promotion_result: Dict,
    model_registry: Any,
    **context: Any,
) -> None:
    """
    We log all model versions, validation metrics, and
    promotion decisions to the model registry.

    The registry provides:
    - Full lineage: training data window → model version
    - Performance history: AUC/precision per run
    - Promotion audit trail for regulatory compliance
    - Rollback capability: any prior version can be
      reinstated within 15 minutes
    """

    registry_entry = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "dag_id": DAG_ID,
        "models": {
            "churn": churn_result,
            "nba": nba_result,
            "clv": clv_result,
        },
        "validation": validation_result,
        "promotion": promotion_result,
    }

    if model_registry:
        model_registry.log_retrain_run(registry_entry)
    else:
        print(f"[REGISTRY] {registry_entry}")


# ---------------------------------------------------------------------------
# DAG task dependency graph
#
#   extract_training_data
#          │
#   ┌──────┴──────────────┐
#   ▼                     ▼
#   compute_feature_drift  check_model_performance
#          │                    │
#          └──────────┬──────────┘
#                     ▼
#          ┌──────────┼──────────┐
#          ▼          ▼          ▼
#   retrain_churn  retrain_nba  retrain_clv
#          └──────────┬──────────┘
#                     ▼
#              validate_new_models
#                     │
#                     ▼
#                shadow_deploy
#                     │
#                     ▼
#               promote_models
#                     │
#                     ▼
#            update_model_registry
#
# ---------------------------------------------------------------------------

TASK_DEPENDENCIES: Dict[str, List[str]] = {
    "extract_training_data":    [],
    "compute_feature_drift":    ["extract_training_data"],
    "check_model_performance":  ["extract_training_data"],
    "retrain_churn_model":      ["compute_feature_drift", "check_model_performance"],
    "retrain_nba_model":        ["compute_feature_drift", "check_model_performance"],
    "retrain_clv_model":        ["compute_feature_drift", "check_model_performance"],
    "validate_new_models":      [
        "retrain_churn_model",
        "retrain_nba_model",
        "retrain_clv_model",
    ],
    "shadow_deploy":            ["validate_new_models"],
    "promote_models":           ["shadow_deploy"],
    "update_model_registry":    ["promote_models"],
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
        "owner":                    "ml-engineering",
        "retries":                  1,
        "retry_delay":              timedelta(minutes=10),
        "retry_exponential_backoff": True,
        "email_on_failure":         True,
        "email":                    ["ml-engineering@afriflow.internal"],
    },
    tags=["ml", "weekly", "retrain", "churn", "nba", "clv", "model-registry"],
    task_dependencies=TASK_DEPENDENCIES,
)
