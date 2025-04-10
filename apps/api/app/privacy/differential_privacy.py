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
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# ── Sensitivity Tiers ───────────────────────────────────────────────
# Data types are classified by privacy sensitivity. More sensitive data
# receives a SMALLER ε (more noise), consuming less total budget per
# query but providing stronger privacy guarantees.

class SensitivityTier(Enum):
    """Privacy sensitivity classification for biomarker data types.

    Patent claim: "A tiered privacy sensitivity classification wherein
    biomarker data types are assigned to sensitivity tiers that
    determine per-query epsilon allocation, with genetically derived
    data receiving the strongest privacy protection."
    """
    CRITICAL = "critical"      # Genetic data, rare conditions
    HIGH = "high"              # Glucose, blood tests, medications
    MEDIUM = "medium"          # Heart rate, HRV, sleep
    LOW = "low"                # Steps, exercise, activity calories

# Per-tier ε allocation: more sensitive → smaller ε → more noise
TIER_EPSILON_MAP: Dict[SensitivityTier, float] = {
    SensitivityTier.CRITICAL: 0.1,    # Strongest protection
    SensitivityTier.HIGH: 0.3,
    SensitivityTier.MEDIUM: 0.5,
    SensitivityTier.LOW: 0.8,         # Least protection needed
}

# Map nutrient targets to their source biomarker sensitivity tier
# Nutrients derived from high-sensitivity biomarkers inherit that tier
NUTRIENT_SENSITIVITY_TIERS: Dict[str, SensitivityTier] = {
    # Genetics-derived adjustments → CRITICAL
    "folate_mcg": SensitivityTier.CRITICAL,
    "b12_mcg": SensitivityTier.CRITICAL,
    "vitamin_d_iu": SensitivityTier.CRITICAL,
    "caffeine_mg": SensitivityTier.CRITICAL,
    # Glucose-derived adjustments → HIGH
    "carbs_g": SensitivityTier.HIGH,
    "kcal": SensitivityTier.HIGH,
    # Heart rate / HRV derived → MEDIUM
    "water_ml": SensitivityTier.MEDIUM,
    "magnesium_mg": SensitivityTier.MEDIUM,
    "vitamin_b6_mg": SensitivityTier.MEDIUM,
    "sodium_mg": SensitivityTier.MEDIUM,
    # General macro targets → LOW (less individual-identifying)
    "protein_g": SensitivityTier.LOW,
    "fat_g": SensitivityTier.LOW,
    "fiber_g": SensitivityTier.LOW,
    "calcium_mg": SensitivityTier.LOW,
}

@dataclass
class QueryRecord:
    """Records a single privacy-consuming query."""
    timestamp: datetime
    nutrient: str
    tier: SensitivityTier
    epsilon_consumed: float
    noise_scale: float

@dataclass
class PrivacyExposureReport:
    """Cumulative privacy exposure status for a user.

    Patent claim: "A privacy exposure tracking method that maintains
    per-tier epsilon consumption history, computes a cumulative exposure
    index, and triggers protective actions when exposure thresholds
    are approached."
    """
    user_id: str
    total_epsilon_spent: float
    total_epsilon_budget: float
    per_tier_spent: Dict[str, float]
    per_tier_query_count: Dict[str, int]
    exposure_index: float        # 0.0 (fresh) to 1.0 (exhausted)
    risk_level: str              # "low", "moderate", "high", "critical"
    queries_until_exhaustion: int  # Estimated remaining queries
    period_hours_remaining: float

class DynamicEpsilonAllocator:
    """Allocates per-query epsilon based on data sensitivity tier.

    Instead of a flat epsilon for all queries, this allocator assigns
    smaller epsilon (more noise, stronger privacy) to sensitive data
    and larger epsilon (less noise) to less sensitive data.

    This mirrors privacy approaches used by Apple (local DP with
    per-domain budgets) and Google (RAPPOR with tiered sensitivity).

    Patent claim: "A dynamic privacy budget allocation system that
    assigns differential privacy parameters based on biomarker data
    sensitivity classification, manages cumulative per-user privacy
    exposure indices, and adaptively adjusts noise injection rates
    as budget thresholds are approached."
    """

    def __init__(
        self,
        tier_epsilon_map: Optional[Dict[SensitivityTier, float]] = None,
        nutrient_tier_map: Optional[Dict[str, SensitivityTier]] = None,
        budget_warning_threshold: float = 0.7,
        budget_critical_threshold: float = 0.9,
    ):
        self._tier_epsilon = tier_epsilon_map or dict(TIER_EPSILON_MAP)
        self._nutrient_tiers = nutrient_tier_map or dict(NUTRIENT_SENSITIVITY_TIERS)
        self._warning_threshold = budget_warning_threshold
        self._critical_threshold = budget_critical_threshold
        self._query_history: Dict[str, List[QueryRecord]] = {}

    def get_epsilon_for_nutrient(self, nutrient: str) -> float:
        """Get the dynamically allocated epsilon for a nutrient target.

        Returns smaller epsilon for more sensitive nutrients (stronger privacy).
        """
        tier = self._nutrient_tiers.get(nutrient, SensitivityTier.MEDIUM)
        return self._tier_epsilon[tier]

    def get_tier_for_nutrient(self, nutrient: str) -> SensitivityTier:
        """Get the sensitivity tier for a nutrient."""
        return self._nutrient_tiers.get(nutrient, SensitivityTier.MEDIUM)

    def get_adaptive_epsilon(
        self,
        nutrient: str,
        budget: "PrivacyBudget",
    ) -> float:
        """Get epsilon that adapts based on remaining budget.

        When budget is running low, epsilon is reduced (more noise)
        to stretch the remaining budget across more queries.
        """
        base_epsilon = self.get_epsilon_for_nutrient(nutrient)
        exposure_ratio = budget.epsilon_spent / budget.epsilon_total

        if exposure_ratio >= self._critical_threshold:
            # Critical: reduce epsilon by 50% to preserve budget
            return base_epsilon * 0.5
        elif exposure_ratio >= self._warning_threshold:
            # Warning: reduce epsilon by 25%
            return base_epsilon * 0.75
        return base_epsilon

    def record_query(
        self,
        user_id: str,
        nutrient: str,
        epsilon_consumed: float,
        noise_scale: float,
    ) -> None:
        """Record a privacy-consuming query for exposure tracking."""
        if user_id not in self._query_history:
            self._query_history[user_id] = []
        self._query_history[user_id].append(QueryRecord(
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            nutrient=nutrient,
            tier=self.get_tier_for_nutrient(nutrient),
            epsilon_consumed=epsilon_consumed,
            noise_scale=noise_scale,
        ))

    def get_exposure_report(self, user_id: str, budget: "PrivacyBudget") -> PrivacyExposureReport:
        """Generate a comprehensive privacy exposure report."""
        history = self._query_history.get(user_id, [])

        per_tier_spent: Dict[str, float] = {t.value: 0.0 for t in SensitivityTier}
        per_tier_count: Dict[str, int] = {t.value: 0 for t in SensitivityTier}

        for record in history:
            per_tier_spent[record.tier.value] += record.epsilon_consumed
            per_tier_count[record.tier.value] += 1

        exposure_index = budget.epsilon_spent / budget.epsilon_total if budget.epsilon_total > 0 else 1.0

        if exposure_index >= self._critical_threshold:
            risk_level = "critical"
        elif exposure_index >= self._warning_threshold:
            risk_level = "high"
        elif exposure_index >= 0.4:
            risk_level = "moderate"
        else:
            risk_level = "low"

        # Estimate remaining queries based on average consumption
        total_queries = len(history)
        if total_queries > 0:
            avg_eps_per_query = budget.epsilon_spent / total_queries
            queries_remaining = int(budget.epsilon_remaining / avg_eps_per_query) if avg_eps_per_query > 0 else 0
        else:
            queries_remaining = int(budget.epsilon_remaining / 0.3)  # Default estimate

        hours_since_reset = (datetime.now(timezone.utc).replace(tzinfo=None) - budget.last_reset).total_seconds() / 3600
        hours_remaining = max(0, budget.reset_period_hours - hours_since_reset)

        return PrivacyExposureReport(
            user_id=user_id,
            total_epsilon_spent=budget.epsilon_spent,
            total_epsilon_budget=budget.epsilon_total,
            per_tier_spent=per_tier_spent,
            per_tier_query_count=per_tier_count,
            exposure_index=round(exposure_index, 4),
            risk_level=risk_level,
            queries_until_exhaustion=queries_remaining,
            period_hours_remaining=round(hours_remaining, 1),
        )

    def reset_history(self, user_id: str) -> None:
        """Clear query history for a user (on budget reset)."""
        self._query_history.pop(user_id, None)

@dataclass
class PrivacyBudget:
# TODO: add comprehensive tests
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
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

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
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
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

# TODO: add comprehensive tests
# NOTE: reviewed 2024-07-28

# NOTE: reviewed 2025-04-10