"""
@file quality_scorer.py
@description Quality Scorer - Calculate data quality scores across dimensions
@author Thabo Kunene
@created 2026-03-19

This module calculates data quality scores across multiple dimensions
including completeness, accuracy, timeliness, and consistency.

Key Classes:
- QualityDimensions: Enum of quality dimensions
- QualityScorer: Main engine for quality score calculation

Features:
- Multi-dimensional quality scoring
- Weighted score calculation
- Domain-specific scoring
- Quality trend tracking
- Threshold-based alerting

Usage:
    >>> from afriflow.data_quality.quality_scorer import QualityScorer
    >>> scorer = QualityScorer()
    >>> score = scorer.calculate_score(
    ...     domain="cib",
    ...     metrics={"completeness": 0.95, "accuracy": 0.98, "timeliness": 0.90}
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("data_quality.scorer")


class QualityDimensions(Enum):
    """
    Data quality dimension enumeration.

    Defines the dimensions used to assess data quality:
    - COMPLETENESS: Percentage of required fields populated
    - ACCURACY: Percentage of values that are correct
    - TIMELINESS: How current the data is
    - CONSISTENCY: Consistency across sources
    - VALIDITY: Conformance to expected formats
    - UNIQUENESS: Absence of duplicates
    """
    COMPLETENESS = "completeness"  # Required fields populated
    ACCURACY = "accuracy"  # Values are correct
    TIMELINESS = "timeliness"  # Data is current
    CONSISTENCY = "consistency"  # Consistent across sources
    VALIDITY = "validity"  # Conforms to formats
    UNIQUENESS = "uniqueness"  # No duplicates


class QualityScorer:
    """
    Multi-dimensional data quality scoring engine.

    Calculates quality scores across multiple dimensions
    with configurable weights per domain.

    Attributes:
        _scores: Dictionary mapping domain-date to score records
        _weights: Dictionary mapping domain to dimension weights
        _thresholds: Quality threshold configuration

    Example:
        >>> scorer = QualityScorer()
        >>> score = scorer.calculate_score(
        ...     domain="cib",
        ...     metrics={
        ...         "completeness": 0.95,
        ...         "accuracy": 0.98,
        ...         "timeliness": 0.90
        ...     }
        ... )
    """

    # Default weights for quality dimensions (equal weights)
    DEFAULT_WEIGHTS = {
        QualityDimensions.COMPLETENESS: 0.20,
        QualityDimensions.ACCURACY: 0.20,
        QualityDimensions.TIMELINESS: 0.20,
        QualityDimensions.CONSISTENCY: 0.15,
        QualityDimensions.VALIDITY: 0.15,
        QualityDimensions.UNIQUENESS: 0.10,
    }

    # Quality thresholds
    THRESHOLDS = {
        "excellent": 0.95,  # >= 95%
        "good": 0.85,  # 85-94%
        "fair": 0.70,  # 70-84%
        "poor": 0.00,  # < 70%
    }

    def __init__(self) -> None:
        """Initialize quality scorer with empty score store."""
        self._scores: Dict[str, Dict[str, Any]] = {}
        self._weights: Dict[str, Dict[QualityDimensions, float]] = {}
        self._thresholds = self.THRESHOLDS.copy()
        logger.info("QualityScorer initialized")

    def calculate_score(
        self,
        domain: str,
        metrics: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate weighted quality score for a domain.

        Args:
            domain: Domain name (e.g., "cib", "forex")
            metrics: Dictionary of dimension metrics (0-1 scale)
            weights: Optional custom weights (default: equal weights)

        Returns:
            Overall quality score (0-100 scale)

        Example:
            >>> score = scorer.calculate_score(
            ...     domain="cib",
            ...     metrics={
            ...         "completeness": 0.95,
            ...         "accuracy": 0.98,
            ...         "timeliness": 0.90
            ...     }
            ... )
            >>> print(f"Quality score: {score:.1f}%")
        """
        # Use provided weights or default weights
        dimension_weights = weights or self.DEFAULT_WEIGHTS

        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0

        for dim_name, value in metrics.items():
            try:
                # Convert string to enum if needed
                if isinstance(dim_name, str):
                    dim = QualityDimensions(dim_name.lower())
                else:
                    dim = dim_name

                # Get weight for this dimension
                weight = dimension_weights.get(dim, 0.0)

                # Add to weighted total
                total_score += value * weight
                total_weight += weight

            except ValueError:
                logger.warning(f"Unknown quality dimension: {dim_name}")

        # Normalize score to 0-100 scale
        if total_weight > 0:
            overall_score = (total_score / total_weight) * 100
        else:
            overall_score = 0.0

        # Store score record
        date = datetime.now().strftime("%Y-%m-%d")
        key = f"{domain}:{date}"
        self._scores[key] = {
            "domain": domain,
            "date": date,
            "overall_score": overall_score,
            "dimension_scores": metrics,
            "quality_level": self._get_quality_level(overall_score),
        }

        logger.info(
            f"Quality score for {domain}: {overall_score:.1f}% "
            f"({self._get_quality_level(overall_score)})"
        )

        return overall_score

    def _get_quality_level(self, score: float) -> str:
        """
        Get quality level from score.

        Args:
            score: Score percentage (0-100)

        Returns:
            Quality level string (excellent, good, fair, poor)
        """
        score_normalized = score / 100

        if score_normalized >= self._thresholds["excellent"]:
            return "excellent"
        elif score_normalized >= self._thresholds["good"]:
            return "good"
        elif score_normalized >= self._thresholds["fair"]:
            return "fair"
        else:
            return "poor"

    def get_score(self, domain: str, date: Optional[str] = None) -> Optional[float]:
        """
        Get quality score for a domain and date.

        Args:
            domain: Domain name
            date: Date (YYYY-MM-DD), default: today

        Returns:
            Quality score or None if not found
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        key = f"{domain}:{date}"
        record = self._scores.get(key)
        return record["overall_score"] if record else None

    def get_quality_level(self, domain: str, date: Optional[str] = None) -> Optional[str]:
        """
        Get quality level for a domain and date.

        Args:
            domain: Domain name
            date: Date (YYYY-MM-DD), default: today

        Returns:
            Quality level or None if not found
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        key = f"{domain}:{date}"
        record = self._scores.get(key)
        return record["quality_level"] if record else None

    def get_scores_by_domain(
        self,
        domain: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get quality scores for a domain over time.

        Args:
            domain: Domain name
            days: Number of days to retrieve

        Returns:
            List of score records sorted by date
        """
        scores = []
        for key, record in self._scores.items():
            if record["domain"] == domain:
                scores.append(record)

        # Sort by date
        scores.sort(key=lambda x: x["date"], reverse=True)
        return scores[:days]

    def get_poor_quality_domains(self) -> List[str]:
        """
        Get domains with poor quality scores.

        Returns:
            List of domain names with poor quality
        """
        poor_domains = set()
        for record in self._scores.values():
            if record["quality_level"] == "poor":
                poor_domains.add(record["domain"])
        return list(poor_domains)

    def get_statistics(self) -> Dict[str, Any]:
        """Get quality scoring statistics."""
        if not self._scores:
            return {
                "total_scores": 0,
                "avg_score": 0.0,
                "excellent_count": 0,
                "good_count": 0,
                "fair_count": 0,
                "poor_count": 0,
            }

        scores = [r["overall_score"] for r in self._scores.values()]
        levels = [r["quality_level"] for r in self._scores.values()]

        return {
            "total_scores": len(self._scores),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "excellent_count": levels.count("excellent"),
            "good_count": levels.count("good"),
            "fair_count": levels.count("fair"),
            "poor_count": levels.count("poor"),
        }


__all__ = [
    "QualityDimensions",
    "QualityScorer",
]
