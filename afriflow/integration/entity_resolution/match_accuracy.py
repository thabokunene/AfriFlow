"""
@file match_accuracy.py
@description Match accuracy evaluator for the AfriFlow entity resolution layer,
    measuring quality by comparing predicted match groupings against ground truth
    using pairwise precision, recall, and F1 metrics.
@author Thabo Kunene
@created 2026-03-19
"""

from dataclasses import dataclass  # structured metrics value object
from typing import Dict, Set        # type hints for group mappings


@dataclass
class MatchMetrics:
    """
    Precision, recall, F1, and error counts for entity resolution evaluation.

    :param precision: Fraction of predicted pairs that are correct (0.0–1.0).
    :param recall: Fraction of ground-truth pairs that were found (0.0–1.0).
    :param f1: Harmonic mean of precision and recall (0.0–1.0).
    :param total_ground_truth_groups: Number of groups in the ground truth.
    :param total_predicted_groups: Number of groups in the predicted output.
    :param false_merges: Count of pairs that were merged but should not have been.
    :param false_splits: Count of pairs that should be merged but were not found.
    """

    precision: float                   # TP / (TP + FP)
    recall: float                      # TP / (TP + FN)
    f1: float                          # 2 * precision * recall / (precision + recall)
    total_ground_truth_groups: int     # total groups in the labelled ground truth
    total_predicted_groups: int        # total groups produced by the resolver
    false_merges: int                  # predicted pairs not in ground truth (FP)
    false_splits: int                  # ground-truth pairs not in prediction (FN)


class MatchAccuracyEvaluator:
    """
    We evaluate entity resolution accuracy using pairwise precision and recall.

    Pairwise evaluation converts group membership into all (i, j) pairs within
    each group and compares the predicted pair set against the ground-truth pair
    set. This is robust to group size variations and is the standard approach for
    entity resolution benchmarking.

    A false merge occurs when two distinct companies are grouped together
    (e.g. two different companies both named 'African Mining Solutions').

    A false split occurs when the same company appears as two separate golden
    records (e.g. CIB knows them as 'Sasol' while insurance knows them as
    'SASOL LTD' and we fail to merge them).
    """

    def __init__(
        self, ground_truth: Dict[str, Set[str]]
    ):
        """
        Initialise the evaluator with a ground truth grouping.

        :param ground_truth: Dict mapping group ID → set of domain entity IDs that
                             belong together. Each entity ID should appear in exactly
                             one group.
        """
        self.ground_truth = ground_truth  # labelled reference dataset
        # Pre-compute the pairwise set once so evaluate() calls are efficient
        self._truth_pairs = self._to_pairs(ground_truth)

    def evaluate(
        self, predicted: Dict[str, Set[str]]
    ) -> MatchMetrics:
        """
        We evaluate predicted groupings against the ground truth using pairwise metrics.

        :param predicted: Dict mapping group ID → set of entity IDs produced by the resolver.
        :return: MatchMetrics with precision, recall, F1, and error counts.
        """
        # Convert predicted groups to pairwise sets for set-intersection comparison
        pred_pairs = self._to_pairs(predicted)

        # Pairwise confusion matrix components
        true_positives = len(
            self._truth_pairs & pred_pairs   # pairs correct in both prediction and ground truth
        )
        false_positives = len(
            pred_pairs - self._truth_pairs   # pairs predicted but not in ground truth (false merges)
        )
        false_negatives = len(
            self._truth_pairs - pred_pairs   # pairs in ground truth but not predicted (false splits)
        )

        # Precision: of all predicted matches, what fraction are correct?
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )

        # Recall: of all true matches, what fraction did we find?
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        # F1: harmonic mean balances precision and recall equally
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
            false_merges=false_positives,    # FP = predicted merges that should not exist
            false_splits=false_negatives,    # FN = ground-truth merges we missed
        )

    @staticmethod
    def _to_pairs(
        groups: Dict[str, Set[str]]
    ) -> Set[frozenset]:
        """
        Convert entity groups into a set of unordered pairwise combinations.

        For each group with N members, generates N*(N-1)/2 pairs. Using frozenset
        ensures that (A, B) and (B, A) are treated as the same pair.

        :param groups: Dict mapping group ID → set of entity IDs.
        :return: Set of frozenset pairs, each containing exactly two entity IDs.
        """
        pairs = set()
        for group_id, members in groups.items():
            member_list = sorted(members)  # sort for deterministic pair generation
            for i in range(len(member_list)):
                for j in range(i + 1, len(member_list)):
                    # frozenset makes the pair order-independent for set operations
                    pairs.add(
                        frozenset(
                            {member_list[i], member_list[j]}
                        )
                    )
        return pairs
