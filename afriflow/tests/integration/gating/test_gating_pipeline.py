import json
import os
import types
import pytest

from afriflow.scripts import gating_framework as gf


class DummyProc:
    def __init__(self, rc=0):
        self.returncode = rc


def test_pipeline_passes_for_forex_and_skips_others(tmp_path, monkeypatch):
    cfg = {
        "subtrees": [
            {
                "name": "forex_ingestion",
                "path": "domains/forex/ingestion",
                "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None},
                "conditions": {"branch_gate_env": "ENABLE_FOREX_BRANCH_GATE", "function_gate_env": "ENABLE_FOREX_FUNC_GATE"},
                "gates": {"line_min": 90, "branch_min": 90, "func_min": 90},
            },
            {
                "name": "equities_ingestion",
                "path": "domains/equities/ingestion",
                "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None},
                "conditions": {},
                "gates": {"line_min": 90, "branch_min": 0, "func_min": 0},
            },
            {
                "name": "fixed_income_ingestion",
                "path": "domains/fixed_income/ingestion",
                "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None},
                "conditions": {},
                "gates": {"line_min": 90, "branch_min": 0, "func_min": 0},
            },
        ]
    }
    cfgp = tmp_path / "config.json"
    cfgp.write_text(json.dumps(cfg), encoding="utf-8")

    chp = tmp_path / "changed.json"
    chp.write_text(
        json.dumps({"files": ["afriflow/domains/forex/ingestion/kafka_producer.py"]}),
        encoding="utf-8",
    )

    os.environ["ENABLE_FOREX_BRANCH_GATE"] = "true"
    os.environ["ENABLE_FOREX_FUNC_GATE"] = "true"
    calls = []

    def fake_run(cmd, cwd=None):
        calls.append(cmd)
        return DummyProc(0)

    monkeypatch.setattr(gf, "subprocess", types.SimpleNamespace(run=fake_run))
    rc = gf.run_cli(
        {
            "config": str(cfgp),
            "coverage_xml": "coverage.xml",
            "coverage_json": "coverage.json",
            "changed_files": str(chp),
            "log_json": str(tmp_path / "log.json"),
        }
    )
    assert rc == 0
    assert any("domains/forex/ingestion" in cmd for cmd in [" ".join(c) for c in calls])


def test_pipeline_fails_when_equities_changes_and_gate_fails(tmp_path, monkeypatch):
    cfg = {
        "subtrees": [
            {
                "name": "equities_ingestion",
                "path": "domains/equities/ingestion",
                "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None},
                "conditions": {},
                "gates": {"line_min": 90, "branch_min": 0, "func_min": 0},
            }
        ]
    }
    cfgp = tmp_path / "config.json"
    cfgp.write_text(json.dumps(cfg), encoding="utf-8")

    chp = tmp_path / "changed.json"
    chp.write_text(
        json.dumps({"files": ["afriflow/domains/equities/ingestion/order_producer.py"]}),
        encoding="utf-8",
    )

    def fake_run(cmd, cwd=None):
        return DummyProc(1)

    monkeypatch.setattr(gf, "subprocess", types.SimpleNamespace(run=fake_run))
    rc = gf.run_cli(
        {
            "config": str(cfgp),
            "coverage_xml": "coverage.xml",
            "coverage_json": "coverage.json",
            "changed_files": str(chp),
            "log_json": str(tmp_path / "log.json"),
        }
    )
    assert rc == 1
