from pydantic import BaseModel


class DietEvent(BaseModel):
    user_id: str
    timestamp: str
    food: str
    calories: float
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None


class ActivityEvent(BaseModel):
    user_id: str
    timestamp: str
    activity_type: str
    duration_minutes: float
    calories_burned: float | None = None
    steps: int | None = None


class SleepEvent(BaseModel):
    user_id: str
    timestamp: str
    duration_minutes: float
    quality: str | None = None
