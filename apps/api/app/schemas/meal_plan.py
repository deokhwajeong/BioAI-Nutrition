"""Request and response models for the weekly meal planner (POST /meal-plan)."""

from pydantic import BaseModel, Field

from .biomarker_schemas import MedicalConstraintIn


class PlanTargets(BaseModel):
    """Daily targets to plan against. Usually the pipeline's nutrient budget."""

    kcal: float = Field(..., gt=0, le=6000, description="Daily energy target (kcal)")
    protein_g: float | None = Field(None, gt=0, le=400, description="Daily protein target (g)")
    carbs_g: float | None = Field(None, ge=0, le=900, description="Daily carbohydrate (g)")
    fat_g: float | None = Field(None, ge=0, le=400, description="Daily fat target (g)")


class MealPlanRequest(BaseModel):
    targets: PlanTargets
    days: int = Field(7, ge=1, le=7, description="Number of days to plan")
    constraints: list[MedicalConstraintIn] = Field(
        default_factory=list,
        description="Medical limits. They override the targets and are hard ceilings.",
    )
    user_id: str | None = Field(
        None,
        description="Also apply the medical constraints stored for this user in the engine",
    )
    exclude_foods: list[str] = Field(
        default_factory=list, description="Foods to leave out (allergies, dislikes)"
    )


class PlannedItemOut(BaseModel):
    food: str
    servings: float
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class PlannedMealOut(BaseModel):
    slot: str = Field(description="breakfast, lunch, dinner, or snack")
    items: list[PlannedItemOut]
    kcal: float


class MacroTotals(BaseModel):
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class PlannedDayOut(BaseModel):
    day: int
    meals: list[PlannedMealOut]
    totals: MacroTotals
    deviation_pct: dict[str, float] = Field(
        description="Percent difference from the effective targets, per nutrient"
    )
    within_limits: bool = Field(description="True when every medical ceiling holds")


class MealPlanResponse(BaseModel):
    days: list[PlannedDayOut]
    requested_targets: MacroTotals
    effective_targets: MacroTotals = Field(
        description="Targets after medical limits and energy balancing"
    )
    ceilings: dict[str, float] = Field(description="Hard medical ceilings the plan respects")
    adjustments: list[str]
    notes: list[str]
    weekly_average: MacroTotals
    guardrails: list[str] = Field(default_factory=lambda: ["non-diagnostic"])
    disclaimer: str
