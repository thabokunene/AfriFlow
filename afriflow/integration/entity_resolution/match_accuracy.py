"""
integration/entity_resolution/match_accuracy.py

Entity resolution accuracy measurement framework.

We evaluate the quality of entity resolution by
comparing predicted matches against a curated ground
truth dataset. This is critical for building RM trust
in the platform, because a 15% false match rate
generates catastrophically wrong cross-sell
recommendations.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass
from typing import Dict, Set


@dataclass
class MatchMetrics:
    """Precision, recall, and F1 for entity resolution."""

    precision: float
    recall: float
    f1: float
    total_ground_truth_groups: int
    total_predicted_groups: int
    false_merges: int
    false_splits: int


class MatchAccuracyEvaluator:
    """We evaluate entity resolution accuracy using
    pairwise precision and recall.

    A false merge occurs when two distinct companies
    are grouped together (e.g., two different companies
    both named 'African Mining Solutions').

    A false split occurs when the same company appears
    as two separate golden records (e.g., CIB knows
    them as 'Sasol' and insurance knows them as
    'SASOL LTD' and we fail to match).
    """

    def __init__(
        self, ground_truth: Dict[str, Set[str]]
    ):
        """Ground truth is a mapping from group ID to
        the set of domain entity IDs that belong
        together."""
        self.ground_truth = ground_truth
        self._truth_pairs = self._to_pairs(ground_truth)

    def evaluate(
        self, predicted: Dict[str, Set[str]]
    ) -> MatchMetrics:
        """We evaluate predicted groupings against
        ground truth using pairwise metrics."""
        pred_pairs = self._to_pairs(predicted)

        true_positives = len(
            self._truth_pairs & pred_pairs
        )
        false_positives = len(
            pred_pairs - self._truth_pairs
        )
        false_negatives = len(
            self._truth_pairs - pred_pairs
        )

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return MatchMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            total_ground_truth_groups=len(self.ground_truth),
            total_predicted_groups=len(predicted),
            false_merges=false_positives,
            false_splits=false_negatives,
        )

    @staticmethod
    def _to_pairs(
        groups: Dict[str, Set[str]]
    ) -> Set[frozenset]:
        """We convert groups to pairwise sets for
        comparison."""
        pairs = set()
        for group_id, members in groups.items():
            member_list = sorted(members)
            for i in range(len(member_list)):
                for j in range(i + 1, len(member_list)):
                    pairs.add(
                        frozenset(
                            {member_list[i], member_list[j]}
                        )
                    )
        return pairs
