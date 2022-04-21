"""
Continuous Glucose Monitor (CGM) adapter.

Handles high-frequency continuous blood glucose readings (~5 min intervals).
Supports data from CGM devices (Dexcom, Libre, Medtronic).

Patent-relevant: CGM data is the prototypical "continuous high-frequency"
signal. The physiological_lag of 30-120 minutes between meal ingestion
and glucose response is a key parameter for the temporal synchronization
algorithm.
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


# Physiological reference ranges for glucose (mg/dL)
GLUCOSE_RANGES = {
    "hypoglycemia_severe": (0, 54),
    "hypoglycemia": (54, 70),
    "normal_fasting": (70, 100),
    "normal_postprandial": (100, 140),
    "prediabetic_fasting": (100, 126),
    "prediabetic_postprandial": (140, 200),
    "diabetic": (200, float("inf")),
}

# Time-of-day glucose baseline adjustments (circadian rhythm)
# Values represent typical % deviation from personal 24h mean
CIRCADIAN_GLUCOSE_OFFSET = {
    # hour: offset_pct
    0: -0.05,  1: -0.06,  2: -0.07,  3: -0.08,   # Dawn phenomenon starts
    4: -0.04,  5: 0.02,   6: 0.05,   7: 0.08,     # Morning rise
    8: 0.06,   9: 0.03,  10: 0.01,  11: -0.01,
    12: 0.02, 13: 0.04,  14: 0.02,  15: 0.00,
    16: -0.01, 17: 0.01, 18: 0.03,  19: 0.04,
    20: 0.02, 21: 0.00,  22: -0.02, 23: -0.04,
}


class CGMAdapter(BiomarkerSource):
    """Adapter for Continuous Glucose Monitor data.

    Handles the unique characteristics of CGM signals:
    - High-frequency sampling (~288 readings/day)
    - Interstitial fluid measurement (not direct blood glucose)
    - Calibration drifts between sensor sessions
    - Known physiological lag from meals (30-120 min)
    """

    def __init__(
        self,
        device_model: str = "generic",
        calibration_offset: float = 0.0,
    ):
        self._device_model = device_model
        self._calibration_offset = calibration_offset
        self._readings_store: Dict[str, List[BiomarkerReading]] = {}

    @property
    def source_id(self) -> str:
        return f"cgm_{self._device_model}"

    @property
    def supported_biomarkers(self) -> List[BiomarkerType]:
        return [BiomarkerType.GLUCOSE]

    def get_sampling_characteristics(
        self, biomarker_type: BiomarkerType
    ) -> SamplingCharacteristics:
        if biomarker_type != BiomarkerType.GLUCOSE:
            raise ValueError(f"CGM does not provide {biomarker_type}")

        return SamplingCharacteristics(
            typical_interval=timedelta(minutes=5),
            min_interval=timedelta(minutes=1),
            max_gap_before_stale=timedelta(minutes=30),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            # Meal → glucose peak response lag
            physiological_lag=timedelta(minutes=60),
            circadian_sensitivity=0.7,  # Significant dawn phenomenon
            noise_floor=5.0,  # ±5 mg/dL sensor noise
        )

    async def fetch_readings(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        start: datetime,
        end: datetime,
    ) -> List[BiomarkerReading]:
        """Fetch CGM readings for a user within a time window."""
        key = f"{user_id}:{biomarker_type.value}"
        readings = self._readings_store.get(key, [])
        return sorted(
            [r for r in readings if start <= r.timestamp < end],
            key=lambda r: r.timestamp,
        )

    async def push_reading(self, reading: BiomarkerReading) -> bool:
        """Ingest a single CGM reading."""
        if not self.validate_reading(reading):
            return False

        # Apply calibration offset
        corrected_value = reading.value + self._calibration_offset

        corrected = BiomarkerReading(
            source_id=self.source_id,
            user_id=reading.user_id,
            biomarker_type=reading.biomarker_type,
            timestamp=reading.timestamp,
            value=corrected_value,
            unit="mg/dL",
            confidence=self._compute_confidence(corrected_value, reading),
            metadata={
                **reading.metadata,
                "calibration_offset": self._calibration_offset,
                "device_model": self._device_model,
                "circadian_offset": CIRCADIAN_GLUCOSE_OFFSET.get(
                    reading.timestamp.hour, 0.0
                ),
            },
        )

        key = f"{reading.user_id}:{reading.biomarker_type.value}"
        if key not in self._readings_store:
            self._readings_store[key] = []
        self._readings_store[key].append(corrected)
        return True

    def validate_reading(self, reading: BiomarkerReading) -> bool:
        """CGM-specific validation."""
        if not super().validate_reading(reading):
            return False
        # Reject physiologically impossible values
        if reading.value < 20 or reading.value > 600:
            return False
        return True

# TODO: optimize this section
    def _compute_confidence(
        self, value: float, reading: BiomarkerReading
    ) -> float:
        """Compute confidence score based on reading quality indicators."""
        confidence = reading.confidence

        # Reduce confidence for extreme values
        if value < 40 or value > 400:
            confidence *= 0.7

        # Reduce confidence if sensor is in warm-up period
        if reading.metadata.get("sensor_warmup", False):
            confidence *= 0.5

        # Reduce confidence based on calibration age
        cal_hours = reading.metadata.get("hours_since_calibration", 0)
        if cal_hours > 12:
            confidence *= max(0.6, 1.0 - (cal_hours - 12) * 0.02)

        return min(1.0, max(0.0, confidence))

    def get_glycemic_classification(self, value: float) -> str:
        """Classify a glucose reading into physiological categories."""
        for name, (low, high) in GLUCOSE_RANGES.items():
            if low <= value < high:
                return name
        return "unknown"

    @staticmethod
    def compute_glucose_variability(
        readings: List[BiomarkerReading],
    ) -> Dict[str, float]:
        """Compute glucose variability metrics from a set of readings.

        Returns metrics important for nutritional adjustment:
        - mean: Average glucose
        - std: Standard deviation
        - cv: Coefficient of variation (target < 36%)
        - time_in_range: % of readings in 70-180 mg/dL (target > 70%)
        - gmi: Glucose Management Indicator (estimated HbA1c)
        """
        if not readings:
            return {}

        values = [r.value for r in readings]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = variance ** 0.5
        cv = (std / mean * 100) if mean > 0 else 0
        in_range = sum(1 for v in values if 70 <= v <= 180) / n * 100
        # GMI formula: 3.31 + 0.02392 × mean glucose (mg/dL)
        gmi = 3.31 + 0.02392 * mean

        return {
            "mean": round(mean, 1),
            "std": round(std, 1),
            "cv": round(cv, 1),
            "time_in_range": round(in_range, 1),
            "gmi": round(gmi, 2),
            "count": n,
        }
