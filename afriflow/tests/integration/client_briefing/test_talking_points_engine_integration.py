"""
Integration tests for TalkingPointsEngine with real data scenarios.

Tests end-to-end functionality including:
- Markdown output generation from signal data
- JSON input processing and validation
- Configuration parameter handling
- Real-world data transformation scenarios

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity.
"""

import json
import pytest
from afriflow.integration.client_briefing.talking_points_engine import TalkingPointsEngine, TalkingPointsConfig


def test_end_to_end_markdown(tmp_path):
    cfg = TalkingPointsConfig(max_points=5, output_format="markdown")
    engine = TalkingPointsEngine(cfg)
    sample = {
        "texts": [
            "Client expansion in Kenya with FX volatility considerations",
            "Working capital solutions and risk mitigation opportunities",
        ]
    }
    p = tmp_path / "sample.json"
    p.write_text(json.dumps(sample), encoding="utf-8")
    md = engine.process(str(p))
    assert isinstance(md, str)
    assert md.strip().count("\n") >= 2
