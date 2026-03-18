import os
import json
import types
import pytest

from afriflow.scripts import gating_framework as gf


def _make_tmp_config(tmp_path, subtrees):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"subtrees": subtrees}), encoding="utf-8")
    return str(p)


def _make_changed(tmp_path, files):
    p = tmp_path / "changed.json"
    p.write_text(json.dumps({"files": files}), encoding="utf-8")
    return str(p)


class DummyProc:
    def __init__(self, rc=0):
        self.returncode = rc


def test_skips_when_no_changed(tmp_path, monkeypatch):
    cfg = _make_tmp_config(
        tmp_path,
        [{"name": "forex", "path": "domains/forex/ingestion", "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None}, "conditions": {}, "gates": {"line_min": 90, "branch_min": 0, "func_min": 0}}],
    )
    ch = _make_changed(tmp_path, [])
    args = {
        "config": cfg,
        "coverage_xml": "coverage.xml",
        "coverage_json": "coverage.json",
        "changed_files": ch,
        "log_json": str(tmp_path / "log.json"),
    }
    monkeypatch.setattr(gf, "subprocess", types.SimpleNamespace(run=lambda *a, **k: DummyProc(0)))
    rc = gf.run_cli(args)
    assert rc == 0
    log = json.loads((tmp_path / "log.json").read_text(encoding="utf-8"))
    assert any(e["gate_status"] == "skipped" for e in log["entries"])


def test_runs_gate_on_match(tmp_path, monkeypatch):
    cfg = _make_tmp_config(
        tmp_path,
        [{"name": "forex", "path": "domains/forex/ingestion", "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None}, "conditions": {}, "gates": {"line_min": 90, "branch_min": 0, "func_min": 0}}],
    )
    ch = _make_changed(tmp_path, ["afriflow/domains/forex/ingestion/kafka_producer.py"])
    args = {
        "config": cfg,
        "coverage_xml": "coverage.xml",
        "coverage_json": "coverage.json",
        "changed_files": ch,
        "log_json": str(tmp_path / "log.json"),
    }
    monkeypatch.setattr(gf, "subprocess", types.SimpleNamespace(run=lambda *a, **k: DummyProc(0)))
    rc = gf.run_cli(args)
    assert rc == 0
    log = json.loads((tmp_path / "log.json").read_text(encoding="utf-8"))
    assert any(e["gate_status"] == "passed" for e in log["entries"])


def test_gate_failure_propagates_rc(tmp_path, monkeypatch):
    cfg = _make_tmp_config(
        tmp_path,
        [{"name": "forex", "path": "domains/forex/ingestion", "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None}, "conditions": {}, "gates": {"line_min": 90, "branch_min": 0, "func_min": 0}}],
    )
    ch = _make_changed(tmp_path, ["afriflow/domains/forex/ingestion/kafka_producer.py"])
    args = {
        "config": cfg,
        "coverage_xml": "coverage.xml",
        "coverage_json": "coverage.json",
        "changed_files": ch,
        "log_json": str(tmp_path / "log.json"),
    }
    monkeypatch.setattr(gf, "subprocess", types.SimpleNamespace(run=lambda *a, **k: DummyProc(1)))
    rc = gf.run_cli(args)
    assert rc == 1
    log = json.loads((tmp_path / "log.json").read_text(encoding="utf-8"))
    assert any(e["gate_status"] == "failed" for e in log["entries"])


def test_conditional_branch_function_thresholds(tmp_path, monkeypatch):
    os.environ["ENABLE_BRANCH_GATE"] = "true"
    os.environ["ENABLE_FUNCTION_GATE"] = "false"
    cfg = _make_tmp_config(
        tmp_path,
        [
            {
                "name": "forex",
                "path": "domains/forex/ingestion",
                "filters": {"file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": None},
                "conditions": {"branch_gate_env": "ENABLE_BRANCH_GATE", "function_gate_env": "ENABLE_FUNCTION_GATE"},
                "gates": {"line_min": 90, "branch_min": 90, "func_min": 90},
            }
        ],
    )
    ch = _make_changed(tmp_path, ["afriflow/domains/forex/ingestion/kafka_producer.py"])
    captured = {}

    def fake_run(cmd, cwd=None):
        captured["cmd"] = cmd
        return DummyProc(0)

    monkeypatch.setattr(gf, "subprocess", types.SimpleNamespace(run=fake_run))
    rc = gf.run_cli(
        {
            "config": cfg,
            "coverage_xml": "coverage.xml",
            "coverage_json": "coverage.json",
            "changed_files": ch,
            "log_json": str(tmp_path / "log.json"),
        }
    )
    assert rc == 0
    assert "--branch-min" in captured["cmd"] and "90" in captured["cmd"]
    assert "--func-min" in captured["cmd"] and "0" in captured["cmd"]
