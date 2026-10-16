"""Bounds on stacked nutrient modifiers and the per-kg protein clamp.

Medical constraints must still win after the clamp (CLAUDE.md: medical constraints always
override genetic optimization).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.engine.metabolic_state import MetabolicState
from app.engine.nutrient_calculator import (
    COMBINED_MODIFIER_MAX,
    COMBINED_MODIFIER_MIN,
    PROTEIN_G_PER_KG_MAX,
    PROTEIN_G_PER_KG_MIN,
    MedicalConstraint,
    NutrientDemandCalculator,
    create_default_targets,
)
from app.main import app

NOW = datetime(2025, 1, 15, 12, 0, 0)
HEADERS = {"X-API-Key": "dev-api-key"}

# The dashboard's demo profile: 70 kg, 175 cm, 30 y, male, moderate activity.
DEMO_WEIGHT = 70
DEMO_KCAL = round((10 * 70 + 6.25 * 175 - 5 * 30 + 5) * 1.55)
DEMO_GENOTYPES = {
    "rs1801133": "CT",
    "rs9939609": "TA",
    "rs429358": "TT",
    "rs7903146": "CT",
    "rs4988235": "GA",
    "rs762551": "AC",
    "rs1544410": "AG",
    "rs4341": "ID",
}


def state_with(**shifts: float) -> MetabolicState:
    state = MetabolicState(timestamp=NOW)
    state.nutrient_priority_shifts = dict(shifts)
    return state


def run(genetic: dict[str, float], state: MetabolicState, weight=DEMO_WEIGHT, calc=None):
    calc = calc or NutrientDemandCalculator()
    base = create_default_targets(kcal=DEMO_KCAL, weight_kg=weight)
    budget = calc.calculate(
        user_id="u",
        base_targets=base,
        metabolic_state=state,
        normalized_signals={},
        genetic_modifiers=genetic,
        weight_kg=weight,
    )
    return base, budget


def test_demo_profile_protein_is_plausible_via_api() -> None:
    client = TestClient(app)
    user = "bounds-demo"
    assert (
        client.post(
            "/engine/genetic-profile",
            json={"user_id": user, "genotypes": DEMO_GENOTYPES},
            headers=HEADERS,
        ).status_code
        == 200
    )
    res = client.post(
        "/engine/nutrient-budget",
        json={"user_id": user, "weight_kg": DEMO_WEIGHT, "kcal_target": DEMO_KCAL},
        headers=HEADERS,
    )
    assert res.status_code == 200
    protein = res.json()["targets"]["protein_g"]["daily_target"]
    assert DEMO_WEIGHT * PROTEIN_G_PER_KG_MIN <= protein <= DEMO_WEIGHT * PROTEIN_G_PER_KG_MAX


def test_default_protein_base_stays_below_ceiling() -> None:
    base = create_default_targets(kcal=4000, weight_kg=70)
    assert base["protein_g"].daily_target <= 70 * 1.6


@pytest.mark.parametrize("factor", [1.3, 2.0, 5.0])
def test_stacking_never_exceeds_combined_cap(factor: float) -> None:
    base, budget = run(
        {"protein_utilization_modifier": factor, "carb_sensitivity_modifier": 1 / factor},
        state_with(protein_priority=factor, carbohydrate_priority=factor, water_priority=factor),
        weight=200,  # heavy enough that the g/kg ceiling is not the binding limit
    )
    for name in ("protein_g", "carbs_g", "water_ml"):
        ratio = budget.targets[name].daily_target / base[name].daily_target
        assert ratio <= COMBINED_MODIFIER_MAX + 1e-9, name
    assert any(m["step"] == "bound" for m in budget.modifications)


def test_stacking_never_drops_below_combined_floor() -> None:
    base, budget = run({"carb_sensitivity_modifier": 4.0}, state_with(carbohydrate_priority=0.2))
    ratio = budget.targets["carbs_g"].daily_target / base["carbs_g"].daily_target
    assert ratio >= COMBINED_MODIFIER_MIN - 1e-9


def test_protein_clamped_to_two_grams_per_kg() -> None:
    _, budget = run({"protein_utilization_modifier": 3.0}, state_with(protein_priority=3.0))
    assert budget.targets["protein_g"].daily_target == pytest.approx(
        DEMO_WEIGHT * PROTEIN_G_PER_KG_MAX
    )


def test_genetic_caffeine_limit_is_a_cap_not_a_multiplier() -> None:
    _, budget = run({"caffeine_max_daily_mg": 200}, state_with())
    assert budget.targets["caffeine_mg"].daily_target == pytest.approx(200)
    assert budget.targets["caffeine_mg"].maximum == pytest.approx(200)


def test_kidney_protein_limit_still_wins_after_clamp() -> None:
    calc = NutrientDemandCalculator()
    ckd_limit = DEMO_WEIGHT * 0.6
    calc.set_medical_constraints(
        "u",
        [
            MedicalConstraint(
                nutrient="protein_g",
                constraint_type="max",
                value=ckd_limit,
                reason="CKD stage 3 protein limit",
                severity="critical",
            )
        ],
    )
    _, budget = run(
        {"protein_utilization_modifier": 3.0}, state_with(protein_priority=3.0), calc=calc
    )
    assert budget.targets["protein_g"].daily_target == pytest.approx(ckd_limit)
    resolution = next(c for c in budget.conflict_resolutions if c.nutrient == "protein_g")
    assert resolution.winner == "medical_critical"
    assert resolution.loser == "genetic"


def test_dp_noise_respects_protein_ceiling_and_medical_limit() -> None:
    """The pipeline's DP stage runs after the calculator; it must not undo either bound."""
    from app.engine.interpolation import CircadianInterpolator
    from app.engine.metabolic_state import MetabolicStateEstimator
    from app.engine.normalization import PhysiologicalNormalizer
    from app.engine.pipeline import NutritionPipeline
    from app.engine.temporal_sync import TemporalSynchronizer
    from app.privacy.differential_privacy import DifferentialPrivacyEngine

    pipeline = NutritionPipeline(
        synchronizer=TemporalSynchronizer(),
        normalizer=PhysiologicalNormalizer(),
        interpolator=CircadianInterpolator(),
        state_estimator=MetabolicStateEstimator(),
        nutrient_calculator=NutrientDemandCalculator(),
        privacy_engine=DifferentialPrivacyEngine(),
    )
    for _ in range(20):
        result = pipeline.execute(
            user_id="dp-bounds",
            readings={},
            genetic_modifiers={"protein_utilization_modifier": 3.0},
            kcal_target=DEMO_KCAL,
            weight_kg=DEMO_WEIGHT,
        )
        protein = result.budget.targets["protein_g"].daily_target
        assert protein <= DEMO_WEIGHT * PROTEIN_G_PER_KG_MAX + 1e-6

    pipeline._nutrient_calculator.set_medical_constraints(
        "dp-ckd",
        [MedicalConstraint("protein_g", "max", 42.0, "CKD protein limit", "critical")],
    )
    for _ in range(20):
        result = pipeline.execute(
            user_id="dp-ckd",
            readings={},
            genetic_modifiers={"protein_utilization_modifier": 3.0},
            kcal_target=DEMO_KCAL,
            weight_kg=DEMO_WEIGHT,
        )
        assert result.budget.targets["protein_g"].daily_target <= 42.0 + 1e-6
