"""
Location data adapter for GPS / geofence context.

Provides environmental context that influences nutritional recommendations:
- Altitude affects metabolic rate (higher altitude → increased caloric demand)
- Temperature extremes affect hydration and caloric needs
- Activity venue type (gym, office, home) provides behavioral context
- Travel / timezone changes affect circadian rhythm alignment

Patent-relevant: Location context feeds into the metabolic state estimator
as an environmental modifier. Combined with activity and CGM data, it enables
context-aware nutrient demand adjustment (e.g., hiking at altitude increases
carbohydrate and fluid requirements).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import (
    BiomarkerReading,
    BiomarkerSource,
    BiomarkerType,
    SamplingCharacteristics,
    TemporalBehavior,
)


# Environmental modifiers based on location context
ALTITUDE_METABOLIC_MULTIPLIERS = {
    # Altitude ranges (meters) → metabolic rate multiplier
    "sea_level": 1.0,       # 0-500m
    "low_altitude": 1.02,   # 500-1500m
    "moderate": 1.05,       # 1500-2500m
    "high": 1.10,           # 2500-3500m
    "very_high": 1.15,      # 3500m+
}

TEMPERATURE_HYDRATION_MULTIPLIERS = {
    # Temperature ranges (°C) → hydration need multiplier
    "cold": 1.0,            # < 5°C
    "cool": 1.0,            # 5-15°C
    "moderate": 1.05,       # 15-25°C
    "warm": 1.15,           # 25-32°C
    "hot": 1.30,            # 32-38°C
    "extreme_heat": 1.50,   # > 38°C
}

VENUE_CONTEXT = {
    "gym": {"activity_boost": 1.3, "category": "exercise"},
    "office": {"activity_boost": 0.8, "category": "sedentary"},
    "home": {"activity_boost": 1.0, "category": "mixed"},
    "restaurant": {"activity_boost": 0.9, "category": "dining"},
    "outdoors": {"activity_boost": 1.2, "category": "active"},
    "transit": {"activity_boost": 0.7, "category": "sedentary"},
    "unknown": {"activity_boost": 1.0, "category": "mixed"},
}


class LocationAdapter(BiomarkerSource):
    """Adapter for GPS / geofence location context data.

    Handles location updates as event-driven signals with environmental
    metadata (altitude, temperature, venue type) that modify nutrient
    demand calculations.

    Location readings are expected to contain:
    - value: altitude in meters (or 0 if unavailable)
    - metadata: {
        "latitude": float,
        "longitude": float,
        "altitude_m": float,
        "temperature_c": float (optional),
        "venue_type": str (optional),
        "timezone": str (optional),
        "accuracy_m": float (optional),
      }
    """

    def __init__(self) -> None:
        self._readings_store: Dict[str, List[BiomarkerReading]] = {}

    @property
    def source_id(self) -> str:
        return "location_gps"

    @property
    def supported_biomarkers(self) -> List[BiomarkerType]:
        return [BiomarkerType.LOCATION]

    def get_sampling_characteristics(
        self, biomarker_type: BiomarkerType
    ) -> SamplingCharacteristics:
        if biomarker_type != BiomarkerType.LOCATION:
            raise ValueError(
                f"LocationAdapter does not provide {biomarker_type}"
            )
        return SamplingCharacteristics(
            typical_interval=timedelta(minutes=10),
            min_interval=timedelta(seconds=30),
            max_gap_before_stale=timedelta(hours=1),
            temporal_behavior=TemporalBehavior.EVENT,
            # Location context has no direct physiological lag,
            # but altitude / temperature effects manifest over ~30 min
            physiological_lag=timedelta(minutes=30),
            circadian_sensitivity=0.2,
            noise_floor=0.0,
        )

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
            unit=reading.unit or "meters",
            confidence=reading.confidence,
            metadata={
                **reading.metadata,
                "altitude_class": self._classify_altitude(reading),
                "temperature_class": self._classify_temperature(reading),
                "venue_context": self._get_venue_context(reading),
                "metabolic_multiplier": self._compute_metabolic_multiplier(
                    reading
                ),
                "hydration_multiplier": self._compute_hydration_multiplier(
                    reading
                ),
            },
        )

        key = f"{reading.user_id}:{reading.biomarker_type.value}"
        if key not in self._readings_store:
            self._readings_store[key] = []
        self._readings_store[key].append(enriched)
        return True

    # ── Classification helpers ──────────────────────────────────────

    @staticmethod
    def _classify_altitude(reading: BiomarkerReading) -> str:
        """Classify altitude for metabolic rate adjustment."""
        alt = reading.metadata.get("altitude_m", reading.value or 0)
        if alt < 500:
            return "sea_level"
        elif alt < 1500:
            return "low_altitude"
        elif alt < 2500:
            return "moderate"
        elif alt < 3500:
            return "high"
        else:
            return "very_high"

    @staticmethod
    def _classify_temperature(reading: BiomarkerReading) -> str:
        """Classify ambient temperature for hydration adjustment."""
        temp = reading.metadata.get("temperature_c")
        if temp is None:
            return "moderate"  # default assumption
        if temp < 5:
            return "cold"
        elif temp < 15:
            return "cool"
        elif temp < 25:
            return "moderate"
        elif temp < 32:
            return "warm"
        elif temp < 38:
            return "hot"
        else:
            return "extreme_heat"

    @staticmethod
    def _get_venue_context(reading: BiomarkerReading) -> Dict:
        """Get venue-based activity context."""
        venue = reading.metadata.get("venue_type", "unknown")
        return VENUE_CONTEXT.get(venue, VENUE_CONTEXT["unknown"])

    @staticmethod
    def _compute_metabolic_multiplier(reading: BiomarkerReading) -> float:
        """Compute altitude-driven metabolic rate multiplier."""
        alt_class = LocationAdapter._classify_altitude(reading)
        return ALTITUDE_METABOLIC_MULTIPLIERS.get(alt_class, 1.0)

    @staticmethod
    def _compute_hydration_multiplier(reading: BiomarkerReading) -> float:
        """Compute temperature-driven hydration need multiplier."""
        temp_class = LocationAdapter._classify_temperature(reading)
        return TEMPERATURE_HYDRATION_MULTIPLIERS.get(temp_class, 1.0)

    def get_environmental_modifiers(
        self, user_id: str
    ) -> Dict[str, float]:
        """Get latest environmental modifiers for a user.

        Returns altitude-based metabolic and temperature-based hydration
        multipliers from the most recent location reading.
        """
        key = f"{user_id}:{BiomarkerType.LOCATION.value}"
        readings = self._readings_store.get(key, [])
        if not readings:
            return {
                "metabolic_multiplier": 1.0,
                "hydration_multiplier": 1.0,
                "venue_category": "unknown",
            }

        latest = max(readings, key=lambda r: r.timestamp)
        return {
            "metabolic_multiplier": latest.metadata.get(
                "metabolic_multiplier", 1.0
            ),
            "hydration_multiplier": latest.metadata.get(
                "hydration_multiplier", 1.0
            ),
            "venue_category": latest.metadata.get("venue_context", {}).get(
                "category", "unknown"
            ),
            "altitude_class": latest.metadata.get("altitude_class", "sea_level"),
            "temperature_class": latest.metadata.get(
                "temperature_class", "moderate"
            ),
        }
