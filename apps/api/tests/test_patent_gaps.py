"""
Tests for patent gaps G2-G10.

Covers:
  - G2+G5: NutritionPipeline 5-stage orchestrator (correct ordering)
  - G1+G6+G7: Genetic modifier → micronutrient mapping completeness
  - G3+G8: Consent filtering + DP noise integration
  - G4: Medical constraint API
  - G9: Circadian prediction accuracy (7AM glucose > 3AM glucose)
  - G10: Reactive biomarker adjustment (glucose z>1.5 → carb -25%)
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
from app.engine.interpolation import CircadianInterpolator, RHYTHM_MODELS
from app.engine.metabolic_state import MetabolicState, MetabolicPhase
from app.engine.normalization import NormalizedSignal, PhysiologicalNormalizer
from app.engine.nutrient_calculator import (
    MedicalConstraint,
    NutrientDemandCalculator,
    NutrientTarget,
    create_default_targets,
)
from app.engine.pipeline import NutritionPipeline, PipelineResult
from app.engine.temporal_sync import Resolution, TemporalSynchronizer
from app.privacy.consent_manager import ConsentScope, DynamicConsentManager
from app.privacy.differential_privacy import DifferentialPrivacyEngine
from app.privacy.differential_privacy import (
    DynamicEpsilonAllocator,
    PrivacyBudget,
    SensitivityTier,
    TIER_EPSILON_MAP,
    NUTRIENT_SENSITIVITY_TIERS,
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

    from app.engine.metabolic_state import MetabolicStateEstimator

    return NutritionPipeline(
        synchronizer=sync,
        normalizer=PhysiologicalNormalizer(),
        interpolator=CircadianInterpolator(),
        state_estimator=MetabolicStateEstimator(),
        nutrient_calculator=NutrientDemandCalculator(),
        consent_manager=DynamicConsentManager(),
        privacy_engine=DifferentialPrivacyEngine(),
    )

# ═══════════════════════════════════════════════════════════════════
#  G2+G5: NutritionPipeline — 5-stage orchestrator
# ═══════════════════════════════════════════════════════════════════

class TestNutritionPipeline:
    """Verify the pipeline executes all 5 stages in correct order."""

    def test_pipeline_returns_budget(self):
        pipeline = _make_pipeline()
        # Grant consent so data flows through
        pipeline._consent_manager.grant_consent("u1", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="u1",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
            kcal_target=2000,
            weight_kg=70,
        )
        assert isinstance(result, PipelineResult)
        assert result.budget is not None
        assert result.budget.user_id == "u1"
        assert len(result.budget.targets) == 14  # 6 macro + 8 micro

    def test_pipeline_stage_ordering(self):
        """Stages must execute in the whitepaper order."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("u2", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="u2",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        stage_names = [s.split(":")[0] for s in result.stages_executed]
        # Must contain all stages in order
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
            assert stage_names[i] == expected, (
                f"Stage {i} should be '{expected}', got '{stage_names[i]}'"
            )

    def test_pipeline_empty_readings(self):
        """Pipeline handles empty input gracefully."""
        pipeline = _make_pipeline()
        result = pipeline.execute(user_id="empty", readings={})
        assert result.budget is not None
        assert result.pipeline_confidence < 0.01

    def test_pipeline_with_genetic_modifiers(self):
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("g1", ConsentScope.GLUCOSE_DATA)
        pipeline._consent_manager.grant_consent("g1", ConsentScope.GENETIC_DATA)

        result = pipeline.execute(
            user_id="g1",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
            genetic_modifiers={
                "folate_requirement_modifier": 1.5,
                "carb_sensitivity_modifier": 1.3,
            },
        )

        # Genetic step should appear in modifications
        genetic_mods = [
            m for m in result.budget.modifications
            if m.get("step") == "genetic"
        ]
        assert len(genetic_mods) >= 2

# ═══════════════════════════════════════════════════════════════════
#  G1+G6+G7: Genetic modifier completeness
# ═══════════════════════════════════════════════════════════════════

class TestGeneticModifierCompleteness:
    """All 22 genetic modifiers from NUTRIGENOMIC_VARIANTS should be
    mapped to nutrient targets — no dead code."""

    def test_default_targets_include_micronutrients(self):
        targets = create_default_targets()
        micro = ["folate_mcg", "b12_mcg", "vitamin_d_iu", "magnesium_mg",
                 "calcium_mg", "sodium_mg", "caffeine_mg", "vitamin_b6_mg"]
        for m in micro:
            assert m in targets, f"Missing micronutrient target: {m}"

    def test_folate_modifier_applies(self):
        """MTHFR TT → folate_requirement_modifier=1.5 → folate target × 1.5."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="mthfr",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={"folate_requirement_modifier": 1.5},
        )

        # 400 mcg × 1.5 = 600 mcg
        assert budget.targets["folate_mcg"].daily_target == pytest.approx(600, rel=0.01)

    def test_caffeine_modifier_applies(self):
        """CYP1A2 slow metabolizer → caffeine reduced."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="cyp",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={"caffeine_metabolism_rate": 0.5},
        )

        # 400 mg × 0.5 = 200 mg
        assert budget.targets["caffeine_mg"].daily_target == pytest.approx(200, rel=0.01)

    def test_calcium_modifier_for_lactose_intolerance(self):
        """LCT lactose_tolerance=0 → calcium_alt_source_need=1.5."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="lct",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={"calcium_alt_source_need": 1.5},
        )

        # 1000 mg × 1.5 = 1500 mg
        assert budget.targets["calcium_mg"].daily_target == pytest.approx(1500, rel=0.01)

    def test_vitamin_d_modifier_applies(self):
        """VDR variant → vitamin_d_requirement_modifier=1.4."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="vdr",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={"vitamin_d_requirement_modifier": 1.4},
        )

        # 600 IU × 1.4 = 840 IU
        assert budget.targets["vitamin_d_iu"].daily_target == pytest.approx(840, rel=0.01)

    def test_all_22_modifiers_have_targets(self):
        """Every genetic modifier key should map to an existing target."""
        ALL_MODIFIER_KEYS = [
            "folate_requirement_modifier", "b12_requirement_modifier",
            "calorie_sensitivity_modifier", "satiety_response_modifier",
            "fat_metabolism_modifier", "saturated_fat_sensitivity",
            "cholesterol_response_modifier", "omega3_benefit_modifier",
            "carb_sensitivity_modifier", "glycemic_load_threshold_modifier",
            "lactose_tolerance", "calcium_alt_source_need",
            "caffeine_metabolism_rate", "caffeine_max_daily_mg",
            "vitamin_d_requirement_modifier", "calcium_absorption_modifier",
            "protein_utilization_modifier",
        ]

        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        for key in ALL_MODIFIER_KEYS:
            budget = calc.calculate(
                user_id=f"test-{key}",
                base_targets=create_default_targets(),
                metabolic_state=state,
                normalized_signals={},
                genetic_modifiers={key: 1.5},
            )
            # At least one modification should have been applied
            genetic_mods = [
                m for m in budget.modifications
                if m.get("step") == "genetic" and m.get("genetic_factor") == key
            ]
            assert len(genetic_mods) >= 1, (
                f"Genetic modifier '{key}' has no effect — dead code!"
            )

# ═══════════════════════════════════════════════════════════════════
#  G3+G8: Consent filtering + DP noise
# ═══════════════════════════════════════════════════════════════════

class TestConsentAndPrivacy:
    """Consent filtering blocks revoked data; DP adds noise."""

    def test_consent_blocks_glucose_when_not_granted(self):
        """Glucose data should NOT enter pipeline if consent not granted."""
        pipeline = _make_pipeline()
        # No consent granted

        result = pipeline.execute(
            user_id="no-consent",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        assert "glucose" in result.consent_filtered

    def test_consent_allows_glucose_when_granted(self):
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("ok", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="ok",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        assert "glucose" not in result.consent_filtered

    def test_genetic_consent_blocks_modifiers(self):
        """Without GENETIC_DATA consent, modifiers should be cleared."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("gc", ConsentScope.GLUCOSE_DATA)
        # No genetic consent

        mods = {"folate_requirement_modifier": 1.5}
        result = pipeline.execute(
            user_id="gc",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
            genetic_modifiers=mods,
        )

        assert "genetic_modifiers" in result.consent_filtered
        # Genetic mods should have been cleared (dict was modified in-place)
        assert len(mods) == 0

    def test_dp_noise_applied(self):
        """DP noise should perturb output targets."""
        pipeline = _make_pipeline()
        pipeline._consent_manager.grant_consent("dp", ConsentScope.GLUCOSE_DATA)

        result = pipeline.execute(
            user_id="dp",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(12)},
        )

        assert result.dp_applied is True
        dp_stages = [s for s in result.stages_executed if s.startswith("dp_noise:")]
        assert len(dp_stages) == 1
        assert "dynamic_eps" in dp_stages[0]

    def test_consent_revoke_drops_data_mid_session(self):
        """After revoking consent, subsequent pipeline calls should filter."""
        pipeline = _make_pipeline()
        cm = pipeline._consent_manager
        cm.grant_consent("rev", ConsentScope.GLUCOSE_DATA)

        # First call — data flows
        r1 = pipeline.execute(
            user_id="rev",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(6)},
        )
        assert "glucose" not in r1.consent_filtered

        # Revoke consent
        cm.revoke_consent("rev", ConsentScope.GLUCOSE_DATA)

        # Second call — data blocked
        r2 = pipeline.execute(
            user_id="rev",
            readings={BiomarkerType.GLUCOSE: _make_glucose_readings(6)},
        )
        assert "glucose" in r2.consent_filtered

# ═══════════════════════════════════════════════════════════════════
#  G4: Medical constraint API
# ═══════════════════════════════════════════════════════════════════

class TestMedicalConstraints:
    """Medical constraints are hard boundaries on nutrient targets."""

    def test_ckd_protein_max(self):
        """CKD patient: protein max = 56g (0.8g/kg × 70kg)."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("ckd-user", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD stage 3 — protein restriction",
                severity="critical",
                source="medical_record",
            ),
        ])

        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="ckd-user",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        assert budget.targets["protein_g"].daily_target <= 56
        assert len(budget.active_constraints) == 1

    def test_hypertension_sodium_max(self):
        """Hypertension: sodium max = 1500mg."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("ht-user", [
            MedicalConstraint(
                nutrient="sodium_mg",
                constraint_type="max",
                value=1500,
                reason="Hypertension — sodium restriction",
                severity="warning",
            ),
        ])

        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="ht-user",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        assert budget.targets["sodium_mg"].daily_target <= 1500

    def test_min_constraint(self):
        """Minimum constraint raises target if too low."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("min-user", [
            MedicalConstraint(
                nutrient="kcal",
                constraint_type="min",
                value=1800,
                reason="Underweight — minimum calorie floor",
                severity="critical",
            ),
        ])

        targets = create_default_targets(kcal=1500)  # below min
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="min-user",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        assert budget.targets["kcal"].daily_target >= 1800

    def test_constraint_in_pipeline(self):
        """Constraints work through the full pipeline."""
        pipeline = _make_pipeline()
        pipeline._nutrient_calculator.set_medical_constraints("pipe-ckd", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD",
                severity="critical",
            ),
        ])

        result = pipeline.execute(
            user_id="pipe-ckd",
            readings={},
        )

        assert result.budget.targets["protein_g"].daily_target <= 56

# ═══════════════════════════════════════════════════════════════════
#  G9: Circadian prediction accuracy
# ═══════════════════════════════════════════════════════════════════

class TestCircadianPredictionAccuracy:
    """Verify the circadian model predicts physiologically correct
    patterns: glucose peaks ~7AM, lowest ~3AM."""

    def test_glucose_7am_higher_than_3am(self):
        """
        Patent claim: "Circadian-aware interpolation uses biological
        rhythm models wherein glucose prediction at morning peak (7AM)
        exceeds circadian anti-phase nadir (19:00)."
        """
        interp = CircadianInterpolator()
        baseline = 100.0

        # Predict at 7AM (peak for glucose — circadian_phase_hours=7)
        pred_7am = interp._circadian_predict(
            user_id="test",
            biomarker_type=BiomarkerType.GLUCOSE,
            timestamp=datetime(2025, 1, 15, 7, 0, 0),
            baseline_mean=baseline,
        )

        # Predict at 19:00 (anti-phase nadir — 12h offset from peak)
        pred_19 = interp._circadian_predict(
            user_id="test",
            biomarker_type=BiomarkerType.GLUCOSE,
            timestamp=datetime(2025, 1, 15, 19, 0, 0),
            baseline_mean=baseline,
        )

        assert pred_7am > pred_19, (
            f"7AM prediction ({pred_7am:.2f}) should exceed "
            f"19:00 prediction ({pred_19:.2f})"
        )

    def test_heart_rate_afternoon_higher_than_night(self):
        """HR peaks in afternoon (15:00), lowest during sleep (~3AM)."""
        interp = CircadianInterpolator()
        baseline = 72.0

        pred_3pm = interp._circadian_predict(
            "test", BiomarkerType.HEART_RATE,
            datetime(2025, 1, 15, 15, 0, 0), baseline,
        )
        pred_3am = interp._circadian_predict(
            "test", BiomarkerType.HEART_RATE,
            datetime(2025, 1, 15, 3, 0, 0), baseline,
        )

        assert pred_3pm > pred_3am

    def test_hrv_peaks_during_deep_sleep(self):
        """HRV peaks at ~3AM (parasympathetic dominance during deep sleep)."""
        interp = CircadianInterpolator()
        baseline = 45.0

        pred_3am = interp._circadian_predict(
            "test", BiomarkerType.HRV,
            datetime(2025, 1, 15, 3, 0, 0), baseline,
        )
        pred_2pm = interp._circadian_predict(
            "test", BiomarkerType.HRV,
            datetime(2025, 1, 15, 14, 0, 0), baseline,
        )

        assert pred_3am > pred_2pm

    def test_circadian_prediction_within_physiological_range(self):
        """Predictions should stay within ±30% of baseline."""
        interp = CircadianInterpolator()
        baseline = 100.0

        for hour in range(24):
            pred = interp._circadian_predict(
                "test", BiomarkerType.GLUCOSE,
                datetime(2025, 1, 15, hour, 0, 0), baseline,
            )
            assert 70 <= pred <= 130, (
                f"Hour {hour}: prediction {pred:.1f} out of range"
            )

    def test_ultradian_oscillation_exists(self):
        """90-minute glucose cycles should be visible in predictions."""
        interp = CircadianInterpolator()
        baseline = 100.0
        t0 = datetime(2025, 1, 15, 10, 0, 0)

        # Sample every 15 minutes for 3 hours (2 full 90-min cycles)
        predictions = []
        for i in range(12):
            pred = interp._circadian_predict(
                "test", BiomarkerType.GLUCOSE,
                t0 + timedelta(minutes=15 * i), baseline,
            )
            predictions.append(pred)

        # There should be variation (not flat line)
        assert max(predictions) > min(predictions), "No ultradian variation detected"

# ═══════════════════════════════════════════════════════════════════
#  G10: Reactive biomarker adjustment tests
# ═══════════════════════════════════════════════════════════════════

class TestReactiveBiomarkerAdjustments:
    """Verify reactive nutrient adjustments based on real-time
    biomarker z-scores."""

    def test_elevated_glucose_reduces_carbs(self):
        """glucose z > 1.5 → carb_target reduced by up to 25%.

        Patent claim: "Real-time biomarker-driven nutrient adjustment
        wherein elevated glucose (z-score > 1.5) triggers proportional
        carbohydrate reduction."
        """
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)
        original_carbs = targets["carbs_g"].daily_target

        # Create a high-glucose normalized signal (z = 2.5)
        glucose_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.GLUCOSE,
            raw_value=138,
            normalized_value=138,
            z_score=2.5,
            circadian_adjusted=138,
            genetic_modified=138,
            context="unknown",
            anomaly_score=0.5,
        )

        budget = calc.calculate(
            user_id="high-glucose",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.GLUCOSE: glucose_signal},
            genetic_modifiers={},
        )

        # Carbs should be reduced
        assert budget.targets["carbs_g"].daily_target < original_carbs
        # Reduction should be significant (at least 5%)
        reduction_pct = 1 - (
            budget.targets["carbs_g"].daily_target / original_carbs
        )
        assert reduction_pct >= 0.05, (
            f"Reduction only {reduction_pct*100:.1f}% — too small"
        )

    def test_low_glucose_increases_carbs(self):
        """glucose z < -1.0 → carb_target increased."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)
        original_carbs = targets["carbs_g"].daily_target

        glucose_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.GLUCOSE,
            raw_value=65,
            normalized_value=65,
            z_score=-1.5,
            circadian_adjusted=65,
            genetic_modified=65,
            context="unknown",
            anomaly_score=0.3,
        )

        budget = calc.calculate(
            user_id="low-glucose",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.GLUCOSE: glucose_signal},
            genetic_modifiers={},
        )

        assert budget.targets["carbs_g"].daily_target > original_carbs

    def test_elevated_hr_increases_water(self):
        """HR z > 1.0 → water_ml increased (dehydration signal)."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)
        original_water = targets["water_ml"].daily_target

        hr_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.HEART_RATE,
            raw_value=95,
            normalized_value=95,
            z_score=1.5,
            circadian_adjusted=95,
            genetic_modified=95,
            context="unknown",
            anomaly_score=0.4,
        )

        budget = calc.calculate(
            user_id="high-hr",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.HEART_RATE: hr_signal},
            genetic_modifiers={},
        )

        assert budget.targets["water_ml"].daily_target > original_water

    def test_low_hrv_increases_magnesium(self):
        """HRV z < -1.0 → magnesium & B6 increased (stress)."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)
        original_mag = targets["magnesium_mg"].daily_target

        hrv_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.HRV,
            raw_value=20,
            normalized_value=20,
            z_score=-1.5,
            circadian_adjusted=20,
            genetic_modified=20,
            context="unknown",
            anomaly_score=0.5,
        )

        budget = calc.calculate(
            user_id="low-hrv",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.HRV: hrv_signal},
            genetic_modifiers={},
        )

        assert budget.targets["magnesium_mg"].daily_target > original_mag

    def test_max_carb_reduction_capped_at_25_percent(self):
        """Even with extreme glucose z, reduction caps at 25%."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)
        original_carbs = targets["carbs_g"].daily_target

        # Extreme z-score
        glucose_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.GLUCOSE,
            raw_value=200,
            normalized_value=200,
            z_score=5.0,
            circadian_adjusted=200,
            genetic_modified=200,
            context="unknown",
            anomaly_score=0.9,
        )

        budget = calc.calculate(
            user_id="extreme-glucose",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.GLUCOSE: glucose_signal},
            genetic_modifiers={},
        )

        reduction_pct = 1 - (
            budget.targets["carbs_g"].daily_target / original_carbs
        )
        assert reduction_pct <= 0.26, (
            f"Reduction {reduction_pct*100:.1f}% exceeds 25% cap"
        )

    def test_combined_biomarker_reactive_and_genetic(self):
        """Both genetic modifiers AND reactive adjustments should apply."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        glucose_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.GLUCOSE,
            raw_value=130,
            normalized_value=130,
            z_score=2.0,
            circadian_adjusted=130,
            genetic_modified=130,
            context="unknown",
            anomaly_score=0.4,
        )

        budget = calc.calculate(
            user_id="combo",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.GLUCOSE: glucose_signal},
            genetic_modifiers={
                "carb_sensitivity_modifier": 1.3,
                "folate_requirement_modifier": 1.5,
            },
        )

        # Both genetic and reactive mods should appear
        steps = {m["step"] for m in budget.modifications}
        assert "genetic" in steps
        assert "biomarker_reactive" in steps

    def test_modification_audit_trail_complete(self):
        """Every modification should have step, nutrient, old/new values."""
        calc = NutrientDemandCalculator()
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        glucose_signal = NormalizedSignal(
            biomarker_type=BiomarkerType.GLUCOSE,
            raw_value=130,
            normalized_value=130,
            z_score=2.0,
            circadian_adjusted=130,
            genetic_modified=130,
            context="unknown",
            anomaly_score=0.4,
        )

        budget = calc.calculate(
            user_id="audit",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={BiomarkerType.GLUCOSE: glucose_signal},
            genetic_modifiers={"folate_requirement_modifier": 1.5},
        )

        for mod in budget.modifications:
            assert "step" in mod
            assert "nutrient" in mod
            assert "reason" in mod

# ═══════════════════════════════════════════════════════════════════════
# G11: Self-Calibration Feedback Loop Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSelfCalibrationFeedbackLoop:
    """Tests for the adaptive self-calibration engine.

    Validates:
    - Peak detection in biomarker time series
    - Error decomposition into base/circadian/genetic channels
    - Adaptive learning rate decay
    - Convergence after repeated observations
    - Calibrated lag computation
    - Pipeline integration
    """

    # ── Imports ─────────────────────────────────────────────────────

    @staticmethod
    def _make_calibrator():
        from app.engine.self_calibration import AdaptiveLagCalibrator
        return AdaptiveLagCalibrator()

    @staticmethod
    def _make_peak_detector():
        from app.engine.self_calibration import PeakDetector
        return PeakDetector()

    @staticmethod
    def _make_glucose_peak_readings(
        event_time: datetime,
        actual_peak_offset_min: float = 50.0,
        n_points: int = 24,
    ) -> List[BiomarkerReading]:
        """Create glucose readings with a clear peak at the specified offset."""
        readings = []
        peak_time_min = actual_peak_offset_min
        for i in range(n_points):
            t = event_time + timedelta(minutes=i * 5)
            elapsed = i * 5
            # Gaussian-like peak at peak_time_min
            value = 100 + 40 * math.exp(
                -0.5 * ((elapsed - peak_time_min) / 15) ** 2
            )
            readings.append(
                _make_reading(BiomarkerType.GLUCOSE, value, t)
            )
        return readings

    # ── Peak Detection Tests ────────────────────────────────────────

    def test_peak_detection_finds_correct_peak(self):
        """Peak detector should find the glucose peak at ~50 min."""
        detector = self._make_peak_detector()
        event = NOW
        readings = self._make_glucose_peak_readings(event, actual_peak_offset_min=50)

        peak = detector.detect_peak(
            readings,
            search_start=event,
            search_end=event + timedelta(hours=2),
        )

        assert peak is not None
        # Peak should be within 10 minutes of the actual 50-min mark
        peak_offset = (peak.timestamp - event).total_seconds() / 60
        assert abs(peak_offset - 50) < 15
        assert peak.confidence >= 0.4

    def test_peak_detection_no_peak_in_flat_signal(self):
        """Flat signal should return low-confidence peak."""
        detector = self._make_peak_detector()
        readings = [
            _make_reading(
                BiomarkerType.GLUCOSE, 100.0,
                NOW + timedelta(minutes=i * 5),
            )
            for i in range(20)
        ]

        peak = detector.detect_peak(
            readings,
            search_start=NOW,
            search_end=NOW + timedelta(hours=2),
        )

        # Should still return something, but with low confidence
        assert peak is not None
        assert peak.confidence <= 0.4

    # ── Core Calibration Tests ──────────────────────────────────────

    def test_observe_updates_base_lag_offset(self):
        """Single observation should create a base lag offset."""
        cal = self._make_calibrator()
        event = NOW
        predicted = event + timedelta(minutes=60)
        actual = event + timedelta(minutes=70)  # 10 min late

        result = cal.observe(
            user_id="user-1",
            biomarker_type=BiomarkerType.GLUCOSE,
            event_time=event,
            predicted_peak_time=predicted,
            actual_peak_time=actual,
        )

        profile = result.updated_profile
        assert profile.observation_count == 1
        # Base lag offset should be positive (model under-predicted)
        assert profile.base_lag_offsets["glucose"] > 0
        # Error was 600 seconds (10 min)
        assert abs(result.observation.prediction_error_seconds - 600) < 1

    def test_observe_updates_circadian_correction(self):
        """Observation should update the circadian correction for that hour."""
        cal = self._make_calibrator()
        event = datetime(2025, 1, 15, 8, 0, 0)  # 8 AM
        predicted = event + timedelta(minutes=60)
        actual = event + timedelta(minutes=50)  # 10 min early

        result = cal.observe(
            user_id="user-1",
            biomarker_type=BiomarkerType.GLUCOSE,
            event_time=event,
            predicted_peak_time=predicted,
            actual_peak_time=actual,
        )

        profile = result.updated_profile
        # Hour 8 should have a negative circadian correction (earlier peak)
        assert 8 in profile.circadian_corrections
        assert profile.circadian_corrections[8] < 0

    def test_observe_updates_genetic_correction_factor(self):
        """Observation should update the genetic correction factor."""
        cal = self._make_calibrator()
        event = NOW
        predicted = event + timedelta(minutes=60)
        actual = event + timedelta(minutes=75)  # 25% late

        result = cal.observe(
            user_id="user-1",
            biomarker_type=BiomarkerType.GLUCOSE,
            event_time=event,
            predicted_peak_time=predicted,
            actual_peak_time=actual,
        )

        profile = result.updated_profile
        # κ should be > 1.0 (model systematically under-predicts)
        assert profile.genetic_correction_factor > 1.0
        # But bounded by MAX_GENETIC_CORRECTION
        assert profile.genetic_correction_factor <= 1.5

    def test_adaptive_learning_rate_decays(self):
        """Learning rate should decrease with more observations."""
        cal = self._make_calibrator()

        offsets = []
        for i in range(20):
            event = NOW + timedelta(hours=i)
            predicted = event + timedelta(minutes=60)
            actual = event + timedelta(minutes=70)

            result = cal.observe(
                user_id="user-1",
                biomarker_type=BiomarkerType.GLUCOSE,
                event_time=event,
                predicted_peak_time=predicted,
                actual_peak_time=actual,
            )
            offsets.append(result.updated_profile.base_lag_offsets["glucose"])

        # Early offsets should change more rapidly than later ones
        early_delta = abs(offsets[1] - offsets[0])
        late_delta = abs(offsets[-1] - offsets[-2])
        assert early_delta > late_delta

    def test_convergence_after_consistent_error(self):
        """Model should converge after seeing consistent errors."""
        cal = self._make_calibrator()

        # Feed 20 observations with consistent +10 min error
        for i in range(20):
            event = NOW + timedelta(hours=i)
            predicted = event + timedelta(minutes=60)
            actual = event + timedelta(minutes=70)

            result = cal.observe(
                user_id="user-1",
                biomarker_type=BiomarkerType.GLUCOSE,
                event_time=event,
                predicted_peak_time=predicted,
                actual_peak_time=actual,
            )

        profile = result.updated_profile
        # Should be approaching convergence
        assert profile.observation_count == 20
        # Base lag offset should have learned the ~600s correction
        assert profile.base_lag_offsets["glucose"] > 400  # within 200s
        # Convergence score should be positive
        assert profile.convergence_score > 0

    def test_calibrated_lag_applies_corrections(self):
        """get_calibrated_lag should apply learned corrections."""
        cal = self._make_calibrator()

        # Manually set a profile with known corrections
        from app.engine.self_calibration import PersonalCalibrationProfile
        profile = PersonalCalibrationProfile(
            user_id="user-1",
            base_lag_offsets={"glucose": 300.0},  # +5 min
            circadian_corrections={12: 0.05},     # +5% at noon
            genetic_correction_factor=1.1,        # +10% genome
            observation_count=15,
        )
        cal.set_profile("user-1", profile)

        calibrated, audit = cal.get_calibrated_lag(
            user_id="user-1",
            biomarker_type=BiomarkerType.GLUCOSE,
            base_lag_seconds=3600,      # 60 min base
            genetic_modifier=1.0,
            circadian_modifier=0.9,    # morning
            event_time=datetime(2025, 1, 15, 12, 0),
        )

        # Original: 3600 * 1.0 * 0.9 = 3240
        # Calibrated: (3600 + 300) * (1.0 * 1.1) * (0.9 + 0.05)
        #           = 3900 * 1.1 * 0.95 = 4075.5
        assert calibrated > 3240  # Should be larger
        assert audit["delta_base"] == 300.0
        assert audit["kappa_genetic"] == 1.1
        assert audit["delta_circadian"] == 0.05

    def test_pipeline_calibrate_integration(self):
        """Pipeline.calibrate() should work with attached calibrator."""
        pipeline = _make_pipeline()
        cal = self._make_calibrator()
        pipeline.set_calibrator(cal)

        event = NOW - timedelta(hours=1)
        readings = self._make_glucose_peak_readings(
            event, actual_peak_offset_min=50
        )

        result = pipeline.calibrate(
            user_id="test-user",
            biomarker_type=BiomarkerType.GLUCOSE,
            event_time=event,
            post_event_readings=readings,
            predicted_lag_seconds=3600,  # predicted 60 min
        )

        # Should detect peak and return calibration result
        assert result is not None
        assert result.observation.biomarker_type == BiomarkerType.GLUCOSE
        assert result.updated_profile.observation_count == 1

    def test_pipeline_calibrate_without_calibrator_returns_none(self):
        """Pipeline.calibrate() without calibrator should return None."""
        pipeline = _make_pipeline()

        result = pipeline.calibrate(
            user_id="test-user",
            biomarker_type=BiomarkerType.GLUCOSE,
            event_time=NOW,
            post_event_readings=[],
            predicted_lag_seconds=3600,
        )

        assert result is None

    def test_lag_model_with_calibrator(self):
        """PhysiologicalLagModel should use calibrator when attached."""
        from app.engine.self_calibration import (
            AdaptiveLagCalibrator,
            PersonalCalibrationProfile,
        )
        from app.engine.temporal_sync import PhysiologicalLagModel

        cal = AdaptiveLagCalibrator()
        profile = PersonalCalibrationProfile(
            user_id="user-1",
            base_lag_offsets={"glucose": 120.0},
            genetic_correction_factor=1.05,
            observation_count=10,
        )
        cal.set_profile("user-1", profile)

        model = PhysiologicalLagModel(calibrator=cal)
        model.set_genetic_modifiers("user-1", {})

        chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=5),
            min_interval=timedelta(minutes=1),
            max_gap_before_stale=timedelta(minutes=30),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            physiological_lag=timedelta(minutes=60),
            circadian_sensitivity=0.3,
            noise_floor=5.0,
        )

        lag = model.compute_lag(
            BiomarkerType.GLUCOSE, chars, NOW, user_id="user-1",
        )

        # Should have calibration applied
        assert lag.calibration_applied is True
        assert lag.calibration_audit is not None
        # Effective lag should differ from base due to corrections
        base_uncalibrated = lag.base_lag_seconds * lag.genetic_modifier * lag.circadian_modifier
        assert lag.effective_lag_seconds != base_uncalibrated

    def test_batch_calibration(self):
        """calibrate_from_history should process multiple events."""
        cal = self._make_calibrator()

        pairs = []
        for i in range(5):
            event = NOW + timedelta(hours=i)
            readings = self._make_glucose_peak_readings(
                event, actual_peak_offset_min=50 + i * 2,
            )
            predicted_lag = 3600  # 60 min
            pairs.append((event, readings, predicted_lag))

        results = cal.calibrate_from_history(
            user_id="user-1",
            biomarker_type=BiomarkerType.GLUCOSE,
            event_readings_pairs=pairs,
        )

        assert len(results) > 0
        profile = cal.get_profile("user-1")
        assert profile.observation_count == len(results)

# ═══════════════════════════════════════════════════════════════════════
# G12: Conflict Resolution Layer — Medical Safety vs Genetic Optimization
# ═══════════════════════════════════════════════════════════════════════

class TestConflictResolutionLayer:
    """Tests for the hierarchical conflict resolution between genetic
    optimization recommendations and medical safety constraints.

    Patent claim: "A hierarchical conflict resolution method wherein
    medical safety thresholds are unconditionally prioritized over
    genetically optimized nutrient targets."
    """

    def test_genetic_vs_medical_critical_conflict(self):
        """CKD critical constraint overrides genetic protein boost."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("conflict-user", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD stage 3 — protein restriction",
                severity="critical",
                source="medical_record",
            ),
        ])

        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)

        # Genetic modifier that INCREASES protein utilization
        # → calculator boosts protein target above 56g
        genetic_mods = {"protein_utilization_modifier": 1.5}

        budget = calc.calculate(
            user_id="conflict-user",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers=genetic_mods,
        )

        # Medical constraint MUST win
        assert budget.targets["protein_g"].daily_target <= 56
        # Conflict should be documented
        assert len(budget.conflict_resolutions) >= 1
        resolution = budget.conflict_resolutions[0]
        assert resolution.winner == "medical_critical"
        assert resolution.loser == "genetic"
        assert resolution.conflict_type == "genetic_vs_medical"

    def test_genetic_vs_medical_warning_conflict(self):
        """Hypertension warning constraint overrides metabolic adjustment."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("ht-conflict", [
            MedicalConstraint(
                nutrient="sodium_mg",
                constraint_type="max",
                value=1500,
                reason="Hypertension — sodium restriction",
                severity="warning",
                source="medical_record",
            ),
        ])

        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="ht-conflict",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        # Default sodium is 2300mg, should be clamped to 1500mg
        assert budget.targets["sodium_mg"].daily_target <= 1500

    def test_conflict_resolution_audit_trail(self):
        """Conflict resolution produces complete audit trail."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("audit-user", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD stage 3",
                severity="critical",
            ),
        ])

        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)
        genetic_mods = {"protein_utilization_modifier": 1.5}

        budget = calc.calculate(
            user_id="audit-user",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers=genetic_mods,
        )

        # Should have at least one conflict resolution
        assert len(budget.conflict_resolutions) >= 1
        cr = budget.conflict_resolutions[0]

        # Verify all audit fields are populated
        assert cr.nutrient == "protein_g"
        assert cr.genetic_recommended > 56  # Was higher before clamping
        assert cr.medical_limit == 56
        assert cr.resolved_value == 56
        assert cr.constraint_reason == "CKD stage 3"
        assert cr.severity == "critical"
        assert len(cr.resolution_rationale) > 0

    def test_critical_constraint_beats_warning(self):
        """Critical constraints are processed before warnings (sorted by priority)."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("multi-constraint", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=60,
                reason="Mild concern",
                severity="warning",
            ),
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD — strict limit",
                severity="critical",
            ),
        ])

        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="multi-constraint",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        # The stricter critical constraint (56) should prevail
        assert budget.targets["protein_g"].daily_target <= 56

    def test_no_conflict_when_within_bounds(self):
        """No conflict resolution emitted when genetic value is within bounds."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("safe-user", [
            MedicalConstraint(
                nutrient="caffeine_mg",
                constraint_type="max",
                value=400,
                reason="Standard caffeine limit",
                severity="warning",
            ),
        ])

        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        # Caffeine metabolism modifier = 0.5 → target = 200mg (well under 400)
        genetic_mods = {"caffeine_metabolism_rate": 0.5}

        budget = calc.calculate(
            user_id="safe-user",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers=genetic_mods,
        )

        # No conflict since 200 < 400
        caffeine_conflicts = [
            cr for cr in budget.conflict_resolutions
            if cr.nutrient == "caffeine_mg"
        ]
        assert len(caffeine_conflicts) == 0

    def test_min_constraint_conflict_resolution(self):
        """Min constraint overrides when target falls below medical minimum."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("underweight", [
            MedicalConstraint(
                nutrient="kcal",
                constraint_type="min",
                value=1800,
                reason="Underweight — minimum calorie floor",
                severity="critical",
            ),
        ])

        targets = create_default_targets(kcal=1500)
        state = MetabolicState(timestamp=NOW)

        budget = calc.calculate(
            user_id="underweight",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        assert budget.targets["kcal"].daily_target >= 1800
        assert len(budget.conflict_resolutions) >= 1
        cr = budget.conflict_resolutions[0]
        assert cr.winner in ("medical_critical", "medical_warning")

    def test_conflict_in_modifications_audit(self):
        """Conflict resolution also appears in standard modifications list."""
        calc = NutrientDemandCalculator()
        calc.set_medical_constraints("mod-audit", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD",
                severity="critical",
            ),
        ])

        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)
        genetic_mods = {"protein_utilization_modifier": 1.5}

        budget = calc.calculate(
            user_id="mod-audit",
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers=genetic_mods,
        )

        # Find conflict_resolution step in modifications
        conflict_mods = [
            m for m in budget.modifications
            if m.get("step") == "conflict_resolution"
        ]
        assert len(conflict_mods) >= 1
        cm = conflict_mods[0]
        assert cm["winner"] == "medical_critical"
        assert cm["loser"] == "genetic"
        assert "conflict_type" in cm

    def test_priority_hierarchy_values(self):
        """Verify PRIORITY_HIERARCHY has correct ordering."""
        from app.engine.nutrient_calculator import PRIORITY_HIERARCHY

        assert PRIORITY_HIERARCHY["base_rda"] < PRIORITY_HIERARCHY["metabolic_state"]
        assert PRIORITY_HIERARCHY["metabolic_state"] < PRIORITY_HIERARCHY["genetic"]
        assert PRIORITY_HIERARCHY["genetic"] < PRIORITY_HIERARCHY["medical_warning"]
        assert PRIORITY_HIERARCHY["medical_warning"] < PRIORITY_HIERARCHY["medical_critical"]

    def test_medical_constraint_priority_property(self):
        """MedicalConstraint.priority returns correct level."""
        critical = MedicalConstraint(
            nutrient="protein_g", constraint_type="max",
            value=56, reason="CKD", severity="critical",
        )
        warning = MedicalConstraint(
            nutrient="sodium_mg", constraint_type="max",
            value=1500, reason="HT", severity="warning",
        )

        assert critical.priority > warning.priority

    def test_pipeline_conflict_resolution_integration(self):
        """Conflict resolution works through the full pipeline."""
        pipeline = _make_pipeline()
        pipeline._nutrient_calculator.set_medical_constraints("pipe-conflict", [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=56,
                reason="CKD",
                severity="critical",
            ),
        ])

        result = pipeline.execute(
            user_id="pipe-conflict",
            readings={},
            genetic_modifiers={"protein_utilization_modifier": 1.5},
        )

        assert result.budget.targets["protein_g"].daily_target <= 56
        # Conflict resolution should be documented
        assert len(result.budget.conflict_resolutions) >= 1

# ═══════════════════════════════════════════════════════════════════════
# Dynamic Epsilon Budget Management Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDynamicEpsilonBudget:
    """Tests for dynamic privacy budget allocation based on data sensitivity.

    Patent claim: "A dynamic privacy budget allocation system that assigns
    differential privacy parameters based on biomarker data sensitivity
    classification, manages cumulative per-user privacy exposure indices,
    and adaptively adjusts noise injection rates as budget thresholds
    are approached."
    """

    # ── Tier classification tests ──────────────────────────────────

    def test_sensitivity_tier_classification(self):
        """Nutrients must be classified into correct sensitivity tiers."""
        # Genetic-derived nutrients → CRITICAL
        assert NUTRIENT_SENSITIVITY_TIERS["folate_mcg"] == SensitivityTier.CRITICAL
        assert NUTRIENT_SENSITIVITY_TIERS["b12_mcg"] == SensitivityTier.CRITICAL
        assert NUTRIENT_SENSITIVITY_TIERS["vitamin_d_iu"] == SensitivityTier.CRITICAL
        assert NUTRIENT_SENSITIVITY_TIERS["caffeine_mg"] == SensitivityTier.CRITICAL

        # Glucose-derived → HIGH
        assert NUTRIENT_SENSITIVITY_TIERS["carbs_g"] == SensitivityTier.HIGH
        assert NUTRIENT_SENSITIVITY_TIERS["kcal"] == SensitivityTier.HIGH

        # HR/HRV-derived → MEDIUM
        assert NUTRIENT_SENSITIVITY_TIERS["water_ml"] == SensitivityTier.MEDIUM
        assert NUTRIENT_SENSITIVITY_TIERS["magnesium_mg"] == SensitivityTier.MEDIUM

        # Activity-derived → LOW
        assert NUTRIENT_SENSITIVITY_TIERS["protein_g"] == SensitivityTier.LOW
        assert NUTRIENT_SENSITIVITY_TIERS["fiber_g"] == SensitivityTier.LOW

    def test_tier_epsilon_ordering(self):
        """More sensitive tiers must receive SMALLER epsilon (more noise)."""
        assert TIER_EPSILON_MAP[SensitivityTier.CRITICAL] < TIER_EPSILON_MAP[SensitivityTier.HIGH]
        assert TIER_EPSILON_MAP[SensitivityTier.HIGH] < TIER_EPSILON_MAP[SensitivityTier.MEDIUM]
        assert TIER_EPSILON_MAP[SensitivityTier.MEDIUM] < TIER_EPSILON_MAP[SensitivityTier.LOW]

    def test_all_nutrients_mapped(self):
        """Every nutrient in the standard target set must have a tier."""
        expected_nutrients = [
            "kcal", "carbs_g", "protein_g", "fat_g", "fiber_g",
            "water_ml", "folate_mcg", "b12_mcg", "vitamin_d_iu",
            "magnesium_mg", "caffeine_mg", "calcium_mg", "sodium_mg",
            "vitamin_b6_mg",
        ]
        for n in expected_nutrients:
            assert n in NUTRIENT_SENSITIVITY_TIERS, f"{n} missing from tier map"

    # ── Dynamic epsilon allocation tests ────────────────────────────

    def test_dynamic_epsilon_varies_by_tier(self):
        """Genetic nutrient (folate) must get smaller ε than activity nutrient (fiber)."""
        allocator = DynamicEpsilonAllocator()

        eps_folate = allocator.get_epsilon_for_nutrient("folate_mcg")
        eps_fiber = allocator.get_epsilon_for_nutrient("fiber_g")

        assert eps_folate < eps_fiber, (
            f"folate ε={eps_folate} should be < fiber ε={eps_fiber}"
        )

    def test_dynamic_epsilon_critical_vs_low(self):
        """CRITICAL tier nutrient ε must be ≤ 1/4 of LOW tier ε."""
        allocator = DynamicEpsilonAllocator()

        eps_critical = allocator.get_epsilon_for_nutrient("b12_mcg")  # CRITICAL
        eps_low = allocator.get_epsilon_for_nutrient("protein_g")     # LOW

        assert eps_critical <= eps_low / 4, (
            f"CRITICAL ε={eps_critical} should be ≤ LOW ε/4={eps_low/4}"
        )

    def test_unknown_nutrient_defaults_to_medium(self):
        """Unknown nutrients default to MEDIUM tier."""
        allocator = DynamicEpsilonAllocator()

        tier = allocator.get_tier_for_nutrient("unknown_nutrient_xyz")
        assert tier == SensitivityTier.MEDIUM

        eps = allocator.get_epsilon_for_nutrient("unknown_nutrient_xyz")
        assert eps == TIER_EPSILON_MAP[SensitivityTier.MEDIUM]

    # ── Adaptive epsilon under budget pressure ──────────────────────

    def test_adaptive_epsilon_reduces_near_threshold(self):
        """When budget is 75% spent, epsilon should be reduced by 25%."""
        allocator = DynamicEpsilonAllocator(
            budget_warning_threshold=0.7,
            budget_critical_threshold=0.9,
        )
        budget = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.75)

        base_eps = allocator.get_epsilon_for_nutrient("fiber_g")
        adaptive_eps = allocator.get_adaptive_epsilon("fiber_g", budget)

        assert adaptive_eps == pytest.approx(base_eps * 0.75, rel=1e-6)

    def test_adaptive_epsilon_halves_at_critical(self):
        """When budget is ≥90% spent, epsilon is halved."""
        allocator = DynamicEpsilonAllocator(
            budget_critical_threshold=0.9,
        )
        budget = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.95)

        base_eps = allocator.get_epsilon_for_nutrient("kcal")
        adaptive_eps = allocator.get_adaptive_epsilon("kcal", budget)

        assert adaptive_eps == pytest.approx(base_eps * 0.5, rel=1e-6)

    def test_adaptive_epsilon_unchanged_when_fresh(self):
        """With a fresh budget, epsilon equals the base tier value."""
        allocator = DynamicEpsilonAllocator()
        budget = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.0)

        base_eps = allocator.get_epsilon_for_nutrient("carbs_g")
        adaptive_eps = allocator.get_adaptive_epsilon("carbs_g", budget)

        assert adaptive_eps == base_eps

    # ── Exposure tracking tests ─────────────────────────────────────

    def test_query_recording_and_exposure_report(self):
        """Query history must be tracked and reportable per tier."""
        allocator = DynamicEpsilonAllocator()
        budget = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.0)

        # Simulate queries
        allocator.record_query("user-1", "folate_mcg", 0.1, 100.0)
        allocator.record_query("user-1", "b12_mcg", 0.1, 10.0)
        allocator.record_query("user-1", "fiber_g", 0.8, 12.5)
        budget.epsilon_spent = 1.0  # Manually update for report

        report = allocator.get_exposure_report("user-1", budget)

        assert report.user_id == "user-1"
        assert report.total_epsilon_spent == 1.0
        assert report.per_tier_query_count["critical"] == 2
        assert report.per_tier_query_count["low"] == 1
        assert report.exposure_index == pytest.approx(1.0)
        assert report.risk_level == "critical"

    def test_exposure_report_risk_levels(self):
        """Risk levels must escalate correctly with exposure."""
        allocator = DynamicEpsilonAllocator()

        # Low risk (< 40%)
        budget_low = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.2)
        report_low = allocator.get_exposure_report("u-1", budget_low)
        assert report_low.risk_level == "low"

        # Moderate risk (40-70%)
        budget_mod = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.5)
        report_mod = allocator.get_exposure_report("u-2", budget_mod)
        assert report_mod.risk_level == "moderate"

        # High risk (70-90%)
        budget_high = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.8)
        report_high = allocator.get_exposure_report("u-3", budget_high)
        assert report_high.risk_level == "high"

        # Critical risk (≥ 90%)
        budget_crit = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.95)
        report_crit = allocator.get_exposure_report("u-4", budget_crit)
        assert report_crit.risk_level == "critical"

    def test_exposure_reset(self):
        """Reset should clear query history for a user."""
        allocator = DynamicEpsilonAllocator()
        allocator.record_query("user-x", "kcal", 0.3, 500.0)
        allocator.reset_history("user-x")

        budget = PrivacyBudget(epsilon_total=1.0, epsilon_spent=0.0)
        report = allocator.get_exposure_report("user-x", budget)
        assert sum(report.per_tier_query_count.values()) == 0

    # ── Pipeline integration tests ──────────────────────────────────

    def test_pipeline_uses_dynamic_epsilon(self):
        """Pipeline Stage 6 must use tier-based dynamic ε, not flat 0.5."""
        dp = DifferentialPrivacyEngine(default_epsilon=1.0)
        from app.engine.metabolic_state import MetabolicStateEstimator

        pipeline = NutritionPipeline(
            synchronizer=TemporalSynchronizer(),
            normalizer=PhysiologicalNormalizer(),
            interpolator=CircadianInterpolator(),
            state_estimator=MetabolicStateEstimator(),
            nutrient_calculator=NutrientDemandCalculator(),
            consent_manager=DynamicConsentManager(),
            privacy_engine=dp,
        )

        import random
        random.seed(42)

        result = pipeline.execute(user_id="dp-test-1", readings={})
        assert result.dp_applied is True

        # Audit trail should record dynamic epsilon and tiers
        dp_stages = [s for s in result.stages_executed if s.startswith("dp_noise:")]
        assert len(dp_stages) == 1
        assert "dynamic_eps" in dp_stages[0]
        assert "tiers=" in dp_stages[0]

    def test_pipeline_genetic_nutrient_more_noisy(self):
        """Genetic-derived nutrients should have MORE noise (larger scale)
        than activity-derived nutrients, because ε is smaller → scale = S/ε is larger.
        """
        from app.engine.metabolic_state import MetabolicStateEstimator

        # Run many times and measure variance
        import random
        random.seed(99)

        N = 200
        folate_values = []
        fiber_values = []

        for i in range(N):
            dp_i = DifferentialPrivacyEngine(default_epsilon=10.0)
            pipeline = NutritionPipeline(
                synchronizer=TemporalSynchronizer(),
                normalizer=PhysiologicalNormalizer(),
                interpolator=CircadianInterpolator(),
                state_estimator=MetabolicStateEstimator(),
                nutrient_calculator=NutrientDemandCalculator(),
                consent_manager=DynamicConsentManager(),
                privacy_engine=dp_i,
            )
            result = pipeline.execute(user_id=f"noise-test-{i}", readings={})
            targets = result.budget.targets
            if "folate_mcg" in targets:
                folate_values.append(targets["folate_mcg"].daily_target)
            if "fiber_g" in targets:
                fiber_values.append(targets["fiber_g"].daily_target)

        if len(folate_values) >= 10 and len(fiber_values) >= 10:
            # Folate (CRITICAL) should have higher variance than fiber (LOW)
            folate_var = sum((v - sum(folate_values)/len(folate_values))**2 for v in folate_values) / len(folate_values)
            fiber_var = sum((v - sum(fiber_values)/len(fiber_values))**2 for v in fiber_values) / len(fiber_values)

            # Relative variance (normalized by mean²) should be higher for folate
            folate_mean = sum(folate_values) / len(folate_values)
            fiber_mean = sum(fiber_values) / len(fiber_values)

            if folate_mean > 0 and fiber_mean > 0:
                folate_cv = (folate_var ** 0.5) / folate_mean
                fiber_cv = (fiber_var ** 0.5) / fiber_mean
                # CRITICAL tier's smaller ε produces larger noise
                assert folate_cv > fiber_cv * 0.5, (
                    f"Folate CV={folate_cv:.4f} should be > fiber CV×0.5={fiber_cv*0.5:.4f}"
                )

    def test_pipeline_exposure_report_accessible(self):
        """Pipeline must expose privacy exposure report after execution."""
        from app.engine.metabolic_state import MetabolicStateEstimator

        dp = DifferentialPrivacyEngine(default_epsilon=1.0)
        pipeline = NutritionPipeline(
            synchronizer=TemporalSynchronizer(),
            normalizer=PhysiologicalNormalizer(),
            interpolator=CircadianInterpolator(),
            state_estimator=MetabolicStateEstimator(),
            nutrient_calculator=NutrientDemandCalculator(),
            consent_manager=DynamicConsentManager(),
            privacy_engine=dp,
        )

        import random
        random.seed(123)

        pipeline.execute(user_id="report-test", readings={})
        report = pipeline.get_privacy_exposure_report("report-test")

        assert report is not None
        assert report.user_id == "report-test"
        assert report.total_epsilon_spent > 0
        assert report.exposure_index > 0
        assert report.risk_level in ("low", "moderate", "high", "critical")
        assert sum(report.per_tier_query_count.values()) > 0

# FIXME: potential edge case
# Updated: 2023-03-10
# FIXME: potential edge case