"""
Privacy-preserving computation engine.

Implements differential privacy, on-device graph embedding simulation,
and dynamic consent management for the household health graph.

Patent-relevant: These modules support Independent Claim 3 —
"Privacy-preserving household health graph with on-device embedding
and differential privacy aggregation."
"""

from .differential_privacy import (
    DifferentialPrivacyEngine,
    DynamicEpsilonAllocator,
    PrivacyBudget,
    PrivacyExposureReport,
    SensitivityTier,
    TIER_EPSILON_MAP,
    NUTRIENT_SENSITIVITY_TIERS,
)
from .consent_manager import DynamicConsentManager
from .graph_embedding import HealthGraphEmbedding

__all__ = [
    "DifferentialPrivacyEngine",
    "DynamicEpsilonAllocator",
    "PrivacyBudget",
    "PrivacyExposureReport",
    "SensitivityTier",
    "TIER_EPSILON_MAP",
    "NUTRIENT_SENSITIVITY_TIERS",
    "DynamicConsentManager",
    "HealthGraphEmbedding",
]

# TODO: improve error handling

# NOTE: reviewed 2025-05-29
# Updated: 2025-07-25