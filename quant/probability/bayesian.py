"""Small transparent Bayesian updating primitives."""

from __future__ import annotations

from dataclasses import dataclass

from scipy.stats import beta as beta_distribution


@dataclass(frozen=True)
class BetaPosterior:
    alpha: float
    beta: float
    wins: int
    losses: int

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def credible_interval(self, level: float = 0.95) -> tuple[float, float]:
        if not 0 < level < 1:
            raise ValueError("credible interval level must be in (0, 1)")
        tail = (1 - level) / 2
        return (
            float(beta_distribution.ppf(tail, self.alpha, self.beta)),
            float(beta_distribution.ppf(1 - tail, self.alpha, self.beta)),
        )

    def probability_above(self, threshold: float) -> float:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between zero and one")
        return float(1 - beta_distribution.cdf(threshold, self.alpha, self.beta))


def beta_binomial_update(
    prior_alpha: float, prior_beta: float, wins: int, losses: int
) -> BetaPosterior:
    if prior_alpha <= 0 or prior_beta <= 0 or wins < 0 or losses < 0:
        raise ValueError("Beta prior parameters must be positive and counts non-negative")
    return BetaPosterior(prior_alpha + wins, prior_beta + losses, wins, losses)


def bayes_binary_update(
    prior_probability: float, likelihood_if_true: float, likelihood_if_false: float
) -> float:
    """Update a binary hypothesis from explicitly supplied numerical likelihoods."""

    if not all(0 <= x <= 1 for x in (prior_probability, likelihood_if_true, likelihood_if_false)):
        raise ValueError("probabilities must be between zero and one")
    denominator = likelihood_if_true * prior_probability + likelihood_if_false * (
        1 - prior_probability
    )
    if denominator == 0:
        raise ValueError("likelihood evidence has zero marginal probability")
    return float(likelihood_if_true * prior_probability / denominator)
