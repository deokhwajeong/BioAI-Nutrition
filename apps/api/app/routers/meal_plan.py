"""Weekly meal planning endpoint."""

from fastapi import APIRouter, HTTPException

from ..schemas.meal_plan import (
    MacroTotals,
    MealPlanRequest,
    MealPlanResponse,
    PlannedDayOut,
    PlannedItemOut,
    PlannedMealOut,
)
from ..services.meal_planner import (
    DISCLAIMER,
    TRACKED,
    MealPlan,
    PlanConstraint,
    build_meal_plan,
)
from .biomarker_engine import _nutrient_calculator

router = APIRouter(prefix="/meal-plan", tags=["meal-plan"])


def _totals(values: dict[str, float]) -> MacroTotals:
    return MacroTotals(**{n: round(values[n], 1) for n in TRACKED})


def _to_response(plan: MealPlan) -> MealPlanResponse:
    days_out: list[PlannedDayOut] = []
    for day in plan.days:
        totals = {n: day.total(n) for n in TRACKED}
        days_out.append(
            PlannedDayOut(
                day=day.day,
                meals=[
                    PlannedMealOut(
                        slot=meal.slot,
                        kcal=round(meal.total("kcal"), 1),
                        items=[
                            PlannedItemOut(
                                food=item.food,
                                servings=item.servings,
                                **{n: round(item.amount(n), 1) for n in TRACKED},
                            )
                            for item in meal.items
                        ],
                    )
                    for meal in day.meals
                ],
                totals=_totals(totals),
                deviation_pct={
                    n: round((totals[n] - t) / t * 100, 1)
                    for n, t in plan.effective_targets.items()
                    if t > 0
                },
                within_limits=all(totals[n] <= c + 1e-9 for n, c in plan.ceilings.items()),
            )
        )
    count = max(len(plan.days), 1)
    average = {n: sum(d.total(n) for d in plan.days) / count for n in TRACKED}
    return MealPlanResponse(
        days=days_out,
        requested_targets=_totals(plan.requested_targets),
        effective_targets=_totals(plan.effective_targets),
        ceilings=plan.ceilings,
        adjustments=plan.adjustments,
        notes=plan.notes,
        weekly_average=_totals(average),
        disclaimer=DISCLAIMER,
    )


@router.post("", response_model=MealPlanResponse)
def create_meal_plan(req: MealPlanRequest) -> MealPlanResponse:
    """Plan up to 7 days of meals from the built-in food table against daily targets.

    Medical constraints (from the request and, with ``user_id``, those stored in the engine)
    are applied before planning and enforced as hard ceilings after it, so they always win
    over the targets. General wellness guidance, not medical advice.
    """
    constraints = [
        PlanConstraint(c.nutrient, c.constraint_type, c.value, c.reason, c.severity)
        for c in req.constraints
    ]
    if req.user_id:
        constraints += [
            PlanConstraint(c.nutrient, c.constraint_type, c.value, c.reason, c.severity)
            for c in _nutrient_calculator._user_constraints.get(req.user_id, [])
        ]
    targets = {k: v for k, v in req.targets.model_dump().items() if v is not None}
    try:
        plan = build_meal_plan(targets, constraints, req.exclude_foods, req.days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _to_response(plan)
