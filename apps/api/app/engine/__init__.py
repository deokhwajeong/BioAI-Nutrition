"""
Core engine for heterogeneous biomarker processing.

USPTO/IPC Classification Coverage:
    G16H 20/60 — ICT for nutrition control (primary, all modules)
    G06F 16/27 — Data synchronization (temporal_sync)
    G06F 11/34 — Performance monitoring (self_calibration)
    G06N 20/00 — Machine learning (self_calibration feedback loop)
    G06N 7/01  — Probabilistic models (temporal_sync, interpolation, normalization)
    G06F 21/62 — Access control (pipeline consent filtering, DP noise)
    H04L 9/32  — Security protocols (edge_processor)

    See patent_classifications.py for the complete registry mapping
    each classification to its defensive rationale and claim keywords.

This package implements the key inventive steps:
1. Temporal Synchronization: Aligning data from sources with different
   sampling rates using physiological-lag-aware time windows
2. Dynamic Physiological Lag Model: Personalized, circadian-adaptive
   lag compensation via t_sync = t_event + Δt_base(b)×γ(g)×φ(c)
3. Physiological Normalization: Context-dependent scaling that accounts
   for individual baselines, circadian rhythm, and genetic modifiers
4. Genetic-Baseline Normalization: Z-scores relative to genotype-adjusted
   reference ranges, not just population averages
5. Circadian Interpolation: Filling gaps using biological rhythm models
6. Metabolic State Estimation: Inferring current metabolic context
7. Nutrient Demand Calculation: Real-time nutrient budget computation
"""

from .temporal_sync import (
    TemporalSynchronizer,
    SynchronizedFrame,
    PhysiologicalLagModel,
    LagComputation,
)
from .normalization import (
    PhysiologicalNormalizer,
    NormalizedSignal,
    GeneticBaselineProfile,
)
from .interpolation import CircadianInterpolator
from .metabolic_state import MetabolicStateEstimator, MetabolicState
from .nutrient_calculator import NutrientDemandCalculator, NutrientBudget, ConflictResolution
from .pipeline import NutritionPipeline, PipelineResult
from .self_calibration import (
    AdaptiveLagCalibrator,
    PersonalCalibrationProfile,
    PeakDetector,
    CalibrationResult,
)
from .patent_classifications import (
    PatentClassification,
    PATENT_CLASSIFICATION_REGISTRY,
    get_classifications_for_module,
    get_all_claim_keywords,
    get_tc_strategy_summary,
)

__all__ = [
    "TemporalSynchronizer",
    "SynchronizedFrame",
    "PhysiologicalLagModel",
    "LagComputation",
    "PhysiologicalNormalizer",
    "NormalizedSignal",
    "GeneticBaselineProfile",
    "CircadianInterpolator",
    "MetabolicStateEstimator",
    "MetabolicState",
    "NutrientDemandCalculator",
    "NutrientBudget",
    "ConflictResolution",
    "NutritionPipeline",
    "PipelineResult",
    "AdaptiveLagCalibrator",
    "PersonalCalibrationProfile",
    "PeakDetector",
    "CalibrationResult",
    "PatentClassification",
    "PATENT_CLASSIFICATION_REGISTRY",
    "get_classifications_for_module",
    "get_all_claim_keywords",
    "get_tc_strategy_summary",
]

# FIXME: potential edge case
# NOTE: reviewed 2023-08-19
# TODO: add comprehensive tests
# Updated: 2025-04-30
# NOTE: reviewed 2025-05-24