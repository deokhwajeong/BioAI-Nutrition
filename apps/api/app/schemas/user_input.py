from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class FoodItem(BaseModel):
    name: str


class FoodNutrition(BaseModel):
    name: str
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    note: str | None = None


class AnalyzeMealRequest(BaseModel):
    items: list[FoodItem]


class AnalyzeMealResponse(BaseModel):
    items: list[FoodNutrition]


class UserTargets(BaseModel):
    """Daily targets. Anything left out falls back to the engine's defaults."""

    calories: float | None = Field(
        None,
        description="Daily calorie target (kcal)",
        validation_alias=AliasChoices("calories", "kcal"),
    )
    protein_g: float | None = Field(None, description="Daily protein target (g)")
    fiber_g: float | None = Field(None, description="Daily fiber target (g)")
    omega3_g: float | None = Field(None, description="Daily omega-3 target (g)")
    water_ml: float | None = Field(None, description="Daily water target (mL)")


class DailyFeatures(BaseModel):
    """One day of intake, activity, and sleep. Missing values never trigger a rule."""

    date: str | None = Field(None, description="ISO date")
    calories: float | None = Field(
        None,
        description="Energy intake (kcal)",
        validation_alias=AliasChoices("calories", "kcal_avg"),
    )
    protein_g: float | None = None
    carbs_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    omega3_g: float | None = None
    water_ml: float | None = None
    steps: float | None = None
    sleep_hours: float | None = None


class Recommendation(BaseModel):
    id: str = Field(description="Rule id from rules/*.yaml")
    message: str
    rationale: str
    priority: Literal["high", "medium", "low"]
    guardrails: list[str] = Field(description="Always includes 'non-diagnostic'")
    triggered_by: list[str] = Field(description="The rule conditions that matched")


class RecommendationRequest(BaseModel):
    daily_features: DailyFeatures
    user_targets: UserTargets = Field(default_factory=UserTargets)
    top_n: int | None = Field(None, ge=1, le=20, description="Return at most this many")


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    disclaimer: str = "General wellness suggestions from fixed rules. Not medical advice."
