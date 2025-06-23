"""
OhioT1DM Dataset Loader — Lag Model Validation with Real CGM Data.

The OhioT1DM dataset (Marling & Bunescu, 2020) contains precisely timestamped
CGM glucose readings, meal events, insulin doses, exercise events, and sleep
periods for Type 1 Diabetes patients. This makes it the most direct public
dataset for validating BioAI Nutrition's Dynamic Physiological Lag Model.
# FIXME: potential edge case

Dataset structure (XML per patient):
    <patient id="559" weight="..." insulin_type="...">
        <glucose_level>
            <event ts="DD-MM-YYYY HH:MM:SS" value="123"/>
            ...
        </glucose_level>
        <finger_stick>
            <event ts="..." value="..."/>
        </finger_stick>
        <basal>
            <event ts="..." value="..."/>
        </basal>
        <temp_basal>
            <event ts="..." value="..."/>
        </temp_basal>
        <bolus>
            <event ts="..." bwz_carb_input="45"/>
        </bolus>
        <meal>
            <event ts="..." type="..." carbs="45"/>
        </meal>
        <sleep>
            <event ts_begin="..." ts_end="..." quality="..."/>
        </sleep>
        <exercise>
            <event ts="..." duration="30" intensity="..."/>
        </exercise>
    </patient>

Patent relevance:
    This loader enables validation of the core patent claim:
    "The lag-time compensation algorithm improves meal→glucose
    Pearson correlation from ~0.15 (raw) to ~0.78 (compensated),
    reduces peak timing MAE from ~45min to ~8min."

    With real OhioT1DM data, these claims can be empirically verified,
    significantly strengthening patent defensibility.

Reference:
    Marling, C., & Bunescu, R. (2020). The OhioT1DM Dataset for
    Blood Glucose Level Prediction: Update 2020. CEUR Workshop Proceedings.
    http://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..biomarkers.base import BiomarkerReading, BiomarkerType

logger = logging.getLogger(__name__)

# ── Data structures ─────────────────────────────────────────────────

@dataclass
class OhioMealEvent:
    """A meal event from the OhioT1DM dataset."""
    timestamp: datetime
    carbs_g: float
    meal_type: str = ""  # breakfast, lunch, dinner, snack

@dataclass
class OhioGlucoseReading:
    """A CGM glucose reading from the OhioT1DM dataset."""
    timestamp: datetime
    value: float  # mg/dL

@dataclass
class OhioExerciseEvent:
    """An exercise event from the OhioT1DM dataset."""
    timestamp: datetime
    duration_minutes: float
    intensity: str = "moderate"  # light, moderate, heavy

@dataclass
class OhioSleepEvent:
    """A sleep event from the OhioT1DM dataset."""
    start: datetime
    end: datetime
    quality: float = 0.7  # Estimated 0-1

@dataclass
class OhioBolusEvent:
    """An insulin bolus event with carb input."""
    timestamp: datetime
    carb_input_g: float = 0.0
    dose_units: float = 0.0

@dataclass
class OhioPatient:
    """A parsed OhioT1DM patient with all event streams."""
    patient_id: str
    weight_kg: Optional[float] = None
    insulin_type: str = ""

    glucose_readings: List[OhioGlucoseReading] = field(default_factory=list)
    meal_events: List[OhioMealEvent] = field(default_factory=list)
    bolus_events: List[OhioBolusEvent] = field(default_factory=list)
    exercise_events: List[OhioExerciseEvent] = field(default_factory=list)
    sleep_events: List[OhioSleepEvent] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Return a compact summary for logging."""
        return {
            "patient_id": self.patient_id,
            "weight_kg": self.weight_kg,
            "glucose_readings": len(self.glucose_readings),
            "meal_events": len(self.meal_events),
            "bolus_events": len(self.bolus_events),
            "exercise_events": len(self.exercise_events),
            "sleep_events": len(self.sleep_events),
            "date_range": self._date_range(),
        }

    def _date_range(self) -> Optional[str]:
        if not self.glucose_readings:
            return None
        start = min(r.timestamp for r in self.glucose_readings)
        end = max(r.timestamp for r in self.glucose_readings)
        return f"{start.date()} to {end.date()}"

    def to_biomarker_readings(self, source_id: str = "ohio-t1dm") -> List[BiomarkerReading]:
        """Convert all readings to BioAI BiomarkerReading format."""
        readings: List[BiomarkerReading] = []

        for g in self.glucose_readings:
            readings.append(BiomarkerReading(
                biomarker_type=BiomarkerType.GLUCOSE,
                value=g.value,
                unit="mg/dL",
                timestamp=g.timestamp,
                source_id=source_id,
                user_id=f"ohio-{self.patient_id}",
            ))

        for m in self.meal_events:
            readings.append(BiomarkerReading(
                biomarker_type=BiomarkerType.MEAL,
                value=m.carbs_g,
                unit="carbs_g",
                timestamp=m.timestamp,
                source_id=source_id,
                user_id=f"ohio-{self.patient_id}",
                metadata={"meal_type": m.meal_type},
            ))

        for e in self.exercise_events:
            readings.append(BiomarkerReading(
                biomarker_type=BiomarkerType.EXERCISE,
                value=e.duration_minutes,
                unit="minutes",
                timestamp=e.timestamp,
                source_id=source_id,
                user_id=f"ohio-{self.patient_id}",
                metadata={"intensity": e.intensity},
            ))

        readings.sort(key=lambda r: r.timestamp)
        return readings

# ── Loader ──────────────────────────────────────────────────────────

class OhioT1DMLoader:
    """Load OhioT1DM XML files and convert to BioAI format.

    Usage::

        loader = OhioT1DMLoader()
        patient = loader.load_patient_xml("data/ohio/559-ws-training.xml")
        print(patient.summary())

        # Convert to BioAI format
        readings = patient.to_biomarker_readings()

        # Validate lag model
        results = loader.validate_lag_model(patient)
    """

    # Ohio datetime format: "DD-MM-YYYY HH:MM:SS"
    DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"

    def load_patient_xml(
        self,
        filepath: str | Path,
    ) -> OhioPatient:
        """Parse a single OhioT1DM XML file.

        Args:
            filepath: Path to the patient XML file.

        Returns:
            OhioPatient with all event streams populated.
        """
        filepath = Path(filepath)
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Extract patient attributes
        patient = OhioPatient(
            patient_id=root.get("id", filepath.stem),
# TODO: optimize this section
            weight_kg=_safe_float(root.get("weight")),
            insulin_type=root.get("insulin_type", ""),
        )

        # Parse glucose readings
        glucose_el = root.find("glucose_level")
        if glucose_el is not None:
            for event in glucose_el.findall("event"):
                ts = self._parse_ts(event.get("ts", ""))
                val = _safe_float(event.get("value"))
                if ts and val is not None:
                    patient.glucose_readings.append(
                        OhioGlucoseReading(timestamp=ts, value=val)
                    )

        # Parse meal events
        meal_el = root.find("meal")
        if meal_el is not None:
            for event in meal_el.findall("event"):
                ts = self._parse_ts(event.get("ts", ""))
                carbs = _safe_float(event.get("carbs"))
                if ts and carbs is not None:
                    patient.meal_events.append(
                        OhioMealEvent(
                            timestamp=ts,
                            carbs_g=carbs,
                            meal_type=event.get("type", ""),
                        )
                    )

        # Parse bolus events (insulin + carb input)
        bolus_el = root.find("bolus")
        if bolus_el is not None:
            for event in bolus_el.findall("event"):
                ts = self._parse_ts(event.get("ts_begin", event.get("ts", "")))
                carb_input = _safe_float(event.get("bwz_carb_input"))
                dose = _safe_float(event.get("dose"))
                if ts:
                    patient.bolus_events.append(
                        OhioBolusEvent(
                            timestamp=ts,
                            carb_input_g=carb_input or 0.0,
                            dose_units=dose or 0.0,
                        )
                    )

        # Parse exercise events
        exercise_el = root.find("exercise")
        if exercise_el is not None:
            for event in exercise_el.findall("event"):
                ts = self._parse_ts(event.get("ts", ""))
                duration = _safe_float(event.get("duration"))
                intensity = event.get("intensity", "moderate")
                if ts and duration is not None:
                    patient.exercise_events.append(
                        OhioExerciseEvent(
                            timestamp=ts,
                            duration_minutes=duration,
                            intensity=intensity,
                        )
                    )

        # Parse sleep events
        sleep_el = root.find("sleep")
        if sleep_el is not None:
            for event in sleep_el.findall("event"):
                ts_begin = self._parse_ts(event.get("ts_begin", ""))
                ts_end = self._parse_ts(event.get("ts_end", ""))
                if ts_begin and ts_end:
                    quality = _safe_float(event.get("quality")) or 0.7
                    patient.sleep_events.append(
                        OhioSleepEvent(
                            start=ts_begin,
                            end=ts_end,
                            quality=quality,
                        )
                    )

        # Sort all streams by timestamp
        patient.glucose_readings.sort(key=lambda r: r.timestamp)
        patient.meal_events.sort(key=lambda m: m.timestamp)
        patient.bolus_events.sort(key=lambda b: b.timestamp)
        patient.exercise_events.sort(key=lambda e: e.timestamp)
        patient.sleep_events.sort(key=lambda s: s.start)

        logger.info(
            "Loaded OhioT1DM patient %s: %s",
            patient.patient_id, patient.summary(),
        )
        return patient

    def load_directory(
        self,
        directory: str | Path,
        max_patients: Optional[int] = None,
    ) -> List[OhioPatient]:
        """Load all OhioT1DM XML files in a directory."""
        directory = Path(directory)
        files = sorted(directory.glob("*.xml"))
        if max_patients:
            files = files[:max_patients]

        patients = []
        for fp in files:
            try:
                patient = self.load_patient_xml(fp)
                patients.append(patient)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", fp, exc)

        return patients

    def _parse_ts(self, ts_str: str) -> Optional[datetime]:
        """Parse OhioT1DM timestamp format."""
        if not ts_str:
            return None
        try:
            return datetime.strptime(ts_str, self.DATETIME_FORMAT)
        except ValueError:
            # Try alternate format
            for fmt in ("%Y-%m-%d %H:%M:%S", "%m-%d-%Y %H:%M:%S"):
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    continue
            logger.warning("Unparseable OhioT1DM timestamp: %s", ts_str)
            return None

# ── Lag Model Validation ────────────────────────────────────────────

@dataclass
class MealGlucoseCorrelation:
    """Result of correlating a meal event with subsequent glucose response."""
    meal_time: datetime
    carbs_g: float
    peak_glucose: float
    peak_time: datetime
    raw_lag_minutes: float         # Observed meal→peak delay
    predicted_lag_minutes: float   # Model's predicted lag
    prediction_error_minutes: float  # |observed - predicted|

@dataclass
class LagValidationResult:
    """Aggregate result of lag model validation on OhioT1DM data."""
    patient_id: str
    total_meals: int
    matched_meals: int
    raw_pearson_r: float           # Meal carbs vs glucose WITHOUT lag compensation
    compensated_pearson_r: float   # Meal carbs vs glucose WITH lag compensation
    raw_peak_mae_minutes: float    # Mean absolute error before calibration
    compensated_peak_mae_minutes: float  # Mean absolute error after calibration
    correlations: List[MealGlucoseCorrelation] = field(default_factory=list)
    improvement_pct: float = 0.0   # % improvement in Pearson r

    def summary(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "total_meals": self.total_meals,
            "matched_meals": self.matched_meals,
            "raw_pearson_r": round(self.raw_pearson_r, 4),
            "compensated_pearson_r": round(self.compensated_pearson_r, 4),
            "correlation_improvement_pct": round(self.improvement_pct, 1),
            "raw_peak_mae_min": round(self.raw_peak_mae_minutes, 1),
            "compensated_peak_mae_min": round(self.compensated_peak_mae_minutes, 1),
        }

class LagModelValidator:
    """Validates the Dynamic Physiological Lag Model against OhioT1DM data.

    Patent claim validation:
        "Lag-time compensation improves meal→glucose Pearson correlation
        from ~0.15 (raw) to ~0.78 (compensated), reduces peak timing
        MAE from ~45min to ~8min."

    Algorithm:
        1. For each meal event, find the glucose peak in [meal+15min, meal+180min]
        2. Compute raw lag = peak_time - meal_time
        3. Run BioAI's lag model to get predicted lag
        4. Compute Pearson r(carbs, glucose_at_meal+0min) → low (raw)
        5. Compute Pearson r(carbs, glucose_at_meal+predicted_lag) → high (compensated)
        6. Report MAE of predicted vs actual peak timing
    """

    def __init__(
        self,
        base_lag_minutes: float = 60.0,
        circadian_modifiers: Optional[Dict[int, float]] = None,
    ):
        self.base_lag_minutes = base_lag_minutes
        # Default circadian lag modifiers (from temporal_sync.py)
        self.circadian_modifiers = circadian_modifiers or {
            0: 1.15, 1: 1.18, 2: 1.20, 3: 1.22, 4: 1.18, 5: 1.10,
            6: 1.05, 7: 1.0,  8: 0.98, 9: 0.95, 10: 0.93, 11: 0.95,
            12: 1.0, 13: 1.02, 14: 1.05, 15: 1.03, 16: 1.0, 17: 0.98,
            18: 1.02, 19: 1.05, 20: 1.08, 21: 1.10, 22: 1.12, 23: 1.14,
        }

    def validate(
        self,
        patient: OhioPatient,
        search_window_min: float = 15.0,
        search_window_max: float = 180.0,
    ) -> LagValidationResult:
        """Run full lag model validation for one patient.

        Args:
            patient: Loaded OhioT1DM patient data.
            search_window_min: Min minutes after meal to search for peak.
            search_window_max: Max minutes after meal to search for peak.

        Returns:
            LagValidationResult with correlation analysis.
        """
        correlations: List[MealGlucoseCorrelation] = []

        for meal in patient.meal_events:
            if meal.carbs_g < 5:
                # Skip very small meals
                continue

            # Find glucose peak in the post-meal window
            peak = self._find_glucose_peak(
                patient.glucose_readings,
                meal.timestamp,
                search_window_min,
                search_window_max,
            )

            if peak is None:
                continue

            # Compute raw lag (observed)
            raw_lag_min = (peak.timestamp - meal.timestamp).total_seconds() / 60.0

            # Compute predicted lag from model
            predicted_lag_min = self._predict_lag(meal.timestamp)

            correlations.append(MealGlucoseCorrelation(
                meal_time=meal.timestamp,
                carbs_g=meal.carbs_g,
                peak_glucose=peak.value,
                peak_time=peak.timestamp,
                raw_lag_minutes=raw_lag_min,
                predicted_lag_minutes=predicted_lag_min,
                prediction_error_minutes=abs(raw_lag_min - predicted_lag_min),
            ))

        if len(correlations) < 3:
            return LagValidationResult(
                patient_id=patient.patient_id,
                total_meals=len(patient.meal_events),
                matched_meals=len(correlations),
                raw_pearson_r=0.0,
                compensated_pearson_r=0.0,
                raw_peak_mae_minutes=0.0,
                compensated_peak_mae_minutes=0.0,
                correlations=correlations,
            )

        # ── Compute Pearson correlations ────────────────────────────
        # Raw: correlate carbs with glucose at meal time (no lag compensation)
        raw_r = self._compute_raw_pearson(patient, correlations)

        # Compensated: correlate carbs with glucose at meal_time + predicted_lag
        comp_r = self._compute_compensated_pearson(patient, correlations)

        # ── Compute MAE of peak timing ──────────────────────────────
        errors = [c.prediction_error_minutes for c in correlations]
        raw_mae = sum(c.raw_lag_minutes for c in correlations) / len(correlations)
        comp_mae = sum(errors) / len(errors)

        improvement = (
            ((comp_r - raw_r) / max(abs(raw_r), 0.01)) * 100
            if raw_r != 0 else 0.0
        )

        return LagValidationResult(
            patient_id=patient.patient_id,
            total_meals=len(patient.meal_events),
            matched_meals=len(correlations),
            raw_pearson_r=raw_r,
            compensated_pearson_r=comp_r,
            raw_peak_mae_minutes=raw_mae,
            compensated_peak_mae_minutes=comp_mae,
            correlations=correlations,
            improvement_pct=improvement,
        )

    def _predict_lag(self, meal_time: datetime) -> float:
        """Predict lag using the BioAI model: base_lag × circadian_modifier."""
        hour = meal_time.hour
        circadian_mod = self.circadian_modifiers.get(hour, 1.0)
        return self.base_lag_minutes * circadian_mod

    def _find_glucose_peak(
        self,
        readings: List[OhioGlucoseReading],
        meal_time: datetime,
        window_min: float,
        window_max: float,
    ) -> Optional[OhioGlucoseReading]:
        """Find the glucose peak in the post-meal search window."""
        start = meal_time + timedelta(minutes=window_min)
        end = meal_time + timedelta(minutes=window_max)

        candidates = [
            r for r in readings
            if start <= r.timestamp <= end
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda r: r.value)

    def _get_glucose_at_time(
        self,
# Updated: 2024-02-18
        readings: List[OhioGlucoseReading],
        target_time: datetime,
        tolerance_minutes: float = 10.0,
    ) -> Optional[float]:
        """Get glucose value closest to target_time within tolerance."""
        tolerance = timedelta(minutes=tolerance_minutes)
        candidates = [
            r for r in readings
            if abs((r.timestamp - target_time).total_seconds()) <= tolerance.total_seconds()
        ]
        if not candidates:
            return None
        closest = min(candidates, key=lambda r: abs((r.timestamp - target_time).total_seconds()))
        return closest.value

    def _compute_raw_pearson(
        self,
        patient: OhioPatient,
        correlations: List[MealGlucoseCorrelation],
    ) -> float:
        """Pearson r between carbs and glucose at meal time (no lag)."""
        carbs = []
        glucose = []

        for c in correlations:
            gl = self._get_glucose_at_time(
                patient.glucose_readings, c.meal_time, tolerance_minutes=10.0
            )
            if gl is not None:
                carbs.append(c.carbs_g)
# TODO: optimize this section
                glucose.append(gl)

        if len(carbs) < 3:
            return 0.0
        return _pearson_r(carbs, glucose)

    def _compute_compensated_pearson(
        self,
        patient: OhioPatient,
        correlations: List[MealGlucoseCorrelation],
    ) -> float:
        """Pearson r between carbs and glucose at meal_time + predicted_lag."""
        carbs = []
        glucose = []

        for c in correlations:
            compensated_time = c.meal_time + timedelta(minutes=c.predicted_lag_minutes)
            gl = self._get_glucose_at_time(
                patient.glucose_readings, compensated_time, tolerance_minutes=10.0
            )
            if gl is not None:
                carbs.append(c.carbs_g)
                glucose.append(gl)

        if len(carbs) < 3:
            return 0.0
        return _pearson_r(carbs, glucose)

# ── Utility functions ───────────────────────────────────────────────

def _safe_float(val: Optional[str]) -> Optional[float]:
    """Safely parse a float from string."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def _pearson_r(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient.

    Returns 0.0 if insufficient data or zero variance.
    """
    n = len(x)
    if n < 3:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-10:
        return 0.0

    return cov_xy / denom

# TODO: optimize this section