"""
Privacy-preserving computation engine.

Implements differential privacy, on-device graph embedding simulation,
and dynamic consent management for the household health graph.

Patent-relevant: These modules support Independent Claim 3 —
"Privacy-preserving household health graph with on-device embedding
and differential privacy aggregation."
"""

from .differential_privacy import DifferentialPrivacyEngine
from .consent_manager import DynamicConsentManager
from .graph_embedding import HealthGraphEmbedding

__all__ = [
    "DifferentialPrivacyEngine",
    "DynamicConsentManager",
    "HealthGraphEmbedding",
]
