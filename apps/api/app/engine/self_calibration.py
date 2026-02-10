"""
Adaptive Self-Calibration Engine (Feedback Loop).

Patent-critical module: Implements an adaptive learning algorithm that
back-propagates the error between predicted and actual biomarker peak
times to fine-tune individual lag coefficients.

Core innovation: The Physiological Lag Model computes an initial lag
prediction using three static axes:

    t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)

This module closes the loop by observing the actual biomarker response
and computing a correction signal:

    ε_k = t_peak_actual - t_peak_predicted

This error is then decomposed and back-propagated to refine each axis:

    1. Base lag personal offset:  δ_base(b)  — per-biomarker additive correction
    2. Circadian phase shift:     δ_circ(h)  — per-hour additive correction
    3. Genetic factor correction:  κ_genetic  — multiplicative genome factor

The updated model becomes:

    t_sync_calibrated = t_event
        + (Δt_base(b) + δ_base(b))
        × γ_genetic(g) × κ_genetic
        × (φ_circadian(c) + δ_circ(h))

This transforms the static formula into a **self-evolving, user-adaptive
model** — a critical differentiator for patent claims.

Learning algorithm:
    Exponential Moving Average (EMA) with adaptive learning rate:
        α = α_0 / (1 + observation_count / τ)
    where τ = convergence_time_constant (default 20 observations)

    This provides:
    - Fast initial adaptation (high α when few observations)
    - Stable convergence (low α after many observations)
    - Resistance to overfitting (bounded correction magnitudes)

Peak detection:
    Biomarker peaks are detected using a local maximum finder with
    configurable prominence threshold — essential for identifying
    actual glucose/HR response peaks in noisy physiological data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..biomarkers.base import BiomarkerReading, BiomarkerType


# ═══════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class CalibrationObservation:
    """A single observed prediction-vs-actual peak comparison.

    Records the discrepancy between the model's predicted peak time
    and the actual measured peak, along with context needed for
    decomposing the error into correction signals.

    Attributes:
        biomarker_type: Which signal was being tracked.
        event_time: When the causal event occurred (e.g., meal time).
        predicted_peak_time: Peak time predicted by the lag model.
        actual_peak_time: Actual observed peak time.
        prediction_error_seconds: ε = actual - predicted (positive = undershoot).
        hour_of_day: Hour when the event occurred (for circadian decomposition).
        relative_error: Fractional error (ε / predicted_lag).
        confidence: Confidence of the peak detection (0-1).
    """

    biomarker_type: BiomarkerType
    event_time: datetime
    predicted_peak_time: datetime
    actual_peak_time: datetime
    prediction_error_seconds: float
    hour_of_day: int
    relative_error: float
    confidence: float = 1.0


@dataclass
class PersonalCalibrationProfile:
    """Stores learned corrections for a single user.

    This profile accumulates through the feedback loop and persists
    across sessions, enabling the model to converge to the user's
    true physiological parameters over time.

    Patent claim: "A personal calibration profile comprising learned
    offset corrections for base lag, circadian phase, and genetic
    factor, derived from iterative comparison of predicted versus
    observed biomarker response peaks."

    Attributes:
        user_id: User identifier.
        base_lag_offsets: δ_base(b) — per-biomarker additive correction (seconds).
        circadian_corrections: δ_circ(h) — per-hour additive correction.
        genetic_correction_factor: κ_genetic — multiplicative correction on γ.
        observation_count: Total calibration observations processed.
        per_biomarker_count: Observations per biomarker type.
        observation_history: Recent observations for convergence analysis.
        last_updated: Timestamp of last calibration update.
        convergence_score: How stable the corrections are (0-1).
        mae_history: Mean absolute error trend for convergence tracking.
    """

    user_id: str
    base_lag_offsets: Dict[str, float] = field(default_factory=dict)
    circadian_corrections: Dict[int, float] = field(default_factory=dict)
    genetic_correction_factor: float = 1.0
    observation_count: int = 0
    per_biomarker_count: Dict[str, int] = field(default_factory=dict)
    observation_history: List[CalibrationObservation] = field(
        default_factory=list
    )
    last_updated: Optional[datetime] = None
    convergence_score: float = 0.0
    mae_history: List[float] = field(default_factory=list)

    @property
    def is_converged(self) -> bool:
        """Whether the profile has reached stable convergence.

        Convergence is declared when:
        1. At least 10 observations have been processed, AND
        2. The convergence score exceeds 0.8 (recent errors are small)
        """
        return self.observation_count >= 10 and self.convergence_score > 0.8


@dataclass
class DetectedPeak:
    """A detected peak in a biomarker time series.

    Attributes:
        timestamp: When the peak occurred.
        value: Peak value.
        prominence: How much the peak stands out from surrounding data.
        confidence: Detection confidence (0-1).
    """

    timestamp: datetime
    value: float
    prominence: float
    confidence: float


@dataclass
class CalibrationResult:
    """Result of a single calibration step.

    Attributes:
        observation: The observation that triggered this calibration.
        applied_corrections: Dict describing what was updated.
        updated_profile: The user's profile after this update.
        improvement_estimate: Estimated lag prediction improvement (seconds).
    """

    observation: CalibrationObservation
    applied_corrections: Dict[str, float]
    updated_profile: PersonalCalibrationProfile
    improvement_estimate: float


# ═══════════════════════════════════════════════════════════════════════
# Peak Detection
# ═══════════════════════════════════════════════════════════════════════


class PeakDetector:
    """Detects biomarker response peaks in time-series data.

    Uses a local maximum finder with prominence-based filtering to
    identify genuine physiological response peaks (e.g., post-prandial
    glucose spike) and distinguish them from noise.

    Algorithm:
        1. Smooth the raw signal using exponential moving average
        2. Identify local maxima (value > both neighbors)
        3. Compute prominence = peak_value - max(left_trough, right_trough)
        4. Filter by prominence threshold
        5. Return highest-prominence peak in the search window

    Parameters:
        smoothing_alpha: EMA smoothing parameter (0-1, higher = less smooth).
        min_prominence_fraction: Minimum prominence as fraction of signal range.
    """

    def __init__(
        self,
        smoothing_alpha: float = 0.3,
        min_prominence_fraction: float = 0.1,
    ):
        self._smoothing_alpha = smoothing_alpha
        self._min_prominence_fraction = min_prominence_fraction

    def detect_peak(
        self,
        readings: List[BiomarkerReading],
        search_start: datetime,
        search_end: datetime,
    ) -> Optional[DetectedPeak]:
        """Detect the most prominent peak within a time window.

        Args:
            readings: Time-ordered biomarker readings.
            search_start: Start of the peak search window.
            search_end: End of the peak search window.

        Returns:
            DetectedPeak if a valid peak is found, else None.
        """
        # Filter to search window and sort by time
        windowed = sorted(
            [r for r in readings if search_start <= r.timestamp <= search_end],
            key=lambda r: r.timestamp,
        )

        if len(windowed) < 3:
            # Need at least 3 points for peak detection
            if len(windowed) == 0:
                return None
            # With 1-2 points, return the max as a low-confidence peak
            best = max(windowed, key=lambda r: r.value)
            return DetectedPeak(
                timestamp=best.timestamp,
                value=best.value,
                prominence=0.0,
                confidence=0.2,
            )

        # Step 1: Smooth the signal
        smoothed = self._ema_smooth([r.value for r in windowed])

        # Step 2: Find local maxima
        peaks: List[Tuple[int, float]] = []  # (index, prominence)
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] > smoothed[i - 1] and smoothed[i] > smoothed[i + 1]:
                # Step 3: Compute prominence
                # Left trough: minimum between start and this peak
                left_min = min(smoothed[:i]) if i > 0 else smoothed[0]
                # Right trough: minimum between this peak and end
                right_min = (
                    min(smoothed[i + 1 :]) if i < len(smoothed) - 1
                    else smoothed[-1]
                )
                prominence = smoothed[i] - max(left_min, right_min)
                peaks.append((i, prominence))

        if not peaks:
            # No local maxima — return global max with low confidence
            max_idx = max(range(len(smoothed)), key=lambda i: smoothed[i])
            return DetectedPeak(
                timestamp=windowed[max_idx].timestamp,
                value=windowed[max_idx].value,
                prominence=0.0,
                confidence=0.3,
            )

        # Step 4: Filter by minimum prominence
        signal_range = max(smoothed) - min(smoothed)
        min_prominence = signal_range * self._min_prominence_fraction

        significant_peaks = [
            (idx, prom) for idx, prom in peaks if prom >= min_prominence
        ]

        if not significant_peaks:
            # No significant peaks — return highest peak with low confidence
            best_idx, best_prom = max(peaks, key=lambda x: x[1])
            return DetectedPeak(
                timestamp=windowed[best_idx].timestamp,
                value=windowed[best_idx].value,
                prominence=best_prom,
                confidence=0.4,
            )

        # Step 5: Return highest-prominence significant peak
        best_idx, best_prom = max(significant_peaks, key=lambda x: x[1])

        # Confidence based on prominence relative to signal range
        confidence = min(1.0, best_prom / (signal_range + 1e-6))
        confidence = max(0.5, confidence)  # Floor at 0.5 for detected peaks

        return DetectedPeak(
            timestamp=windowed[best_idx].timestamp,
            value=windowed[best_idx].value,
            prominence=best_prom,
            confidence=confidence,
        )

    def _ema_smooth(self, values: List[float]) -> List[float]:
        """Exponential moving average smoothing."""
        if not values:
            return []
        smoothed = [values[0]]
        alpha = self._smoothing_alpha
        for v in values[1:]:
            smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])
        return smoothed


# ═══════════════════════════════════════════════════════════════════════
# Adaptive Self-Calibration Engine
# ═══════════════════════════════════════════════════════════════════════


class AdaptiveLagCalibrator:
    """Self-calibrating feedback loop for the Physiological Lag Model.

    This engine transforms the static lag formula into an adaptive,
    self-evolving model by iteratively comparing predicted peaks with
    actual measured peaks and back-propagating the error.

    Mathematical foundation:

    Given prediction error at step k:
        ε_k = t_peak_actual^(k) - t_peak_predicted^(k)

    The error is decomposed into three correction channels:

    1. Base Lag Offset (additive, per-biomarker):
        δ_base(b)^(k+1) = (1 - α) × δ_base(b)^(k) + α × ε_k
        Captures individual metabolic speed for each biomarker type.

    2. Circadian Phase Correction (additive, per-hour):
        δ_circ(h)^(k+1) = (1 - α_c) × δ_circ(h)^(k) + α_c × ε_k
        where h = hour_of_day(event_time)
        Captures personal circadian rhythm deviations.

    3. Genetic Factor Correction (multiplicative):
        κ_genetic^(k+1) = (1 - α_g) × κ_genetic^(k) + α_g × (1 + ε_rel)
        where ε_rel = ε_k / predicted_lag
        Captures systematic under/over-estimation from genetic model.

    Learning rate schedule (adaptive):
        α(k) = α_0 / (1 + k / τ)

    This provides:
        - Fast convergence in early observations (high α)
        - Stability after many observations (low α)
        - Bounded corrections (hard clamps prevent divergence)

    The calibrated lag model becomes:

        t_sync_calibrated = t_event
            + (Δt_base(b) + δ_base(b))
            × γ_genetic(g) × κ_genetic
            × (φ_circadian(c) + δ_circ(h))

    Patent claim: "An adaptive calibration method for a physiological
    lag prediction model, comprising: (a) detecting actual biomarker
    response peaks from measured time-series data; (b) computing the
    temporal error between predicted and actual peaks; (c) decomposing
    said error into base-lag, circadian, and genetic correction channels;
    (d) updating per-user correction parameters using an exponential
    moving average with adaptive learning rate; and (e) applying said
    corrections to subsequent predictions, thereby enabling the model
    to self-evolve with continued use."
    """

    # ── Default hyperparameters ─────────────────────────────────────

    DEFAULT_ALPHA_BASE = 0.3       # Initial learning rate for base lag
    DEFAULT_ALPHA_CIRCADIAN = 0.2  # Initial learning rate for circadian
    DEFAULT_ALPHA_GENETIC = 0.1    # Initial learning rate for genetic (slow)
    DEFAULT_TAU = 20.0             # Convergence time constant (observations)

    # Bound constraints (prevent divergence)
    MAX_BASE_OFFSET_SECONDS = 1800.0   # ±30 minutes
    MAX_CIRCADIAN_CORRECTION = 0.3     # ±30% of circadian modifier
    MAX_GENETIC_CORRECTION = 0.5       # κ ∈ [0.5, 1.5]

    # History window for convergence analysis
    CONVERGENCE_WINDOW = 10
    MAX_HISTORY = 100

    def __init__(
        self,
        alpha_base: float = DEFAULT_ALPHA_BASE,
        alpha_circadian: float = DEFAULT_ALPHA_CIRCADIAN,
        alpha_genetic: float = DEFAULT_ALPHA_GENETIC,
        tau: float = DEFAULT_TAU,
        peak_detector: Optional[PeakDetector] = None,
    ):
        """Initialize the calibration engine.

        Args:
            alpha_base: Initial learning rate for base lag corrections.
            alpha_circadian: Initial learning rate for circadian corrections.
            alpha_genetic: Initial learning rate for genetic corrections.
            tau: Convergence time constant (higher = slower convergence).
            peak_detector: Optional custom peak detector.
        """
        self._alpha_base = alpha_base
        self._alpha_circadian = alpha_circadian
        self._alpha_genetic = alpha_genetic
        self._tau = tau
        self._peak_detector = peak_detector or PeakDetector()

        # Per-user calibration profiles
        self._profiles: Dict[str, PersonalCalibrationProfile] = {}

    # ── Profile Management ──────────────────────────────────────────

    def get_profile(self, user_id: str) -> PersonalCalibrationProfile:
        """Get or create a user's calibration profile."""
        if user_id not in self._profiles:
            self._profiles[user_id] = PersonalCalibrationProfile(
                user_id=user_id
            )
        return self._profiles[user_id]

    def set_profile(
        self, user_id: str, profile: PersonalCalibrationProfile
    ) -> None:
        """Set a user's calibration profile (e.g., loaded from storage)."""
        self._profiles[user_id] = profile

    # ── Peak Detection ──────────────────────────────────────────────

    def detect_response_peak(
        self,
        readings: List[BiomarkerReading],
        event_time: datetime,
        expected_lag_seconds: float,
        search_window_multiplier: float = 2.5,
    ) -> Optional[DetectedPeak]:
        """Detect the actual biomarker response peak after an event.

        Searches in a window around the expected peak time, using the
        predicted lag to set the search center.

        Args:
            readings: All available readings for this biomarker.
            event_time: When the causal event (e.g., meal) occurred.
            expected_lag_seconds: Predicted lag from the lag model.
            search_window_multiplier: How wide to search (× expected lag).

        Returns:
            DetectedPeak if a valid peak is found, else None.
        """
        half_window = expected_lag_seconds * search_window_multiplier / 2
        search_center = event_time + timedelta(seconds=expected_lag_seconds)
        search_start = search_center - timedelta(seconds=half_window)
        search_end = search_center + timedelta(seconds=half_window)

        return self._peak_detector.detect_peak(
            readings, search_start, search_end,
        )

    # ── Core Calibration Loop ───────────────────────────────────────

    def observe(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        event_time: datetime,
        predicted_peak_time: datetime,
        actual_peak_time: datetime,
        confidence: float = 1.0,
    ) -> CalibrationResult:
        """Record a prediction-vs-actual observation and update the model.

        This is the core feedback loop entry point. Each call:
        1. Computes the prediction error ε
        2. Decomposes ε into base, circadian, and genetic channels
        3. Updates the personal calibration profile
        4. Estimates the improvement in prediction accuracy

        Args:
            user_id: User identifier.
            biomarker_type: Which biomarker was predicted.
            event_time: When the causal event occurred.
            predicted_peak_time: Model's predicted peak time.
            actual_peak_time: Actual observed peak time.
            confidence: Confidence in the peak detection (0-1).

        Returns:
            CalibrationResult with full audit trail.
        """
        profile = self.get_profile(user_id)

        # ── Compute prediction error ────────────────────────────────
        error_seconds = (
            actual_peak_time - predicted_peak_time
        ).total_seconds()

        predicted_lag = (
            predicted_peak_time - event_time
        ).total_seconds()

        # Relative error (for genetic correction)
        relative_error = (
            error_seconds / predicted_lag if predicted_lag > 0 else 0.0
        )

        observation = CalibrationObservation(
            biomarker_type=biomarker_type,
            event_time=event_time,
            predicted_peak_time=predicted_peak_time,
            actual_peak_time=actual_peak_time,
            prediction_error_seconds=error_seconds,
            hour_of_day=event_time.hour,
            relative_error=relative_error,
            confidence=confidence,
        )

        # ── Compute adaptive learning rates ─────────────────────────
        bt_key = biomarker_type.value
        bt_count = profile.per_biomarker_count.get(bt_key, 0)

        alpha_b = self._adaptive_alpha(self._alpha_base, bt_count)
        alpha_c = self._adaptive_alpha(self._alpha_circadian, bt_count)
        alpha_g = self._adaptive_alpha(
            self._alpha_genetic, profile.observation_count
        )

        # Weight update by detection confidence
        alpha_b *= confidence
        alpha_c *= confidence
        alpha_g *= confidence

        corrections: Dict[str, float] = {}

        # ── Channel 1: Base Lag Offset ──────────────────────────────
        # δ_base(b)^(k+1) = (1 - α) × δ_base(b)^(k) + α × ε_k
        old_offset = profile.base_lag_offsets.get(bt_key, 0.0)
        new_offset = (1 - alpha_b) * old_offset + alpha_b * error_seconds
        new_offset = max(
            -self.MAX_BASE_OFFSET_SECONDS,
            min(self.MAX_BASE_OFFSET_SECONDS, new_offset),
        )
        profile.base_lag_offsets[bt_key] = new_offset
        corrections["base_lag_offset"] = new_offset

        # ── Channel 2: Circadian Phase Correction ───────────────────
        # δ_circ(h)^(k+1) = (1 - α_c) × δ_circ(h)^(k) + α_c × ε_k
        # Expressed as a fractional correction to φ_circadian
        hour = event_time.hour
        old_circ = profile.circadian_corrections.get(hour, 0.0)
        circ_correction = error_seconds / (predicted_lag + 1e-6)
        new_circ = (1 - alpha_c) * old_circ + alpha_c * circ_correction
        new_circ = max(
            -self.MAX_CIRCADIAN_CORRECTION,
            min(self.MAX_CIRCADIAN_CORRECTION, new_circ),
        )
        profile.circadian_corrections[hour] = new_circ
        corrections["circadian_correction"] = new_circ

        # ── Channel 3: Genetic Factor Correction ────────────────────
        # κ^(k+1) = (1 - α_g) × κ^(k) + α_g × (1 + ε_relative)
        old_kappa = profile.genetic_correction_factor
        new_kappa = (1 - alpha_g) * old_kappa + alpha_g * (1 + relative_error)
        new_kappa = max(
            1.0 - self.MAX_GENETIC_CORRECTION,
            min(1.0 + self.MAX_GENETIC_CORRECTION, new_kappa),
        )
        profile.genetic_correction_factor = new_kappa
        corrections["genetic_correction_factor"] = new_kappa

        # ── Update profile metadata ─────────────────────────────────
        profile.observation_count += 1
        profile.per_biomarker_count[bt_key] = bt_count + 1
        profile.last_updated = datetime.utcnow()

        # Maintain observation history (bounded)
        profile.observation_history.append(observation)
        if len(profile.observation_history) > self.MAX_HISTORY:
            profile.observation_history = profile.observation_history[
                -self.MAX_HISTORY :
            ]

        # ── Compute convergence score ───────────────────────────────
        profile.mae_history.append(abs(error_seconds))
        if len(profile.mae_history) > self.MAX_HISTORY:
            profile.mae_history = profile.mae_history[-self.MAX_HISTORY :]

        profile.convergence_score = self._compute_convergence(profile)

        # ── Estimate improvement ────────────────────────────────────
        # How much would the correction have improved this prediction?
        improvement = abs(error_seconds) - abs(error_seconds - new_offset)

        return CalibrationResult(
            observation=observation,
            applied_corrections=corrections,
            updated_profile=profile,
            improvement_estimate=max(0.0, improvement),
        )

    # ── Calibrated Lag Computation ──────────────────────────────────

    def get_calibrated_lag(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        base_lag_seconds: float,
        genetic_modifier: float,
        circadian_modifier: float,
        event_time: datetime,
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute the calibrated lag by applying learned corrections.

        The calibrated model:
            t_lag = (Δt_base + δ_base) × (γ × κ) × (φ + δ_circ)

        Args:
            user_id: User for profile lookup.
            biomarker_type: Signal type.
            base_lag_seconds: Δt_base(b) from the static model.
            genetic_modifier: γ_genetic(g) from the static model.
            circadian_modifier: φ_circadian(c) from the static model.
            event_time: Time of the causal event.

        Returns:
            Tuple of (calibrated_lag_seconds, audit_dict).
        """
        profile = self.get_profile(user_id)
        bt_key = biomarker_type.value

        # Apply corrections
        delta_base = profile.base_lag_offsets.get(bt_key, 0.0)
        delta_circ = profile.circadian_corrections.get(event_time.hour, 0.0)
        kappa = profile.genetic_correction_factor

        # Calibrated formula
        calibrated_base = base_lag_seconds + delta_base
        calibrated_base = max(0, calibrated_base)  # Lag cannot be negative

        calibrated_genetic = genetic_modifier * kappa
        calibrated_circadian = circadian_modifier + delta_circ

        calibrated_lag = (
            calibrated_base * calibrated_genetic * calibrated_circadian
        )

        # Ensure non-negative
        calibrated_lag = max(0, calibrated_lag)

        audit = {
            "original_lag": base_lag_seconds * genetic_modifier * circadian_modifier,
            "calibrated_lag": calibrated_lag,
            "delta_base": delta_base,
            "delta_circadian": delta_circ,
            "kappa_genetic": kappa,
            "observation_count": profile.observation_count,
            "convergence_score": profile.convergence_score,
            "is_converged": profile.is_converged,
        }

        return calibrated_lag, audit

    # ── Batch Calibration ───────────────────────────────────────────

    def calibrate_from_history(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        event_readings_pairs: List[
            Tuple[datetime, List[BiomarkerReading], float]
        ],
    ) -> List[CalibrationResult]:
        """Run batch calibration from historical event-readings pairs.

        Each tuple contains:
            (event_time, subsequent_readings, predicted_lag_seconds)

        This method detects peaks and runs observe() for each pair.
        Useful for bootstrapping a profile from existing data.

        Args:
            user_id: User identifier.
            biomarker_type: Signal type.
            event_readings_pairs: List of (event_time, readings, predicted_lag).

        Returns:
            List of CalibrationResults.
        """
        results: List[CalibrationResult] = []

        for event_time, readings, predicted_lag in event_readings_pairs:
            # Detect actual peak
            peak = self.detect_response_peak(
                readings, event_time, predicted_lag,
            )
            if peak is None or peak.confidence < 0.3:
                continue

            # Compute predicted peak time
            predicted_peak = event_time + timedelta(seconds=predicted_lag)

            # Observe and calibrate
            result = self.observe(
                user_id=user_id,
                biomarker_type=biomarker_type,
                event_time=event_time,
                predicted_peak_time=predicted_peak,
                actual_peak_time=peak.timestamp,
                confidence=peak.confidence,
            )
            results.append(result)

        return results

    # ── Internal helpers ────────────────────────────────────────────

    def _adaptive_alpha(self, alpha_0: float, step: int) -> float:
        """Compute adaptive learning rate.

        α(k) = α_0 / (1 + k / τ)

        Starts at α_0, decays towards 0 as step increases.
        This provides fast initial learning and stable convergence.
        """
        return alpha_0 / (1.0 + step / self._tau)

    def _compute_convergence(
        self, profile: PersonalCalibrationProfile
    ) -> float:
        """Compute convergence score from recent MAE trend.

        Score is high (close to 1.0) when:
        1. Recent MAE is significantly lower than early MAE
        2. MAE variance is low (stable predictions)

        Score is low (close to 0.0) when:
        1. Not enough data
        2. Errors are still large or volatile
        """
        hist = profile.mae_history
        if len(hist) < self.CONVERGENCE_WINDOW:
            return 0.0

        recent = hist[-self.CONVERGENCE_WINDOW :]
        early = hist[: self.CONVERGENCE_WINDOW]

        recent_mae = sum(recent) / len(recent)
        early_mae = sum(early) / len(early) if early else recent_mae

        # Improvement ratio (how much has MAE decreased?)
        if early_mae > 0:
            improvement = 1.0 - (recent_mae / early_mae)
        else:
            improvement = 0.0

        # Stability (low variance = stable)
        if len(recent) > 1:
            mean_recent = recent_mae
            variance = sum((x - mean_recent) ** 2 for x in recent) / len(
                recent
            )
            std = math.sqrt(variance)
            stability = 1.0 / (1.0 + std / (mean_recent + 1e-6))
        else:
            stability = 0.0

        # Combined score (weighted average)
        score = 0.6 * max(0, improvement) + 0.4 * stability

        return max(0.0, min(1.0, score))

    # ── Diagnostic helpers ──────────────────────────────────────────

    def get_calibration_summary(
        self, user_id: str
    ) -> Dict[str, Any]:
        """Get a summary of the user's calibration state.

        Useful for diagnostics, API responses, and debugging.
        """
        profile = self.get_profile(user_id)

        summary: Dict[str, Any] = {
            "user_id": user_id,
            "observation_count": profile.observation_count,
            "convergence_score": round(profile.convergence_score, 3),
            "is_converged": profile.is_converged,
            "genetic_correction_factor": round(
                profile.genetic_correction_factor, 4
            ),
            "base_lag_offsets": {
                k: round(v, 1) for k, v in profile.base_lag_offsets.items()
            },
            "circadian_corrections": {
                str(k): round(v, 4)
                for k, v in profile.circadian_corrections.items()
            },
            "last_updated": (
                profile.last_updated.isoformat()
                if profile.last_updated
                else None
            ),
        }

        if profile.mae_history:
            summary["current_mae"] = round(profile.mae_history[-1], 1)
            if len(profile.mae_history) >= self.CONVERGENCE_WINDOW:
                recent = profile.mae_history[-self.CONVERGENCE_WINDOW :]
                summary["recent_avg_mae"] = round(
                    sum(recent) / len(recent), 1
                )

        return summary
