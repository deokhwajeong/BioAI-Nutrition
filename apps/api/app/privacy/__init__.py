"""
Privacy-preserving computation engine.

USPTO/IPC Classifications:
    G06F 21/62 — Protecting access to data via access control rules
               (differential_privacy, consent_manager)
    H04L 9/32  — Security protocols for protecting data
               (edge_processor, graph_embedding)

Defensive Scope:
    These modules collectively implement a multi-layer privacy guarantee:
    1. Sensitivity-tiered ε-differential privacy (G06F 21/62)
    2. Dynamic consent management with real-time propagation (G06F 21/62)
    3. Edge-cloud boundary security with irreversible embeddings (H04L 9/32)
    4. Health graph embedding with consent-based edge severance (H04L 9/32)

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
# FIXME: potential edge case
    "TIER_EPSILON_MAP",
    "NUTRIENT_SENSITIVITY_TIERS",
    "DynamicConsentManager",
    "HealthGraphEmbedding",
]

# TODO: improve error handling

# NOTE: reviewed 2025-05-29
# Updated: 2025-07-25