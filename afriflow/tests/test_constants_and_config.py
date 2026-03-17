import importlib
import os
from contextlib import contextmanager


@contextmanager
def set_env(**env):
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_schema_registry_env_backward_compatibility():
    with set_env(SCHEMA_REGISTRY_URL=None, SCHEMA_REGISTRY="http://legacy:8081"):
        constants = importlib.import_module("afriflow.domains.shared.constants")
        importlib.reload(constants)
        assert (
            constants.DEFAULT_SCHEMA_REGISTRY
            == constants.DEFAULT_SCHEMA_REGISTRY_URL
            == "http://legacy:8081"
        )


def test_config_load_prefers_url_then_legacy():
    with set_env(
        SCHEMA_REGISTRY_URL="http://preferred:8081",
        SCHEMA_REGISTRY="http://legacy:8081",
        KAFKA_BROKER="kafka:9092",
        DATABASE_URL="sqlite:///tmp.db",
        APP_ENV="test",
    ):
        config_mod = importlib.import_module("afriflow.domains.shared.config")
        importlib.reload(config_mod)
        cfg = config_mod.AppConfig.load()
        assert cfg.schema_registry_url == "http://preferred:8081"
        assert cfg.kafka_broker == "kafka:9092"
        assert cfg.db_url == "sqlite:///tmp.db"
        assert cfg.env == "test"
