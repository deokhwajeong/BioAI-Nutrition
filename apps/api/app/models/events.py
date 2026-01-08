from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DietEvent(BaseModel):
    user_id: str
    timestamp: str
    food: str
    calories: float
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

class ActivityEvent(BaseModel):
    user_id: str
    timestamp: str
    activity_type: str
    duration_minutes: float
    calories_burned: Optional[float] = None
    steps: Optional[int] = None

class SleepEvent(BaseModel):
    user_id: str
    timestamp: str
    duration_minutes: float
    quality: Optional[str] = None