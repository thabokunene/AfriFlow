import importlib
import pytest


MODULES = [
    "afriflow.domains.cib.processing.flink.corridor_aggregator",
    "afriflow.domains.cib.processing.flink.late_arrival_handler",
    "afriflow.domains.cib.processing.spark.client_profitability",
    "afriflow.domains.cib.processing.spark.payment_enrichment",
]


@pytest.mark.parametrize("module_path", MODULES)
def test_processor_accepts_authorized_role(module_path):
    m = importlib.import_module(module_path)
    proc = m.Processor()
    out = proc.process_sync({"access_role": "system", "source": "unit-test", "payload": {"v": 1}})
    assert out.get("processed") is True


@pytest.mark.parametrize("module_path", MODULES)
def test_processor_rejects_missing_source(module_path):
    m = importlib.import_module(module_path)
    proc = m.Processor()
    with pytest.raises(ValueError):
        proc.process_sync({"access_role": "system", "payload": 1})


@pytest.mark.parametrize("module_path", MODULES)
def test_processor_rejects_unauthorized_role(module_path):
    m = importlib.import_module(module_path)
    proc = m.Processor()
    with pytest.raises(PermissionError):
        proc.process_sync({"access_role": "guest", "source": "unit-test"})
