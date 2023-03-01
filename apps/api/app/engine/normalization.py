"""
Physiological-Aware Normalization Layer.

Core module: Transforms raw biomarker values into physiologically
meaningful normalized signals by accounting for:

1. Personal Baseline Learning — adapts to individual "normal" ranges
   rather than population averages
2. Circadian Rhythm Correction — time-of-day compensation for signals
   with known diurnal patterns (glucose, cortisol, heart rate)
3. Context-Dependent Scaling — same raw value has different meaning
   depending on metabolic state (fasting vs postprandial, rest vs exercise)
4. Genetic Modifier Weighting — SNP-based metabolic efficiency coefficients
   that scale nutrient utilization rates
5. Genetic-Baseline Normalization — computes genotype-adjusted reference
   ranges so z-scores reflect deviation from the user's GENETIC normal,
   not population average

This is NOT standard Z-score normalization. The biological context
awareness combined with genetic baseline computation is the inventive step.

Example: A TCF7L2 T/T carrier (rs7903146) has a genetically higher fasting
glucose baseline (~100-110 mg/dL vs population ~80-100 mg/dL). Their
glucose reading of 108 mg/dL produces:
  - Population z-score: (108 − 100) / 15 = +0.53  → "slightly elevated"
  - Genetic-baseline z-score: (108 − 106) / 12 = +0.17  → "normal for genotype"

This prevents false-positive alerts for genetically normal variants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..biomarkers.base import BiomarkerType


# Circadian rhythm profiles for key biomarkers
# Values represent typical deviation from 24h personal mean at each hour
# Based on published chronobiology data
CIRCADIAN_PROFILES = {
    BiomarkerType.GLUCOSE: {
        0: -0.05,  1: -0.06,  2: -0.07,  3: -0.08,
        4: -0.04,  5: 0.02,   6: 0.05,   7: 0.08,
        8: 0.06,   9: 0.03,  10: 0.01,  11: -0.01,
        12: 0.02, 13: 0.04,  14: 0.02,  15: 0.00,
        16: -0.01, 17: 0.01, 18: 0.03,  19: 0.04,
        20: 0.02, 21: 0.00,  22: -0.02, 23: -0.04,
    },
    BiomarkerType.HEART_RATE: {
        0: -0.15,  1: -0.18,  2: -0.20,  3: -0.18,
        4: -0.15,  5: -0.08,  6: -0.02,  7: 0.05,
        8: 0.08,   9: 0.10,  10: 0.12,  11: 0.10,
        12: 0.08, 13: 0.06,  14: 0.05,  15: 0.08,
        16: 0.10, 17: 0.12,  18: 0.10,  19: 0.08,
        20: 0.05, 21: 0.00,  22: -0.05, 23: -0.10,
    },
    BiomarkerType.HRV: {
        0: 0.15,   1: 0.18,   2: 0.20,   3: 0.18,
        4: 0.12,   5: 0.05,   6: -0.02,  7: -0.08,
        8: -0.12,  9: -0.10, 10: -0.08, 11: -0.06,
        12: -0.04, 13: -0.02, 14: -0.05, 15: -0.08,
        16: -0.10, 17: -0.08, 18: -0.05, 19: -0.02,
        20: 0.02,  21: 0.05,  22: 0.08,  23: 0.12,
    },
}

# Population reference ranges (used before personal baseline is learned)
POPULATION_RANGES = {
    BiomarkerType.GLUCOSE: {"mean": 100.0, "std": 15.0, "unit": "mg/dL"},
    BiomarkerType.HEART_RATE: {"mean": 72.0, "std": 12.0, "unit": "bpm"},
    BiomarkerType.HRV: {"mean": 45.0, "std": 20.0, "unit": "ms"},
    BiomarkerType.STEPS: {"mean": 8000.0, "std": 3000.0, "unit": "steps"},
    BiomarkerType.SLEEP: {"mean": 7.5, "std": 1.0, "unit": "hours"},
}


# ═══════════════════════════════════════════════════════════════════════
# Genetic Baseline Profile
# ═══════════════════════════════════════════════════════════════════════
#
# Instead of normalizing against population means, this computes a
# genotype-adjusted reference range for each biomarker.
#
# The adjustment formula:
#   μ_genetic(b) = μ_population(b) × Π_i(modifier_i)
#   σ_genetic(b) = σ_population(b) × f(n_variants)
#
# Where:
#   modifier_i = genetic modifier for SNP i that affects biomarker b
#   f(n) = 1.0 - 0.05 × n  (tighter range with more genetic data)
#
# ═══════════════════════════════════════════════════════════════════════

# Maps genetic modifier keys → which biomarker's baseline they shift
GENETIC_BASELINE_EFFECTS: Dict[str, Dict[BiomarkerType, Tuple[str, float]]] = {
    # SNP effect name → { biomarker: (direction, magnitude_pct) }
    "carb_sensitivity_modifier": {
        BiomarkerType.GLUCOSE: ("mean_shift_pct", 5.0),
        # Higher carb sensitivity → lower baseline glucose (better clearance)
        # modifier > 1.0: shift mean DOWN by magnitude_pct per 0.1 above 1.0
    },
    "insulin_response_modifier": {
        BiomarkerType.GLUCOSE: ("mean_shift_pct", 8.0),
        # Lower insulin response → higher baseline glucose
        # modifier < 1.0: shift mean UP by magnitude_pct per 0.1 below 1.0
    },
    "calorie_sensitivity_modifier": {
        BiomarkerType.HEART_RATE: ("mean_shift_pct", 2.0),
    },
    "fat_metabolism_modifier": {
        BiomarkerType.HEART_RATE: ("mean_shift_pct", 1.5),
    },
}


@dataclass
class GeneticBaselineAdjustment:
    """Record of how a single genetic modifier shifted a biomarker's baseline.

    Attributes:
        modifier_name: Which genetic modifier was applied.
        modifier_value: The SNP-derived modifier value (e.g., 0.8).
        biomarker_type: Which biomarker was adjusted.
        mean_shift: How much the baseline mean was shifted (absolute).
        direction: "up" or "down".
    """

    modifier_name: str
    modifier_value: float
    biomarker_type: str
    mean_shift: float
    direction: str


@dataclass
class GeneticBaselineProfile:
    """Genotype-adjusted physiological reference ranges.

    Instead of normalizing against population means, this provides
    PERSONALIZED reference ranges computed from the user's SNP profile.

    Example for a user with TCF7L2 T/T + FTO A/A:
      Population glucose: μ=100 mg/dL, σ=15 mg/dL
      Genetic glucose:    μ=106 mg/dL, σ=12 mg/dL
      → Their "normal" fasting glucose is 6% higher than average
      → Tighter confidence interval because we have genetic data

    Attributes:
        user_id: User identifier.
        adjusted_ranges: Genotype-adjusted {biomarker: (mean, std)}.
        variant_count: Number of SNP variants used.
        adjustments: Audit trail of each adjustment applied.
        confidence: How reliable this profile is (more SNPs = higher).
    """

    user_id: str
    adjusted_ranges: Dict[BiomarkerType, Tuple[float, float]] = field(
        default_factory=dict
    )
    variant_count: int = 0
    adjustments: List[GeneticBaselineAdjustment] = field(default_factory=list)
    confidence: float = 0.0

    def get_range(self, biomarker_type: BiomarkerType) -> Tuple[float, float]:
        """Get the adjusted (mean, std) for a biomarker type.

        Falls back to population range if no genetic adjustment exists.
        """
        if biomarker_type in self.adjusted_ranges:
            return self.adjusted_ranges[biomarker_type]
        pop = POPULATION_RANGES.get(biomarker_type, {"mean": 0, "std": 1})
        return (pop["mean"], pop["std"])

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response."""
        return {
            "user_id": self.user_id,
            "variant_count": self.variant_count,
            "confidence": round(self.confidence, 3),
            "adjusted_ranges": {
                bt.value: {
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                    "population_mean": POPULATION_RANGES.get(
                        bt, {"mean": 0}
                    )["mean"],
                    "population_std": POPULATION_RANGES.get(
                        bt, {"std": 1}
                    )["std"],
                    "shift_pct": round(
                        (mean - POPULATION_RANGES.get(bt, {"mean": mean})["mean"])
                        / max(1, POPULATION_RANGES.get(bt, {"mean": 1})["mean"])
                        * 100,
                        1,
                    ),
                }
                for bt, (mean, std) in self.adjusted_ranges.items()
            },
            "adjustments": [
                {
                    "modifier": a.modifier_name,
                    "value": a.modifier_value,
                    "biomarker": a.biomarker_type,
                    "shift": round(a.mean_shift, 2),
                    "direction": a.direction,
                }
                for a in self.adjustments
            ],
        }


class GeneticBaselineCalculator:
    """Computes genotype-adjusted reference ranges for biomarkers.

    This transforms population-level normal ranges into INDIVIDUAL
    normal ranges by factoring in SNP-derived metabolic modifiers.

    The key insight: a user with genetic variants that affect glucose
    metabolism should not be judged against population glucose norms.
    Their "normal" is genetically different.

    Algorithm:
        For each biomarker b:
          1. Start with population range: μ_pop, σ_pop
          2. For each genetic modifier m that affects b:
             - Compute direction: m > 1.0 → one direction, m < 1.0 → other
             - Compute magnitude: |m - 1.0| × effect_magnitude_pct
             - Apply: μ_adjusted += μ_pop × shift_pct / 100
          3. Adjust variance: σ_adjusted = σ_pop × (1 - 0.05 × n_variants)
          4. Store as user's genetic baseline
    """

    @staticmethod
    def compute(
        user_id: str,
        genetic_modifiers: Dict[str, float],
    ) -> GeneticBaselineProfile:
        """Compute genetic baseline profile from SNP modifiers.

        Args:
            user_id: User identifier.
            genetic_modifiers: Dict of modifier_name → value
                (e.g., {"carb_sensitivity_modifier": 1.3, ...})

        Returns:
            GeneticBaselineProfile with adjusted reference ranges.
        """
        profile = GeneticBaselineProfile(user_id=user_id)
        if not genetic_modifiers:
            # No genetics → use population ranges as-is
            for bt, pop in POPULATION_RANGES.items():
                profile.adjusted_ranges[bt] = (pop["mean"], pop["std"])
            return profile

        # Track adjustments per biomarker
        biomarker_shifts: Dict[BiomarkerType, List[float]] = {}
        adjustments: List[GeneticBaselineAdjustment] = []

        for modifier_name, modifier_value in genetic_modifiers.items():
            effects = GENETIC_BASELINE_EFFECTS.get(modifier_name, {})
            for bt, (effect_type, magnitude_pct) in effects.items():
                if effect_type != "mean_shift_pct":
                    continue

                # Compute shift direction and amount
                # For "response" modifiers (insulin_response):
                #   value < 1.0 = weaker response → higher baseline
                #   value > 1.0 = stronger response → lower baseline
                # For "sensitivity" modifiers (carb_sensitivity):
                #   value > 1.0 = more sensitive → better clearance → lower baseline
                #   value < 1.0 = less sensitive → higher baseline
                deviation = modifier_value - 1.0

                if "response" in modifier_name:
                    # Lower response → higher baseline (inverse)
                    shift_pct = -deviation * magnitude_pct
                else:
                    # Higher sensitivity → lower baseline (inverse)
                    shift_pct = -deviation * magnitude_pct

                if bt not in biomarker_shifts:
                    biomarker_shifts[bt] = []
                biomarker_shifts[bt].append(shift_pct)

                pop_mean = POPULATION_RANGES.get(bt, {"mean": 100})["mean"]
                abs_shift = pop_mean * shift_pct / 100.0
                direction = "up" if shift_pct > 0 else "down"
                adjustments.append(
                    GeneticBaselineAdjustment(
                        modifier_name=modifier_name,
                        modifier_value=modifier_value,
                        biomarker_type=bt.value,
                        mean_shift=abs_shift,
                        direction=direction,
                    )
                )

        # Apply accumulated shifts to each biomarker
        n_variants = len(genetic_modifiers)
        for bt, pop in POPULATION_RANGES.items():
            pop_mean = pop["mean"]
            pop_std = pop["std"]

            shifts = biomarker_shifts.get(bt, [])
            total_shift_pct = sum(shifts)
            adjusted_mean = pop_mean * (1 + total_shift_pct / 100.0)

            # Tighter std with more genetic data (we know more about this person)
            # Each variant reduces uncertainty by ~5%, capped at 40% reduction
            std_reduction = min(0.4, 0.05 * n_variants)
            adjusted_std = pop_std * (1 - std_reduction)

            profile.adjusted_ranges[bt] = (
                round(adjusted_mean, 2),
                round(adjusted_std, 2),
            )

        profile.variant_count = n_variants
        profile.adjustments = adjustments
        # Confidence: sigmoid of variant count, peaks near 8 variants
        profile.confidence = round(
            1.0 / (1.0 + math.exp(-0.5 * (n_variants - 4))), 3
        )

        return profile


@dataclass
class PersonalBaseline:
    """Learned personal baseline for a biomarker.

    Updated incrementally with each new reading using an exponentially
    weighted moving average (EWMA). The decay factor determines how
    quickly the baseline adapts to changes.

    Patent-relevant: The dual-timescale baseline (short-term for acute
    detection, long-term for trend tracking) enables detection of both
    immediate anomalies and gradual health changes.
    """

    biomarker_type: BiomarkerType
    short_term_mean: float = 0.0   # EWMA with α=0.1 (fast adaptation)
    long_term_mean: float = 0.0    # EWMA with α=0.01 (slow, stable)
    variance: float = 0.0          # Running variance estimate
    sample_count: int = 0
    last_updated: Optional[datetime] = None

    # Hours of day → mean value (learned circadian pattern)
    hourly_means: Dict[int, float] = field(default_factory=dict)
    hourly_counts: Dict[int, int] = field(default_factory=dict)

    def update(self, value: float, timestamp: datetime) -> None:
        """Update baseline with a new observation.

        Uses dual-timescale EWMA:
        - Short-term (α=0.1): captures recent trends, 20-reading window
        - Long-term (α=0.01): stable personal average, 200+ readings
        """
        self.sample_count += 1

        if self.sample_count == 1:
            self.short_term_mean = value
            self.long_term_mean = value
            self.variance = 0.0
        else:
            # Short-term EWMA
            alpha_short = 0.1
            self.short_term_mean = (
                alpha_short * value + (1 - alpha_short) * self.short_term_mean
            )

            # Long-term EWMA
            alpha_long = 0.01
            self.long_term_mean = (
                alpha_long * value + (1 - alpha_long) * self.long_term_mean
            )

            # Running variance (Welford's method adapted for EWMA)
            delta = value - self.long_term_mean
            self.variance = (
                (1 - alpha_long) * (self.variance + alpha_long * delta ** 2)
            )

        # Update hourly profile
        hour = timestamp.hour
        if hour not in self.hourly_means:
            self.hourly_means[hour] = value
            self.hourly_counts[hour] = 1
        else:
            n = self.hourly_counts[hour]
            self.hourly_means[hour] = (
                self.hourly_means[hour] * n + value
            ) / (n + 1)
            self.hourly_counts[hour] = n + 1

        self.last_updated = timestamp

    @property
    def std(self) -> float:
        """Standard deviation estimate."""
        return math.sqrt(max(0, self.variance))

    @property
    def is_mature(self) -> bool:
        """Whether enough data has been collected for reliable baseline."""
        return self.sample_count >= 50


@dataclass
class NormalizedSignal:
    """Result of physiological normalization.

    Attributes:
        biomarker_type: What was measured.
        raw_value: Original measurement.
        normalized_value: After all normalization steps.
        z_score: Standard deviations from personal baseline.
        circadian_adjusted: Value after removing circadian component.
        genetic_modified: Value after applying genetic modifiers.
        context: Description of the normalization context applied.
        anomaly_score: 0-1, how unusual this reading is for this person.
    """

    biomarker_type: BiomarkerType
    raw_value: float
    normalized_value: float
    z_score: float
    circadian_adjusted: float
    genetic_modified: float
    context: str
    anomaly_score: float


class PhysiologicalNormalizer:
    """Normalizes biomarker values with biological context awareness.

    Patent-core algorithm:

    normalize(raw_value, biomarker, timestamp, context) →
      1. Circadian correction:
         adjusted = raw - baseline.hourly_mean[hour]
         (removes expected time-of-day variation)

      2. Personal Z-score:
         z = (adjusted - baseline.long_term_mean) / baseline.std
         (standardizes relative to THIS person's normal)

      3. Context scaling:
         if metabolic_state == "postprandial":
           z_glucose *= 0.7  # glucose naturally rises after meals
         if metabolic_state == "exercising":
           z_heart_rate *= 0.5  # elevated HR is expected

      4. Genetic modifier:
         effective_z = z × genetic_modifier[biomarker]
         (e.g., TCF7L2 T/T carrier needs stricter glucose control)

      5. Anomaly detection:
         anomaly = 1 - exp(-0.5 × z²)
         (probability of being an outlier for this individual)

    Result: A normalized value that reflects clinical significance
    rather than raw magnitude.
    """

    def __init__(self):
        self._baselines: Dict[str, Dict[BiomarkerType, PersonalBaseline]] = {}
        self._genetic_modifiers: Dict[str, Dict[str, float]] = {}
        self._genetic_baselines: Dict[str, GeneticBaselineProfile] = {}

    def set_genetic_modifiers(
        self, user_id: str, modifiers: Dict[str, float]
    ) -> None:
        """Set genetic modifier coefficients for a user.

        Also recomputes the genetic baseline profile for this user,
        which adjusts the reference ranges used in normalization.
        """
        self._genetic_modifiers[user_id] = modifiers
        # Recompute genetic baseline whenever modifiers change
        self._genetic_baselines[user_id] = (
            GeneticBaselineCalculator.compute(user_id, modifiers)
        )

    def get_genetic_baseline(self, user_id: str) -> GeneticBaselineProfile:
        """Get the user's genetic baseline profile (or compute default)."""
        if user_id not in self._genetic_baselines:
            modifiers = self._genetic_modifiers.get(user_id, {})
            self._genetic_baselines[user_id] = (
                GeneticBaselineCalculator.compute(user_id, modifiers)
            )
        return self._genetic_baselines[user_id]

    def get_or_create_baseline(
        self, user_id: str, biomarker_type: BiomarkerType
    ) -> PersonalBaseline:
        """Get existing baseline or create from population defaults."""
        if user_id not in self._baselines:
            self._baselines[user_id] = {}

        if biomarker_type not in self._baselines[user_id]:
            pop = POPULATION_RANGES.get(biomarker_type, {"mean": 0, "std": 1})
            baseline = PersonalBaseline(
                biomarker_type=biomarker_type,
                short_term_mean=pop["mean"],
                long_term_mean=pop["mean"],
                variance=pop["std"] ** 2,
            )
            self._baselines[user_id][biomarker_type] = baseline

        return self._baselines[user_id][biomarker_type]

    def normalize(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        raw_value: float,
        timestamp: datetime,
        metabolic_context: str = "unknown",
        update_baseline: bool = True,
    ) -> NormalizedSignal:
        """Normalize a raw biomarker reading with physiological awareness.

        This is the main normalization entry point.

        Args:
            user_id: User identifier.
            biomarker_type: What is being measured.
            raw_value: The raw measurement value.
            timestamp: When the measurement was taken.
            metabolic_context: Current metabolic state (fasting, postprandial,
                exercising, sleeping, etc.)
            update_baseline: Whether to update the personal baseline.

        Returns:
            NormalizedSignal with all normalization steps applied.
        """
        baseline = self.get_or_create_baseline(user_id, biomarker_type)

        # Step 1: Circadian correction
        circadian_adjusted = self._circadian_correct(
            raw_value, biomarker_type, timestamp, baseline
        )

        # Step 2: Personal Z-score — use GENETIC baseline when available
        genetic_baseline = self.get_genetic_baseline(user_id)
        genetic_mean, genetic_std = genetic_baseline.get_range(biomarker_type)

        if baseline.is_mature:
            # Prefer personal measured baseline when mature (50+ samples)
            ref_mean = baseline.long_term_mean
            ref_std = baseline.std if baseline.std > 0 else genetic_std
        elif genetic_baseline.confidence > 0.3:
            # Use genetic baseline when we have SNP data but not enough
            # personal measurement history yet
            ref_mean = genetic_mean
            ref_std = genetic_std
        else:
            # Fall back to population range (no genetics, no history)
            pop = POPULATION_RANGES.get(
                biomarker_type, {"mean": raw_value, "std": 1.0}
            )
            ref_mean = pop["mean"]
            ref_std = pop["std"]

        z_score = (circadian_adjusted - ref_mean) / max(0.001, ref_std)

        # Step 3: Context-dependent scaling
        context_factor = self._get_context_factor(
            biomarker_type, metabolic_context
        )
        context_z = z_score * context_factor

        # Step 4: Genetic modifier
        genetic_factor = self._get_genetic_factor(user_id, biomarker_type)
        genetic_z = context_z * genetic_factor

        # Step 5: Anomaly score
        anomaly_score = 1.0 - math.exp(-0.5 * genetic_z ** 2)

        # Update baseline with raw (unmodified) value
        if update_baseline:
            baseline.update(raw_value, timestamp)

        return NormalizedSignal(
            biomarker_type=biomarker_type,
            raw_value=raw_value,
            normalized_value=genetic_z,
            z_score=z_score,
            circadian_adjusted=circadian_adjusted,
            genetic_modified=genetic_z,
            context=metabolic_context,
            anomaly_score=min(1.0, anomaly_score),
        )

    def normalize_frame_signals(
        self,
        user_id: str,
        signals: Dict[BiomarkerType, float],
        timestamp: datetime,
        metabolic_context: str = "unknown",
    ) -> Dict[BiomarkerType, NormalizedSignal]:
        """Normalize all signals in a synchronized frame at once."""
        results: Dict[BiomarkerType, NormalizedSignal] = {}
        for bt, value in signals.items():
            results[bt] = self.normalize(
                user_id, bt, value, timestamp, metabolic_context
            )
        return results

    def _circadian_correct(
        self,
        value: float,
        biomarker_type: BiomarkerType,
        timestamp: datetime,
        baseline: PersonalBaseline,
    ) -> float:
        """Remove circadian rhythm component from a reading.

        Patent-relevant: Uses personal circadian profile if available
        (learned from individual's data) or falls back to population
        circadian profile. This means the same glucose reading of 120
        at 7am (expected morning rise) is treated differently than 120
        at 3am (unexpected).
        """
        # Prefer personal hourly profile if mature
        if baseline.is_mature and timestamp.hour in baseline.hourly_means:
            hourly_mean = baseline.hourly_means[timestamp.hour]
            circadian_offset = hourly_mean - baseline.long_term_mean
        else:
            # Fall back to population circadian profile
            profile = CIRCADIAN_PROFILES.get(biomarker_type, {})
            pct_offset = profile.get(timestamp.hour, 0.0)
            ref_mean = (
                baseline.long_term_mean
                if baseline.is_mature
                else POPULATION_RANGES.get(
                    biomarker_type, {"mean": value}
                )["mean"]
            )
            circadian_offset = ref_mean * pct_offset

        return value - circadian_offset

    def _get_context_factor(
        self,
        biomarker_type: BiomarkerType,
        context: str,
    ) -> float:
        """Get context-dependent scaling factor.

        Patent-relevant: Same reading, different meaning based on context.
        A heart rate of 150 during exercise is normal; at rest it's alarming.
        A glucose of 140 after a meal is expected; fasting it's concerning.
        """
        context_factors = {
            BiomarkerType.GLUCOSE: {
                "fasting": 1.0,
                "postprandial": 0.7,    # Expected elevation
                "exercising": 0.8,       # Exercise mobilizes glucose
                "sleeping": 1.2,         # Unexpected if elevated
                "unknown": 0.9,
            },
            BiomarkerType.HEART_RATE: {
                "resting": 1.0,
                "exercising": 0.4,       # Very expected to be high
                "postprandial": 0.8,
                "sleeping": 1.3,         # Concerning if elevated
                "stressed": 0.6,
                "unknown": 0.8,
            },
            BiomarkerType.HRV: {
                "resting": 1.0,
                "exercising": 0.5,       # Expected to drop
                "sleeping": 1.2,         # Important recovery metric
                "stressed": 0.7,
                "unknown": 0.8,
            },
        }

        factors = context_factors.get(biomarker_type, {})
        return factors.get(context, 1.0)

    def _get_genetic_factor(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
    ) -> float:
        """Get genetic modifier for a biomarker.

        Maps biomarker types to relevant genetic modifiers.
        E.g., for glucose, uses the carb_sensitivity_modifier from
        TCF7L2 genotype data.
        """
        modifiers = self._genetic_modifiers.get(user_id, {})
        if not modifiers:
            return 1.0

        # Map biomarker types to relevant genetic modifier keys
        modifier_keys = {
            BiomarkerType.GLUCOSE: [
                "carb_sensitivity_modifier",
                "insulin_response_modifier",
            ],
            BiomarkerType.STEPS: [
                "power_exercise_response",
                "endurance_exercise_response",
            ],
            BiomarkerType.SLEEP: [],  # Sleep is less genetically modified
            BiomarkerType.HEART_RATE: [],
        }

        keys = modifier_keys.get(biomarker_type, [])
        if not keys:
            return 1.0

        # Average of applicable genetic modifiers
        applicable = [modifiers[k] for k in keys if k in modifiers]
        if not applicable:
            return 1.0

        return sum(applicable) / len(applicable)

# TODO: optimize this section
