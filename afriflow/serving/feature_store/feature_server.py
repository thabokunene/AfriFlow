"""
Feature Server

Materialises and serves pre-computed features for online inference.

The feature server sits between the batch pipeline and the API:
  Batch DAG → Delta Lake → Feature Server → API (< 50ms p99)

Design decisions:
  1. Write path  : Airflow DAGs write features to Delta partitioned
     by (golden_id, feature_date). The feature server reads the
     latest partition per golden_id.

  2. Read path   : In production, features are loaded into a Redis
     hash per golden_id on DAG completion. The server reads from
     Redis with a Delta Lake fallback.

  3. TTL enforcement : Each feature definition has a TTL. The server
     marks features as STALE if the write timestamp + TTL has passed.
     Stale features are returned with a staleness flag to the model.

  4. Default values : Missing or stale features fall back to the
     default value defined in FeatureDefinition. This prevents
     model failures when one domain is temporarily unavailable.

For this portfolio demo, the feature server uses an in-memory store.
The interface is identical to the production Redis-backed version.

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .feature_definitions import (
    FEATURE_REGISTRY,
    FeatureDefinition,
    get_feature,
    model_input_features,
)


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class FeatureValue:
    """A stored feature value with metadata."""

    feature_name: str
    golden_id: str        # "MARKET" for market-wide features
    value: Any
    written_at_epoch: float   # Unix timestamp when written
    is_stale: bool = False
    source: str = "batch"    # batch / streaming / fallback


@dataclass
class FeatureVector:
    """
    A complete feature vector for a client — all features
    needed to score NBA, churn, CLV in a single read.
    """

    golden_id: str
    features: Dict[str, Any]        # feature_name → value
    staleness: Dict[str, bool]      # feature_name → is_stale
    missing_features: List[str]     # features with no value at all
    vector_completeness: float      # 0–1
    retrieved_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Feature server
# ---------------------------------------------------------------------------

class FeatureServer:
    """
    In-memory feature server for AfriFlow.

    Production version backed by Redis (via redis-py).
    Interface is identical — swap the backend by subclassing.

    Usage::

        server = FeatureServer()

        # Write features from a batch DAG
        server.write_batch({
            "GLD-001": {
                "cib_total_facility_value_zar": 200_000_000,
                "forex_volume_trend_3m": -0.12,
                ...
            }
        })

        # Read feature vector for online inference
        vector = server.get_vector("GLD-001")
        churn = ChurnPredictor().predict(
            golden_record={"golden_id": "GLD-001"},
            forex_profile={"volume_trend_3m": vector.features["forex_volume_trend_3m"]},
        )
    """

    def __init__(self):
        # {(golden_id, feature_name) → FeatureValue}
        self._store: Dict[Tuple[str, str], FeatureValue] = {}

    def write(
        self,
        golden_id: str,
        feature_name: str,
        value: Any,
        source: str = "batch",
    ) -> None:
        """Write a single feature value for a client."""
        key = (golden_id, feature_name)
        self._store[key] = FeatureValue(
            feature_name=feature_name,
            golden_id=golden_id,
            value=value,
            written_at_epoch=time.time(),
            is_stale=False,
            source=source,
        )

    def write_batch(
        self,
        feature_map: Dict[str, Dict[str, Any]],
        source: str = "batch",
    ) -> int:
        """
        Write multiple clients' features at once.

        feature_map: {golden_id: {feature_name: value, ...}}
        Returns: number of feature values written.
        """
        count = 0
        for golden_id, features in feature_map.items():
            for name, value in features.items():
                self.write(golden_id, name, value, source)
                count += 1
        return count

    def get(
        self,
        golden_id: str,
        feature_name: str,
    ) -> Optional[FeatureValue]:
        """Retrieve a single feature value, enforcing TTL."""
        key = (golden_id, feature_name)
        fv = self._store.get(key)
        if fv is None:
            return None

        # Check staleness
        defn = get_feature(feature_name)
        if defn:
            ttl_seconds = defn.ttl_minutes * 60
            age = time.time() - fv.written_at_epoch
            if age > ttl_seconds:
                fv.is_stale = True

        return fv

    def get_vector(
        self,
        golden_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> FeatureVector:
        """
        Retrieve a complete feature vector for a client.

        If feature_names is None, retrieves all model input features.
        Stale features are returned with their last-known value and
        flagged in the staleness dict.
        Missing features use the FeatureDefinition default.
        """
        if feature_names is None:
            feature_names = [f.name for f in model_input_features()]

        features: Dict[str, Any] = {}
        staleness: Dict[str, bool] = {}
        missing: List[str] = []

        for name in feature_names:
            fv = self.get(golden_id, name)
            if fv is None:
                # Fall back to default
                defn = get_feature(name)
                if defn and defn.default_value is not None:
                    features[name] = defn.default_value
                    staleness[name] = True  # using default = implicitly stale
                else:
                    missing.append(name)
            else:
                features[name] = fv.value
                staleness[name] = fv.is_stale

        total = len(feature_names)
        present = total - len(missing)
        completeness = present / total if total > 0 else 0.0

        return FeatureVector(
            golden_id=golden_id,
            features=features,
            staleness=staleness,
            missing_features=missing,
            vector_completeness=round(completeness, 3),
        )

    def get_multi_vector(
        self,
        golden_ids: List[str],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, FeatureVector]:
        """Retrieve feature vectors for multiple clients at once."""
        return {
            gid: self.get_vector(gid, feature_names)
            for gid in golden_ids
        }

    def invalidate(
        self,
        golden_id: str,
        feature_name: Optional[str] = None,
    ) -> int:
        """
        Invalidate features for a client.
        If feature_name is None, invalidates all features for the client.
        Returns number of features invalidated.
        """
        if feature_name:
            key = (golden_id, feature_name)
            if key in self._store:
                del self._store[key]
                return 1
            return 0
        else:
            keys = [
                k for k in self._store
                if k[0] == golden_id
            ]
            for k in keys:
                del self._store[k]
            return len(keys)

    def stats(self) -> Dict:
        """Return store statistics for monitoring."""
        total = len(self._store)
        stale = sum(
            1 for fv in self._store.values() if fv.is_stale
        )
        by_source: Dict[str, int] = {}
        for fv in self._store.values():
            by_source[fv.source] = by_source.get(fv.source, 0) + 1

        unique_clients = len({k[0] for k in self._store})

        return {
            "total_features": total,
            "stale_features": stale,
            "unique_clients": unique_clients,
            "by_source": by_source,
        }
