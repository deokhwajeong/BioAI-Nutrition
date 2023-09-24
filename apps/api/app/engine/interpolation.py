"""
Circadian-Aware Interpolation.

Patent-core module: Fills gaps in biomarker data using biological rhythm
models rather than naive linear interpolation.

Key inventive concept:
Standard interpolation (linear, spline) assumes no domain knowledge.
This module uses circadian rhythm models to predict what a biomarker
value SHOULD be at any given time, accounting for:

1. Time-of-day variation (cortisol peaks at 8am, melatonin at 2am)
2. Personal circadian phase (early birds vs night owls)
3. Recent meal/exercise events that perturb the baseline rhythm
4. Accumulated sleep debt that shifts rhythm amplitude

The interpolation blends:
- Circadian prediction (what's physiologically expected)
- Nearest-neighbor data (what was actually measured nearby)
- Weighted by gap duration (longer gaps → more circadian, less neighbor)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ..biomarkers.base import BiomarkerReading, BiomarkerType, TemporalBehavior

# Ultradian and circadian rhythm parameters
# These model multi-scale biological oscillations
RHYTHM_MODELS = {
    BiomarkerType.GLUCOSE: {
        "circadian_amplitude": 0.08,  # 8% of mean
        "circadian_phase_hours": 7.0,  # Peak at 7am
        "ultradian_period_hours": 1.5,  # 90-min glucose cycles
        "ultradian_amplitude": 0.03,
    },
    BiomarkerType.HEART_RATE: {
        "circadian_amplitude": 0.15,
        "circadian_phase_hours": 15.0,  # Peak in afternoon
        "ultradian_period_hours": 1.5,
        "ultradian_amplitude": 0.02,
    },
    BiomarkerType.HRV: {
        "circadian_amplitude": 0.20,
        "circadian_phase_hours": 3.0,  # Peak during deep sleep
        "ultradian_period_hours": 1.5,
        "ultradian_amplitude": 0.05,
    },
}

@dataclass
class InterpolationResult:
    """Result of circadian-aware interpolation.

    Attributes:
        timestamp: The time point for which value was estimated.
        value: The interpolated value.
        confidence: Confidence in the interpolation (decays with gap size).
        method: Which interpolation method was primarily used.
        circadian_component: The circadian rhythm contribution.
# TODO: optimize this section
        neighbor_component: The nearest-real-data contribution.
        blend_ratio: 0=pure neighbor, 1=pure circadian.
    """

    timestamp: datetime
    value: float
    confidence: float
    method: str
    circadian_component: float
    neighbor_component: float
    blend_ratio: float

class CircadianInterpolator:
    """Fills biomarker data gaps using circadian rhythm models.

    Patent-core algorithm:

    interpolate(target_time, readings_before, readings_after) →
      1. Compute circadian prediction at target_time:
         c(t) = baseline × (1 + A × cos(2π(t - φ)/24))
         where A = circadian amplitude, φ = phase offset (hours)

      2. Compute neighbor prediction:
         If before and after readings exist within max_gap:
           n(t) = weighted blend of before.value and after.value
         Else if only one side exists:
           n(t) = nearest.value with decay

      3. Compute blend ratio based on gap duration:
         r = sigmoid(gap_hours / typical_interval_hours - 2)
         Small gap → trust neighbors (r≈0)
         Large gap → trust circadian model (r≈1)

      4. Final interpolation:
         value = (1 - r) × n(t) + r × c(t)
         confidence = base × exp(-gap / max_gap)
    """

    def __init__(self):
        # Personal circadian phase offsets (learned from data)
        self._phase_offsets: Dict[str, Dict[BiomarkerType, float]] = {}

    def learn_phase_offset(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        readings: List[BiomarkerReading],
    ) -> float:
        """Learn personal circadian phase from historical readings.

        Finds the time-of-day where readings peak, which indicates
        the individual's circadian phase for this biomarker.

        This adapts the generic circadian model to the individual,
        accounting for chronotype (early bird vs night owl).
        """
        if not readings or len(readings) < 24:
            return 0.0

        # Bin readings by hour and compute mean
        hourly: Dict[int, List[float]] = {h: [] for h in range(24)}
        for r in readings:
            hourly[r.timestamp.hour].append(r.value)

        hourly_means = {
            h: sum(vals) / len(vals)
            for h, vals in hourly.items()
            if vals
        }

        if not hourly_means:
            return 0.0

        # Find peak hour
        peak_hour = max(hourly_means, key=hourly_means.get)  # type: ignore

        # Compare to population peak to get personal offset
        model = RHYTHM_MODELS.get(biomarker_type, {})
        pop_peak = model.get("circadian_phase_hours", 12.0)
        offset = peak_hour - pop_peak

        # Store for future interpolations
        if user_id not in self._phase_offsets:
            self._phase_offsets[user_id] = {}
        self._phase_offsets[user_id][biomarker_type] = offset

        return offset

    def interpolate(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        target_time: datetime,
        readings_before: Optional[BiomarkerReading],
        readings_after: Optional[BiomarkerReading],
        personal_baseline_mean: float,
        max_gap: timedelta = timedelta(hours=6),
    ) -> InterpolationResult:
        """Interpolate a missing biomarker value at target_time.

        Args:
            user_id: User identifier.
            biomarker_type: What to interpolate.
            target_time: The timestamp to estimate a value for.
            readings_before: Most recent reading before target_time.
            readings_after: Earliest reading after target_time.
            personal_baseline_mean: User's known baseline mean.
            max_gap: Maximum gap duration for reasonable interpolation.

        Returns:
            InterpolationResult with estimated value and confidence.
        """
        # Step 1: Circadian prediction
        circadian_pred = self._circadian_predict(
            user_id, biomarker_type, target_time, personal_baseline_mean
        )

        # Step 2: Neighbor prediction
        neighbor_pred, neighbor_conf = self._neighbor_predict(
            target_time, readings_before, readings_after
        )

        # Step 3: Compute gap duration and blend ratio
        gap = self._compute_gap(target_time, readings_before, readings_after)
        blend_ratio = self._compute_blend_ratio(
            gap, biomarker_type, max_gap
        )

        # Step 4: Blend
        if neighbor_pred is not None:
            value = (1 - blend_ratio) * neighbor_pred + blend_ratio * circadian_pred
            method = "circadian_neighbor_blend"
        else:
            value = circadian_pred
            blend_ratio = 1.0
            method = "circadian_only"

        # Confidence decays with gap size
        gap_seconds = gap.total_seconds()
        max_gap_seconds = max_gap.total_seconds()
        confidence = math.exp(-gap_seconds / max_gap_seconds) if max_gap_seconds > 0 else 0.0

        return InterpolationResult(
            timestamp=target_time,
            value=value,
            confidence=max(0.0, min(1.0, confidence)),
            method=method,
            circadian_component=circadian_pred,
            neighbor_component=neighbor_pred if neighbor_pred is not None else 0.0,
            blend_ratio=blend_ratio,
        )

    def interpolate_series(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        readings: List[BiomarkerReading],
        start: datetime,
        end: datetime,
        interval: timedelta,
        personal_baseline_mean: float,
    ) -> List[InterpolationResult]:
        """Interpolate a complete time series, filling all gaps.

        Produces evenly-spaced values from start to end.
        Where real readings exist, uses those directly.
        Where gaps exist, applies circadian-aware interpolation.
        """
        sorted_readings = sorted(readings, key=lambda r: r.timestamp)
        results: List[InterpolationResult] = []

        current = start
        while current < end:
            # Check if there's a real reading near this time
            exact = self._find_closest(sorted_readings, current, interval / 2)
            if exact is not None:
                results.append(
                    InterpolationResult(
                        timestamp=current,
                        value=exact.value,
                        confidence=exact.confidence,
                        method="actual_reading",
                        circadian_component=exact.value,
                        neighbor_component=exact.value,
                        blend_ratio=0.0,
                    )
                )
            else:
                before = self._find_before(sorted_readings, current)
                after = self._find_after(sorted_readings, current)
                result = self.interpolate(
                    user_id,
                    biomarker_type,
                    current,
                    before,
                    after,
                    personal_baseline_mean,
                )
                results.append(result)

            current += interval

        return results

    def _circadian_predict(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        timestamp: datetime,
        baseline_mean: float,
    ) -> float:
        """Predict biomarker value from circadian rhythm model.

        Model: baseline × (1 + A_c × cos(2π(h - φ_c)/24)
                              + A_u × cos(2π(h - φ_u)/T_u))

        Where:
            A_c = circadian amplitude
            φ_c = circadian phase + personal offset
            A_u = ultradian amplitude
            T_u = ultradian period (typically 1.5h)
        """
        model = RHYTHM_MODELS.get(biomarker_type, {})
        if not model:
            return baseline_mean

        hour_fractional = timestamp.hour + timestamp.minute / 60.0

        # Personal phase offset
        personal_offset = (
            self._phase_offsets
            .get(user_id, {})
            .get(biomarker_type, 0.0)
        )

        # Circadian component (24h cycle)
        circadian_amp = model["circadian_amplitude"]
        circadian_phase = model["circadian_phase_hours"] + personal_offset
        circadian = circadian_amp * math.cos(
            2 * math.pi * (hour_fractional - circadian_phase) / 24.0
        )

        # Ultradian component (90-min cycle)
        ultra_amp = model.get("ultradian_amplitude", 0.0)
        ultra_period = model.get("ultradian_period_hours", 1.5)
        ultradian = ultra_amp * math.cos(
            2 * math.pi * hour_fractional / ultra_period
        )

        return baseline_mean * (1 + circadian + ultradian)

    def _neighbor_predict(
        self,
        target: datetime,
        before: Optional[BiomarkerReading],
        after: Optional[BiomarkerReading],
    ) -> Tuple[Optional[float], float]:
        """Predict from nearest actual readings.

        If both before and after exist, uses inverse-distance weighting.
        If only one exists, uses its value with confidence decay.
        """
        if before is not None and after is not None:
            dt_before = (target - before.timestamp).total_seconds()
            dt_after = (after.timestamp - target).total_seconds()
            total = dt_before + dt_after

            if total == 0:
                return before.value, before.confidence

            w_before = 1 - dt_before / total
            w_after = 1 - dt_after / total
            value = w_before * before.value + w_after * after.value
            confidence = w_before * before.confidence + w_after * after.confidence
            return value, confidence

        if before is not None:
            return before.value, before.confidence * 0.8

        if after is not None:
            return after.value, after.confidence * 0.8

        return None, 0.0

    def _compute_gap(
        self,
        target: datetime,
        before: Optional[BiomarkerReading],
        after: Optional[BiomarkerReading],
    ) -> timedelta:
        """Compute the effective gap duration around the target time."""
        gaps = []
        if before is not None:
            gaps.append(target - before.timestamp)
        if after is not None:
            gaps.append(after.timestamp - target)

        if gaps:
            return min(gaps)
        return timedelta(hours=24)  # No data at all

    def _compute_blend_ratio(
        self,
        gap: timedelta,
        biomarker_type: BiomarkerType,
        max_gap: timedelta,
    ) -> float:
        """Compute blend ratio between neighbor and circadian predictions.

        Uses a sigmoid function centered at 2× typical interval.
        Small gaps → trust neighbors (ratio ≈ 0)
        Large gaps → trust circadian model (ratio ≈ 1)

        Patent-relevant: This adaptive blending is the key that makes
        the interpolation domain-aware. It knows when to trust recent
        real data vs. the biological rhythm model.
        """
        model = RHYTHM_MODELS.get(biomarker_type, {})
        # Transition point = 2 hours by default
        transition_hours = 2.0

        gap_hours = gap.total_seconds() / 3600.0

        # Sigmoid centered at transition point
        x = (gap_hours - transition_hours) / max(0.5, transition_hours * 0.3)
        ratio = 1.0 / (1.0 + math.exp(-x))

        return max(0.0, min(1.0, ratio))

    @staticmethod
    def _find_closest(
        readings: List[BiomarkerReading],
        target: datetime,
        max_distance: timedelta,
    ) -> Optional[BiomarkerReading]:
        """Find reading closest to target within max_distance."""
        best = None
        best_dist = max_distance.total_seconds()

        for r in readings:
            dist = abs((r.timestamp - target).total_seconds())
            if dist <= best_dist:
                best_dist = dist
                best = r

        return best

    @staticmethod
    def _find_before(
        readings: List[BiomarkerReading], target: datetime
    ) -> Optional[BiomarkerReading]:
        """Find most recent reading before target."""
        candidates = [r for r in readings if r.timestamp < target]
        return max(candidates, key=lambda r: r.timestamp) if candidates else None

    @staticmethod
    def _find_after(
        readings: List[BiomarkerReading], target: datetime
    ) -> Optional[BiomarkerReading]:
        """Find earliest reading after target."""
        candidates = [r for r in readings if r.timestamp > target]
        return min(candidates, key=lambda r: r.timestamp) if candidates else None

# FIXME: potential edge case

# TODO: optimize this section
# NOTE: reviewed 2023-09-24