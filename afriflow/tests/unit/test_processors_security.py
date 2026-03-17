import importlib
import pytest


PROCESSOR_MODULES = [
    "domains.cell.processing.flink.expansion_detector",
    "afriflow.domains.cib.processing.flink.flow_drift_detector",
    "domains.pbb.processing.spark.payroll_analytics",
    "domains.pbb.processing.spark.pbb_enrichment",
    "domains.pbb.processing.flink.account_activity_monitor",
    "domains.pbb.processing.flink.payroll_drift_detector",
    "domains.cell.processing.spark.sim_deflation_adjuster",
    "domains.cell.processing.spark.geographic_analytics",
    "domains.cell.processing.spark.cell_enrichment",
    "domains.cell.processing.flink.workforce_growth_detector",
    "domains.cell.processing.flink.momo_flow_aggregator",
    "domains.insurance.processing.spark.policy_enrichment",
    "domains.insurance.processing.spark.claims_analytics",
    "domains.insurance.processing.flink.lapse_risk_detector",
    "domains.insurance.processing.flink.claims_spike_detector",
    "domains.forex.processing.spark.hedge_effectiveness",
    "domains.forex.processing.spark.fx_enrichment",
    "domains.forex.processing.flink.parallel_market_monitor",
    "domains.forex.processing.flink.rate_anomaly_detector",
    "domains.forex.processing.flink.hedge_gap_detector",
]


@pytest.mark.parametrize("module_path", PROCESSOR_MODULES)
def test_processor_accepts_authorized_role(module_path):
    m = importlib.import_module(module_path)
    proc = m.Processor()
    out = proc.process_sync({"access_role": "system", "source": "unit-test", "payload": {"v": 1}})
    assert out.get("processed") is True


@pytest.mark.parametrize("module_path", PROCESSOR_MODULES)
def test_processor_rejects_missing_source(module_path):
    m = importlib.import_module(module_path)
    proc = m.Processor()
    with pytest.raises(ValueError):
        proc.process_sync({"access_role": "system", "payload": 1})


@pytest.mark.parametrize("module_path", PROCESSOR_MODULES)
def test_processor_rejects_unauthorized_role(module_path):
    m = importlib.import_module(module_path)
    proc = m.Processor()
    with pytest.raises(PermissionError):
        proc.process_sync({"access_role": "guest", "source": "unit-test"})
