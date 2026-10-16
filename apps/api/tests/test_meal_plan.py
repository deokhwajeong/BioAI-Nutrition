"""Weekly meal planner: fit to targets, variety, exclusions, and medical limits winning."""

import pytest
from fastapi.testclient import TestClient

from app.main import app, settings
from app.services.meal_analyzer import NUTRITION_DB
from app.services.meal_planner import FOOD_GROUPS, PlanConstraint, build_meal_plan

TARGETS = {"kcal": 2400, "protein_g": 110, "carbs_g": 270, "fat_g": 85}
client = TestClient(app)
HEADERS = {"X-API-Key": settings.api_key}


def test_every_planner_food_is_in_the_food_table() -> None:
    for foods in FOOD_GROUPS.values():
        assert set(foods) <= set(NUTRITION_DB)


def test_plan_has_seven_days_of_four_meals_close_to_target() -> None:
    plan = build_meal_plan(TARGETS)
    assert len(plan.days) == 7
    for day in plan.days:
        assert [m.slot for m in day.meals] == ["breakfast", "lunch", "dinner", "snack"]
        assert abs(day.total("kcal") - 2400) / 2400 < 0.08
        assert abs(day.total("protein_g") - 110) / 110 < 0.10
        for item in (i for m in day.meals for i in m.items):
            assert item.servings in {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}


def test_plan_is_deterministic_and_varied() -> None:
    a, b = build_meal_plan(TARGETS), build_meal_plan(TARGETS)
    menu = [[(i.food, i.servings) for m in d.meals for i in m.items] for d in a.days]
    assert menu == [[(i.food, i.servings) for m in d.meals for i in m.items] for d in b.days]
    lunches = [d.meals[1].items[0].food for d in a.days if d.meals[1].items]
    assert len(set(lunches)) >= 5
    for day in a.days:
        # Cooking oil is the one ingredient allowed in more than one meal.
        foods = [i.food for m in day.meals for i in m.items if i.food != "olive oil"]
        assert len(foods) == len(set(foods)), "a food appears twice in one day"


def test_medical_protein_limit_overrides_a_higher_target() -> None:
    """A genetics-raised protein target of 150 g loses to a 56 g kidney-related limit."""
    limit = PlanConstraint("protein_g", "max", 56, "kidney-related protein limit", "critical")
    plan = build_meal_plan({**TARGETS, "protein_g": 150}, [limit])
    assert plan.effective_targets["protein_g"] == 56
    assert plan.ceilings == {"protein_g": 56}
    assert any("lowered from 150 to 56" in a for a in plan.adjustments)
    for day in plan.days:
        assert day.total("protein_g") <= 56 + 1e-9


def test_strict_limit_never_breaks_even_when_energy_falls_short() -> None:
    limit = PlanConstraint("protein_g", "max", 30, "strict limit", "critical")
    plan = build_meal_plan(TARGETS, [limit])
    assert all(d.total("protein_g") <= 30 + 1e-9 for d in plan.days)
    assert any("below the" in n for n in plan.notes)  # shortfall is reported, not hidden


def test_energy_ceiling_and_untracked_nutrients() -> None:
    plan = build_meal_plan(
        TARGETS,
        [
            PlanConstraint("kcal", "max", 1800, "energy limit"),
            PlanConstraint("sodium_mg", "max", 1500, "hypertension"),
        ],
    )
    assert all(d.total("kcal") <= 1800 + 1e-9 for d in plan.days)
    assert any("sodium_mg" in n and "cannot check" in n for n in plan.notes)


def test_min_constraint_raises_target_and_max_beats_conflicting_min() -> None:
    plan = build_meal_plan(TARGETS, [PlanConstraint("protein_g", "min", 130, "recovery")])
    assert plan.effective_targets["protein_g"] == 130
    plan = build_meal_plan(
        TARGETS,
        [
            PlanConstraint("protein_g", "max", 60, "kidney", "critical"),
            PlanConstraint("protein_g", "min", 90, "athlete"),
        ],
    )
    assert plan.effective_targets["protein_g"] == 60
    assert any("maximum wins" in n for n in plan.notes)


def test_excluded_foods_never_appear() -> None:
    plan = build_meal_plan(TARGETS, exclude_foods=["salmon", "Peanut Butter", "egg"])
    foods = {i.food for d in plan.days for m in d.meals for i in m.items}
    assert not foods & {"salmon", "peanut butter", "eggs"}


def test_requires_positive_energy() -> None:
    with pytest.raises(ValueError):
        build_meal_plan({"kcal": 0})


def test_endpoint_returns_plan_with_guardrail_and_limits() -> None:
    res = client.post(
        "/meal-plan",
        headers=HEADERS,
        json={
            "targets": {"kcal": 2400, "protein_g": 140},
            "days": 3,
            "constraints": [
                {
                    "nutrient": "protein_g",
                    "constraint_type": "max",
                    "value": 56,
                    "reason": "kidney-related protein limit",
                    "severity": "critical",
                }
            ],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["days"]) == 3
    assert body["guardrails"] == ["non-diagnostic"]
    assert "not medical advice" in body["disclaimer"].lower()
    assert body["effective_targets"]["protein_g"] == 56
    assert all(d["within_limits"] and d["totals"]["protein_g"] <= 56 for d in body["days"])


def test_endpoint_applies_constraints_stored_in_the_engine() -> None:
    client.post(
        "/engine/medical-constraints",
        headers=HEADERS,
        json={
            "user_id": "plan-user",
            "constraints": [
                {"nutrient": "kcal", "constraint_type": "max", "value": 1900, "reason": "test"}
            ],
        },
    )
    res = client.post(
        "/meal-plan", headers=HEADERS, json={"targets": {"kcal": 2400}, "user_id": "plan-user"}
    )
    assert res.status_code == 200
    assert all(d["totals"]["kcal"] <= 1900 for d in res.json()["days"])


def test_endpoint_requires_api_key_and_validates() -> None:
    assert client.post("/meal-plan", json={"targets": {"kcal": 2000}}).status_code == 401
    bad = client.post("/meal-plan", headers=HEADERS, json={"targets": {"kcal": 2000}, "days": 9})
    assert bad.status_code == 422
