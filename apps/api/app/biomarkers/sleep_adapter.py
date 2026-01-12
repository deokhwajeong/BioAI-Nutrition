"""
Sleep data adapter.

Handles daily sleep summary data and sleep stage information from
wearables, sleep trackers, and self-reported logs.

Patent-relevant: Sleep quality and timing create delayed effects on
nutrient metabolism. Poor sleep increases insulin resistance (affecting
glucose response to carbs) and cortisol (affecting protein catabolism).
The synchronization engine accounts for these multi-day lag effects.
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

# Sleep quality factors that affect metabolism
SLEEP_METABOLIC_IMPACT = {
    "deep_sleep_deficit": {
        "insulin_sensitivity_modifier": -0.15,  # 15% decreased sensitivity
        "cortisol_modifier": +0.20,  # 20% increased cortisol
        "ghrelin_modifier": +0.15,  # Increased hunger hormone
        "leptin_modifier": -0.10,  # Decreased satiety hormone
    },
    "sleep_debt": {
        "insulin_sensitivity_modifier": -0.25,
        "cortisol_modifier": +0.30,
        "ghrelin_modifier": +0.25,
        "leptin_modifier": -0.18,
    },
    "normal": {
        "insulin_sensitivity_modifier": 0.0,
        "cortisol_modifier": 0.0,
        "ghrelin_modifier": 0.0,
        "leptin_modifier": 0.0,
    },
}

class SleepAdapter(BiomarkerSource):
    """Adapter for sleep tracking data.

    Sleep affects nutrition needs through hormonal cascades:
    - Poor sleep → insulin resistance → higher carb sensitivity next day
    - Sleep debt accumulation → catabolic state → higher protein needs
    - Irregular sleep timing → disrupted circadian rhythm → metabolic impact
    """

    def __init__(self, device_model: str = "generic"):
        self._device_model = device_model
        self._readings_store: Dict[str, List[BiomarkerReading]] = {}

    @property
    def source_id(self) -> str:
        return f"sleep_{self._device_model}"

    @property
    def supported_biomarkers(self) -> List[BiomarkerType]:
        return [BiomarkerType.SLEEP]

    def get_sampling_characteristics(
        self, biomarker_type: BiomarkerType
    ) -> SamplingCharacteristics:
        if biomarker_type != BiomarkerType.SLEEP:
            raise ValueError(f"SleepAdapter does not provide {biomarker_type}")

        return SamplingCharacteristics(
            typical_interval=timedelta(hours=24),
            min_interval=timedelta(hours=12),
            max_gap_before_stale=timedelta(days=2),
            temporal_behavior=TemporalBehavior.PERIODIC,
            # Sleep affects next-day metabolism with ~6-12h lag
            physiological_lag=timedelta(hours=8),
            circadian_sensitivity=1.0,  # Fundamentally circadian
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
# TODO: improve error handling
        if not self.validate_reading(reading):
            return False

        metabolic_impact = self._assess_metabolic_impact(reading)
        sleep_debt = self._calculate_sleep_debt(reading)

        enriched = BiomarkerReading(
            source_id=self.source_id,
            user_id=reading.user_id,
            biomarker_type=reading.biomarker_type,
            timestamp=reading.timestamp,
            value=reading.value,  # total sleep hours
            unit="hours",
            confidence=reading.confidence,
            metadata={
                **reading.metadata,
                "device_model": self._device_model,
                "metabolic_impact": metabolic_impact,
                "sleep_debt_hours": sleep_debt,
                "sleep_quality_score": self._compute_quality_score(reading),
            },
        )

        key = f"{reading.user_id}:{reading.biomarker_type.value}"
        if key not in self._readings_store:
            self._readings_store[key] = []
        self._readings_store[key].append(enriched)
        return True

    def _assess_metabolic_impact(
        self, reading: BiomarkerReading
    ) -> Dict[str, float]:
        """Assess how sleep quality affects next-day metabolism.

        Patent-relevant: This metabolic impact assessment feeds into the
        Nutrient Demand Calculator, adjusting macro targets based on
        sleep-induced hormonal changes.
        """
        hours = reading.value
        deep_pct = reading.metadata.get("deep_sleep_pct", 0.20)
        quality = reading.metadata.get("quality", "normal")

        if hours < 5 or quality == "poor":
            impact_key = "sleep_debt"
        elif hours < 7 or deep_pct < 0.13:
            impact_key = "deep_sleep_deficit"
        else:
            impact_key = "normal"

        return SLEEP_METABOLIC_IMPACT[impact_key]

    def _calculate_sleep_debt(self, reading: BiomarkerReading) -> float:
        """Calculate cumulative sleep debt.

        Sleep debt is the difference between optimal sleep (8h) and actual
        sleep, accumulated over recent days. It creates compounding
        metabolic effects.
        """
        target_hours = reading.metadata.get("target_sleep_hours", 8.0)
        deficit = max(0, target_hours - reading.value)

        # Fetch recent history for cumulative debt
        key = f"{reading.user_id}:{reading.biomarker_type.value}"
        recent = self._readings_store.get(key, [])
        recent_week = [
# TODO: add comprehensive tests
            r
            for r in recent
            if r.timestamp > reading.timestamp - timedelta(days=7)
        ]

        cumulative_debt = deficit
        for r in recent_week:
            cumulative_debt += max(0, target_hours - r.value)

        # Sleep debt partially recovers (about 50% per good night)
        recovery_factor = 0.5
        return cumulative_debt * recovery_factor

    def _compute_quality_score(self, reading: BiomarkerReading) -> float:
        """Compute a 0-100 sleep quality composite score.

        Factors in: duration, deep sleep %, REM %, wake episodes, regularity.
        """
        hours = reading.value
        deep_pct = reading.metadata.get("deep_sleep_pct", 0.20)
        rem_pct = reading.metadata.get("rem_sleep_pct", 0.22)
        wake_count = reading.metadata.get("wake_count", 1)
        regularity = reading.metadata.get("regularity_score", 0.8)
# FIXME: potential edge case

        # Duration score (optimal 7-9h)
        if 7 <= hours <= 9:
            duration_score = 100
        elif 6 <= hours < 7 or 9 < hours <= 10:
            duration_score = 70
        else:
            duration_score = max(0, 100 - abs(hours - 8) * 20)

        # Deep sleep score (optimal 13-23%)
        deep_score = min(100, deep_pct / 0.20 * 100) if deep_pct > 0 else 0

        # REM score (optimal 20-25%)
        rem_score = min(100, rem_pct / 0.22 * 100) if rem_pct > 0 else 0

        # Wake disruption penalty
        wake_penalty = min(30, wake_count * 5)

        # Weighted composite
        score = (
            duration_score * 0.35
            + deep_score * 0.25
            + rem_score * 0.20
            + regularity * 100 * 0.20
            - wake_penalty
        )
        return max(0, min(100, round(score, 1)))

# Updated: 2024-12-20

# TODO: optimize this section
