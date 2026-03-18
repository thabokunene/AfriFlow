"""
Unit tests for TalkingPointsEngine core functionality.

Tests comprehensive error handling and edge cases including:
- Model loading failures and error propagation
- Empty input validation and error raising
- JSON output format validation
- Processing timeout scenarios
- Configuration parameter validation

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity.
"""

import json
import os
import time
import pytest
from afriflow.integration.client_briefing.talking_points_engine import (
    TalkingPointsEngine,
    TalkingPointsConfig,
    ModelLoadError,
    EmptyInputError,
    ProcessingTimeoutError,
)


def test_model_load_failure(tmp_path):
    bad = tmp_path / "missing.model"
    cfg = TalkingPointsConfig(model_path=str(bad))
    with pytest.raises(ModelLoadError):
        TalkingPointsEngine(cfg)


def test_empty_input_raises():
    engine = TalkingPointsEngine(TalkingPointsConfig())
    with pytest.raises(EmptyInputError):
        engine.process("")


def test_plain_text_json_output():
    engine = TalkingPointsEngine(TalkingPointsConfig(max_points=4, output_format="json"))
    out = engine.process("Expansion in Kenya with forex risk and working capital needs")
    assert isinstance(out, dict)
    assert "points" in out
    assert len(out["points"]) > 0
    for p in out["points"]:
        assert "text" in p and isinstance(p["text"], str)
        assert p["relevance"] >= 0 and p["conciseness"] >= 0 and p["uniqueness"] >= 0


def test_markdown_format():
    engine = TalkingPointsEngine(TalkingPointsConfig(output_format="markdown"))
    md = engine.process("Seasonal patterns and FX hedging strategy review")
    assert isinstance(md, str)
    assert md.strip().startswith("- ")


def test_text_format():
    engine = TalkingPointsEngine(TalkingPointsConfig(output_format="text"))
    txt = engine.process("Revenue growth opportunities in agriculture and telecom corridors")
    assert isinstance(txt, str)
    assert txt.strip().splitlines()[0].startswith("1.")


def test_csv_input(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("text\nHello world about forex and expansion\n", encoding="utf-8")
    engine = TalkingPointsEngine(TalkingPointsConfig(output_format="json"))
    out = engine.process(str(p))
    assert len(out["points"]) >= 1


def test_json_file_input(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"texts": ["FX risk rising in Kenya market", "Working capital options"]}), encoding="utf-8")
    engine = TalkingPointsEngine(TalkingPointsConfig(output_format="json"))
    out = engine.process(str(p))
    assert len(out["points"]) >= 1


def test_timeout_trigger():
    cfg = TalkingPointsConfig(timeout_seconds=0.0, simulate_latency_ms=10)
    engine = TalkingPointsEngine(cfg)
    with pytest.raises(ProcessingTimeoutError):
        engine.process("Any text")


def test_batch_processing():
    engine = TalkingPointsEngine(TalkingPointsConfig(output_format="json"))
    outs = engine.batch_process([{"text": "Topic one"}, {"text": "Topic two"}])
    assert isinstance(outs, list) and len(outs) == 2


def test_caching_hits():
    engine = TalkingPointsEngine(TalkingPointsConfig())
    _ = engine.extract_key_topics("Kenya expansion and forex risk")
    before = engine.extract_key_topics.cache_info().hits
    _ = engine.extract_key_topics("Kenya expansion and forex risk")
    after = engine.extract_key_topics.cache_info().hits
    assert after > before


def test_performance_under_threshold():
    engine = TalkingPointsEngine(TalkingPointsConfig())
    start = time.time()
    _ = engine.process("Short text about FX risk and opportunities")
    assert time.time() - start < 1.0
