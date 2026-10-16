from pydantic import BaseModel, Field


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
    kcal: float | None = Field(None, description="Daily calorie target")
    protein_g: float | None = Field(None, description="Daily protein target (g)")
    fiber_g: float | None = Field(None, description="Daily fiber target (g)")


class DailyFeatures(BaseModel):
    date: str | None = Field(None, description="ISO date")
    kcal_avg: float | None = None
    protein_g: float | None = None
    fiber_g: float | None = None
    late_meal_freq: float | None = None
    steps: float | None = None
    sleep_hours: float | None = None
    sleep_regularity: float | None = None
    ultra_processed_ratio: float | None = None
    persona: str | None = None


class Recommendation(BaseModel):
    id: str
    message: str
    rationale: str
    tags: list[str] = []


class RecommendationRequest(BaseModel):
    daily_features: DailyFeatures
    user_targets: UserTargets


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
