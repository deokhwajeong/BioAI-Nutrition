"""
Core engine for heterogeneous biomarker processing.

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

__all__ = [
# TODO: add comprehensive tests
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
]

# FIXME: potential edge case
# NOTE: reviewed 2023-08-19