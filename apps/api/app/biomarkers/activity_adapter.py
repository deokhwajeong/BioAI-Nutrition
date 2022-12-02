"""
Activity data adapter for wearable devices.

Handles variable-frequency activity data (accelerometer, steps, heart rate)
from fitness trackers and smartwatches.

Patent-relevant: Activity data has complex temporal relationships with
nutrition. Exercise intensity affects glucose utilization immediately,
but muscle glycogen replenishment creates delayed nutrient demands
(2-48 hours post-exercise).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from .base import (
    BiomarkerReading,
    BiomarkerSource,
    BiomarkerType,
    SamplingCharacteristics,
    TemporalBehavior,
)

# MET (Metabolic Equivalent of Task) values for common activities
ACTIVITY_MET_VALUES = {
    "sedentary": 1.0,
    "light_walk": 2.5,
    "moderate_walk": 3.5,
    "brisk_walk": 4.5,
    "jogging": 7.0,
    "running": 9.8,
    "cycling_light": 4.0,
    "cycling_moderate": 6.8,
    "cycling_vigorous": 10.0,
    "swimming": 6.0,
    "weight_training": 5.0,
    "yoga": 2.5,
    "hiit": 12.0,
    "stairs": 8.0,
}

# Post-exercise nutrient demand windows
# Maps exercise intensity to delayed nutrient need durations
POST_EXERCISE_WINDOWS = {
    "low": {"carb_replenish_hours": 2, "protein_window_hours": 4},
    "moderate": {"carb_replenish_hours": 4, "protein_window_hours": 6},
    "high": {"carb_replenish_hours": 8, "protein_window_hours": 24},
    "extreme": {"carb_replenish_hours": 24, "protein_window_hours": 48},
}

class ActivityAdapter(BiomarkerSource):
    """Adapter for wearable activity tracker data.

    Handles multiple activity signal types with different temporal properties:
    - Steps: aggregated per minute/hour, semi-continuous
    - Heart Rate: quasi-continuous (~1s–1min)
    - Exercise Sessions: discrete events with duration
    - Calories: derived metric, aggregated
    """

    def __init__(self, device_model: str = "generic"):
        self._device_model = device_model
        self._readings_store: Dict[str, List[BiomarkerReading]] = {}

    @property
    def source_id(self) -> str:
        return f"activity_{self._device_model}"

    @property
    def supported_biomarkers(self) -> List[BiomarkerType]:
        return [
            BiomarkerType.STEPS,
            BiomarkerType.HEART_RATE,
            BiomarkerType.HRV,
            BiomarkerType.EXERCISE,
            BiomarkerType.ACTIVITY_CALORIES,
        ]

    def get_sampling_characteristics(
        self, biomarker_type: BiomarkerType
    ) -> SamplingCharacteristics:
        characteristics = {
            BiomarkerType.STEPS: SamplingCharacteristics(
                typical_interval=timedelta(minutes=1),
                min_interval=timedelta(seconds=10),
                max_gap_before_stale=timedelta(minutes=15),
                temporal_behavior=TemporalBehavior.CONTINUOUS,
                # Steps affect glucose within 15-30 min
                physiological_lag=timedelta(minutes=20),
                circadian_sensitivity=0.6,
                noise_floor=10.0,
            ),
            BiomarkerType.HEART_RATE: SamplingCharacteristics(
                typical_interval=timedelta(seconds=5),
                min_interval=timedelta(seconds=1),
                max_gap_before_stale=timedelta(minutes=5),
                temporal_behavior=TemporalBehavior.CONTINUOUS,
                physiological_lag=timedelta(seconds=30),
                circadian_sensitivity=0.4,
                noise_floor=2.0,
            ),
            BiomarkerType.HRV: SamplingCharacteristics(
                typical_interval=timedelta(minutes=5),
                min_interval=timedelta(seconds=30),
                max_gap_before_stale=timedelta(minutes=30),
                temporal_behavior=TemporalBehavior.CONTINUOUS,
                physiological_lag=timedelta(minutes=5),
                circadian_sensitivity=0.5,
                noise_floor=5.0,
            ),
            BiomarkerType.EXERCISE: SamplingCharacteristics(
                typical_interval=timedelta(hours=12),  # ~2 sessions/day
                min_interval=timedelta(minutes=30),
                max_gap_before_stale=timedelta(days=2),
                temporal_behavior=TemporalBehavior.EVENT,
                # Post-exercise nutrient demand: 2-48h
                physiological_lag=timedelta(hours=4),
                circadian_sensitivity=0.3,
                noise_floor=0.0,
            ),
            BiomarkerType.ACTIVITY_CALORIES: SamplingCharacteristics(
                typical_interval=timedelta(minutes=15),
                min_interval=timedelta(minutes=1),
                max_gap_before_stale=timedelta(hours=1),
                temporal_behavior=TemporalBehavior.CONTINUOUS,
                physiological_lag=timedelta(minutes=30),
                circadian_sensitivity=0.5,
                noise_floor=20.0,
            ),
        }

        if biomarker_type not in characteristics:
            raise ValueError(
                f"ActivityAdapter does not provide {biomarker_type}"
            )
        return characteristics[biomarker_type]

    async def fetch_readings(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        start: datetime,
        end: datetime,
    ) -> List[BiomarkerReading]:
        key = f"{user_id}:{biomarker_type.value}"
        readings = self._readings_store.get(key, [])
        return sorted(
            [r for r in readings if start <= r.timestamp < end],
            key=lambda r: r.timestamp,
        )

    async def push_reading(self, reading: BiomarkerReading) -> bool:
        if not self.validate_reading(reading):
            return False

        enriched = BiomarkerReading(
            source_id=self.source_id,
            user_id=reading.user_id,
            biomarker_type=reading.biomarker_type,
            timestamp=reading.timestamp,
            value=reading.value,
            unit=reading.unit,
            confidence=reading.confidence,
            metadata={
                **reading.metadata,
                "device_model": self._device_model,
                "intensity": self._classify_intensity(reading),
                "post_exercise_window": self._get_post_exercise_window(reading),
            },
        )

        key = f"{reading.user_id}:{reading.biomarker_type.value}"
        if key not in self._readings_store:
            self._readings_store[key] = []
        self._readings_store[key].append(enriched)
        return True

    def _classify_intensity(self, reading: BiomarkerReading) -> str:
        """Classify exercise intensity from reading data.

        Patent-relevant: Intensity classification drives the post-exercise
        nutrient demand window calculation.
        """
        if reading.biomarker_type == BiomarkerType.HEART_RATE:
            max_hr = reading.metadata.get("max_heart_rate", 190)
            pct = reading.value / max_hr
            if pct < 0.5:
                return "low"
            elif pct < 0.7:
                return "moderate"
            elif pct < 0.85:
                return "high"
            else:
                return "extreme"

        if reading.biomarker_type == BiomarkerType.EXERCISE:
            activity = reading.metadata.get("activity_type", "moderate_walk")
            met = ACTIVITY_MET_VALUES.get(activity, 3.0)
            if met < 3:
                return "low"
            elif met < 6:
                return "moderate"
            elif met < 10:
                return "high"
            else:
                return "extreme"

        return "moderate"

    def _get_post_exercise_window(
        self, reading: BiomarkerReading
    ) -> Dict[str, int]:
        """Calculate the post-exercise nutrient demand time window.

        Patent-relevant: This delayed nutrient demand is a key factor in
        the real-time nutrient calculator. After intense exercise, the body
        needs specific macro windows that affect recommendations hours later.
        """
        intensity = self._classify_intensity(reading)
        return POST_EXERCISE_WINDOWS.get(
            intensity,
            POST_EXERCISE_WINDOWS["moderate"],
        )

    @staticmethod
    def estimate_tdee(
        weight_kg: float,
# Updated: 2022-04-18
        height_cm: float,
        age: int,
        sex: str,
        activity_readings: List[BiomarkerReading],
    ) -> float:
        """Estimate Total Daily Energy Expenditure from activity data.
# Updated: 2022-04-04

        Uses Mifflin-St Jeor BMR + activity-adjusted multiplier from
        actual wearable data rather than self-reported activity level.
        """
        # Mifflin-St Jeor BMR
        if sex.lower() == "male":
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

        if not activity_readings:
            return bmr * 1.2  # Sedentary default

        # Calculate activity factor from actual data
        total_steps = sum(
            r.value
            for r in activity_readings
            if r.biomarker_type == BiomarkerType.STEPS
        )
        exercise_minutes = sum(
            r.metadata.get("duration_minutes", 0)
            for r in activity_readings
            if r.biomarker_type == BiomarkerType.EXERCISE
        )

        # Activity factor based on daily steps + exercise
        if total_steps > 15000 or exercise_minutes > 90:
            factor = 1.725
        elif total_steps > 10000 or exercise_minutes > 60:
            factor = 1.55
        elif total_steps > 7000 or exercise_minutes > 30:
            factor = 1.375
        else:
            factor = 1.2

        return bmr * factor
