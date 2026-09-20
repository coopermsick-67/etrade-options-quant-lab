"""Reproducible bootstrap intervals for research statistics."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np


def bootstrap_interval(
    values: Sequence[float],
    statistic: Callable[[np.ndarray], float] = np.mean,
    confidence: float = 0.95,
    iterations: int = 2_000,
    seed: int = 7,
    block_size: int = 1,
) -> tuple[float, float]:
    observations = np.asarray(values, dtype=float)
    if observations.ndim != 1 or len(observations) < 2:
        raise ValueError("at least two observations are required")
    if not 0 < confidence < 1 or iterations < 1 or block_size < 1:
        raise ValueError("invalid bootstrap settings")
    rng = np.random.default_rng(seed)
    if block_size == 1:
        samples = rng.integers(0, len(observations), size=(iterations, len(observations)))
        estimates = np.asarray([statistic(observations[indexes]) for indexes in samples])
    else:
        blocks = [
            observations[start : start + block_size]
            for start in range(0, len(observations), block_size)
        ]
        bootstrap_estimates: list[float] = []
        target = len(observations)
        for _ in range(iterations):
            draw: list[float] = []
            while len(draw) < target:
                draw.extend(blocks[int(rng.integers(0, len(blocks)))])
            bootstrap_estimates.append(statistic(np.asarray(draw[:target])))
        estimates = np.asarray(bootstrap_estimates)
    alpha = (1 - confidence) / 2
    return float(np.quantile(estimates, alpha)), float(np.quantile(estimates, 1 - alpha))
