"""Output noise on nutrient targets: scale, determinism, re-release, and safety ordering."""

import random
import statistics

from app.engine.interpolation import CircadianInterpolator
from app.engine.metabolic_state import MetabolicStateEstimator
from app.engine.normalization import PhysiologicalNormalizer
from app.engine.nutrient_calculator import (
    MedicalConstraint,
    NutrientDemandCalculator,
    create_default_targets,
)
from app.engine.pipeline import NutritionPipeline
from app.engine.temporal_sync import TemporalSynchronizer
from app.privacy.differential_privacy import (
    DAILY_RELEASE_EPSILON,
    NUTRIENT_DP_SENSITIVITY,
    TIER_EPSILON_MAP,
    DifferentialPrivacyEngine,
    DynamicEpsilonAllocator,
)

KCAL = 2556  # Mifflin-St Jeor x 1.55 for the dashboard's 70 kg, 175 cm, 30 y profile
WEIGHT = 70


def make_pipeline(seed: int | None = None, engine: DifferentialPrivacyEngine | None = None):
    return NutritionPipeline(
        synchronizer=TemporalSynchronizer(),
        normalizer=PhysiologicalNormalizer(),
        interpolator=CircadianInterpolator(),
        state_estimator=MetabolicStateEstimator(),
        nutrient_calculator=NutrientDemandCalculator(),
        privacy_engine=engine or DifferentialPrivacyEngine(seed=seed),
    )


def run(pipeline: NutritionPipeline, user: str = "u", kcal: float = KCAL):
    return pipeline.execute(user_id=user, readings={}, kcal_target=kcal, weight_kg=WEIGHT)


def test_every_default_target_has_a_documented_sensitivity() -> None:
    assert set(create_default_targets()) <= set(NUTRIENT_DP_SENSITIVITY)


def test_noise_scale_is_small_relative_to_the_target() -> None:
    """Mean absolute noise (b = sensitivity / epsilon) is at most 10% of each base target.

    Energy and macros sit near 2 to 5%; the genetics-derived micronutrients get the
    strongest privacy tier and so the most noise (folate and caffeine at 10%).
    """
    allocator = DynamicEpsilonAllocator()
    for name, target in create_default_targets(KCAL, WEIGHT).items():
        b = NUTRIENT_DP_SENSITIVITY[name] / allocator.get_epsilon_for_nutrient(name)
        assert b <= 0.10 * target.daily_target + 1e-9, (name, b)
        if name in ("kcal", "protein_g", "fat_g", "fiber_g", "water_ml"):
            assert b <= 0.05 * target.daily_target, (name, b)


def test_one_release_fits_the_daily_budget() -> None:
    allocator = DynamicEpsilonAllocator()
    cost = sum(allocator.get_epsilon_for_nutrient(n) for n in create_default_targets())
    assert cost <= DAILY_RELEASE_EPSILON
    assert cost == sum(
        TIER_EPSILON_MAP[allocator.get_tier_for_nutrient(n)] for n in create_default_targets()
    )


def test_seeded_engines_give_identical_releases() -> None:
    a = run(make_pipeline(seed=7)).budget.targets
    b = run(make_pipeline(seed=7)).budget.targets
    assert {k: t.daily_target for k, t in a.items()} == {k: t.daily_target for k, t in b.items()}


def test_noise_is_real_and_rarely_reaches_a_bound() -> None:
    """Across seeds the energy target moves, stays plausible, and is seldom clipped to a cap."""
    values = []
    clipped = 0
    for seed in range(200):
        target = run(make_pipeline(seed=seed)).budget.targets["kcal"]
        values.append(target.daily_target)
        clipped += target.daily_target in (target.minimum, target.maximum)
    assert statistics.pstdev(values) > 10  # noise is applied
    assert all(abs(v - KCAL) < 0.15 * KCAL for v in values)
    assert clipped <= 4  # under 2% of releases touch a bound


def test_repeat_with_same_inputs_reuses_the_release_and_spends_nothing() -> None:
    engine = DifferentialPrivacyEngine(seed=3)
    pipeline = make_pipeline(engine=engine)
    first = {k: t.daily_target for k, t in run(pipeline).budget.targets.items()}
    spent = engine.get_or_create_budget("u").epsilon_spent
    second_result = run(pipeline)
    second = {k: t.daily_target for k, t in second_result.budget.targets.items()}
    assert first == second
    assert engine.get_or_create_budget("u").epsilon_spent == spent
    assert any("reused=" in s and "reused=0" not in s for s in second_result.stages_executed)


def test_changed_input_after_budget_is_spent_reuses_the_stale_noisy_value() -> None:
    engine = DifferentialPrivacyEngine(seed=5)
    pipeline = make_pipeline(engine=engine)
    run(pipeline, kcal=2400)
    run(pipeline, kcal=2450)  # spends most of what is left
    run(pipeline, kcal=2500)
    result = run(pipeline, kcal=2550)
    assert all("unprotected=0" in s for s in result.stages_executed if s.startswith("dp_noise"))


def test_medical_cap_still_applies_after_noise() -> None:
    pipeline = make_pipeline(seed=11)
    pipeline._nutrient_calculator.set_medical_constraints(
        "ckd", [MedicalConstraint("protein_g", "max", 42.0, "CKD protein limit", "critical")]
    )
    for seed in range(30):
        pipeline._privacy_engine._rng = random.Random(seed)
        pipeline.forget_user("ckd")
        pipeline._privacy_engine.forget_user("ckd")
        result = run(pipeline, user="ckd")
        assert result.budget.targets["protein_g"].daily_target <= 42.0 + 1e-9


def test_forget_user_clears_cached_releases() -> None:
    pipeline = make_pipeline(seed=1)
    run(pipeline, user="gone")
    assert "gone" in pipeline._released
    pipeline.forget_user("gone")
    assert "gone" not in pipeline._released
