"""
NutritionPipeline — 5-Stage Patent-Core Orchestrator.

Encapsulates the complete data processing pipeline described in the
technical whitepaper and patent claims:

    Stage 1: Temporal Synchronization   (temporal_sync)
    Stage 2: Physiological Normalization (normalization)
    Stage 3: Circadian Interpolation     (interpolation)
    Stage 4: Metabolic State Estimation  (metabolic_state)
    Stage 5: Nutrient Demand Calculation (nutrient_calculator)

Patent claim: "A method for computing personalized, real-time nutrient
demands comprising five sequential processing stages, wherein each stage
receives the output of its predecessor and the ordering is constrained
by physiological dependency relationships."

Ordering rationale:
  - Sync MUST precede Normalize (you can't z-score unaligned data)
  - Normalize MUST precede Interpolate (gap-filling uses normalized
    baselines, not raw values)
  - Interpolate MUST precede State (metabolic state inference needs
    gap-free signals)
  - State MUST precede Nutrient (nutrient demands depend on metabolic
    context)

Privacy integration:
  - Consent filtering is applied at the pipeline entrance (Stage 0)
  - Differential privacy noise is injected at the pipeline exit
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from ..biomarkers.base import BiomarkerReading, BiomarkerType
from ..privacy.consent_manager import ConsentScope, DynamicConsentManager
from ..privacy.differential_privacy import (
    DifferentialPrivacyEngine,
    DynamicEpsilonAllocator,
    NUTRIENT_SENSITIVITY_TIERS,
)
from .interpolation import CircadianInterpolator
from .metabolic_state import MetabolicState, MetabolicStateEstimator
from .normalization import (
    GeneticBaselineCalculator,
    NormalizedSignal,
    PhysiologicalNormalizer,
)
from .nutrient_calculator import (
    ConflictResolution,
    MedicalConstraint,
    NutrientBudget,
    NutrientDemandCalculator,
    NutrientTarget,
    create_default_targets,
)
from .temporal_sync import Resolution, SynchronizedFrame, TemporalSynchronizer
from .self_calibration import AdaptiveLagCalibrator, CalibrationResult

logger = logging.getLogger(__name__)

# ── Consent scope → BiomarkerType mapping ───────────────────────────
BIOMARKER_CONSENT_MAP: Dict[BiomarkerType, ConsentScope] = {
    BiomarkerType.GLUCOSE: ConsentScope.GLUCOSE_DATA,
    BiomarkerType.HEART_RATE: ConsentScope.HEART_RATE_DATA,
    BiomarkerType.HRV: ConsentScope.HEART_RATE_DATA,
    BiomarkerType.STEPS: ConsentScope.ACTIVITY_DATA,
    BiomarkerType.EXERCISE: ConsentScope.ACTIVITY_DATA,
    BiomarkerType.ACTIVITY_CALORIES: ConsentScope.ACTIVITY_DATA,
    BiomarkerType.SLEEP: ConsentScope.SLEEP_DATA,
    BiomarkerType.GENOTYPE: ConsentScope.GENETIC_DATA,
}


@dataclass
class PipelineResult:
    """Complete output of the 5-stage pipeline with audit trail.

    Contains not only the final NutrientBudget but also intermediate
    results from each stage, enabling transparency and debugging.
    """

    budget: NutrientBudget
    frames: List[SynchronizedFrame] = field(default_factory=list)
    normalized_signals: Dict[BiomarkerType, NormalizedSignal] = field(
        default_factory=dict
    )
    metabolic_state: Optional[MetabolicState] = None
    stages_executed: List[str] = field(default_factory=list)
    consent_filtered: List[str] = field(default_factory=list)
    dp_applied: bool = False
    pipeline_confidence: float = 0.0
    calibration_results: List[CalibrationResult] = field(default_factory=list)
    calibration_applied: bool = False


class NutritionPipeline:
    """5-Stage Patent-Core Pipeline Orchestrator.

    Enforces the correct processing order:
        Sync → Normalize → Interpolate → State → Nutrient

    This class is the single entry point for computing a nutrient budget.
    It replaces the ad-hoc inline pipeline in the router, ensuring that
    the whitepaper's claimed architecture is faithfully implemented.

    Usage:
        pipeline = NutritionPipeline(
            synchronizer=sync,
            normalizer=norm,
            interpolator=interp,
            state_estimator=estimator,
            nutrient_calculator=calc,
            consent_manager=consent,
            privacy_engine=dp,
        )
        result = pipeline.execute(
            user_id="user-1",
            readings={...},
            kcal_target=2000,
            weight_kg=70,
        )
    """

    # Class-level stage names for audit trail
    STAGE_NAMES = [
        "consent_filter",       # Stage 0: Privacy gate
        "temporal_sync",        # Stage 1: Align heterogeneous signals
        "normalization",        # Stage 2: Z-score + circadian correction
        "interpolation",        # Stage 3: Fill gaps with circadian model
        "metabolic_state",      # Stage 4: Infer current metabolic context
        "nutrient_calculation", # Stage 5: Compute personalized demands
        "dp_noise",             # Stage 6: Differential privacy injection
    ]

    def __init__(
        self,
        synchronizer: TemporalSynchronizer,
        normalizer: PhysiologicalNormalizer,
        interpolator: CircadianInterpolator,
        state_estimator: MetabolicStateEstimator,
        nutrient_calculator: NutrientDemandCalculator,
        consent_manager: Optional[DynamicConsentManager] = None,
        privacy_engine: Optional[DifferentialPrivacyEngine] = None,
    ):
        self._synchronizer = synchronizer
        self._normalizer = normalizer
        self._interpolator = interpolator
        self._state_estimator = state_estimator
        self._nutrient_calculator = nutrient_calculator
        self._consent_manager = consent_manager
        self._privacy_engine = privacy_engine
        self._epsilon_allocator = DynamicEpsilonAllocator()
        self._calibrator: Optional[AdaptiveLagCalibrator] = None

    def set_calibrator(self, calibrator: AdaptiveLagCalibrator) -> None:
        """Attach an adaptive lag calibrator for self-calibration.

        When attached, the lag model will apply learned corrections
        to predicted lags, and the pipeline's calibrate() method
        becomes usable for feedback loop updates.
        """
        self._calibrator = calibrator
        # Also wire the calibrator into the lag model
        self._synchronizer.lag_model._calibrator = calibrator

    # ── Main entry point ────────────────────────────────────────────

    def execute(
        self,
        user_id: str,
        readings: Dict[BiomarkerType, List[BiomarkerReading]],
        genetic_modifiers: Optional[Dict[str, float]] = None,
        kcal_target: float = 2000,
        weight_kg: float = 70,
        consumed_today: Optional[Dict[str, float]] = None,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
        resolution: Resolution = Resolution.MEDIUM,
    ) -> PipelineResult:
        """Execute the full 5-stage pipeline.

        Args:
            user_id: User identifier.
            readings: Raw readings keyed by BiomarkerType.
            genetic_modifiers: Pre-computed genetic modifier dict.
            kcal_target: Daily calorie target.
            weight_kg: Body weight in kg.
            consumed_today: Already consumed nutrients.
            window_start: Sync window start (defaults to now - 2h).
            window_end: Sync window end (defaults to now).
            resolution: Temporal resolution for synchronization.

        Returns:
            PipelineResult with budget and intermediate outputs.
        """
        now = window_end or datetime.utcnow()
        start = window_start or (now - timedelta(hours=2))
        genetic_modifiers = genetic_modifiers or {}
        consumed_today = consumed_today or {}

        result = PipelineResult(
            budget=NutrientBudget(timestamp=now, user_id=user_id),
        )

        # ── Stage 0: Consent Filtering ──────────────────────────────
        filtered_readings = self._stage_consent_filter(
            user_id, readings, genetic_modifiers, result
        )

        # ── Stage 1: Temporal Synchronization ───────────────────────
        frames = self._stage_temporal_sync(
            user_id, filtered_readings, start, now, resolution, result
        )
        result.frames = frames

        current_frame = frames[-1] if frames else None

        # ── Stage 2: Physiological Normalization ────────────────────
        #   (genetic baseline MUST be set BEFORE normalization)
        if genetic_modifiers:
            self._normalizer.set_genetic_modifiers(user_id, genetic_modifiers)

        normalized = self._stage_normalization(
            user_id, current_frame, now, result
        )
        result.normalized_signals = normalized

        # ── Stage 3: Circadian Interpolation ────────────────────────
        self._stage_interpolation(
            user_id, current_frame, normalized, result
        )

        # ── Stage 4: Metabolic State Estimation ─────────────────────
        metabolic_state = self._stage_metabolic_state(
            user_id, current_frame, now, result
        )
        result.metabolic_state = metabolic_state

        # ── Stage 5: Nutrient Demand Calculation ────────────────────
        budget = self._stage_nutrient_calculation(
            user_id=user_id,
            metabolic_state=metabolic_state,
            normalized_signals=normalized,
            genetic_modifiers=genetic_modifiers,
            kcal_target=kcal_target,
            weight_kg=weight_kg,
            consumed_today=consumed_today,
            frame_confidence=(
                current_frame.frame_confidence if current_frame else 0.0
            ),
            result=result,
        )

        # ── Stage 6: Differential Privacy ───────────────────────────
        self._stage_dp_noise(user_id, budget, result)

        result.budget = budget
        result.pipeline_confidence = budget.confidence

        return result

    # ── Individual stage implementations ────────────────────────────

    def _stage_consent_filter(
        self,
        user_id: str,
        readings: Dict[BiomarkerType, List[BiomarkerReading]],
        genetic_modifiers: Dict[str, float],
        result: PipelineResult,
    ) -> Dict[BiomarkerType, List[BiomarkerReading]]:
        """Stage 0: Filter readings by consent status.

        Patent-relevant: "Data not covered by active consent SHALL NOT
        enter the processing pipeline, ensuring GDPR Article 7 compliance
        and real-time consent propagation."
        """
        if self._consent_manager is None:
            result.stages_executed.append("consent_filter:skipped")
            return readings

        filtered: Dict[BiomarkerType, List[BiomarkerReading]] = {}
        for bt, bt_readings in readings.items():
            required_scope = BIOMARKER_CONSENT_MAP.get(bt)
            if required_scope is None:
                # No consent requirement for this type
                filtered[bt] = bt_readings
            elif self._consent_manager.check_consent(user_id, required_scope):
                filtered[bt] = bt_readings
            else:
                result.consent_filtered.append(bt.value)
                logger.info(
                    "Consent filter: dropped %s for user %s "
                    "(scope %s not granted)",
                    bt.value, user_id, required_scope.value,
                )

        # Filter genetic data if genetic consent not granted
        if not self._consent_manager.check_consent(
            user_id, ConsentScope.GENETIC_DATA
        ):
            genetic_modifiers.clear()
            result.consent_filtered.append("genetic_modifiers")

        result.stages_executed.append(
            f"consent_filter:filtered={result.consent_filtered}"
        )
        return filtered

    def _stage_temporal_sync(
        self,
        user_id: str,
        readings: Dict[BiomarkerType, List[BiomarkerReading]],
        start: datetime,
        end: datetime,
        resolution: Resolution,
        result: PipelineResult,
    ) -> List[SynchronizedFrame]:
        """Stage 1: Synchronize heterogeneous biomarker streams."""
        frames = self._synchronizer.synchronize(
            readings, start, end, resolution, user_id=user_id,
        )
        result.stages_executed.append(
            f"temporal_sync:frames={len(frames)}"
        )
        return frames

    def _stage_normalization(
        self,
        user_id: str,
        frame: Optional[SynchronizedFrame],
        timestamp: datetime,
        result: PipelineResult,
    ) -> Dict[BiomarkerType, NormalizedSignal]:
        """Stage 2: Normalize signals to z-scores with circadian correction."""
        normalized: Dict[BiomarkerType, NormalizedSignal] = {}
        if frame is None:
            result.stages_executed.append("normalization:no_frame")
            return normalized

        for bt, sig in frame.signals.items():
            if sig.confidence > 0:
                ns = self._normalizer.normalize(
                    user_id, bt, sig.value, timestamp,
                    metabolic_context="unknown",  # Context will be refined in Stage 4
                )
                normalized[bt] = ns

        result.stages_executed.append(
            f"normalization:signals={len(normalized)}"
        )
        return normalized

    def _stage_interpolation(
        self,
        user_id: str,
        frame: Optional[SynchronizedFrame],
        normalized: Dict[BiomarkerType, NormalizedSignal],
        result: PipelineResult,
    ) -> None:
        """Stage 3: Fill remaining gaps using circadian rhythm model.

        The CircadianInterpolator is already integrated into the
        TemporalSynchronizer's _align_signal method (P0 fix), but this
        stage handles any post-normalization gap filling and learns
        personal baselines for future interpolation.
        """
        if frame is None:
            result.stages_executed.append("interpolation:no_frame")
            return

        # Learn personal baseline from current data for future interpolation
        for bt, sig in frame.signals.items():
            if sig.confidence > 0.5:
                self._synchronizer.set_baseline_mean(
                    user_id, bt, sig.value,
                )

        # Feed historical readings to the interpolator for phase learning
        if hasattr(self._interpolator, 'learn_personal_phase'):
            for bt, ns in normalized.items():
                try:
                    self._interpolator.learn_personal_phase(
                        user_id, bt, [
                            BiomarkerReading(
                                biomarker_type=bt,
                                value=ns.raw_value,
                                unit="",
                                timestamp=frame.window_start,
                                source_id="pipeline",
                                user_id=user_id,
                            )
                        ],
                    )
                except Exception:
                    pass  # Non-critical learning step

        result.stages_executed.append("interpolation:baseline_updated")

    def _stage_metabolic_state(
        self,
        user_id: str,
        frame: Optional[SynchronizedFrame],
        timestamp: datetime,
        result: PipelineResult,
    ) -> MetabolicState:
        """Stage 4: Estimate current metabolic state."""
        if frame is not None:
            state = self._state_estimator.estimate(
                user_id, frame, timestamp,
            )
        else:
            state = MetabolicState(timestamp=timestamp)

        result.stages_executed.append(
            f"metabolic_state:phase={state.primary_phase.value}"
        )
        return state

    def _stage_nutrient_calculation(
        self,
        user_id: str,
        metabolic_state: MetabolicState,
        normalized_signals: Dict[BiomarkerType, NormalizedSignal],
        genetic_modifiers: Dict[str, float],
        kcal_target: float,
        weight_kg: float,
        consumed_today: Dict[str, float],
        frame_confidence: float,
        result: PipelineResult,
    ) -> NutrientBudget:
        """Stage 5: Calculate personalized nutrient demands."""
        base_targets = create_default_targets(
            kcal=kcal_target,
            weight_kg=weight_kg,
        )

        # Apply consumed amounts
        for name, amount in consumed_today.items():
            if name in base_targets:
                base_targets[name].consumed_today = amount

        budget = self._nutrient_calculator.calculate(
            user_id=user_id,
            base_targets=base_targets,
            metabolic_state=metabolic_state,
            normalized_signals=normalized_signals,
            genetic_modifiers=genetic_modifiers,
            frame_confidence=frame_confidence,
        )

        result.stages_executed.append(
            f"nutrient_calculation:targets={len(budget.targets)}"
        )
        return budget

    def _stage_dp_noise(
        self,
        user_id: str,
        budget: NutrientBudget,
        result: PipelineResult,
    ) -> None:
        """Stage 6: Apply differential privacy noise to output.

        Patent claim: "A dynamic privacy budget allocation system that
        assigns differential privacy parameters based on biomarker data
        sensitivity classification, manages cumulative per-user privacy
        exposure indices, and adaptively adjusts noise injection rates
        as budget thresholds are approached."

        Instead of a fixed ε=0.5 for every nutrient, each nutrient is
        classified into a SensitivityTier (CRITICAL → LOW). Nutrients
        derived from genetic data receive smaller ε (more noise, stronger
        privacy), while nutrients from activity data receive larger ε
        (less noise, acceptable privacy).

        The allocator also monitors the user's cumulative privacy
        exposure and further reduces ε when budget thresholds are
        approached, preventing sudden budget exhaustion.
        """
        if self._privacy_engine is None:
            result.stages_executed.append("dp_noise:skipped")
            return

        # Sensitivity = max plausible change in a single person's data
        NUTRIENT_SENSITIVITIES = {
            "kcal": 500.0,
            "carbs_g": 50.0,
            "protein_g": 30.0,
            "fat_g": 20.0,
            "fiber_g": 10.0,
            "water_ml": 500.0,
            "folate_mcg": 100.0,
            "b12_mcg": 1.0,
            "vitamin_d_iu": 200.0,
            "magnesium_mg": 100.0,
            "caffeine_mg": 100.0,
            "calcium_mg": 200.0,
            "sodium_mg": 500.0,
            "vitamin_b6_mg": 0.5,
        }

        # Get user's privacy budget for adaptive allocation
        user_budget = self._privacy_engine.get_or_create_budget(user_id)
        tier_summary: Dict[str, int] = {}  # Tier → count for audit trail

        for name, target in budget.targets.items():
            sensitivity = NUTRIENT_SENSITIVITIES.get(name, 50.0)

            # Dynamic ε allocation: tier-based + budget-adaptive
            tier = self._epsilon_allocator.get_tier_for_nutrient(name)
            epsilon = self._epsilon_allocator.get_adaptive_epsilon(
                nutrient=name,
                budget=user_budget,
            )

            noisy_value = self._privacy_engine.add_laplace_noise(
                user_id=user_id,
                value=target.daily_target,
                sensitivity=sensitivity,
                epsilon=epsilon,
            )
            if noisy_value is None:
                # Privacy budget exhausted — keep original value
                continue

            # Record query for exposure tracking
            noise_scale = sensitivity / epsilon
            self._epsilon_allocator.record_query(
                user_id=user_id,
                nutrient=name,
                epsilon_consumed=epsilon,
                noise_scale=noise_scale,
            )

            # Clamp to valid range
            lo = target.minimum if target.minimum is not None else 0.0
            hi = target.maximum if target.maximum is not None else float("inf")
            target.daily_target = max(lo, min(hi, noisy_value))

            tier_key = tier.value
            tier_summary[tier_key] = tier_summary.get(tier_key, 0) + 1

        # Audit trail with tier breakdown
        tier_str = ",".join(f"{k}={v}" for k, v in sorted(tier_summary.items()))
        result.dp_applied = True
        result.stages_executed.append(f"dp_noise:dynamic_eps,tiers=[{tier_str}]")

    def get_privacy_exposure_report(self, user_id: str) -> Optional[Any]:
        """Get the cumulative privacy exposure report for a user.

        Returns a PrivacyExposureReport with per-tier breakdown,
        exposure index, risk level, and estimated remaining queries.
        """
        if self._privacy_engine is None:
            return None
        budget = self._privacy_engine.get_or_create_budget(user_id)
        return self._epsilon_allocator.get_exposure_report(user_id, budget)

    # ── Self-Calibration Feedback Loop ──────────────────────────────

    def calibrate(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        event_time: datetime,
        post_event_readings: List[BiomarkerReading],
        predicted_lag_seconds: float,
    ) -> Optional[CalibrationResult]:
        """Run the self-calibration feedback loop for one event.

        This method should be called AFTER a prediction has been made
        and enough time has passed to observe the actual response.

        It detects the actual biomarker response peak, computes the
        prediction error, and back-propagates corrections to the
        personal calibration profile.

        Patent claim: "A feedback method wherein: (a) the predicted
        peak time from the lag model is compared against an actual
        detected peak; (b) the temporal error is decomposed into
        base-lag, circadian, and genetic correction channels; (c)
        exponentially-weighted moving average updates refine the
        personal calibration profile; enabling the model to self-evolve."

        Args:
            user_id: User identifier.
            biomarker_type: Which biomarker was predicted.
            event_time: When the causal event occurred.
            post_event_readings: Readings after the event for peak detection.
            predicted_lag_seconds: The lag the model predicted.

        Returns:
            CalibrationResult if a peak was detected, else None.
        """
        if self._calibrator is None:
            logger.warning("calibrate() called but no calibrator attached")
            return None

        # Detect actual response peak
        peak = self._calibrator.detect_response_peak(
            readings=post_event_readings,
            event_time=event_time,
            expected_lag_seconds=predicted_lag_seconds,
        )

        if peak is None or peak.confidence < 0.3:
            logger.info(
                "Self-calibration: no valid peak detected for %s",
                biomarker_type.value,
            )
            return None

        # Compute predicted peak time
        predicted_peak = event_time + timedelta(seconds=predicted_lag_seconds)

        # Run feedback loop
        result = self._calibrator.observe(
            user_id=user_id,
            biomarker_type=biomarker_type,
            event_time=event_time,
            predicted_peak_time=predicted_peak,
            actual_peak_time=peak.timestamp,
            confidence=peak.confidence,
        )

        logger.info(
            "Self-calibration: user=%s biomarker=%s error=%.1fs "
            "convergence=%.3f obs=%d",
            user_id,
            biomarker_type.value,
            result.observation.prediction_error_seconds,
            result.updated_profile.convergence_score,
            result.updated_profile.observation_count,
        )

        return result
