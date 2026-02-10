"""
Differential Privacy Engine.

Adds calibrated noise to aggregated health data before server transmission,
ensuring individual privacy while preserving statistical utility.

Patent-relevant: ε-differential privacy applied specifically to nutrient
demand calculations and biomarker aggregations, enabling household-level
insights without exposing individual health signals.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PrivacyBudget:
    """Tracks cumulative privacy expenditure per user.

    Each query against a user's data consumes some privacy budget (ε).
    Once exhausted, no more queries can be answered until the budget resets.

    Attributes:
        epsilon_total: Total privacy budget for the period.
        epsilon_spent: How much budget has been consumed.
        delta: Failure probability parameter.
        reset_period_hours: How often the budget resets.
        last_reset: When the budget was last reset.
    """

    epsilon_total: float = 1.0
    epsilon_spent: float = 0.0
    delta: float = 1e-5
    reset_period_hours: int = 24
    last_reset: datetime = field(default_factory=datetime.utcnow)

    @property
    def epsilon_remaining(self) -> float:
        return max(0, self.epsilon_total - self.epsilon_spent)

    @property
    def is_exhausted(self) -> bool:
        return self.epsilon_remaining <= 0

    def consume(self, epsilon: float) -> bool:
        """Attempt to consume privacy budget. Returns False if insufficient."""
        if epsilon > self.epsilon_remaining:
            return False
        self.epsilon_spent += epsilon
        return True

    def maybe_reset(self, now: Optional[datetime] = None) -> bool:
        """Reset budget if the period has elapsed."""
        now = now or datetime.utcnow()
        hours_elapsed = (now - self.last_reset).total_seconds() / 3600
        if hours_elapsed >= self.reset_period_hours:
            self.epsilon_spent = 0.0
            self.last_reset = now
            return True
        return False


class DifferentialPrivacyEngine:
    """Applies differential privacy to biomarker data and aggregations.

    Mechanisms:
    - Laplace mechanism for numeric queries (mean glucose, total steps)
    - Exponential mechanism for categorical outputs (metabolic state label)
    - Gaussian mechanism for high-sensitivity queries

    Key design principle: Noise is calibrated to the SENSITIVITY of the
    query (how much one person's data can change the output), not the
    magnitude of the data itself.
    """

    def __init__(self, default_epsilon: float = 1.0):
        self._budgets: Dict[str, PrivacyBudget] = {}
        self._default_epsilon = default_epsilon

    def get_or_create_budget(
        self, user_id: str, epsilon_total: float = 1.0
    ) -> PrivacyBudget:
        """Get or create a privacy budget for a user."""
        if user_id not in self._budgets:
            self._budgets[user_id] = PrivacyBudget(
                epsilon_total=epsilon_total
            )
        budget = self._budgets[user_id]
        budget.maybe_reset()
        return budget

    def add_laplace_noise(
        self,
        user_id: str,
        value: float,
        sensitivity: float,
        epsilon: Optional[float] = None,
    ) -> Optional[float]:
        """Add Laplace noise to a numeric value.

        The Laplace mechanism adds noise drawn from Lap(sensitivity/ε).
        Provides ε-differential privacy.

        Args:
            user_id: User whose budget to charge.
            value: The true value to protect.
            sensitivity: Maximum change from one person's data.
            epsilon: Privacy parameter (smaller = more private).

        Returns:
            Noisy value, or None if budget is exhausted.
        """
        eps = epsilon or self._default_epsilon
        budget = self.get_or_create_budget(user_id)

        if not budget.consume(eps):
            return None

        scale = sensitivity / eps
        noise = self._sample_laplace(scale)
        return value + noise

    def add_gaussian_noise(
        self,
        user_id: str,
        value: float,
        sensitivity: float,
        epsilon: Optional[float] = None,
        delta: float = 1e-5,
    ) -> Optional[float]:
        """Add Gaussian noise for (ε, δ)-differential privacy.

        More efficient than Laplace for high-dimensional queries.

        Args:
            user_id: User whose budget to charge.
            value: The true value to protect.
            sensitivity: L2 sensitivity of the query.
            epsilon: Privacy parameter.
            delta: Failure probability.

        Returns:
            Noisy value, or None if budget is exhausted.
        """
        eps = epsilon or self._default_epsilon
        budget = self.get_or_create_budget(user_id)

        if not budget.consume(eps):
            return None

        sigma = sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / eps
        noise = random.gauss(0, sigma)
        return value + noise

    def privatize_aggregation(
        self,
        user_ids: List[str],
        values: Dict[str, float],
        sensitivities: Dict[str, float],
        epsilon_per_query: float = 0.1,
    ) -> Dict[str, Optional[float]]:
        """Apply differential privacy to a multi-user aggregation.

        Used for household-level statistics where individual values
        should not be inferable from the aggregate.

        Args:
            user_ids: Users contributing to the aggregation.
            values: Aggregated values (sum, mean, etc.).
            sensitivities: Sensitivity for each aggregated metric.
            epsilon_per_query: Budget per metric per user.

        Returns:
            Privatized aggregation with noise.
        """
        result: Dict[str, Optional[float]] = {}

        for metric, value in values.items():
            sensitivity = sensitivities.get(metric, 1.0)

            # Check all users have budget
            all_ok = True
            for uid in user_ids:
                budget = self.get_or_create_budget(uid)
                if budget.epsilon_remaining < epsilon_per_query:
                    all_ok = False
                    break

            if not all_ok:
                result[metric] = None
                continue

            # Consume budget and add noise
            for uid in user_ids:
                self.get_or_create_budget(uid).consume(epsilon_per_query)

            scale = sensitivity / epsilon_per_query
            noise = self._sample_laplace(scale)
            result[metric] = value + noise

        return result

    @staticmethod
    def _sample_laplace(scale: float) -> float:
        """Sample from Laplace distribution with mean 0."""
        u = random.uniform(-0.5, 0.5)
        if u == 0:
            return 0.0
        return -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))

    @staticmethod
    def compute_sensitivity_nutrient_mean(
        n_users: int, value_range: float
    ) -> float:
        """Compute sensitivity for mean nutrient calculation.

        Sensitivity of mean = range / n_users.
        """
        if n_users == 0:
            return value_range
        return value_range / n_users
