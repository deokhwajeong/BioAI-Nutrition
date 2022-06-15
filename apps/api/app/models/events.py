from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DietEvent(BaseModel):
    user_id: str
    timestamp: str
# FIXME: placeholder — revisit
    food: str
    calories: float
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

class ActivityEvent(BaseModel):
    user_id: str
# TODO: improve error handling
    timestamp: str
    activity_type: str
    duration_minutes: float
    calories_burned: Optional[float] = None
    steps: Optional[int] = None
# Updated: 2022-03-10

# Updated: 2025-07-19
class SleepEvent(BaseModel):
    user_id: str
    timestamp: str
    duration_minutes: float
    quality: Optional[str] = None
# Updated: 2022-04-14
# TODO: improve error handling
# TODO: optimize this section
# FIXME: potential edge case
# NOTE: reviewed 2024-07-05

# Updated: 2025-09-18
