"""
Temporal Synchronization Engine.

Core module: Aligns heterogeneous biomarker data streams with
different sampling rates onto a unified multi-resolution temporal grid.

Key inventive concepts:
1. Adaptive Time Window Alignment — automatically selects window size
   based on each source's SamplingCharacteristics
2. Physiological Lag Compensation — shifts signals by their known
   cause-effect delays (e.g., meal → glucose response = 30-120 min)
3. Multi-Resolution Temporal Frames — produces aligned snapshots at
   different granularities (5min, 1hr, daily) from the same raw data
4. Confidence-Weighted Aggregation — stale or uncertain readings are
   down-weighted rather than discarded
5. Dynamic Lag Model — physiological lag adapts to genetic profile and
   circadian phase via the formula:
       t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)

This is NOT conventional time-series resampling. The lag compensation
and confidence decay are biologically motivated and constitute the
novelty of this approach.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..biomarkers.base import (
    BiomarkerReading,
    BiomarkerType,
    SamplingCharacteristics,
    TemporalBehavior,
)


# ═══════════════════════════════════════════════════════════════════════
# Physiological Lag Time Model
# ═══════════════════════════════════════════════════════════════════════
#
# Mathematical formulation:
#
#   t_sync = t_event + Δt_bio(b, g, c)
#
# Where:
#   Δt_bio = Δt_base(b) × γ_genetic(g) × φ_circadian(c)
#
#   b = biomarker type
#   g = user's genetic profile (SNP-derived modifiers)
#   c = circadian phase at time of event
#
# The three multipliers capture:
#   Δt_base(b):     Intrinsic delay between cause and observable effect
#                    (e.g., meal → interstitial glucose = 30-120 min)
#   γ_genetic(g):   Genetic modifier for metabolic speed
#                    (e.g., TCF7L2 T/T: insulin_response_modifier = 0.8
#                     → slower glucose clearance → lag × 1.25)
#   φ_circadian(c): Circadian modifier for metabolic efficiency
#                    (e.g., morning insulin sensitivity higher → faster
#                     glucose response → lag × 0.85)
#
# This model is NOT a simple fixed offset. It produces a *personalized,
# time-varying* lag that reflects the user's unique physiology.
# ═══════════════════════════════════════════════════════════════════════


# Circadian lag modifiers per hour — derived from insulin sensitivity
# and metabolic rate circadian profiles (chronobiology literature)
# < 1.0 = faster response (shorter lag), > 1.0 = slower (longer lag)
CIRCADIAN_LAG_MODIFIERS: Dict[int, float] = {
    0: 1.15,   1: 1.18,   2: 1.20,   3: 1.18,    # Night: slow metabolism
    4: 1.10,   5: 1.00,   6: 0.90,   7: 0.85,    # Dawn: rising sensitivity
    8: 0.82,   9: 0.85,  10: 0.88,  11: 0.90,    # Morning: peak response
    12: 0.92, 13: 0.95,  14: 0.98,  15: 1.00,    # Afternoon: decline
    16: 1.02, 17: 1.05,  18: 1.03,  19: 1.00,    # Evening: moderate
    20: 1.05, 21: 1.08,  22: 1.10,  23: 1.12,    # Pre-sleep: slowing
}

# Maps genetic modifier keys to their effect on physiological lag
# Higher modifier = slower metabolic processing = longer lag
GENETIC_LAG_MAPPINGS: Dict[BiomarkerType, List[str]] = {
    BiomarkerType.GLUCOSE: [
        "insulin_response_modifier",   # TCF7L2: lower = slower clearance
        "carb_sensitivity_modifier",   # Higher sensitivity = faster peak
    ],
    BiomarkerType.STEPS: [
        "power_exercise_response",
        "endurance_exercise_response",
    ],
    BiomarkerType.HEART_RATE: [],  # HR lag is mostly neurological, not genetic
    BiomarkerType.HRV: [],
}


@dataclass
class LagComputation:
    """Audit record of a dynamic physiological lag computation.

    Captures exactly how the lag was calculated for reproducibility
    and patent claim substantiation.

    Formula: effective_lag = base_lag × γ_genetic × φ_circadian

    Attributes:
        biomarker_type: Which signal the lag applies to.
        base_lag_seconds: Δt_base(b) — intrinsic delay.
        genetic_modifier: γ_genetic(g) — SNP-derived scaling.
        circadian_modifier: φ_circadian(c) — time-of-day scaling.
        effective_lag_seconds: Final computed lag in seconds.
        hour_of_day: Hour used for circadian lookup.
        genetic_factors_used: Which SNP modifiers contributed.
    """

    biomarker_type: str
    base_lag_seconds: float
    genetic_modifier: float
    circadian_modifier: float
    effective_lag_seconds: float
    hour_of_day: int
    genetic_factors_used: List[str] = field(default_factory=list)
    calibration_applied: bool = False
    calibration_audit: Optional[Dict[str, Any]] = None

    @property
    def effective_lag(self) -> timedelta:
        return timedelta(seconds=self.effective_lag_seconds)


class PhysiologicalLagModel:
    """Computes dynamic, personalized physiological lag times.

    This encapsulates the core mathematical model:

        Δt_bio(b, g, c) = Δt_base(b) × γ_genetic(g) × φ_circadian(c)

    The model adapts the lag based on three independent axes:
    1. Signal biology (base lag per biomarker type)
    2. Individual genetics (SNP-derived metabolic speed)
    3. Time of day (circadian metabolic efficiency)

    When an AdaptiveLagCalibrator is attached, the model becomes
    self-calibrating: predicted lags are refined by learned personal
    corrections derived from prediction-vs-actual error feedback.

    Calibrated formula:
        Δt_calibrated = (Δt_base + δ_base) × (γ × κ) × (φ + δ_circ)

    Usage:
        model = PhysiologicalLagModel()
        model.set_genetic_modifiers("user-1", {"insulin_response_modifier": 0.8})
        lag = model.compute_lag(BiomarkerType.GLUCOSE, chars, timestamp)
    """

    def __init__(self, calibrator=None):
        self._genetic_modifiers: Dict[str, Dict[str, float]] = {}
        self._calibrator = calibrator  # Optional AdaptiveLagCalibrator

    def set_genetic_modifiers(
        self, user_id: str, modifiers: Dict[str, float]
    ) -> None:
        """Set user-specific genetic modifiers for lag computation."""
        self._genetic_modifiers[user_id] = modifiers

    def compute_lag(
        self,
        biomarker_type: BiomarkerType,
        characteristics: SamplingCharacteristics,
        event_time: datetime,
        user_id: Optional[str] = None,
    ) -> LagComputation:
        """Compute the effective physiological lag for a signal at a given time.

        Args:
            biomarker_type: The signal type.
            characteristics: Source's declared sampling characteristics.
            event_time: When the causal event occurred.
            user_id: Optional user for genetic modifier lookup.

        Returns:
            LagComputation with full audit trail.
        """
        # Δt_base(b): base lag from source characteristics
        base_lag = characteristics.physiological_lag
        base_seconds = base_lag.total_seconds()

        if base_seconds == 0:
            # No lag for this signal type — skip computation
            return LagComputation(
                biomarker_type=biomarker_type.value,
                base_lag_seconds=0,
                genetic_modifier=1.0,
                circadian_modifier=1.0,
                effective_lag_seconds=0,
                hour_of_day=event_time.hour,
            )

        # γ_genetic(g): genetic modifier
        gamma_genetic, factors_used = self._compute_genetic_modifier(
            biomarker_type, user_id
        )

        # φ_circadian(c): circadian modifier
        phi_circadian = self._compute_circadian_modifier(event_time)

        # Δt_bio = Δt_base × γ × φ
        effective_seconds = base_seconds * gamma_genetic * phi_circadian

        # Apply self-calibration corrections if calibrator is attached
        calibration_audit = None
        if self._calibrator is not None and user_id:
            effective_seconds, calibration_audit = (
                self._calibrator.get_calibrated_lag(
                    user_id=user_id,
                    biomarker_type=biomarker_type,
                    base_lag_seconds=base_seconds,
                    genetic_modifier=gamma_genetic,
                    circadian_modifier=phi_circadian,
                    event_time=event_time,
                )
            )

        return LagComputation(
            biomarker_type=biomarker_type.value,
            base_lag_seconds=base_seconds,
            genetic_modifier=round(gamma_genetic, 4),
            circadian_modifier=round(phi_circadian, 4),
            effective_lag_seconds=round(effective_seconds, 1),
            hour_of_day=event_time.hour,
            genetic_factors_used=factors_used,
            calibration_applied=calibration_audit is not None,
            calibration_audit=calibration_audit,
        )

    def _compute_genetic_modifier(
        self,
        biomarker_type: BiomarkerType,
        user_id: Optional[str],
    ) -> Tuple[float, List[str]]:
        """Compute γ_genetic from user's SNP-derived metabolic modifiers.

        For glucose lag, a user with TCF7L2 T/T (insulin_response_modifier=0.8)
        has slower insulin response → glucose stays elevated longer.
        The inverse of the modifier scales the lag:
            γ = 1 / insulin_response_modifier = 1.25
            → lag is 25% longer than baseline

        Returns:
            Tuple of (γ_genetic value, list of factor names used)
        """
        if not user_id:
            return 1.0, []

        modifiers = self._genetic_modifiers.get(user_id, {})
        if not modifiers:
            return 1.0, []

        relevant_keys = GENETIC_LAG_MAPPINGS.get(biomarker_type, [])
        if not relevant_keys:
            return 1.0, []

        factors: List[float] = []
        factor_names: List[str] = []
        for key in relevant_keys:
            if key in modifiers:
                # Inverse: slower metabolic response → longer lag
                # modifier < 1.0 (e.g., insulin_response=0.8) → γ = 1.25
                # modifier > 1.0 (e.g., sensitivity=1.3)     → γ = 0.77
                factors.append(1.0 / modifiers[key])
                factor_names.append(f"{key}={modifiers[key]}")

        if not factors:
            return 1.0, []

        # Geometric mean of all applicable genetic factors
        gamma = math.exp(sum(math.log(f) for f in factors) / len(factors))

        # Clamp to reasonable bounds [0.5, 2.0]
        gamma = max(0.5, min(2.0, gamma))

        return gamma, factor_names

    @staticmethod
    def _compute_circadian_modifier(event_time: datetime) -> float:
        """Compute φ_circadian from time of day.

        Metabolic processes speed up and slow down with circadian rhythm.
        Morning: higher insulin sensitivity → faster glucose clearance → shorter lag
        Night: lower metabolic rate → slower processing → longer lag

        Uses sub-hour interpolation for smooth transitions.
        """
        hour = event_time.hour
        minute_fraction = event_time.minute / 60.0

        # Interpolate between current hour and next hour
        phi_current = CIRCADIAN_LAG_MODIFIERS.get(hour, 1.0)
        phi_next = CIRCADIAN_LAG_MODIFIERS.get((hour + 1) % 24, 1.0)
        phi = phi_current + (phi_next - phi_current) * minute_fraction

        return phi


class Resolution(str, Enum):
    """Temporal resolution levels for synchronized frames."""

    FINE = "fine"        # 5-minute windows (near real-time)
    MEDIUM = "medium"    # 1-hour windows (hourly overview)
    COARSE = "coarse"    # 24-hour windows (daily summary)


# Resolution → window duration mapping
RESOLUTION_DURATIONS = {
    Resolution.FINE: timedelta(minutes=5),
    Resolution.MEDIUM: timedelta(hours=1),
    Resolution.COARSE: timedelta(days=1),
}


@dataclass
class AlignedSignal:
    """A single biomarker's value within a synchronized time window.

    Attributes:
        biomarker_type: What is being measured.
        value: The aggregated/interpolated value for this window.
        confidence: Effective confidence after staleness decay.
        sample_count: Number of raw readings that contributed.
        lag_compensated: Whether physiological lag was applied.
        lag_computation: Full audit of how the lag was computed.
        original_timestamps: Timestamps of contributing raw readings.
    """

    biomarker_type: BiomarkerType
    value: float
    confidence: float
    sample_count: int
    lag_compensated: bool
    lag_computation: Optional[LagComputation] = None
    original_timestamps: List[datetime] = field(default_factory=list)


@dataclass
class SynchronizedFrame:
    """A single time-window snapshot containing all aligned biomarker signals.

    This is the fundamental output unit of the synchronization engine.
    It represents a moment in time where all available biomarker data has
    been aligned, lag-compensated, and confidence-weighted.

    Patent claim: "A synchronized temporal frame comprising a plurality
    of heterogeneous biomarker signals aligned to a common time window,
    wherein each signal is offset by its physiological lag duration and
    weighted by a confidence score that decays based on data staleness."

    Attributes:
        window_start: Start of the time window (UTC).
        window_end: End of the time window (UTC).
        resolution: Granularity level of this frame.
        signals: Dict mapping BiomarkerType to AlignedSignal.
        frame_confidence: Overall frame quality (0-1).
        completeness: Fraction of expected signals that are present.
    """

    window_start: datetime
    window_end: datetime
    resolution: Resolution
    signals: Dict[BiomarkerType, AlignedSignal] = field(default_factory=dict)
    frame_confidence: float = 0.0
    completeness: float = 0.0
    lag_computations: List[LagComputation] = field(default_factory=list)

    def to_feature_vector(self) -> Dict[str, float]:
        """Convert frame to a flat feature dictionary for ML models.

        Returns signal values with confidence-weighted keys.
        """
        features: Dict[str, float] = {}
        for bt, signal in self.signals.items():
            features[f"{bt.value}_value"] = signal.value
            features[f"{bt.value}_confidence"] = signal.confidence
            features[f"{bt.value}_samples"] = float(signal.sample_count)
        features["frame_confidence"] = self.frame_confidence
        features["frame_completeness"] = self.completeness
        features["hour_of_day"] = self.window_start.hour
        features["day_of_week"] = self.window_start.weekday()
        return features


class TemporalSynchronizer:
    """Engine that aligns heterogeneous biomarker streams onto a unified grid.

    Patent-core algorithm:

    For each time window [t, t+Δ]:
      For each biomarker type b:
        1. Determine the source's SamplingCharacteristics
        2. Compute the lag-adjusted query window:
           [t - lag(b), t + Δ - lag(b)]
        3. Gather all raw readings within that adjusted window
        4. If no readings found, check if data is stale:
           - If gap < max_gap: interpolate (delegate to CircadianInterpolator)
           - If gap >= max_gap: mark as missing with zero confidence
        5. Aggregate readings using temporal_behavior-appropriate method:
           - CONTINUOUS: weighted mean (closer readings weighted more)
           - EVENT: sum or count within window
           - PERIODIC: most recent value with decay
           - STATIC: always use current value (no decay)
        6. Compute confidence = base_confidence × staleness_decay

    This produces a SynchronizedFrame with all signals aligned to [t, t+Δ].
    """

    def __init__(
        self,
        lag_model: Optional[PhysiologicalLagModel] = None,
        interpolator: Optional["CircadianInterpolator"] = None,
    ):
        self._characteristics: Dict[BiomarkerType, SamplingCharacteristics] = {}
        self._lag_model = lag_model or PhysiologicalLagModel()
        # Lazy import to avoid circular dependency at module level
        if interpolator is not None:
            self._interpolator = interpolator
        else:
            from .interpolation import CircadianInterpolator as _CI
            self._interpolator = _CI()
        # Personal baseline means for interpolation (learned over time)
        self._baseline_means: Dict[str, Dict[BiomarkerType, float]] = {}

    @property
    def lag_model(self) -> PhysiologicalLagModel:
        """Access the lag model for genetic modifier registration."""
        return self._lag_model

    @property
    def interpolator(self):
        """Access the circadian interpolator."""
        return self._interpolator

    def set_baseline_mean(
        self, user_id: str, biomarker_type: BiomarkerType, mean: float
# FIXME: potential edge case
    ) -> None:
        """Set a user's personal baseline mean for a biomarker.

        Used by CircadianInterpolator when filling data gaps.
        Can be updated as personal baseline learning accumulates data.
        """
        if user_id not in self._baseline_means:
            self._baseline_means[user_id] = {}
        self._baseline_means[user_id][biomarker_type] = mean

    def _get_baseline_mean(
        self, user_id: Optional[str], biomarker_type: BiomarkerType
    ) -> float:
        """Get user's baseline mean, falling back to population average."""
        if user_id:
            user_means = self._baseline_means.get(user_id, {})
            if biomarker_type in user_means:
                return user_means[biomarker_type]
        # Fallback to population defaults
        from .normalization import POPULATION_RANGES
        pop = POPULATION_RANGES.get(biomarker_type, {})
        return pop.get("mean", 0.0)  # type: ignore

    def register_source(
        self,
        biomarker_type: BiomarkerType,
        characteristics: SamplingCharacteristics,
    ) -> None:
        """Register a biomarker source's temporal characteristics."""
        self._characteristics[biomarker_type] = characteristics

    def synchronize(
        self,
        readings: Dict[BiomarkerType, List[BiomarkerReading]],
        window_start: datetime,
        window_end: datetime,
        resolution: Resolution = Resolution.MEDIUM,
        user_id: Optional[str] = None,
    ) -> List[SynchronizedFrame]:
        """Synchronize heterogeneous biomarker streams into aligned frames.

        This is the main entry point. It takes raw readings from multiple
        sources and produces a time-ordered list of SynchronizedFrames.

        Args:
            readings: Dict mapping BiomarkerType to raw readings.
            window_start: Start of the synchronization period.
            window_end: End of the synchronization period.
            resolution: Desired temporal granularity.
            user_id: Optional user ID for genetic lag adaptation.

        Returns:
            List of SynchronizedFrames covering [window_start, window_end].
        """
        frame_duration = RESOLUTION_DURATIONS[resolution]
        frames: List[SynchronizedFrame] = []

        current = window_start
        while current < window_end:
            frame_end = min(current + frame_duration, window_end)
            frame = self._build_frame(
                readings, current, frame_end, resolution, user_id
            )
            frames.append(frame)
            current = frame_end

        return frames

    def _build_frame(
        self,
        readings: Dict[BiomarkerType, List[BiomarkerReading]],
        frame_start: datetime,
        frame_end: datetime,
        resolution: Resolution,
        user_id: Optional[str] = None,
    ) -> SynchronizedFrame:
        """Build a single synchronized frame for one time window.

        Implements the per-window alignment with dynamic lag
        compensation using the PhysiologicalLagModel.
        """
        frame = SynchronizedFrame(
            window_start=frame_start,
            window_end=frame_end,
            resolution=resolution,
        )

        expected_signals = len(self._characteristics)
        present_signals = 0

        for biomarker_type, chars in self._characteristics.items():
            raw = readings.get(biomarker_type, [])

            # Compute dynamic lag using the physiological model
            lag_comp = self._lag_model.compute_lag(
                biomarker_type, chars, frame_start, user_id
            )

            aligned = self._align_signal(
                raw, biomarker_type, chars, frame_start, frame_end,
                lag_override=lag_comp.effective_lag,
                user_id=user_id,
            )
            if aligned is not None:
                aligned.lag_computation = lag_comp
                frame.signals[biomarker_type] = aligned
                frame.lag_computations.append(lag_comp)
                if aligned.confidence > 0:
                    present_signals += 1

        # Compute frame-level metrics
        if frame.signals:
            confidences = [s.confidence for s in frame.signals.values()]
            frame.frame_confidence = sum(confidences) / len(confidences)
        frame.completeness = (
            present_signals / expected_signals if expected_signals > 0 else 0
        )

        return frame

    def _align_signal(
        self,
        raw_readings: List[BiomarkerReading],
        biomarker_type: BiomarkerType,
        chars: SamplingCharacteristics,
        frame_start: datetime,
        frame_end: datetime,
        lag_override: Optional[timedelta] = None,
        user_id: Optional[str] = None,
    ) -> Optional[AlignedSignal]:
        """Align a single biomarker's readings to a time window.

        Implements physiological lag compensation using the dynamic
        lag model. The query window is shifted backwards by the
        *personalized, circadian-adjusted* lag, so that cause-effect
        relationships are temporally aligned.

        Example: For a user with TCF7L2 T/T (slower insulin response)
        at 8am (high morning sensitivity), the glucose lag might be:
          base=60min × γ_genetic=1.25 × φ_circadian=0.82 = 61.5min
        vs. the same user at 10pm:
          base=60min × γ_genetic=1.25 × φ_circadian=1.10 = 82.5min
        """
        # Use dynamic lag from model, or fall back to static lag
        lag = lag_override if lag_override is not None else chars.physiological_lag

        # STATIC signals ignore time windows entirely
        if chars.temporal_behavior == TemporalBehavior.STATIC:
            if raw_readings:
                latest = raw_readings[-1]
                return AlignedSignal(
                    biomarker_type=biomarker_type,
                    value=latest.value,
                    confidence=latest.confidence,
                    sample_count=1,
                    lag_compensated=False,
                    original_timestamps=[latest.timestamp],
                )
            return None

        # Lag-adjusted query window
        query_start = frame_start - lag
        query_end = frame_end - lag

        # Find readings within the lag-adjusted window
        in_window = [
            r
            for r in raw_readings
            if query_start <= r.timestamp < query_end
        ]

        if in_window:
            return self._aggregate_readings(
                in_window, biomarker_type, chars, frame_start, True
            )

        # No readings in window — delegate to CircadianInterpolator
        # for gap filling using biological rhythm models.
        nearest = self._find_nearest_reading(
            raw_readings, query_start, query_end
        )
        if nearest is None:
            # No data at all — try circadian-only interpolation
            if (
                chars.temporal_behavior == TemporalBehavior.CONTINUOUS
                and self._interpolator is not None
            ):
                baseline = self._get_baseline_mean(user_id, biomarker_type)
                if baseline > 0:
                    target_time = frame_start + (frame_end - frame_start) / 2
                    interp = self._interpolator.interpolate(
                        user_id=user_id or "",
                        biomarker_type=biomarker_type,
                        target_time=target_time,
                        readings_before=None,
                        readings_after=None,
                        personal_baseline_mean=baseline,
                        max_gap=chars.max_gap_before_stale,
                    )
                    return AlignedSignal(
                        biomarker_type=biomarker_type,
                        value=interp.value,
                        confidence=interp.confidence * 0.5,  # penalize no-data
                        sample_count=0,
                        lag_compensated=True,
                    )
            return AlignedSignal(
                biomarker_type=biomarker_type,
                value=0.0,
                confidence=0.0,
                sample_count=0,
                lag_compensated=True,
            )

        # Calculate staleness
        if nearest.timestamp < query_start:
            gap = query_start - nearest.timestamp
        else:
            gap = nearest.timestamp - query_end

        if gap > chars.max_gap_before_stale:
            # Data too stale — use CircadianInterpolator to blend
            # nearest reading with circadian prediction
            if (
                chars.temporal_behavior == TemporalBehavior.CONTINUOUS
                and self._interpolator is not None
            ):
                baseline = self._get_baseline_mean(user_id, biomarker_type)
                if baseline > 0:
                    target_time = frame_start + (frame_end - frame_start) / 2
                    # Determine if nearest is before or after the target
                    before = nearest if nearest.timestamp < target_time else None
                    after = nearest if nearest.timestamp >= target_time else None
                    interp = self._interpolator.interpolate(
                        user_id=user_id or "",
                        biomarker_type=biomarker_type,
                        target_time=target_time,
                        readings_before=before,
                        readings_after=after,
                        personal_baseline_mean=baseline,
                        max_gap=chars.max_gap_before_stale,
                    )
                    return AlignedSignal(
                        biomarker_type=biomarker_type,
                        value=interp.value,
                        confidence=interp.confidence,
                        sample_count=0,
                        lag_compensated=True,
                        original_timestamps=[nearest.timestamp],
                    )
            # Fallback: return stale reading with zero confidence
            return AlignedSignal(
                biomarker_type=biomarker_type,
                value=nearest.value,
                confidence=0.0,
                sample_count=0,
                lag_compensated=True,
                original_timestamps=[nearest.timestamp],
            )

        # Apply staleness decay
        decay = self._staleness_decay(gap, chars)
        return AlignedSignal(
            biomarker_type=biomarker_type,
            value=nearest.value,
            confidence=nearest.confidence * decay,
            sample_count=1,
            lag_compensated=True,
            original_timestamps=[nearest.timestamp],
        )

    def _aggregate_readings(
        self,
        readings: List[BiomarkerReading],
        biomarker_type: BiomarkerType,
        chars: SamplingCharacteristics,
        frame_center: datetime,
        lag_compensated: bool,
    ) -> AlignedSignal:
        """Aggregate multiple readings within a window.

        Different aggregation strategies per temporal behavior:
        - CONTINUOUS: Distance-weighted mean (closer = higher weight)
        - EVENT: Sum of values (e.g., total calories from multiple meals)
        - PERIODIC: Most recent value
        """
        if chars.temporal_behavior == TemporalBehavior.CONTINUOUS:
            value, confidence = self._weighted_mean(
                readings, frame_center, chars
            )
        elif chars.temporal_behavior == TemporalBehavior.EVENT:
            value = sum(r.value for r in readings)
            confidence = (
                sum(r.confidence for r in readings) / len(readings)
            )
        elif chars.temporal_behavior == TemporalBehavior.PERIODIC:
            # Use most recent
            latest = max(readings, key=lambda r: r.timestamp)
            value = latest.value
            confidence = latest.confidence
        else:
            value = readings[-1].value
            confidence = readings[-1].confidence

        return AlignedSignal(
            biomarker_type=biomarker_type,
            value=value,
            confidence=confidence,
            sample_count=len(readings),
            lag_compensated=lag_compensated,
            original_timestamps=[r.timestamp for r in readings],
        )

    def _weighted_mean(
        self,
        readings: List[BiomarkerReading],
        center: datetime,
        chars: SamplingCharacteristics,
    ) -> Tuple[float, float]:
        """Compute distance-weighted mean of continuous readings.

        Readings closer to the window center receive higher weight.
        This is more accurate than simple arithmetic mean for
        continuous signals where temporal proximity matters.
        """
        if not readings:
            return 0.0, 0.0

        sigma = chars.typical_interval.total_seconds()
        if sigma == 0:
            sigma = 60.0  # Default 1 minute

        total_weight = 0.0
        weighted_sum = 0.0
        confidence_sum = 0.0

        for r in readings:
            dt = abs((r.timestamp - center).total_seconds())
            # Gaussian kernel weight
            weight = math.exp(-0.5 * (dt / sigma) ** 2) * r.confidence
            weighted_sum += r.value * weight
            confidence_sum += r.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0, 0.0

        return (
            weighted_sum / total_weight,
            confidence_sum / total_weight,
        )

    @staticmethod
    def _staleness_decay(
        gap: timedelta, chars: SamplingCharacteristics
    ) -> float:
        """Compute confidence decay due to data staleness.

        Uses exponential decay with the source's typical interval as
        the half-life. This means confidence drops to 50% after one
        typical interval of missing data.

        Patent-relevant: Unlike binary stale/fresh cutoffs, this
        continuous decay function preserves usable information from
        slightly outdated readings while appropriately reducing their
        influence.
        """
        half_life = chars.typical_interval.total_seconds()
        if half_life == 0:
            return 1.0

        gap_seconds = gap.total_seconds()
        # Exponential decay: confidence halves every half_life seconds
        decay = math.exp(-0.693 * gap_seconds / half_life)
        return max(0.0, min(1.0, decay))

    @staticmethod
    def _find_nearest_reading(
        readings: List[BiomarkerReading],
        query_start: datetime,
        query_end: datetime,
    ) -> Optional[BiomarkerReading]:
        """Find the reading closest to the query window."""
        if not readings:
            return None

        query_center = query_start + (query_end - query_start) / 2
        return min(
            readings,
            key=lambda r: abs((r.timestamp - query_center).total_seconds()),
        )

# Updated: 2023-12-21

# NOTE: reviewed 2025-02-10