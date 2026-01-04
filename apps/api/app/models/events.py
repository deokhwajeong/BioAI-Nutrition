"""Pydantic models for BioAI Nutrition events with aliases for backward compatibility.

This module defines data contracts for ingest events (food intake, activity, sleep).
Aliases are provided so that legacy payload keys like 'type', 'duration', 'calories' and
'quality' are accepted while still exposing descriptive field names in the API docs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event contract with common fields."""

    user_id: str = Field(
        ..., description="Unique identifier for the user"
    )
    timestamp: datetime = Field(
        ..., description="ISO timestamp when the event occurred"
    )

    class Config:
        # Allow population by field name even when aliases are defined on child models
        allow_population_by_field_name = True


class DietEvent(BaseEvent):
    """Event representing a food intake."""

    food: str = Field(
        ..., description="Name of food consumed"
    )
    calories: float = Field(
        ..., gt=0, description="Calories consumed"
    )
    protein: Optional[float] = Field(
        None, gt=0, description="Protein grams"
    )
    carbs: Optional[float] = Field(
        None, gt=0, description="Carbohydrates grams"
    )
    fat: Optional[float] = Field(
        None, gt=0, description="Fat grams"
    )


class ActivityEvent(BaseEvent):
    """Event representing a physical activity session."""

    # Accept legacy key 'type' for activity_type
    activity_type: str = Field(
        ..., alias="type", description="Type of activity, e.g. running or cycling"
    )
    # Accept legacy key 'duration' for duration_minutes
    duration_minutes: float = Field(
        ..., gt=0, alias="duration", description="Duration in minutes"
    )
    distance_km: Optional[float] = Field(
        None, gt=0, description="Distance in kilometers"
    )
    # Accept legacy key 'calories' for calories_burned
    calories_burned: Optional[float] = Field(
        None, gt=0, alias="calories", description="Calories burned"
    )

    class Config:
        allow_population_by_field_name = True


class SleepEvent(BaseEvent):
    """Event representing a sleep period."""

    # Accept legacy key 'duration' for duration_minutes
    duration_minutes: float = Field(
        ..., gt=0, alias="duration", description="Sleep duration in minutes"
    )
    # Accept legacy key 'quality' for sleep_quality
    sleep_quality: Optional[int] = Field(
        None, ge=1, le=5, alias="quality",
        description="Self-reported sleep quality (1-5)"
    )

    class Config:
        allow_population_by_field_name = True
