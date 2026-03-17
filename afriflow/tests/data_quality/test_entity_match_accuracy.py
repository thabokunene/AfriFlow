"""
tests/data_quality/test_entity_match_accuracy.py

We test the accuracy measurement framework for entity
resolution by comparing resolved matches against a
curated ground truth dataset.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from integration.entity_resolution.match_accuracy import (
    MatchAccuracyEvaluator,
)


class TestMatchAccuracyMetrics:
    """We verify that precision, recall, and F1 are
    computed correctly against known ground truth."""

    @pytest.fixture
    def evaluator(self):
        ground_truth = {
            "GLD-001": {"CIB-A", "FX-A", "INS-A"},
            "GLD-002": {"CIB-B", "CELL-B"},
            "GLD-003": {"CIB-C", "PBB-C", "FX-C"},
        }
        return MatchAccuracyEvaluator(ground_truth)

    def test_perfect_match_gives_100_precision(self, evaluator):
        predicted = {
            "P-001": {"CIB-A", "FX-A", "INS-A"},
            "P-002": {"CIB-B", "CELL-B"},
            "P-003": {"CIB-C", "PBB-C", "FX-C"},
        }
        metrics = evaluator.evaluate(predicted)
        assert metrics.precision == pytest.approx(1.0, abs=0.01)

    def test_false_merge_reduces_precision(self, evaluator):
        predicted = {
            "P-001": {"CIB-A", "FX-A", "INS-A", "CIB-B"},
        }
        metrics = evaluator.evaluate(predicted)
        assert metrics.precision < 1.0

    def test_split_reduces_recall(self, evaluator):
        predicted = {
            "P-001": {"CIB-A", "FX-A"},
            "P-002": {"INS-A"},
            "P-003": {"CIB-B", "CELL-B"},
            "P-004": {"CIB-C", "PBB-C", "FX-C"},
        }
        metrics = evaluator.evaluate(predicted)
        assert metrics.recall < 1.0
