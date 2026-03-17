import importlib
from typing import Any, Dict, List


class _DummyIngestionStore:
    def __init__(self) -> None:
        self.kwargs: Dict[str, Any] = {}

    def pull_mt103(self, **kwargs: Any) -> List[Dict]:
        self.kwargs = kwargs
        return [{"id": 1}]

    def pull_lc_documents(self, **kwargs: Any) -> List[Dict]:
        self.kwargs = kwargs
        return [{"id": 2}]

    def pull_trade_finance(self, **kwargs: Any) -> List[Dict]:
        self.kwargs = kwargs
        return [{"id": 3}]


class _DummyMarketClient:
    def __init__(self) -> None:
        self.kwargs: Dict[str, Any] = {}

    def get_spot_rates(self, **kwargs: Any) -> Dict:
        self.kwargs = kwargs
        return {"USDZAR": 18.0}

    def get_forward_curves(self, **kwargs: Any) -> Dict:
        self.kwargs = kwargs
        return {"USDZAR": [17.9]}


class _DummyTreasuryClient:
    def __init__(self) -> None:
        self.kwargs: Dict[str, Any] = {}

    def get_hedge_book(self, **kwargs: Any) -> List[Dict]:
        self.kwargs = kwargs
        return [{"pos": 1}]


class _DummyGoldenStore:
    def __init__(self) -> None:
        self.last_since = None

    def get_changed_since(self, since):
        self.last_since = since
        return []

    def get(self, gid: str) -> Dict:
        return {"golden_id": gid}


class _DummyAlertEngine:
    def __init__(self) -> None:
        self.sent = 0

    def send(self, **kwargs: Any) -> bool:
        self.sent += 1
        return True


class _DummyMetricsStore:
    def __init__(self) -> None:
        self.last = None

    def record(self, metrics: Dict) -> None:
        self.last = metrics


def test_daily_cib_refresh_returns_utc_isoformat():
    m = importlib.import_module("afriflow.orchestration.airflow.dags.daily_cib_refresh")
    store = _DummyIngestionStore()
    out = m.extract_swift_mt103(store)
    assert out["as_of"].endswith("+00:00")
    out = m.extract_lc_documents(store)
    assert out["as_of"].endswith("+00:00")
    out = m.extract_trade_finance(store)
    assert out["as_of"].endswith("+00:00")


def test_daily_forex_refresh_returns_utc_isoformat():
    m = importlib.import_module("afriflow.orchestration.airflow.dags.daily_forex_refresh")
    market = _DummyMarketClient()
    treasury = _DummyTreasuryClient()
    out = m.fetch_spot_rates(market)
    assert out["as_of"].endswith("+00:00")
    out = m.fetch_forward_curves(market)
    assert out["as_of"].endswith("+00:00")
    out = m.fetch_hedge_book(treasury)
    assert out["as_of"].endswith("+00:00")


def test_daily_unified_golden_record_utc_in_input():
    m = importlib.import_module("afriflow.orchestration.airflow.dags.daily_unified_golden_record")

    class _DomainStores:
        def get_todays_updated_clients(self, **kwargs: Any) -> List[str]:
            assert kwargs["as_of"].tzinfo is not None
            return []

    ds = _DomainStores()
    out = m.load_domain_updates(ds)
    assert out["client_count"] == 0


def test_daily_data_shadow_check_utc_in_input():
    m = importlib.import_module("afriflow.orchestration.airflow.dags.daily_data_shadow_check")

    class _CibStore:
        def get_active_cib_clients(self, **kwargs: Any) -> List[Dict]:
            assert kwargs["as_of"].tzinfo is not None
            return []

    store = _CibStore()
    out = m.load_cib_client_list(store)
    assert out["client_count"] == 0


def test_hourly_cross_domain_signals_utc_timestamps_and_since():
    m = importlib.import_module("afriflow.orchestration.airflow.dags.hourly_cross_domain_signals")
    golden = _DummyGoldenStore()
    ids = m.identify_changed_clients(golden_record_store=golden)
    assert isinstance(ids, list)
    assert getattr(golden.last_since, "tzinfo") is not None

    engine = _DummyAlertEngine()
    summary = m.dispatch_rm_alerts([], [], [], engine)
    assert summary["run_timestamp"].endswith("+00:00")
    metrics = _DummyMetricsStore()
    m.log_run_metrics(summary, metrics)
    assert metrics.last["run_timestamp"].endswith("+00:00")
