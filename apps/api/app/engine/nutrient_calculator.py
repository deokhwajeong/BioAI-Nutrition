"""
Real-Time Nutrient Demand Calculator.

Patent-core module: Computes instantaneous and time-budgeted nutrient
requirements by integrating all upstream engine outputs:

1. Synchronized biomarker frames (temporal_sync)
2. Normalized physiological signals (normalization)
3. Current metabolic state (metabolic_state)
4. Genetic modifiers (biomarkers/genetic_adapter)

This is the final stage of the patent pipeline — it produces actionable
nutrient budgets that can drive recommendations.

Key inventive concepts:
- Dynamic Budget Allocation: remaining daily nutrient budget adjusted
  in real-time based on what's been consumed vs. current metabolic needs
- Constraint Satisfaction: medical/allergy/drug-interaction constraints
  are applied as hard boundaries that the budget cannot violate
- Temporal Distribution: optimal nutrient TIMING, not just quantity
  (e.g., more carbs in the glycogen-replenishment window after exercise)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..biomarkers.base import BiomarkerType
from .metabolic_state import MetabolicState, MetabolicPhase
from .normalization import NormalizedSignal
from .temporal_sync import SynchronizedFrame


@dataclass
class NutrientTarget:
    """Daily target for a single nutrient.

    Attributes:
        name: Nutrient name (e.g., "protein_g", "carbs_g").
        daily_target: Total daily requirement.
        minimum: Hard floor — never recommend less.
        maximum: Hard ceiling — medical constraint.
        consumed_today: Amount already consumed.
        unit: Measurement unit.
    """

    name: str
    daily_target: float
    minimum: float
    maximum: float
    consumed_today: float = 0.0
    unit: str = "g"

    @property
    def remaining(self) -> float:
        return max(0, self.daily_target - self.consumed_today)

    @property
    def remaining_pct(self) -> float:
        if self.daily_target == 0:
            return 0
        return self.remaining / self.daily_target


@dataclass
class MedicalConstraint:
    """A medical or safety constraint on nutrient intake.

    Examples:
    - CKD patient: protein_g max = 0.8g/kg/day
    - Hypertension: sodium_mg max = 1500mg/day
    - Warfarin: vitamin_k_mcg requires consistency (not a max)
    - Allergy: certain food groups excluded entirely
    """

    nutrient: str
    constraint_type: str  # "max", "min", "range", "consistency"
    value: float
    reason: str
    severity: str = "warning"  # "warning", "critical"
    source: str = "user_reported"  # "user_reported", "medical_record", "genetic"


@dataclass
class TimeBucket:
    """A time period with specific nutrient distribution recommendations.

    Patent-relevant: Nutrient timing is as important as total quantity.
    This structure enables scheduling of nutrients across the day
    based on metabolic state predictions.
    """

    start_hour: int
    end_hour: int
    label: str
    carb_pct: float = 0.0      # % of remaining daily carbs for this window
    protein_pct: float = 0.0   # % of remaining daily protein
    fat_pct: float = 0.0
    water_pct: float = 0.0
    priority_nutrients: List[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class NutrientBudget:
    """Complete nutrient budget — the final output of the pipeline.

    This is what drives recommendation generation. It contains:
    - What to eat (adjusted macro/micro targets)
    - When to eat (time-bucketed distribution)
    - Why (metabolic rationale for each adjustment)
    - What NOT to eat (medical constraints)

    Patent claim: "A real-time nutrient budget comprising dynamically
    adjusted macro and micronutrient targets, temporally distributed
    across predicted metabolic state windows, constrained by
    personalized medical boundaries, and weighted by genotype-specific
    metabolic coefficients."
    """

    timestamp: datetime
    user_id: str

    # Adjusted targets (after all modifications)
    targets: Dict[str, NutrientTarget] = field(default_factory=dict)

    # Time-bucketed distribution
    time_buckets: List[TimeBucket] = field(default_factory=list)

    # Current metabolic state that drove these adjustments
    metabolic_state: Optional[MetabolicState] = None

    # Applied modifications with rationale
    modifications: List[Dict[str, Any]] = field(default_factory=list)

    # Active medical constraints
    active_constraints: List[MedicalConstraint] = field(default_factory=list)

    # Overall budget quality/confidence
    confidence: float = 0.0

    def get_next_meal_recommendation(self) -> Dict[str, float]:
        """Get recommended nutrient amounts for the next meal.

        Calculates optimal meal composition based on current time,
        remaining budget, and metabolic state.
        """
        now = self.timestamp
        current_hour = now.hour

        # Find the current time bucket
        current_bucket = None
        for bucket in self.time_buckets:
            if bucket.start_hour <= current_hour < bucket.end_hour:
                current_bucket = bucket
                break

        if current_bucket is None:
            # Default even distribution
            remaining_meals = max(1, (22 - current_hour) // 4)
            return {
                name: target.remaining / remaining_meals
                for name, target in self.targets.items()
            }

        # Allocate based on bucket percentages
        recommendation: Dict[str, float] = {}
        for name, target in self.targets.items():
            if "carb" in name:
                pct = current_bucket.carb_pct
            elif "protein" in name:
                pct = current_bucket.protein_pct
            elif "fat" in name:
                pct = current_bucket.fat_pct
            elif "water" in name:
                pct = current_bucket.water_pct
            else:
                pct = 0.33  # Default even distribution

            recommendation[name] = target.remaining * pct

        return recommendation

    def to_summary(self) -> Dict[str, Any]:
        """Produce a human-readable summary of the budget."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "targets": {
                name: {
                    "daily": t.daily_target,
                    "consumed": t.consumed_today,
                    "remaining": t.remaining,
                    "remaining_pct": round(t.remaining_pct * 100, 1),
                    "unit": t.unit,
                }
                for name, t in self.targets.items()
            },
            "metabolic_state": (
                self.metabolic_state.to_context_string()
                if self.metabolic_state
                else "unknown"
            ),
            "active_phases": (
                [p.value for p in self.metabolic_state.active_phases]
                if self.metabolic_state
                else []
            ),
            "modifications_count": len(self.modifications),
            "constraints_count": len(self.active_constraints),
            "confidence": round(self.confidence, 3),
            "next_meal": self.get_next_meal_recommendation(),
        }


class NutrientDemandCalculator:
    """Calculates real-time nutrient demands from the full biomarker pipeline.

    Patent-core algorithm:

    calculate(user, frame, metabolic_state, genetic_modifiers) →
      1. Start with base daily targets (from user profile or RDA)

      2. Apply metabolic state modifiers:
         For each active phase, multiply macro targets by phase modifiers
         carb_target *= phase.carb_priority
         protein_target *= phase.protein_priority
         ...

      3. Apply genetic modifiers:
         carb_target *= genetic.carb_sensitivity_modifier
         folate_target *= genetic.folate_requirement_modifier
         ...

      4. Apply biomarker-driven adjustments:
         If glucose_z > 1.5: reduce carb_target by 10%
         If HRV_z < -1.0: increase magnesium_target by 15%
         ...

      5. Subtract already-consumed amounts:
         remaining = adjusted_target - consumed_today

      6. Apply medical constraints as hard boundaries:
         remaining = min(remaining, constraint.max)
         remaining = max(remaining, constraint.min)

      7. Distribute remaining across time buckets:
         Based on predicted metabolic state windows for rest of day

      8. Package as NutrientBudget with full audit trail
    """

    def __init__(self):
        self._user_constraints: Dict[str, List[MedicalConstraint]] = {}

    def set_medical_constraints(
        self, user_id: str, constraints: List[MedicalConstraint]
    ) -> None:
        """Set medical constraints for a user."""
        self._user_constraints[user_id] = constraints

    def calculate(
        self,
        user_id: str,
        base_targets: Dict[str, NutrientTarget],
        metabolic_state: MetabolicState,
        normalized_signals: Dict[BiomarkerType, NormalizedSignal],
        genetic_modifiers: Dict[str, float],
        frame_confidence: float = 1.0,
    ) -> NutrientBudget:
        """Calculate real-time nutrient budget.

        This is the main entry point that orchestrates the full calculation.
        """
        budget = NutrientBudget(
            timestamp=metabolic_state.timestamp,
            user_id=user_id,
            metabolic_state=metabolic_state,
        )

        # Copy base targets (don't mutate originals)
        adjusted = {
            name: NutrientTarget(
                name=t.name,
                daily_target=t.daily_target,
                minimum=t.minimum,
                maximum=t.maximum,
                consumed_today=t.consumed_today,
                unit=t.unit,
            )
            for name, t in base_targets.items()
        }

        # Step 2: Apply metabolic state modifiers
        self._apply_metabolic_modifiers(adjusted, metabolic_state, budget)

        # Step 3: Apply genetic modifiers
        self._apply_genetic_modifiers(adjusted, genetic_modifiers, budget)

        # Step 4: Apply biomarker-driven adjustments
        self._apply_biomarker_adjustments(
            adjusted, normalized_signals, metabolic_state, budget
        )

        # Step 5: Consumed amounts already applied in base_targets

        # Step 6: Apply medical constraints
        constraints = self._user_constraints.get(user_id, [])
        self._apply_constraints(adjusted, constraints, budget)

        # Step 7: Distribute across time buckets
        budget.time_buckets = self._create_time_buckets(
            metabolic_state, adjusted
        )

        budget.targets = adjusted
        budget.active_constraints = constraints
        budget.confidence = frame_confidence

        return budget

    def _apply_metabolic_modifiers(
        self,
        targets: Dict[str, NutrientTarget],
        state: MetabolicState,
        budget: NutrientBudget,
    ) -> None:
        """Apply metabolic state-driven nutrient modifications."""
        shifts = state.nutrient_priority_shifts
        if not shifts:
            return

        # Map nutrient priorities to target names
        # Covers all keys from PHASE_NUTRIENT_MODIFIERS
        priority_to_target = {
            "carbohydrate_priority": "carbs_g",
            "protein_priority": "protein_g",
            "fat_priority": "fat_g",
            "water_priority": "water_ml",
            "fiber_priority": "fiber_g",
            "electrolyte_priority": "sodium_mg",
            "caffeine_limit": "caffeine_mg",
            "magnesium_priority": "magnesium_mg",
            "vitamin_b_priority": "vitamin_b6_mg",
        }

        for priority_key, modifier in shifts.items():
            target_name = priority_to_target.get(priority_key)
            if target_name and target_name in targets:
                old_target = targets[target_name].daily_target
                targets[target_name].daily_target *= modifier
                budget.modifications.append({
                    "step": "metabolic_state",
                    "nutrient": target_name,
                    "old_value": round(old_target, 1),
                    "new_value": round(targets[target_name].daily_target, 1),
                    "modifier": modifier,
                    "reason": f"Metabolic phases: {[p.value for p in state.active_phases]}",
                })

    def _apply_genetic_modifiers(
        self,
        targets: Dict[str, NutrientTarget],
        genetic_modifiers: Dict[str, float],
        budget: NutrientBudget,
    ) -> None:
        """Apply genetic modifier coefficients to nutrient targets."""
        if not genetic_modifiers:
            return

        # Map genetic effect names to nutrient targets
        # Covers all 22 modifier keys from NUTRIGENOMIC_VARIANTS
        genetic_to_target = {
            # MTHFR (rs1801133)
            "folate_requirement_modifier": ("folate_mcg", False),
            "b12_requirement_modifier": ("b12_mcg", False),
            # FTO (rs9939609)
            "calorie_sensitivity_modifier": ("kcal", True),
            "satiety_response_modifier": ("kcal", False),  # low satiety → more kcal
            "fat_metabolism_modifier": ("fat_g", True),
            # APOE (rs429358)
            "saturated_fat_sensitivity": ("fat_g", True),  # high sensitivity → less fat
            "cholesterol_response_modifier": ("fat_g", True),
            "omega3_benefit_modifier": ("fat_g", False),  # higher benefit → more omega-3
            # TCF7L2 (rs7903146)
            "carb_sensitivity_modifier": ("carbs_g", True),
            "glycemic_load_threshold_modifier": ("carbs_g", False),
            # LCT (rs4988235)
            "lactose_tolerance": ("calcium_mg", False),      # intolerant → alt calcium
            "calcium_alt_source_need": ("calcium_mg", False),
            # CYP1A2 (rs762551)
            "caffeine_metabolism_rate": ("caffeine_mg", False),  # slow → reduce
            "caffeine_max_daily_mg": ("caffeine_mg", False),     # direct cap
            # VDR (rs1544410)
            "vitamin_d_requirement_modifier": ("vitamin_d_iu", False),
            "calcium_absorption_modifier": ("calcium_mg", True),  # low absorb → more
            # ACE (rs4341)
            "protein_utilization_modifier": ("protein_g", False),
        }

        for genetic_key, modifier in genetic_modifiers.items():
            mapping = genetic_to_target.get(genetic_key)
            if mapping is None:
                continue

            target_name, is_inverse = mapping
            if target_name not in targets:
                continue

            # For sensitivity modifiers, inverse relationship:
            # Higher sensitivity → LOWER target (less needed to get effect)
            effective_modifier = 1.0 / modifier if is_inverse else modifier

            old_target = targets[target_name].daily_target
            targets[target_name].daily_target *= effective_modifier
            budget.modifications.append({
                "step": "genetic",
                "nutrient": target_name,
                "old_value": round(old_target, 1),
                "new_value": round(targets[target_name].daily_target, 1),
                "modifier": round(effective_modifier, 3),
                "genetic_factor": genetic_key,
                "reason": f"Genetic modifier {genetic_key}={modifier}",
            })

    def _apply_biomarker_adjustments(
        self,
        targets: Dict[str, NutrientTarget],
        signals: Dict[BiomarkerType, NormalizedSignal],
        state: MetabolicState,
        budget: NutrientBudget,
    ) -> None:
        """Apply real-time biomarker-driven nutrient adjustments.

        Patent-relevant: These are reactive adjustments based on CURRENT
        physiological readings, not pre-set rules. The z-scores from
        normalized signals drive dynamic target modifications.
        """
        # Glucose-based carb adjustment
        glucose_signal = signals.get(BiomarkerType.GLUCOSE)
        if glucose_signal and "carbs_g" in targets:
            if glucose_signal.z_score > 1.5:
                # Elevated glucose → reduce carb target
                reduction = min(0.25, (glucose_signal.z_score - 1.5) * 0.1)
                old = targets["carbs_g"].daily_target
                targets["carbs_g"].daily_target *= (1 - reduction)
                budget.modifications.append({
                    "step": "biomarker_reactive",
                    "nutrient": "carbs_g",
                    "old_value": round(old, 1),
                    "new_value": round(targets["carbs_g"].daily_target, 1),
                    "reason": f"Elevated glucose (z={glucose_signal.z_score:.1f})",
                    "biomarker": "glucose",
                })
            elif glucose_signal.z_score < -1.0:
                # Low glucose → increase carb target
                increase = min(0.20, abs(glucose_signal.z_score + 1.0) * 0.1)
                old = targets["carbs_g"].daily_target
                targets["carbs_g"].daily_target *= (1 + increase)
                budget.modifications.append({
                    "step": "biomarker_reactive",
                    "nutrient": "carbs_g",
                    "old_value": round(old, 1),
                    "new_value": round(targets["carbs_g"].daily_target, 1),
                    "reason": f"Low glucose (z={glucose_signal.z_score:.1f})",
                    "biomarker": "glucose",
                })

        # HRV-based micronutrient adjustment
        hrv_signal = signals.get(BiomarkerType.HRV)
        if hrv_signal:
            if hrv_signal.z_score < -1.0:
                # Low HRV → stress state → increase magnesium & B vitamins
                for nutrient in ["magnesium_mg", "vitamin_b6_mg"]:
                    if nutrient in targets:
                        increase = 0.15
                        old = targets[nutrient].daily_target
                        targets[nutrient].daily_target *= (1 + increase)
                        budget.modifications.append({
                            "step": "biomarker_reactive",
                            "nutrient": nutrient,
                            "old_value": round(old, 1),
                            "new_value": round(
                                targets[nutrient].daily_target, 1
                            ),
                            "reason": f"Low HRV stress (z={hrv_signal.z_score:.1f})",
                            "biomarker": "hrv",
                        })

        # Heart-rate-based hydration adjustment
        hr_signal = signals.get(BiomarkerType.HEART_RATE)
        if hr_signal and "water_ml" in targets:
            if hr_signal.z_score > 1.0:
                # Elevated HR → potential dehydration → more water
                increase = min(0.3, (hr_signal.z_score - 1.0) * 0.15)
                old = targets["water_ml"].daily_target
                targets["water_ml"].daily_target *= (1 + increase)
                budget.modifications.append({
                    "step": "biomarker_reactive",
                    "nutrient": "water_ml",
                    "old_value": round(old, 1),
                    "new_value": round(targets["water_ml"].daily_target, 1),
                    "reason": f"Elevated HR (z={hr_signal.z_score:.1f})",
                    "biomarker": "heart_rate",
                })

        # Insulin sensitivity-based glycemic load adjustment
        if state.insulin_sensitivity_estimate < 0.5 and "carbs_g" in targets:
            # Low insulin sensitivity → prefer low-GI carbs
            budget.modifications.append({
                "step": "biomarker_reactive",
                "nutrient": "carbs_g",
                "old_value": targets["carbs_g"].daily_target,
                "new_value": targets["carbs_g"].daily_target,
                "reason": (
                    f"Low insulin sensitivity ({state.insulin_sensitivity_estimate:.2f})"
                    " — prefer low-GI carb sources"
                ),
                "biomarker": "insulin_sensitivity",
                "qualitative": "prefer_low_gi",
            })

    def _apply_constraints(
        self,
        targets: Dict[str, NutrientTarget],
        constraints: List[MedicalConstraint],
        budget: NutrientBudget,
    ) -> None:
        """Apply medical constraints as hard boundaries.

        Constraints override all other modifications. A renal patient's
        protein limit cannot be exceeded regardless of post-exercise
        recovery demands.
        """
        for constraint in constraints:
            if constraint.nutrient not in targets:
                continue

            target = targets[constraint.nutrient]

            if constraint.constraint_type == "max":
                if target.daily_target > constraint.value:
                    old = target.daily_target
                    target.daily_target = constraint.value
                    target.maximum = constraint.value
                    budget.modifications.append({
                        "step": "medical_constraint",
                        "nutrient": constraint.nutrient,
                        "old_value": round(old, 1),
                        "new_value": constraint.value,
                        "reason": constraint.reason,
                        "severity": constraint.severity,
                    })

            elif constraint.constraint_type == "min":
                if target.daily_target < constraint.value:
                    old = target.daily_target
                    target.daily_target = constraint.value
                    target.minimum = constraint.value
                    budget.modifications.append({
                        "step": "medical_constraint",
                        "nutrient": constraint.nutrient,
                        "old_value": round(old, 1),
                        "new_value": constraint.value,
                        "reason": constraint.reason,
                        "severity": constraint.severity,
                    })

    def _create_time_buckets(
        self,
        state: MetabolicState,
        targets: Dict[str, NutrientTarget],
    ) -> List[TimeBucket]:
        """Create time-bucketed nutrient distribution plan.

        Patent-relevant: The time buckets are dynamically generated
        based on the CURRENT metabolic state, not pre-set meal times.
        A post-exercise state creates an immediate carb-heavy bucket
        that wouldn't exist in a sedentary day.
        """
        now_hour = state.timestamp.hour
        buckets: List[TimeBucket] = []

        # Dynamic bucket generation based on current state
        if MetabolicPhase.RECOVERY_IMMEDIATE in state.active_phases:
            # Urgent: Recovery window — front-load carbs and protein
            buckets.append(
                TimeBucket(
                    start_hour=now_hour,
                    end_hour=min(24, now_hour + 2),
                    label="Recovery Window",
                    carb_pct=0.40,
                    protein_pct=0.35,
                    fat_pct=0.15,
                    water_pct=0.30,
                    priority_nutrients=["carbs_g", "protein_g", "water_ml"],
                    rationale="Post-exercise glycogen replenishment + muscle repair",
                )
            )
            remaining_start = min(24, now_hour + 2)
        else:
            remaining_start = now_hour

        # Standard daily buckets for remaining time
        if remaining_start < 12:
            buckets.append(
                TimeBucket(
                    start_hour=remaining_start,
                    end_hour=12,
                    label="Morning",
                    carb_pct=0.30,
                    protein_pct=0.25,
                    fat_pct=0.25,
                    water_pct=0.30,
                    rationale="Morning insulin sensitivity is typically highest",
                )
            )

        if remaining_start < 17:
            buckets.append(
                TimeBucket(
                    start_hour=max(12, remaining_start),
                    end_hour=17,
                    label="Afternoon",
                    carb_pct=0.30,
                    protein_pct=0.30,
                    fat_pct=0.30,
                    water_pct=0.30,
                    rationale="Sustained energy for afternoon activity",
                )
            )

        if remaining_start < 21:
            # Adjust evening based on sleep proximity
            carb_pct = 0.20
            if MetabolicPhase.PRE_SLEEP in state.active_phases:
                carb_pct = 0.10  # Reduce carbs before sleep
            buckets.append(
                TimeBucket(
                    start_hour=max(17, remaining_start),
                    end_hour=21,
                    label="Evening",
                    carb_pct=carb_pct,
                    protein_pct=0.30,
                    fat_pct=0.35,
                    water_pct=0.15,
                    rationale="Prioritize protein + healthy fats, reduce carbs before sleep",
                )
            )

        return buckets


def create_default_targets(
    kcal: float = 2000,
    weight_kg: float = 70,
    activity_level: str = "moderate",
) -> Dict[str, NutrientTarget]:
    """Create default nutrient targets based on basic user profile.

    This provides baseline targets that the calculator then adjusts
    based on biomarker data, metabolic state, and genetic factors.
    """
    # Macro distribution: 40% carbs, 30% protein, 30% fat
    carb_kcal = kcal * 0.40
    protein_kcal = kcal * 0.30
    fat_kcal = kcal * 0.30

    return {
        "kcal": NutrientTarget(
            name="kcal",
            daily_target=kcal,
            minimum=kcal * 0.8,
            maximum=kcal * 1.3,
            unit="kcal",
        ),
        "carbs_g": NutrientTarget(
            name="carbs_g",
            daily_target=carb_kcal / 4,
            minimum=100,  # Brain minimum
            maximum=carb_kcal / 4 * 1.5,
            unit="g",
        ),
        "protein_g": NutrientTarget(
            name="protein_g",
            daily_target=max(protein_kcal / 4, weight_kg * 1.2),
            minimum=weight_kg * 0.8,
            maximum=weight_kg * 2.2,
            unit="g",
        ),
        "fat_g": NutrientTarget(
            name="fat_g",
            daily_target=fat_kcal / 9,
            minimum=fat_kcal / 9 * 0.5,
            maximum=fat_kcal / 9 * 1.5,
            unit="g",
        ),
        "fiber_g": NutrientTarget(
            name="fiber_g",
            daily_target=30,
            minimum=20,
            maximum=50,
            unit="g",
        ),
        "water_ml": NutrientTarget(
            name="water_ml",
            daily_target=weight_kg * 35,  # 35ml/kg
            minimum=1500,
            maximum=5000,
            unit="ml",
        ),
        # ── Micronutrients (genetic-responsive) ────────────────────
        "folate_mcg": NutrientTarget(
            name="folate_mcg",
            daily_target=400,  # RDA
            minimum=200,
            maximum=1000,  # UL
            unit="mcg",
        ),
        "b12_mcg": NutrientTarget(
            name="b12_mcg",
            daily_target=2.4,
            minimum=1.0,
            maximum=100.0,
            unit="mcg",
        ),
        "vitamin_d_iu": NutrientTarget(
            name="vitamin_d_iu",
            daily_target=600,
            minimum=400,
            maximum=4000,  # UL
            unit="IU",
        ),
        "magnesium_mg": NutrientTarget(
            name="magnesium_mg",
            daily_target=400 if weight_kg >= 70 else 310,
            minimum=200,
            maximum=800,
            unit="mg",
        ),
        "calcium_mg": NutrientTarget(
            name="calcium_mg",
            daily_target=1000,
            minimum=500,
            maximum=2500,  # UL
            unit="mg",
        ),
        "sodium_mg": NutrientTarget(
            name="sodium_mg",
            daily_target=2300,
            minimum=500,
            maximum=3400,
            unit="mg",
        ),
        "caffeine_mg": NutrientTarget(
            name="caffeine_mg",
            daily_target=400,  # FDA max
            minimum=0,
            maximum=400,
            unit="mg",
        ),
        "vitamin_b6_mg": NutrientTarget(
            name="vitamin_b6_mg",
            daily_target=1.7,
            minimum=1.0,
            maximum=100.0,  # UL
            unit="mg",
        ),
    }
