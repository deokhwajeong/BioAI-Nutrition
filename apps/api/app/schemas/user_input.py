from pydantic import BaseModel, Field
from typing import List, Optional

class UserTargets(BaseModel):
    kcal: Optional[float] = Field(None, description="Daily calorie target")
    protein_g: Optional[float] = Field(None, description="Daily protein target (g)")
    fiber_g: Optional[float] = Field(None, description="Daily fiber target (g)")

class DailyFeatures(BaseModel):
    date: Optional[str] = Field(None, description="ISO date")
    kcal_avg: Optional[float] = None
    protein_g: Optional[float] = None
    fiber_g: Optional[float] = None
    late_meal_freq: Optional[float] = None
    steps: Optional[float] = None
    sleep_hours: Optional[float] = None
    sleep_regularity: Optional[float] = None
    ultra_processed_ratio: Optional[float] = None
    persona: Optional[str] = None

class Recommendation(BaseModel):
    id: str
    message: str
    rationale: str
    tags: List[str] = []

class RecommendationRequest(BaseModel):
    daily_features: DailyFeatures
    user_targets: UserTargets

class RecommendationResponse(BaseModel):
    recommendations: List[Recommendation]
