from __future__ import annotations

from typing import List, Tuple
import random
import math


def make_series(
    seed: int,
    length: int,
    base: float,
    noise: float = 0.0,
    seasonal_amp: float = 0.0,
    seasonal_period: int = 0,
) -> List[float]:
    rng = random.Random(seed)
    out: List[float] = []
    for i in range(length):
        season = 0.0
        if seasonal_amp and seasonal_period:
            season = seasonal_amp * math.sin(2 * math.pi * (i % seasonal_period) / seasonal_period)
        out.append(base + season + rng.uniform(-noise, noise))
    return out


def make_drift_pair(
    seed: int,
    window: int,
    base: float,
    noise: float,
    drift_type: str = "gradual",
    drift_magnitude: float = 0.1,
) -> Tuple[List[float], List[float]]:
    prev = make_series(seed, window, base=base, noise=noise)
    if drift_type == "gradual":
        curr = [v * (1 + drift_magnitude) for v in make_series(seed, window, base=base, noise=noise)]
    elif drift_type == "spike":
        curr = make_series(seed, window, base=base * (1 + drift_magnitude), noise=noise)
    elif drift_type == "cyclical":
        curr = make_series(seed, window, base=base, noise=noise, seasonal_amp=base * drift_magnitude, seasonal_period=max(3, window // 4))
    else:
        curr = make_series(seed, window, base=base, noise=noise)
    return prev, curr
