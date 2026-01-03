from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event contract with common fields."""
    user_id: str = Field(..., description="Unique identifier for the user")
    timestamp: datetime = Field(..., description="ISO timestamp when the event occurred")


class DietEvent(BaseEvent):
    """Event representing a food intake."""
    food: str = Field(..., description="Name of food consumed")
    calories: float = Field(..., gt=0, description="Calories consumed")
    protein: Optional[float] = Field(None, gt=0, description="Protein grams")
    carbs: Optional[float] = Field(None, gt=0, description="Carbohydrates grams")
    fat: Optional[float] = Field(None, gt=0, description="Fat grams")


class ActivityEvent(BaseEvent):
    """Event representing a physical activity session."""
    activity_type: str = Field(..., description="Type of activity, e.g. running")
    duration_minutes: float = Field(..., gt=0, description="Duration in minutes")
    distance_km: Optional[float] = Field(None, gt=0, description="Distance in kilometers")
    calories_burned: Optional[float] = Field(None, gt=0, description="Estimated calories burned")


class SleepEvent(BaseEvent):
    """Event representing a sleep period."""
    duration_minutes: float = Field(..., gt=0, description="Sleep duration in minutes")
    sleep_quality: Optional[int] = Field(
        None, ge=1, le=5, description="Self-reported sleep quality rating (1-5)"
    )
