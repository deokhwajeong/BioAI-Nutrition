"""
Metabolic State Estimator.

Patent-core module: Infers the user's current metabolic state from
synchronized and normalized biomarker signals.

Metabolic state determines:
1. Which nutrient demands are currently active
2. How biomarker readings should be interpreted (normalization context)
3. What recommendations are physiologically appropriate RIGHT NOW

States are not simply "fasting vs fed" — they include:
- Postprandial phases (absorption, post-absorptive)
- Exercise states (during, immediate recovery, delayed recovery)
- Sleep-related states (pre-sleep, deep sleep, post-waking)
- Stress/recovery states
- Combined states (e.g., "postprandial + recovery" after post-workout meal)

Patent-relevant: The multi-signal state inference and the concept of
"combined metabolic states" that simultaneously affect nutrient demands
from multiple physiological angles is the inventive step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..biomarkers.base import BiomarkerType
from .temporal_sync import SynchronizedFrame, AlignedSignal


class MetabolicPhase(str, Enum):
    """Individual metabolic phases that can combine."""

    # Feeding-related phases
    FASTING = "fasting"                    # >4h since last meal
    POSTPRANDIAL_EARLY = "postprandial_early"  # 0-2h after meal
    POSTPRANDIAL_LATE = "postprandial_late"    # 2-4h after meal
    POST_ABSORPTIVE = "post_absorptive"    # 4-12h after meal

    # Exercise-related phases
    PRE_EXERCISE = "pre_exercise"          # 0-30min before planned exercise
    DURING_EXERCISE = "during_exercise"
    RECOVERY_IMMEDIATE = "recovery_immediate"  # 0-2h after exercise
    RECOVERY_DELAYED = "recovery_delayed"  # 2-48h after intense exercise

    # Sleep-related phases
    PRE_SLEEP = "pre_sleep"                # 1-2h before typical bedtime
    SLEEPING = "sleeping"
    POST_WAKING = "post_waking"            # 0-1h after waking

    # Stress/metabolic states
    METABOLIC_STRESS = "metabolic_stress"  # High cortisol indicators
    RECOVERY = "recovery"                  # High parasympathetic
    CIRCADIAN_LOW = "circadian_low"        # Afternoon energy dip


@dataclass
class MetabolicState:
    """The user's current metabolic state.

    Can contain MULTIPLE active phases simultaneously (e.g., fasting + sleeping).

    Patent-relevant: The combination of phases creates a compound context
    that uniquely determines nutrient demands. "Fasting + Sleeping" has
    different demands than "Fasting + Post-Exercise-Recovery".

    Attributes:
        timestamp: When this state was assessed.
        active_phases: Set of currently active metabolic phases.
        primary_phase: The dominant phase for recommendation purposes.
        phase_intensities: 0-1 intensity for each active phase.
        hours_since_last_meal: Time since last detected meal event.
        hours_since_last_exercise: Time since last detected exercise.
        hours_since_waking: Time since waking up.
        insulin_sensitivity_estimate: 0-1, estimated current sensitivity.
        energy_availability: Estimated current energy status (kcal).
        hydration_estimate: 0-1, estimated hydration level.
        nutrient_priority_shifts: Phase-driven shifts to nutrient priorities.
    """

    timestamp: datetime
    active_phases: Set[MetabolicPhase] = field(default_factory=set)
    primary_phase: MetabolicPhase = MetabolicPhase.FASTING
    phase_intensities: Dict[MetabolicPhase, float] = field(default_factory=dict)
    hours_since_last_meal: float = 12.0
    hours_since_last_exercise: float = 24.0
    hours_since_waking: float = 8.0
    insulin_sensitivity_estimate: float = 0.7
    energy_availability: float = 0.0
    hydration_estimate: float = 0.8
    nutrient_priority_shifts: Dict[str, float] = field(default_factory=dict)
    decision_log: List[str] = field(default_factory=list)

    def to_context_string(self) -> str:
        """Convert to a context string for the normalization layer."""
        if MetabolicPhase.DURING_EXERCISE in self.active_phases:
            return "exercising"
        if MetabolicPhase.SLEEPING in self.active_phases:
            return "sleeping"
        if MetabolicPhase.POSTPRANDIAL_EARLY in self.active_phases:
            return "postprandial"
        if MetabolicPhase.FASTING in self.active_phases:
            return "fasting"
        if MetabolicPhase.RECOVERY_IMMEDIATE in self.active_phases:
            return "recovery"
        return "unknown"


# Nutrient priority modifiers per metabolic phase
# >1.0 = increased need, <1.0 = decreased need
PHASE_NUTRIENT_MODIFIERS: Dict[MetabolicPhase, Dict[str, float]] = {
    MetabolicPhase.FASTING: {
        "carbohydrate_priority": 0.8,
        "protein_priority": 1.0,
        "fat_priority": 1.1,
        "water_priority": 1.0,
        "electrolyte_priority": 0.9,
    },
    MetabolicPhase.POSTPRANDIAL_EARLY: {
        "carbohydrate_priority": 0.6,  # Just ate, don't need more carbs
        "protein_priority": 0.8,
        "fat_priority": 0.7,
        "water_priority": 1.2,
        "fiber_priority": 0.5,
    },
    MetabolicPhase.RECOVERY_IMMEDIATE: {
        "carbohydrate_priority": 1.5,  # Glycogen replenishment
        "protein_priority": 1.4,       # Muscle repair
        "fat_priority": 0.8,
        "water_priority": 1.5,
        "electrolyte_priority": 1.4,
    },
    MetabolicPhase.RECOVERY_DELAYED: {
        "carbohydrate_priority": 1.2,
        "protein_priority": 1.3,
        "fat_priority": 1.0,
        "water_priority": 1.2,
    },
    MetabolicPhase.PRE_SLEEP: {
        "carbohydrate_priority": 0.5,  # Avoid glucose spikes before sleep
        "protein_priority": 1.1,       # Casein protein benefits sleep/recovery
        "fat_priority": 0.8,
        "caffeine_limit": 0.0,         # No caffeine
        "water_priority": 0.7,         # Reduce to avoid nocturia
    },
    MetabolicPhase.POST_WAKING: {
        "carbohydrate_priority": 1.0,
        "protein_priority": 1.2,
        "water_priority": 1.4,         # Rehydrate after sleep
        "electrolyte_priority": 1.2,
    },
    MetabolicPhase.METABOLIC_STRESS: {
        "carbohydrate_priority": 0.7,
        "protein_priority": 1.2,
        "fat_priority": 0.9,
        "magnesium_priority": 1.3,
        "vitamin_b_priority": 1.2,
    },
    MetabolicPhase.DURING_EXERCISE: {
        "carbohydrate_priority": 1.8,   # Fuel for activity
        "protein_priority": 0.5,
        "fat_priority": 0.3,
        "water_priority": 2.0,
        "electrolyte_priority": 1.8,
    },
}


class MetabolicStateEstimator:
    """Estimates current metabolic state from synchronized biomarker frames.

    Patent-core algorithm:

    estimate_state(frame, event_history) →
      1. Determine feeding phase:
         - Find last meal event → compute hours_since_meal
         - Classify: fasting / postprandial_early / late / post_absorptive

      2. Determine exercise phase:
         - Find last exercise event → compute hours_since_exercise
         - Check current heart rate → during_exercise detection
         - Classify: during / recovery_immediate / recovery_delayed

      3. Determine sleep phase:
         - Check time of day + activity level
         - Determine hours_since_waking

      4. Estimate insulin sensitivity:
         - Base on feeding phase + sleep quality + exercise recency
         - Modify by genetic factors

      5. Combine phases → compound metabolic state
         - Multiple phases can be active simultaneously
         - Each phase contributes nutrient priority modifiers
         - Modifiers are multiplicatively combined

      6. Compute nutrient priority shifts from combined state
    """

    def __init__(self):
        self._meal_history: Dict[str, List[datetime]] = {}
        self._exercise_history: Dict[str, List[Dict[str, Any]]] = {}
        self._sleep_history: Dict[str, List[Dict[str, Any]]] = {}

    def record_meal_event(self, user_id: str, timestamp: datetime) -> None:
        """Record a meal event for metabolic state tracking."""
        if user_id not in self._meal_history:
            self._meal_history[user_id] = []
        self._meal_history[user_id].append(timestamp)
        # Keep last 30 days
        cutoff = timestamp - timedelta(days=30)
        self._meal_history[user_id] = [
            t for t in self._meal_history[user_id] if t > cutoff
        ]

    def record_exercise_event(
        self,
        user_id: str,
        timestamp: datetime,
        duration_minutes: float,
        intensity: str,
    ) -> None:
        """Record an exercise event."""
        if user_id not in self._exercise_history:
            self._exercise_history[user_id] = []
        self._exercise_history[user_id].append({
            "timestamp": timestamp,
            "duration_minutes": duration_minutes,
            "intensity": intensity,
        })

    def record_sleep_event(
        self,
        user_id: str,
        sleep_start: datetime,
        sleep_end: datetime,
        quality: float,
    ) -> None:
        """Record a sleep event."""
        if user_id not in self._sleep_history:
            self._sleep_history[user_id] = []
        self._sleep_history[user_id].append({
            "start": sleep_start,
            "end": sleep_end,
            "quality": quality,
        })

    def estimate(
        self,
        user_id: str,
        frame: SynchronizedFrame,
        current_time: Optional[datetime] = None,
    ) -> MetabolicState:
        """Estimate current metabolic state from a synchronized frame.

        This is the main entry point.
        """
        now = current_time or frame.window_end

        state = MetabolicState(timestamp=now)

        # Phase 1: Feeding state
        self._determine_feeding_phase(user_id, now, state)

        # Phase 2: Exercise state
        self._determine_exercise_phase(user_id, now, frame, state)

        # Phase 3: Sleep state
        self._determine_sleep_phase(user_id, now, frame, state)

        # Phase 4: Stress/recovery detection from HRV
        self._detect_stress_state(frame, state)

        # Phase 5: Estimate insulin sensitivity
        self._estimate_insulin_sensitivity(state)

        # Phase 6: Determine primary phase
        state.primary_phase = self._determine_primary_phase(state)

        # Phase 7: Compute combined nutrient priority shifts
        state.nutrient_priority_shifts = self._compute_nutrient_shifts(state)

        return state

    def _determine_feeding_phase(
        self, user_id: str, now: datetime, state: MetabolicState
    ) -> None:
        """Classify current feeding/fasting phase."""
        meals = self._meal_history.get(user_id, [])

        if not meals:
            state.hours_since_last_meal = 12.0
            state.active_phases.add(MetabolicPhase.FASTING)
            state.phase_intensities[MetabolicPhase.FASTING] = 1.0
            state.decision_log.append(
                "Feeding: No meal history → default FASTING (12h assumed)"
            )
            return

        last_meal = max(meals)
        # Ensure timezone-awareness compatibility
        _now = now
        _lm = last_meal
        if hasattr(_lm, 'tzinfo') and _lm.tzinfo is not None and _now.tzinfo is None:
            from datetime import timezone
            _now = _now.replace(tzinfo=timezone.utc)
        elif hasattr(_now, 'tzinfo') and _now.tzinfo is not None and (not hasattr(_lm, 'tzinfo') or _lm.tzinfo is None):
            from datetime import timezone
            _lm = _lm.replace(tzinfo=timezone.utc)
        hours = (_now - _lm).total_seconds() / 3600.0
        state.hours_since_last_meal = hours

        if hours < 2:
            state.active_phases.add(MetabolicPhase.POSTPRANDIAL_EARLY)
            state.phase_intensities[MetabolicPhase.POSTPRANDIAL_EARLY] = (
                1.0 - hours / 2.0
            )
            state.decision_log.append(
                f"Feeding: hours_since_meal={hours:.1f}h < 2h → POSTPRANDIAL_EARLY (intensity={1.0 - hours / 2.0:.2f})"
            )
        elif hours < 4:
            state.active_phases.add(MetabolicPhase.POSTPRANDIAL_LATE)
            state.phase_intensities[MetabolicPhase.POSTPRANDIAL_LATE] = (
                1.0 - (hours - 2) / 2.0
            )
            state.decision_log.append(
                f"Feeding: 2h ≤ hours_since_meal={hours:.1f}h < 4h → POSTPRANDIAL_LATE"
            )
        elif hours < 12:
            state.active_phases.add(MetabolicPhase.POST_ABSORPTIVE)
            state.phase_intensities[MetabolicPhase.POST_ABSORPTIVE] = 0.5
            state.decision_log.append(
                f"Feeding: 4h ≤ hours_since_meal={hours:.1f}h < 12h → POST_ABSORPTIVE"
            )
        else:
            state.active_phases.add(MetabolicPhase.FASTING)
            state.phase_intensities[MetabolicPhase.FASTING] = min(
                1.0, hours / 16.0
            )
            state.decision_log.append(
                f"Feeding: hours_since_meal={hours:.1f}h ≥ 12h → FASTING"
            )

    def _determine_exercise_phase(
        self,
        user_id: str,
        now: datetime,
        frame: SynchronizedFrame,
        state: MetabolicState,
    ) -> None:
        """Classify current exercise/recovery phase."""
        # Check if currently exercising via heart rate
        hr_signal = frame.signals.get(BiomarkerType.HEART_RATE)
        if hr_signal and hr_signal.confidence > 0.5:
            # HR > 100 suggests active exercise (context-dependent)
            if hr_signal.value > 100:
                state.active_phases.add(MetabolicPhase.DURING_EXERCISE)
                state.phase_intensities[MetabolicPhase.DURING_EXERCISE] = min(
                    1.0, (hr_signal.value - 100) / 80.0
                )
                state.decision_log.append(
                    f"Exercise: HR={hr_signal.value:.0f} > 100 threshold → DURING_EXERCISE"
                )
                return
            else:
                state.decision_log.append(
                    f"Exercise: HR={hr_signal.value:.0f} < 100 threshold → not currently exercising"
                )

        # Check exercise history
        exercises = self._exercise_history.get(user_id, [])
        if not exercises:
            state.hours_since_last_exercise = 48.0
            state.decision_log.append(
                "Exercise: No exercise history → hours_since_exercise=48h (default)"
            )
            return

        last_ex = max(exercises, key=lambda e: e["timestamp"])
        end_time = last_ex["timestamp"] + timedelta(
            minutes=last_ex["duration_minutes"]
        )
        # Ensure timezone-awareness compatibility
        _now = now
        _et = end_time
        if hasattr(_et, 'tzinfo') and _et.tzinfo is not None and _now.tzinfo is None:
            from datetime import timezone
            _now = _now.replace(tzinfo=timezone.utc)
        elif hasattr(_now, 'tzinfo') and _now.tzinfo is not None and (not hasattr(_et, 'tzinfo') or _et.tzinfo is None):
            from datetime import timezone
            _et = _et.replace(tzinfo=timezone.utc)
        hours = (_now - _et).total_seconds() / 3600.0
        state.hours_since_last_exercise = max(0, hours)

        intensity = last_ex.get("intensity", "moderate")

        if hours < 0:
            # Still exercising
            state.active_phases.add(MetabolicPhase.DURING_EXERCISE)
            state.phase_intensities[MetabolicPhase.DURING_EXERCISE] = 1.0
            state.decision_log.append(
                f"Exercise: Last exercise still ongoing (ends in {-hours:.1f}h) → DURING_EXERCISE"
            )
        elif hours < 2:
            state.active_phases.add(MetabolicPhase.RECOVERY_IMMEDIATE)
            state.phase_intensities[MetabolicPhase.RECOVERY_IMMEDIATE] = (
                1.0 - hours / 2.0
            )
            state.decision_log.append(
                f"Exercise: {hours:.1f}h since {intensity} exercise < 2h → RECOVERY_IMMEDIATE"
            )
        elif intensity in ("high", "extreme") and hours < 48:
            state.active_phases.add(MetabolicPhase.RECOVERY_DELAYED)
            state.phase_intensities[MetabolicPhase.RECOVERY_DELAYED] = (
                max(0, 1.0 - hours / 48.0)
            )
            state.decision_log.append(
                f"Exercise: {hours:.1f}h since {intensity} exercise, 2h-48h → RECOVERY_DELAYED"
            )
        else:
            state.decision_log.append(
                f"Exercise: {hours:.1f}h since {intensity} exercise → no active exercise phase"
            )

    def _determine_sleep_phase(
        self,
        user_id: str,
        now: datetime,
        frame: SynchronizedFrame,
        state: MetabolicState,
    ) -> None:
        """Classify sleep-related phase."""
        sleeps = self._sleep_history.get(user_id, [])

        # Simple time-of-day heuristic + activity level
        hour = now.hour
        steps_signal = frame.signals.get(BiomarkerType.STEPS)
        step_rate = 0
        if steps_signal and steps_signal.confidence > 0.3:
            step_rate = steps_signal.value

        # Detect current sleeping
        if (hour >= 23 or hour < 6) and step_rate < 5:
            state.active_phases.add(MetabolicPhase.SLEEPING)
            state.phase_intensities[MetabolicPhase.SLEEPING] = 0.8
            state.decision_log.append(
                f"Sleep: hour={hour:02d}:00 ∈ [23:00-06:00] AND step_rate={step_rate:.0f} < 5 → SLEEPING"
            )
            return
        elif hour >= 23 or hour < 6:
            state.decision_log.append(
                f"Sleep: hour={hour:02d}:00 ∈ [23:00-06:00] BUT step_rate={step_rate:.0f} ≥ 5 → not sleeping"
            )
        else:
            state.decision_log.append(
                f"Sleep: hour={hour:02d}:00 ∉ [23:00-06:00] → not in sleep window"
            )

        # Check if recently woke up
        if sleeps:
            last_sleep = max(sleeps, key=lambda s: s["end"])
            # Ensure timezone-awareness compatibility
            sleep_end = last_sleep["end"]
            _now = now
            if hasattr(sleep_end, 'tzinfo') and sleep_end.tzinfo is not None and _now.tzinfo is None:
                from datetime import timezone
                _now = _now.replace(tzinfo=timezone.utc)
            elif hasattr(_now, 'tzinfo') and _now.tzinfo is not None and (not hasattr(sleep_end, 'tzinfo') or sleep_end.tzinfo is None):
                from datetime import timezone
                sleep_end = sleep_end.replace(tzinfo=timezone.utc)
            hours_since_waking = (
                _now - sleep_end
            ).total_seconds() / 3600.0
            state.hours_since_waking = max(0, hours_since_waking)

            if hours_since_waking < 1:
                state.active_phases.add(MetabolicPhase.POST_WAKING)
                state.phase_intensities[MetabolicPhase.POST_WAKING] = (
                    1.0 - hours_since_waking
                )
                state.decision_log.append(
                    f"Sleep: {hours_since_waking:.1f}h since waking < 1h → POST_WAKING"
                )

        # Check if approaching bedtime (21:00-23:00)
        if 21 <= hour < 23:
            state.active_phases.add(MetabolicPhase.PRE_SLEEP)
            state.phase_intensities[MetabolicPhase.PRE_SLEEP] = (
                (hour - 21) / 2.0
            )
            state.decision_log.append(
                f"Sleep: hour={hour:02d}:00 ∈ [21:00-23:00] → PRE_SLEEP"
            )

    def _detect_stress_state(
        self, frame: SynchronizedFrame, state: MetabolicState
    ) -> None:
        """Detect metabolic stress from HRV and heart rate signals."""
        hrv_signal = frame.signals.get(BiomarkerType.HRV)

        if hrv_signal and hrv_signal.confidence > 0.5:
            # Low HRV indicates sympathetic dominance (stress)
            if hrv_signal.value < 30:
                state.active_phases.add(MetabolicPhase.METABOLIC_STRESS)
                state.phase_intensities[MetabolicPhase.METABOLIC_STRESS] = (
                    max(0, 1.0 - hrv_signal.value / 30.0)
                )
                state.decision_log.append(
                    f"Stress: HRV={hrv_signal.value:.1f}ms < 30ms threshold → METABOLIC_STRESS"
                )
            # High HRV indicates parasympathetic dominance (recovery)
            elif hrv_signal.value > 60:
                state.active_phases.add(MetabolicPhase.RECOVERY)
                state.phase_intensities[MetabolicPhase.RECOVERY] = min(
                    1.0, (hrv_signal.value - 60) / 40.0
                )
                state.decision_log.append(
                    f"Stress: HRV={hrv_signal.value:.1f}ms > 60ms → RECOVERY (parasympathetic)"
                )
            else:
                state.decision_log.append(
                    f"Stress: HRV={hrv_signal.value:.1f}ms ∈ [30-60ms] → neutral autonomic state"
                )
        else:
            state.decision_log.append(
                "Stress: HRV signal unavailable or low confidence → skipped"
            )

    def _estimate_insulin_sensitivity(self, state: MetabolicState) -> None:
        """Estimate current insulin sensitivity from metabolic state.

        Patent-relevant: Insulin sensitivity affects how carbohydrate
        intake should be distributed. This is a dynamic estimate that
        changes throughout the day based on multiple factors.
        """
        sensitivity = 0.7  # Population average baseline

        # Fasting improves sensitivity
        if MetabolicPhase.FASTING in state.active_phases:
            sensitivity += 0.1

        # Post-exercise improves sensitivity (for 24-48h)
        if MetabolicPhase.RECOVERY_IMMEDIATE in state.active_phases:
            sensitivity += 0.15
        elif MetabolicPhase.RECOVERY_DELAYED in state.active_phases:
            intensity = state.phase_intensities.get(
                MetabolicPhase.RECOVERY_DELAYED, 0
            )
            sensitivity += 0.10 * intensity

        # Postprandial reduces sensitivity temporarily
        if MetabolicPhase.POSTPRANDIAL_EARLY in state.active_phases:
            sensitivity -= 0.1

        # Stress reduces sensitivity
        if MetabolicPhase.METABOLIC_STRESS in state.active_phases:
            intensity = state.phase_intensities.get(
                MetabolicPhase.METABOLIC_STRESS, 0
            )
            sensitivity -= 0.15 * intensity

        # Poor sleep reduces next-day sensitivity
        if state.hours_since_waking < 12:
            # Recent sleep data would modify this further
            pass

        # Morning typically has better sensitivity (circadian)
        hour = state.timestamp.hour
        if 6 <= hour <= 10:
            sensitivity += 0.05
        elif 20 <= hour <= 23:
            sensitivity -= 0.05

        state.insulin_sensitivity_estimate = max(0.2, min(1.0, sensitivity))

    def _determine_primary_phase(self, state: MetabolicState) -> MetabolicPhase:
        """Determine the dominant metabolic phase.

        Priority order (highest to lowest):
        1. During exercise (immediate energy needs)
        2. Immediate recovery (anabolic window)
        3. Sleeping (rest/recovery)
        4. Postprandial (digestion)
        5. Fasting
        6. Other
        """
        priority = [
            MetabolicPhase.DURING_EXERCISE,
            MetabolicPhase.RECOVERY_IMMEDIATE,
            MetabolicPhase.SLEEPING,
            MetabolicPhase.POSTPRANDIAL_EARLY,
            MetabolicPhase.POSTPRANDIAL_LATE,
            MetabolicPhase.POST_WAKING,
            MetabolicPhase.PRE_SLEEP,
            MetabolicPhase.FASTING,
            MetabolicPhase.RECOVERY_DELAYED,
            MetabolicPhase.POST_ABSORPTIVE,
            MetabolicPhase.METABOLIC_STRESS,
            MetabolicPhase.RECOVERY,
            MetabolicPhase.CIRCADIAN_LOW,
        ]

        for phase in priority:
            if phase in state.active_phases:
                return phase

        return MetabolicPhase.FASTING

    def _compute_nutrient_shifts(
        self, state: MetabolicState
    ) -> Dict[str, float]:
        """Compute combined nutrient priority shifts from all active phases.

        Patent-relevant: Multiple simultaneous metabolic phases create
        compound nutrient demands. This multiplicative combination
        produces unique nutrient profiles for each metabolic combination.

        Example: RECOVERY_IMMEDIATE + POST_WAKING =
          carb_priority: 1.5 × 1.0 = 1.5
          protein_priority: 1.4 × 1.2 = 1.68 (extra protein from both)
          water_priority: 1.5 × 1.4 = 2.1 (compounded hydration need)
        """
        combined: Dict[str, float] = {}

        for phase in state.active_phases:
            modifiers = PHASE_NUTRIENT_MODIFIERS.get(phase, {})
            intensity = state.phase_intensities.get(phase, 1.0)

            for nutrient, modifier in modifiers.items():
                # Scale modifier by phase intensity
                scaled = 1.0 + (modifier - 1.0) * intensity

                if nutrient in combined:
                    # Multiplicative combination
                    combined[nutrient] *= scaled
                else:
                    combined[nutrient] = scaled

        return {k: round(v, 3) for k, v in combined.items()}
