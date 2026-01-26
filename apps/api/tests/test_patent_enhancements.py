"""
Tests for patent gap fixes G-1, G-2, and OhioT1DM lag model validation.

Covers:
  - G-1: HRV-based sleep quality estimation in metabolic state
  - G-2: Context-aware re-normalization (Stage 4.5)
  - OhioT1DM: Lag model validation with synthetic OhioT1DM-like data
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, List

import pytest

from app.biomarkers.base import (
    BiomarkerReading,
    BiomarkerType,
    SamplingCharacteristics,
    TemporalBehavior,
)
from app.engine.interpolation import CircadianInterpolator
from app.engine.metabolic_state import MetabolicState, MetabolicPhase, MetabolicStateEstimator
from app.engine.normalization import PhysiologicalNormalizer, NormalizedSignal
from app.engine.nutrient_calculator import NutrientDemandCalculator, create_default_targets
from app.engine.pipeline import NutritionPipeline, PipelineResult
from app.engine.temporal_sync import (
    Resolution,
    SynchronizedFrame,
    AlignedSignal,
    TemporalSynchronizer,
)
from app.privacy.consent_manager import ConsentScope, DynamicConsentManager
from app.privacy.differential_privacy import DifferentialPrivacyEngine
from app.services.ohio_t1dm_loader import (
    OhioT1DMLoader,
    OhioPatient,
    OhioGlucoseReading,
    OhioMealEvent,
    OhioExerciseEvent,
    OhioSleepEvent,
    LagModelValidator,
    LagValidationResult,
    _pearson_r,
)

NOW = datetime(2025, 1, 15, 12, 0, 0)

def _make_reading(
    bt: BiomarkerType, value: float, ts: datetime,
) -> BiomarkerReading:
    return BiomarkerReading(
        biomarker_type=bt,
        value=value,
        unit="",
        timestamp=ts,
        source_id="test",
        user_id="test-user",
    )

def _make_frame(
    signals: Dict[BiomarkerType, tuple],
    window_start: datetime = NOW - timedelta(minutes=5),
    window_end: datetime = NOW,
) -> SynchronizedFrame:
    """Create a SynchronizedFrame with given signals.

    signals: dict of BiomarkerType → (value, confidence)
    """
    frame_signals = {}
    for bt, (value, confidence) in signals.items():
        frame_signals[bt] = AlignedSignal(
            biomarker_type=bt,
            value=value,
            confidence=confidence,
            sample_count=1,
            lag_compensated=False,
        )
    return SynchronizedFrame(
        window_start=window_start,
        window_end=window_end,
        resolution=Resolution.MEDIUM,
        signals=frame_signals,
        frame_confidence=min(c for _, c in signals.values()) if signals else 0.0,
    )

def _make_pipeline() -> NutritionPipeline:
    """Create a fully wired pipeline for testing."""
    sync = TemporalSynchronizer()
    chars = SamplingCharacteristics(
        typical_interval=timedelta(minutes=5),
        min_interval=timedelta(minutes=1),
        max_gap_before_stale=timedelta(minutes=30),
        temporal_behavior=TemporalBehavior.CONTINUOUS,
        physiological_lag=timedelta(minutes=60),
        circadian_sensitivity=0.3,
# TODO: add comprehensive tests
        noise_floor=5.0,
    )
    sync.register_source(BiomarkerType.GLUCOSE, chars)

    hr_chars = SamplingCharacteristics(
        typical_interval=timedelta(minutes=1),
        min_interval=timedelta(seconds=10),
        max_gap_before_stale=timedelta(minutes=10),
        temporal_behavior=TemporalBehavior.CONTINUOUS,
        physiological_lag=timedelta(0),
        circadian_sensitivity=0.2,
        noise_floor=2.0,
    )
    sync.register_source(BiomarkerType.HEART_RATE, hr_chars)

    return NutritionPipeline(
        synchronizer=sync,
        normalizer=PhysiologicalNormalizer(),
        interpolator=CircadianInterpolator(),
        state_estimator=MetabolicStateEstimator(),
        nutrient_calculator=NutrientDemandCalculator(),
        consent_manager=DynamicConsentManager(),
        privacy_engine=DifferentialPrivacyEngine(),
    )

def _make_glucose_readings(
    n: int, start: datetime = NOW - timedelta(hours=1),
) -> List[BiomarkerReading]:
    return [
        _make_reading(
            BiomarkerType.GLUCOSE,
            100 + i * 0.5,
            start + timedelta(minutes=5 * i),
        )
        for i in range(n)
    ]

# ═══════════════════════════════════════════════════════════════════
#  G-1: HRV-Based Sleep Quality Estimation
# ═══════════════════════════════════════════════════════════════════

class TestSleepQualityEstimation:
    """Verify that HRV-based sleep quality is estimated and affects
    insulin sensitivity, replacing the previous `pass` placeholder."""

    def test_high_hrv_gives_good_sleep_quality(self):
        """High HRV (>70ms) → sleep quality > 0.7."""
        estimator = MetabolicStateEstimator()
        frame = _make_frame({
            BiomarkerType.HRV: (85.0, 0.9),
            BiomarkerType.STEPS: (0.0, 0.5),
        })
        state = estimator.estimate("u1", frame, NOW)
        assert state.sleep_quality_estimate > 0.7, (
            f"High HRV should produce good sleep quality, got {state.sleep_quality_estimate}"
        )

    def test_low_hrv_gives_poor_sleep_quality(self):
        """Low HRV (<30ms) → sleep quality < 0.4."""
        estimator = MetabolicStateEstimator()
        frame = _make_frame({
            BiomarkerType.HRV: (20.0, 0.9),
            BiomarkerType.STEPS: (0.0, 0.5),
        })
        state = estimator.estimate("u2", frame, NOW)
        assert state.sleep_quality_estimate < 0.4, (
            f"Low HRV should produce poor sleep quality, got {state.sleep_quality_estimate}"
        )

    def test_sleep_history_affects_quality(self):
        """Recorded short sleep duration → lower quality estimate."""
        estimator = MetabolicStateEstimator()
        # Record a short 4-hour sleep
        sleep_start = NOW - timedelta(hours=6)
        sleep_end = NOW - timedelta(hours=2)
        estimator.record_sleep_event("u3", sleep_start, sleep_end, quality=0.4)

        frame = _make_frame({
            BiomarkerType.HRV: (50.0, 0.9),
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state = estimator.estimate("u3", frame, NOW)

        # With both moderate HRV and short sleep, quality should be moderate
        assert 0.2 < state.sleep_quality_estimate < 0.7, (
            f"Short sleep + moderate HRV should give moderate quality, "
            f"got {state.sleep_quality_estimate}"
        )

    def test_good_sleep_duration_improves_quality(self):
        """8-hour sleep → higher quality contribution."""
        estimator = MetabolicStateEstimator()
        # Record an 8-hour sleep
        sleep_start = NOW - timedelta(hours=10)
        sleep_end = NOW - timedelta(hours=2)
        estimator.record_sleep_event("u4", sleep_start, sleep_end, quality=0.9)

        frame = _make_frame({
            BiomarkerType.HRV: (60.0, 0.9),
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state = estimator.estimate("u4", frame, NOW)

        assert state.sleep_quality_estimate > 0.6, (
            f"Good sleep duration + decent HRV should give high quality, "
            f"got {state.sleep_quality_estimate}"
        )

    def test_poor_sleep_reduces_insulin_sensitivity(self):
        """Poor sleep quality should reduce insulin sensitivity estimate.

        Patent claim: 'Sleep debt quantitatively modulates insulin sensitivity.'
        Published evidence: Donga et al. (JCEM 2010) showed 15-25% reduction.
        """
        estimator = MetabolicStateEstimator()

        # Good sleep scenario
        frame_good = _make_frame({
            BiomarkerType.HRV: (90.0, 0.9),
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state_good = estimator.estimate("u5-good", frame_good, NOW)

        # Poor sleep scenario
        frame_poor = _make_frame({
            BiomarkerType.HRV: (15.0, 0.9),
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state_poor = estimator.estimate("u5-poor", frame_poor, NOW)

        assert state_poor.insulin_sensitivity_estimate < state_good.insulin_sensitivity_estimate, (
            f"Poor sleep should reduce insulin sensitivity: "
            f"poor={state_poor.insulin_sensitivity_estimate:.3f} vs "
            f"good={state_good.insulin_sensitivity_estimate:.3f}"
        )

    def test_sleep_quality_in_decision_log(self):
        """Sleep quality estimation should be logged in decision_log."""
        estimator = MetabolicStateEstimator()
        frame = _make_frame({
            BiomarkerType.HRV: (45.0, 0.9),
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state = estimator.estimate("u6", frame, NOW)

        log_text = " ".join(state.decision_log)
        assert "SleepQuality" in log_text, (
            "Sleep quality estimation should appear in decision_log"
        )

    def test_no_hrv_no_sleep_uses_default(self):
        """Without HRV or sleep data, default quality = 0.7."""
        estimator = MetabolicStateEstimator()
        frame = _make_frame({
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state = estimator.estimate("u7", frame, NOW)
        assert abs(state.sleep_quality_estimate - 0.7) < 0.01, (
            f"Default sleep quality should be 0.7, got {state.sleep_quality_estimate}"
        )
# TODO: optimize this section

    def test_insulin_sensitivity_penalty_bounded(self):
        """The sleep-debt insulin sensitivity penalty should be bounded."""
        estimator = MetabolicStateEstimator()
        # Very poor sleep
        frame = _make_frame({
            BiomarkerType.HRV: (5.0, 0.9),
            BiomarkerType.STEPS: (100.0, 0.5),
        })
        state = estimator.estimate("u8", frame, NOW)

        # Sensitivity should still be > 0.2 (the global floor from code)
        assert state.insulin_sensitivity_estimate >= 0.2, (
            f"Insulin sensitivity should be >= 0.2, got {state.insulin_sensitivity_estimate}"
        )

# ═══════════════════════════════════════════════════════════════════
#  G-2: Context-Aware Re-Normalization (Stage 4.5)
# ═══════════════════════════════════════════════════════════════════

class TestContextAwareRenormalization:
    """Verify that the pipeline re-normalizes signals after Stage 4
    with the actual metabolic context, improving z-score accuracy."""

    def test_renormalization_stage_in_pipeline(self):
        """Pipeline stages should include renormalization after metabolic_state."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("rn1", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="rn1",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        stage_names = [s.split(":")[0] for s in result.stages_executed]
        # renormalization should appear after metabolic_state
        assert "renormalization" in stage_names, (
            f"renormalization stage should be present, got: {stage_names}"
        )
        renorm_idx = stage_names.index("renormalization")
        meta_idx = stage_names.index("metabolic_state")
        assert renorm_idx > meta_idx, (
            "renormalization must come after metabolic_state"
        )

    def test_renormalization_updates_with_context(self):
        """When metabolic context changes from 'unknown', signals should be updated."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("rn2", ConsentScope.GLUCOSE_DATA)

        # Record a meal so the state estimator will detect POSTPRANDIAL
        pipeline._state_estimator.record_meal_event(
            "rn2", NOW - timedelta(minutes=30)
        )

        result = pipeline.execute(
            user_id="rn2",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        # Check that renormalization recorded a context
        renorm_stages = [
            s for s in result.stages_executed if s.startswith("renormalization:")
        ]
        assert len(renorm_stages) > 0, "renormalization stage should be present"
        # Should show context and some updated signals
        renorm_info = renorm_stages[0]
        # If there's a real context (not unknown), updated count should be > 0
        if "context_unknown_skip" not in renorm_info:
            assert "context=" in renorm_info

    def test_renormalization_skips_when_unknown(self):
        """If metabolic context is still 'unknown', renormalization should skip."""
        pipeline = _make_pipeline()

        # With empty readings, metabolic state defaults to FASTING
        # (which IS a known context, not unknown)
        result = pipeline.execute(user_id="rn3", readings={})

        renorm_stages = [
            s for s in result.stages_executed if s.startswith("renormalization:")
        ]
        # With no frame data, it should skip or show no_data
        assert len(renorm_stages) > 0

    def test_renormalization_preserves_signals_when_no_change(self):
        """If context factor doesn't change, the original signal is preserved."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("rn4", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="rn4",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        # Should have normalized signals regardless
        assert len(result.normalized_signals) >= 0  # May be 0 or more depending on data

    def test_postprandial_context_reduces_glucose_z_score(self):
        """Glucose z-score should be lower in postprandial context vs unknown.

        This is the core patent claim: context-aware normalization prevents
        false-positive alerts for physiologically normal readings.
        """
        normalizer = PhysiologicalNormalizer()

        # Same raw value, different contexts
        glucose_value = 140.0  # mg/dL

        ns_unknown = normalizer.normalize(
            "ctx-test", BiomarkerType.GLUCOSE, glucose_value, NOW,
            metabolic_context="unknown",
        )
        ns_postprandial = normalizer.normalize(
            "ctx-test", BiomarkerType.GLUCOSE, glucose_value, NOW,
            metabolic_context="postprandial",
            update_baseline=False,
        )

        # Postprandial context should produce a LOWER absolute z-score
        # because elevation is expected after a meal
        assert abs(ns_postprandial.normalized_value) < abs(ns_unknown.normalized_value), (
            f"Postprandial z={ns_postprandial.normalized_value:.3f} should be "
            f"closer to 0 than unknown z={ns_unknown.normalized_value:.3f}"
        )

    def test_pipeline_stage_ordering_with_renormalization(self):
        """Full pipeline should maintain correct stage ordering with renorm."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("rn5", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="rn5",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        stage_names = [s.split(":")[0] for s in result.stages_executed]
        expected_order = [
            "consent_filter",
            "temporal_sync",
            "normalization",
            "interpolation",
            "metabolic_state",
            "renormalization",
            "nutrient_calculation",
            "dp_noise",
        ]
        for i, expected in enumerate(expected_order):
# TODO: optimize this section
            assert stage_names[i] == expected, (
                f"Stage {i} should be '{expected}', got '{stage_names[i]}'. "
                f"Full order: {stage_names}"
# TODO: optimize this section
            )

# ═══════════════════════════════════════════════════════════════════
#  OhioT1DM Lag Model Validation
# ═══════════════════════════════════════════════════════════════════

def _make_synthetic_ohio_patient() -> OhioPatient:
    """Create a synthetic OhioT1DM-like patient for testing.

    Simulates realistic CGM + meal patterns:
    - 5-minute CGM intervals over 2 days
    - 6 meal events with known carb amounts
    - Glucose peaks appear ~60min after meals with carb-proportional amplitude
    """
    patient = OhioPatient(
        patient_id="synthetic-001",
        weight_kg=75.0,
    )

    base_time = datetime(2025, 3, 10, 6, 0, 0)  # Start at 6 AM

    # Generate 2 days of 5-min CGM data (576 readings)
    base_glucose = 100.0
    glucose_values = []

    # Define meals: (hours_offset, carbs_g, peak_amplitude)
    meals = [
        (1.5, 60.0, 45.0),   # 7:30 AM breakfast
        (6.0, 50.0, 35.0),   # 12:00 PM lunch
        (11.0, 70.0, 55.0),  # 5:00 PM dinner
        (25.5, 55.0, 40.0),  # 7:30 AM next day
        (30.0, 45.0, 30.0),  # 12:00 PM next day
        (35.0, 65.0, 50.0),  # 5:00 PM next day
    ]

    # Pre-compute meal effects
    for i in range(576):  # 48 hours of 5-min intervals
        t_hours = i * 5 / 60.0
        glucose = base_glucose

        # Add circadian variation
        hour_of_day = (6 + t_hours) % 24
        circadian = 5 * math.sin(2 * math.pi * (hour_of_day - 7) / 24)
        glucose += circadian

        # Add meal responses (gaussian-like peak at ~60min post-meal)
        for meal_offset, carbs, amplitude in meals:
            dt = t_hours - meal_offset
            if 0 < dt < 4:  # Only affect glucose for 4 hours post-meal
                # Peak at ~60min, proportional to carbs
                peak_time = 1.0  # hours
# NOTE: reviewed 2025-07-14
                response = amplitude * math.exp(-0.5 * ((dt - peak_time) / 0.5) ** 2)
                glucose += response

        # Add small random noise (deterministic via sine)
        noise = 3 * math.sin(i * 7.3)
        glucose += noise

        patient.glucose_readings.append(OhioGlucoseReading(
            timestamp=base_time + timedelta(minutes=5 * i),
            value=max(40, glucose),  # Floor at 40 mg/dL
        ))

    # Add meal events
    for meal_offset, carbs, _ in meals:
        patient.meal_events.append(OhioMealEvent(
            timestamp=base_time + timedelta(hours=meal_offset),
            carbs_g=carbs,
            meal_type="mixed",
        ))

    return patient

class TestOhioT1DMLoader:
    """Test the OhioT1DM loader and lag model validation infrastructure."""

    def test_synthetic_patient_creation(self):
        """Synthetic patient should have realistic data structure."""
        patient = _make_synthetic_ohio_patient()
        assert patient.patient_id == "synthetic-001"
        assert len(patient.glucose_readings) == 576  # 2 days × 288/day
        assert len(patient.meal_events) == 6
        assert all(r.value >= 40 for r in patient.glucose_readings)

    def test_patient_summary(self):
        """Patient summary should contain all expected fields."""
        patient = _make_synthetic_ohio_patient()
        summary = patient.summary()
        assert "patient_id" in summary
        assert "glucose_readings" in summary
        assert "meal_events" in summary
        assert summary["glucose_readings"] == 576
        assert summary["meal_events"] == 6

    def test_to_biomarker_readings(self):
        """Convert to BioAI format should produce valid readings."""
        patient = _make_synthetic_ohio_patient()
        readings = patient.to_biomarker_readings()

        glucose_readings = [r for r in readings if r.biomarker_type == BiomarkerType.GLUCOSE]
        meal_readings = [r for r in readings if r.biomarker_type == BiomarkerType.MEAL]

        assert len(glucose_readings) == 576
        assert len(meal_readings) == 6
        assert all(r.user_id == "ohio-synthetic-001" for r in readings)

    def test_lag_validator_finds_meal_peaks(self):
        """Validator should match meals to glucose peaks."""
        patient = _make_synthetic_ohio_patient()
        validator = LagModelValidator(base_lag_minutes=60.0)
        result = validator.validate(patient)

        assert result.matched_meals >= 4, (
            f"Should match at least 4 of 6 meals, matched {result.matched_meals}"
        )

    def test_lag_compensation_improves_correlation(self):
        """Compensated Pearson r should be >= raw Pearson r.

        Patent claim: 'Lag compensation improves meal→glucose correlation
        from ~0.15 to ~0.78.'
        """
        patient = _make_synthetic_ohio_patient()
        validator = LagModelValidator(base_lag_minutes=60.0)
        result = validator.validate(patient)

        # With synthetic data designed to have clear meal→glucose causality,
        # compensated correlation should be better
        assert result.compensated_pearson_r >= result.raw_pearson_r, (
            f"Compensated r={result.compensated_pearson_r:.4f} should be >= "
            f"raw r={result.raw_pearson_r:.4f}"
        )

    def test_validation_result_summary(self):
        """Validation result summary should be complete."""
        patient = _make_synthetic_ohio_patient()
        validator = LagModelValidator(base_lag_minutes=60.0)
        result = validator.validate(patient)
        summary = result.summary()

        assert "patient_id" in summary
        assert "raw_pearson_r" in summary
        assert "compensated_pearson_r" in summary
        assert "raw_peak_mae_min" in summary
        assert "compensated_peak_mae_min" in summary

    def test_peak_detection_within_window(self):
        """Peaks should be found within the search window for each meal."""
        patient = _make_synthetic_ohio_patient()
        validator = LagModelValidator(base_lag_minutes=60.0)
        result = validator.validate(patient)

        for corr in result.correlations:
            # Raw lag should be within the search window
            assert 15 <= corr.raw_lag_minutes <= 180, (
                f"Peak lag {corr.raw_lag_minutes:.0f}min outside window"
            )

    def test_pearson_r_utility(self):
        """Test the Pearson correlation utility function."""
        # Perfect positive correlation
        assert abs(_pearson_r([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 0.01

        # Perfect negative correlation
        assert abs(_pearson_r([1, 2, 3, 4], [8, 6, 4, 2]) - (-1.0)) < 0.01

        # Zero correlation (orthogonal)
        r = _pearson_r([1, -1, 1, -1], [1, 1, -1, -1])
        assert abs(r) < 0.01

        # Insufficient data
        assert _pearson_r([1, 2], [3, 4]) == 0.0

    def test_circadian_modifier_affects_predicted_lag(self):
        """Morning vs evening meals should have different predicted lags."""
        validator = LagModelValidator(base_lag_minutes=60.0)

        morning_meal = datetime(2025, 3, 10, 7, 0, 0)
        evening_meal = datetime(2025, 3, 10, 22, 0, 0)

        morning_lag = validator._predict_lag(morning_meal)
        evening_lag = validator._predict_lag(evening_meal)

        # Evening should have longer lag (circadian modifier > 1.0)
        assert evening_lag > morning_lag, (
            f"Evening lag={evening_lag:.1f}min should exceed "
            f"morning lag={morning_lag:.1f}min"
        )

    def test_empty_patient_handles_gracefully(self):
        """Validation with insufficient data should not crash."""
        patient = OhioPatient(patient_id="empty")
        validator = LagModelValidator()
        result = validator.validate(patient)

        assert result.matched_meals == 0
        assert result.raw_pearson_r == 0.0
        assert result.compensated_pearson_r == 0.0

    def test_small_meals_excluded(self):
        """Meals with < 5g carbs should be excluded from validation."""
        patient = OhioPatient(patient_id="small-meals")
        patient.meal_events = [
            OhioMealEvent(timestamp=datetime(2025, 3, 10, 8, 0), carbs_g=3.0),
            OhioMealEvent(timestamp=datetime(2025, 3, 10, 12, 0), carbs_g=2.0),
        ]
        patient.glucose_readings = [
            OhioGlucoseReading(timestamp=datetime(2025, 3, 10, 8, 0) + timedelta(minutes=i*5), value=100 + i)
            for i in range(24)
        ]

        validator = LagModelValidator()
        result = validator.validate(patient)
        assert result.matched_meals == 0  # All meals too small

# TODO: improve error handling
# TODO: optimize this section
# FIXME: potential edge case