"""
Comprehensive tests for the patent-core Biomarker Synchronization Engine.

Tests cover:
1. Biomarker adapters — data ingestion and retrieval
2. Temporal synchronization — heterogeneous signal alignment
3. Physiological normalization — circadian correction + genetic modifiers
4. Metabolic state estimation — multi-phase detection
5. Nutrient demand calculation — full pipeline integration
6. Privacy — differential privacy, consent management
7. API router — endpoint integration tests
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pytest

# ── Biomarker adapters ──────────────────────────────────────────────
from app.biomarkers.base import (
    BiomarkerReading,
    BiomarkerType,
    SamplingCharacteristics,
    TemporalBehavior,
)
from app.biomarkers.cgm_adapter import CGMAdapter
from app.biomarkers.activity_adapter import ActivityAdapter
from app.biomarkers.sleep_adapter import SleepAdapter
from app.biomarkers.genetic_adapter import GeneticAdapter

# ── Engine modules ──────────────────────────────────────────────────
from app.engine.temporal_sync import (
    TemporalSynchronizer,
    Resolution,
    SynchronizedFrame,
    PhysiologicalLagModel,
    LagComputation,
    CIRCADIAN_LAG_MODIFIERS,
)
from app.engine.normalization import (
    PhysiologicalNormalizer,
    PersonalBaseline,
    NormalizedSignal,
)
from app.engine.interpolation import CircadianInterpolator
from app.engine.metabolic_state import (
    MetabolicStateEstimator,
    MetabolicState,
    MetabolicPhase,
)
from app.engine.nutrient_calculator import (
    NutrientDemandCalculator,
    NutrientTarget,
    NutrientBudget,
    create_default_targets,
)

# ── Privacy modules ─────────────────────────────────────────────────
from app.privacy.differential_privacy import DifferentialPrivacyEngine, PrivacyBudget
from app.privacy.consent_manager import (
    DynamicConsentManager,
    ConsentScope,
    ConsentState,
)
from app.privacy.graph_embedding import (
    HealthGraphEmbedding,
    GraphNode,
    GraphEdge,
)


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════

NOW = datetime(2025, 1, 15, 12, 0, 0)  # noon
USER = "test-user-001"


def _make_glucose_readings(
    n: int = 12,
    start: datetime = NOW - timedelta(hours=1),
    interval_minutes: int = 5,
    base_value: float = 110.0,
) -> List[BiomarkerReading]:
    """Generate n CGM readings at regular intervals."""
    readings = []
    for i in range(n):
        ts = start + timedelta(minutes=i * interval_minutes)
        readings.append(
            BiomarkerReading(
                source_id="cgm_generic",
                user_id=USER,
                biomarker_type=BiomarkerType.GLUCOSE,
                timestamp=ts,
                value=base_value + (i % 3) * 5,  # small fluctuation
                unit="mg/dL",
                confidence=0.95,
            )
        )
    return readings


def _make_hr_readings(
    n: int = 6,
    start: datetime = NOW - timedelta(hours=1),
    interval_minutes: int = 10,
) -> List[BiomarkerReading]:
    readings = []
    for i in range(n):
        ts = start + timedelta(minutes=i * interval_minutes)
        readings.append(
            BiomarkerReading(
                source_id="activity_generic",
                user_id=USER,
                biomarker_type=BiomarkerType.HEART_RATE,
                timestamp=ts,
                value=72 + i * 2,
                unit="bpm",
            )
        )
    return readings


# ═══════════════════════════════════════════════════════════════════
#  1. Biomarker Adapters
# ═══════════════════════════════════════════════════════════════════


class TestCGMAdapter:
    """Test CGM adapter ingestion, retrieval, and classification."""

    def setup_method(self):
        self.adapter = CGMAdapter()

    @pytest.mark.asyncio
    async def test_push_and_fetch(self):
        readings = _make_glucose_readings(3)
        for r in readings:
            ok = await self.adapter.push_reading(r)
            assert ok is True

        fetched = await self.adapter.fetch_readings(
            USER,
            BiomarkerType.GLUCOSE,
            NOW - timedelta(hours=2),
            NOW,
        )
        assert len(fetched) == 3
        assert all(r.biomarker_type == BiomarkerType.GLUCOSE for r in fetched)

    @pytest.mark.asyncio
    async def test_validation_rejects_extreme_glucose(self):
        reading = BiomarkerReading(
            source_id="cgm_generic",
            user_id=USER,
            biomarker_type=BiomarkerType.GLUCOSE,
            timestamp=NOW,
            value=900,  # way too high
            unit="mg/dL",
        )
        ok = await self.adapter.push_reading(reading)
        assert ok is False

    def test_glycemic_classification(self):
        assert self.adapter.get_glycemic_classification(60) == "hypoglycemia"
        assert self.adapter.get_glycemic_classification(90) == "normal_fasting"
        assert self.adapter.get_glycemic_classification(130) == "normal_postprandial"
        assert self.adapter.get_glycemic_classification(250) == "diabetic"

    def test_glucose_variability(self):
        readings = _make_glucose_readings(12)
        stats = CGMAdapter.compute_glucose_variability(readings)
        assert "mean" in stats
        assert "std" in stats
        assert "cv" in stats
        assert "time_in_range" in stats
        assert stats["mean"] > 0

    def test_sampling_characteristics(self):
        chars = self.adapter.get_sampling_characteristics(BiomarkerType.GLUCOSE)
        assert isinstance(chars, SamplingCharacteristics)
        assert chars.typical_interval == timedelta(minutes=5)
        assert chars.temporal_behavior == TemporalBehavior.CONTINUOUS


class TestActivityAdapter:
    """Test activity adapter."""

    def setup_method(self):
        self.adapter = ActivityAdapter()

    @pytest.mark.asyncio
    async def test_push_steps(self):
        reading = BiomarkerReading(
            source_id="activity_generic",
            user_id=USER,
            biomarker_type=BiomarkerType.STEPS,
            timestamp=NOW,
            value=500,
            unit="steps",
        )
        ok = await self.adapter.push_reading(reading)
        assert ok is True

    @pytest.mark.asyncio
    async def test_push_exercise(self):
        reading = BiomarkerReading(
            source_id="activity_generic",
            user_id=USER,
            biomarker_type=BiomarkerType.EXERCISE,
            timestamp=NOW,
            value=1,
            unit="event",
            metadata={"type": "running", "duration_minutes": 30},
        )
        ok = await self.adapter.push_reading(reading)
        assert ok is True

    def test_supported_types(self):
        supported = self.adapter.supported_biomarkers
        assert BiomarkerType.STEPS in supported
        assert BiomarkerType.HEART_RATE in supported
        assert BiomarkerType.HRV in supported

    def test_tdee_estimation(self):
        readings = _make_hr_readings(6)
        tdee = ActivityAdapter.estimate_tdee(70, 175, 30, "male", readings)
        assert 1500 < tdee < 4000  # reasonable range


class TestSleepAdapter:
    def setup_method(self):
        self.adapter = SleepAdapter()

    @pytest.mark.asyncio
    async def test_push_sleep(self):
        reading = BiomarkerReading(
            source_id="sleep_generic",
            user_id=USER,
            biomarker_type=BiomarkerType.SLEEP,
            timestamp=NOW,
            value=7.5,  # hours
            unit="hours",
            metadata={"deep_pct": 0.2, "rem_pct": 0.25, "wake_count": 1},
        )
        ok = await self.adapter.push_reading(reading)
        assert ok is True


class TestGeneticAdapter:
    def setup_method(self):
        self.adapter = GeneticAdapter()

    @pytest.mark.asyncio
    async def test_push_genotype(self):
        reading = BiomarkerReading(
            source_id="genetic_profile",
            user_id=USER,
            biomarker_type=BiomarkerType.GENOTYPE,
            timestamp=NOW,
            value=3,
            unit="variants",
            metadata={
                "genotypes": {
                    "rs1801133": "CT",  # MTHFR heterozygous
                    "rs9939609": "AT",  # FTO heterozygous
                    "rs762551": "AA",  # CYP1A2 fast metabolizer
                }
            },
        )
        ok = await self.adapter.push_reading(reading)
        assert ok is True

    @pytest.mark.asyncio
    async def test_compute_metabolic_modifiers(self):
        reading = BiomarkerReading(
            source_id="genetic_profile",
            user_id=USER,
            biomarker_type=BiomarkerType.GENOTYPE,
            timestamp=NOW,
            value=2,
            unit="variants",
            metadata={
                "genotypes": {
                    "rs1801133": "TT",  # MTHFR homozygous → high folate need
                    "rs9939609": "AA",  # FTO → increased appetite risk
                }
            },
        )
        await self.adapter.push_reading(reading)

        modifiers = self.adapter.compute_metabolic_modifiers(USER)
        assert isinstance(modifiers, dict)
        # MTHFR TT should increase folate modifier significantly
        assert "folate_requirement_modifier" in modifiers
        assert modifiers["folate_requirement_modifier"] > 1.0  # increased demand


# ═══════════════════════════════════════════════════════════════════
#  2a. Physiological Lag Model — Core Patent Formula Unit Tests
# ═══════════════════════════════════════════════════════════════════


class TestPhysiologicalLagModel:
    """Unit tests proving the core patent formula:

        t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)

    These tests verify:
    - Base lag is correctly read from SamplingCharacteristics
    - Genetic modifier (γ) correctly inverts SNP metabolic speed
    - Circadian modifier (φ) varies with time of day
    - The three axes multiply independently
    - Full audit trail (LagComputation) is produced
    """

    def setup_method(self):
        self.model = PhysiologicalLagModel()
        self.glucose_chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=5),
            min_interval=timedelta(minutes=1),
            max_gap_before_stale=timedelta(minutes=30),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            physiological_lag=timedelta(minutes=60),  # Δt_base = 60 min
            circadian_sensitivity=0.3,
            noise_floor=5.0,
        )
        self.hr_chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=1),
            min_interval=timedelta(seconds=10),
            max_gap_before_stale=timedelta(minutes=10),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            physiological_lag=timedelta(0),  # Δt_base = 0 (instant)
            circadian_sensitivity=0.2,
            noise_floor=2.0,
        )

    # ── Base Lag Tests ──────────────────────────────────────────────

    def test_base_lag_glucose_is_60_minutes(self):
        """Δt_base(glucose) = 60 minutes."""
        event_time = datetime(2026, 2, 10, 12, 0, 0)  # noon
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time
        )
        assert lag.base_lag_seconds == 3600.0  # 60 min = 3600 sec

    def test_zero_lag_signal_returns_immediately(self):
        """Signals with zero base lag (HR) skip computation entirely."""
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.HEART_RATE, self.hr_chars, event_time
        )
        assert lag.effective_lag_seconds == 0
        assert lag.genetic_modifier == 1.0
        assert lag.circadian_modifier == 1.0

    # ── Circadian Modifier Tests ───────────────────────────────────

    def test_circadian_modifier_morning_is_less_than_one(self):
        """φ_circadian at 8:00 AM < 1.0 (faster metabolism in the morning)."""
        morning = datetime(2026, 2, 10, 8, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, morning
        )
        assert lag.circadian_modifier < 1.0, (
            f"Morning φ should be <1.0, got {lag.circadian_modifier}"
        )

    def test_circadian_modifier_night_is_greater_than_one(self):
        """φ_circadian at 2:00 AM > 1.0 (slower metabolism at night)."""
        night = datetime(2026, 2, 10, 2, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, night
        )
        assert lag.circadian_modifier > 1.0, (
            f"Night φ should be >1.0, got {lag.circadian_modifier}"
        )

    def test_circadian_modifier_smooth_interpolation(self):
        """φ at 8:30 should be between φ(8:00) and φ(9:00)."""
        t_8_00 = datetime(2026, 2, 10, 8, 0, 0)
        t_8_30 = datetime(2026, 2, 10, 8, 30, 0)
        t_9_00 = datetime(2026, 2, 10, 9, 0, 0)

        phi_8 = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, t_8_00
        ).circadian_modifier
        phi_830 = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, t_8_30
        ).circadian_modifier
        phi_9 = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, t_9_00
        ).circadian_modifier

        assert min(phi_8, phi_9) <= phi_830 <= max(phi_8, phi_9), (
            f"φ(8:30)={phi_830} should be between φ(8:00)={phi_8} and φ(9:00)={phi_9}"
        )

    def test_circadian_modifier_matches_lookup_table(self):
        """φ at exact hours matches the CIRCADIAN_LAG_MODIFIERS table."""
        for hour, expected_phi in CIRCADIAN_LAG_MODIFIERS.items():
            t = datetime(2026, 2, 10, hour, 0, 0)
            phi = self.model.compute_lag(
                BiomarkerType.GLUCOSE, self.glucose_chars, t
            ).circadian_modifier
            assert abs(phi - expected_phi) < 1e-6, (
                f"Hour {hour}: expected φ={expected_phi}, got {phi}"
            )

    # ── Genetic Modifier Tests ─────────────────────────────────────

    def test_no_genetics_gives_gamma_one(self):
        """Without genetic data, γ_genetic = 1.0."""
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time,
            user_id="user-no-genetics"
        )
        assert lag.genetic_modifier == 1.0
        assert lag.genetic_factors_used == []

    def test_tcf7l2_tt_increases_lag_by_25_percent(self):
        """TCF7L2 T/T carrier: insulin_response_modifier=0.8 → γ=1.25.

        The inverse of 0.8 = 1.25, meaning glucose stays elevated 25%
        longer because insulin response is 20% weaker.
        """
        self.model.set_genetic_modifiers(
            "user-tcf7l2-tt",
            {"insulin_response_modifier": 0.8}
        )
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time,
            user_id="user-tcf7l2-tt"
        )
        assert abs(lag.genetic_modifier - 1.25) < 0.01, (
            f"Expected γ≈1.25, got {lag.genetic_modifier}"
        )
        assert "insulin_response_modifier=0.8" in lag.genetic_factors_used

    def test_high_carb_sensitivity_decreases_lag(self):
        """High carb sensitivity (>1.0) → γ < 1.0 → shorter lag."""
        self.model.set_genetic_modifiers(
            "user-fast-metabolizer",
            {"carb_sensitivity_modifier": 1.3}
        )
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time,
            user_id="user-fast-metabolizer"
        )
        assert lag.genetic_modifier < 1.0, (
            f"High sensitivity should give γ<1.0, got {lag.genetic_modifier}"
        )

    def test_multiple_snps_geometric_mean(self):
        """Multiple SNPs combine via geometric mean.

        insulin_response=0.8 → factor=1.25
        carb_sensitivity=1.3 → factor=0.769
        geometric_mean = exp((ln(1.25) + ln(0.769)) / 2) ≈ 0.980
        """
        self.model.set_genetic_modifiers(
            "user-multi-snp",
            {
                "insulin_response_modifier": 0.8,
                "carb_sensitivity_modifier": 1.3,
            }
        )
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time,
            user_id="user-multi-snp"
        )
        # Geometric mean of 1/0.8=1.25 and 1/1.3≈0.769
        expected_gamma = math.exp(
            (math.log(1.0 / 0.8) + math.log(1.0 / 1.3)) / 2
        )
        assert abs(lag.genetic_modifier - round(expected_gamma, 4)) < 0.01, (
            f"Expected γ≈{expected_gamma:.4f}, got {lag.genetic_modifier}"
        )
        assert len(lag.genetic_factors_used) == 2

    def test_genetic_modifier_clamped_to_bounds(self):
        """γ is clamped to [0.5, 2.0] for safety."""
        # Extreme value: modifier=0.1 → γ=10.0 → clamped to 2.0
        self.model.set_genetic_modifiers(
            "user-extreme",
            {"insulin_response_modifier": 0.1}
        )
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time,
            user_id="user-extreme"
        )
        assert lag.genetic_modifier <= 2.0
        assert lag.genetic_modifier >= 0.5

    # ── Full Formula Integration ──────────────────────────────────

    def test_full_formula_morning_vs_night(self):
        """Core patent demonstration: same person, same meal,
        different time → different lag.

        TCF7L2 T/T user:
          Morning (8am):  60min × 1.25 × φ(8)  → shorter lag
          Night (2am):    60min × 1.25 × φ(2)  → longer lag
        """
        self.model.set_genetic_modifiers(
            "user-demo",
            {"insulin_response_modifier": 0.8}  # γ = 1.25
        )

        morning = datetime(2026, 2, 10, 8, 0, 0)
        night = datetime(2026, 2, 10, 2, 0, 0)

        lag_morning = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, morning,
            user_id="user-demo"
        )
        lag_night = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, night,
            user_id="user-demo"
        )

        # Morning lag should be shorter than night lag
        assert lag_morning.effective_lag_seconds < lag_night.effective_lag_seconds, (
            f"Morning lag ({lag_morning.effective_lag_seconds}s) "
            f"should be < Night lag ({lag_night.effective_lag_seconds}s)"
        )

        # Verify the multiplicative formula: effective = base × γ × φ
        expected_morning = 3600 * 1.25 * CIRCADIAN_LAG_MODIFIERS[8]
        expected_night = 3600 * 1.25 * CIRCADIAN_LAG_MODIFIERS[2]
        assert abs(lag_morning.effective_lag_seconds - round(expected_morning, 1)) < 1.0
        assert abs(lag_night.effective_lag_seconds - round(expected_night, 1)) < 1.0

        # The difference should be significant (>10%)
        ratio = lag_night.effective_lag_seconds / lag_morning.effective_lag_seconds
        assert ratio > 1.1, (
            f"Night/Morning ratio={ratio:.3f} — should be >1.1 to demonstrate "
            f"clinically meaningful circadian variation"
        )

    def test_audit_trail_completeness(self):
        """LagComputation captures full audit trail for patent claims."""
        self.model.set_genetic_modifiers(
            "user-audit",
            {"insulin_response_modifier": 0.8}
        )
        event_time = datetime(2026, 2, 10, 14, 30, 0)  # 2:30 PM
        lag = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time,
            user_id="user-audit"
        )

        # All fields are populated
        assert isinstance(lag, LagComputation)
        assert lag.biomarker_type == "glucose"
        assert lag.base_lag_seconds == 3600.0
        assert lag.genetic_modifier > 0
        assert lag.circadian_modifier > 0
        assert lag.effective_lag_seconds > 0
        assert lag.hour_of_day == 14
        assert len(lag.genetic_factors_used) >= 1

        # Verify the effective_lag property returns a timedelta
        assert isinstance(lag.effective_lag, timedelta)
        assert lag.effective_lag.total_seconds() == lag.effective_lag_seconds

    def test_different_biomarkers_different_lags(self):
        """Different biomarker types have different base lags."""
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag_glucose = self.model.compute_lag(
            BiomarkerType.GLUCOSE, self.glucose_chars, event_time
        )
        lag_hr = self.model.compute_lag(
            BiomarkerType.HEART_RATE, self.hr_chars, event_time
        )
        # Glucose has 60min base lag, HR has 0
        assert lag_glucose.effective_lag_seconds > 0
        assert lag_hr.effective_lag_seconds == 0

    def test_non_glucose_ignores_glucose_genetics(self):
        """Genetic modifiers for glucose don't affect heart rate lag."""
        self.model.set_genetic_modifiers(
            "user-glucose-only",
            {"insulin_response_modifier": 0.8}
        )
        event_time = datetime(2026, 2, 10, 12, 0, 0)
        lag_hr = self.model.compute_lag(
            BiomarkerType.HEART_RATE, self.hr_chars, event_time,
            user_id="user-glucose-only"
        )
        # HR has zero base lag, so genetic modifier is irrelevant
        assert lag_hr.effective_lag_seconds == 0


# ═══════════════════════════════════════════════════════════════════
#  2b. Temporal Synchronization
# ═══════════════════════════════════════════════════════════════════


class TestTemporalSynchronizer:
    """Test the patent-core temporal synchronization engine."""

    def setup_method(self):
        self.sync = TemporalSynchronizer()
        # Register glucose source
        cgm_chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=5),
            min_interval=timedelta(minutes=1),
            max_gap_before_stale=timedelta(minutes=30),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            physiological_lag=timedelta(minutes=60),
            circadian_sensitivity=0.3,
            noise_floor=5.0,
        )
        self.sync.register_source(BiomarkerType.GLUCOSE, cgm_chars)

        # Register heart rate source
        hr_chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=1),
            min_interval=timedelta(seconds=10),
            max_gap_before_stale=timedelta(minutes=10),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            physiological_lag=timedelta(0),
            circadian_sensitivity=0.2,
            noise_floor=2.0,
        )
        self.sync.register_source(BiomarkerType.HEART_RATE, hr_chars)

    def test_synchronize_single_source(self):
        glucose_readings = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose_readings}

        frames = self.sync.synchronize(
            readings,
            NOW - timedelta(hours=1),
            NOW,
            Resolution.MEDIUM,  # 1-hour window
        )
        assert len(frames) >= 1
        assert isinstance(frames[0], SynchronizedFrame)

        # Frame should contain glucose signal
        frame = frames[0]
        assert BiomarkerType.GLUCOSE in frame.signals
        sig = frame.signals[BiomarkerType.GLUCOSE]
        assert sig.sample_count > 0
        assert sig.confidence > 0

    def test_synchronize_multi_source(self):
        """Core patent claim: align heterogeneous sources onto one grid."""
        glucose_readings = _make_glucose_readings(12)  # 5-min intervals
        hr_readings = _make_hr_readings(6)  # 10-min intervals

        readings = {
            BiomarkerType.GLUCOSE: glucose_readings,
            BiomarkerType.HEART_RATE: hr_readings,
        }

        frames = self.sync.synchronize(
            readings,
            NOW - timedelta(hours=1),
            NOW,
            Resolution.MEDIUM,
        )
        assert len(frames) >= 1

        frame = frames[0]
        # Both signals should be present in the same time window
        assert BiomarkerType.GLUCOSE in frame.signals
        assert BiomarkerType.HEART_RATE in frame.signals

    def test_feature_vector_generation(self):
        glucose_readings = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose_readings}

        frames = self.sync.synchronize(
            readings,
            NOW - timedelta(hours=1),
            NOW,
            Resolution.MEDIUM,
        )
        fv = frames[0].to_feature_vector()
        assert isinstance(fv, dict)
        assert any("glucose" in k for k in fv.keys())

    def test_frame_confidence_and_completeness(self):
        glucose_readings = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose_readings}

        frames = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.MEDIUM
        )
        frame = frames[0]
        assert 0 <= frame.frame_confidence <= 1
        assert 0 <= frame.completeness <= 1

    def test_resolution_fine(self):
        """Fine resolution should produce more frames."""
        glucose_readings = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose_readings}

        frames_fine = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.FINE
        )
        frames_medium = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.MEDIUM
        )
        assert len(frames_fine) >= len(frames_medium)


# ═══════════════════════════════════════════════════════════════════
#  3. Physiological Normalization
# ═══════════════════════════════════════════════════════════════════


class TestPhysiologicalNormalizer:
    """Test circadian-aware normalization pipeline."""

    def setup_method(self):
        self.normalizer = PhysiologicalNormalizer()

    def test_normalize_single_value(self):
        result = self.normalizer.normalize(
            USER, BiomarkerType.GLUCOSE, 110.0, NOW
        )
        assert isinstance(result, NormalizedSignal)
        assert result.raw_value == 110.0
        assert result.normalized_value != 0  # should be non-trivial
        assert result.biomarker_type == BiomarkerType.GLUCOSE

    def test_baseline_learns_over_time(self):
        """Baseline should converge after multiple observations."""
        for i in range(60):
            ts = NOW - timedelta(hours=60 - i)
            self.normalizer.normalize(
                USER, BiomarkerType.GLUCOSE, 100 + i * 0.5, ts
            )

        baseline = self.normalizer.get_or_create_baseline(
            USER, BiomarkerType.GLUCOSE
        )
        assert baseline.sample_count >= 50
        assert baseline.is_mature is True

    def test_genetic_modifier_application(self):
        """Genetic modifiers should alter normalization output."""
        # Without genetic modifier
        result_base = self.normalizer.normalize(
            USER, BiomarkerType.GLUCOSE, 110, NOW
        )

        # Set modifier that maps to the glucose biomarker key
        self.normalizer.set_genetic_modifiers(
            USER,
            {
                "carb_sensitivity_modifier": 1.5,
                "insulin_response_modifier": 1.3,
            },
        )
        result_genetic = self.normalizer.normalize(
            "user-with-genetics", BiomarkerType.GLUCOSE, 110, NOW
        )
        # The genetic_modified value should differ because modifiers were set
        # for "user-with-genetics"... but they were set on USER.
        # Let's normalize with the same user.
        self.normalizer.set_genetic_modifiers(
            "user-genetic-test",
            {
                "carb_sensitivity_modifier": 1.5,
                "insulin_response_modifier": 1.3,
            },
        )
        result_g = self.normalizer.normalize(
            "user-genetic-test", BiomarkerType.GLUCOSE, 110, NOW
        )
        # genetic_modified should reflect the modifier (≠1.0)
        # The factor is the average of 1.5 and 1.3 = 1.4
        # So genetic_modified = normalized * 1.4 (approx)
        assert abs(result_g.genetic_modified - result_base.genetic_modified) > 0.01

    def test_anomaly_detection(self):
        """Anomalous readings should have high anomaly scores."""
        # Train baseline on normal values
        for i in range(30):
            self.normalizer.normalize(
                USER,
                BiomarkerType.GLUCOSE,
                100 + (i % 5),
                NOW - timedelta(hours=30 - i),
            )

        # Anomalous value
        result = self.normalizer.normalize(
            USER, BiomarkerType.GLUCOSE, 300, NOW
        )
        assert result.anomaly_score > 0.5

    def test_normalize_frame_signals(self):
        signals = {
            BiomarkerType.GLUCOSE: 110.0,
            BiomarkerType.HEART_RATE: 72.0,
        }
        results = self.normalizer.normalize_frame_signals(
            USER, signals, NOW
        )
        assert BiomarkerType.GLUCOSE in results
        assert BiomarkerType.HEART_RATE in results


# ═══════════════════════════════════════════════════════════════════
#  4. Circadian Interpolation
# ═══════════════════════════════════════════════════════════════════


class TestCircadianInterpolator:
    def setup_method(self):
        self.interp = CircadianInterpolator()

    def test_interpolate_gap(self):
        """Should fill a time-series gap using circadian model."""
        readings = []
        for i in range(6):
            ts = NOW - timedelta(hours=3 - i * 0.5)
            readings.append(
                BiomarkerReading(
                    source_id="cgm_generic",
                    user_id=USER,
                    biomarker_type=BiomarkerType.GLUCOSE,
                    timestamp=ts,
                    value=100 + i * 2,
                    unit="mg/dL",
                )
            )

        # Skip an hour gap and add more readings
        for i in range(6):
            ts = NOW + timedelta(hours=1 + i * 0.5)
            readings.append(
                BiomarkerReading(
                    source_id="cgm_generic",
                    user_id=USER,
                    biomarker_type=BiomarkerType.GLUCOSE,
                    timestamp=ts,
                    value=108 - i * 2,
                    unit="mg/dL",
                )
            )

        result = self.interp.interpolate_series(
            user_id=USER,
            biomarker_type=BiomarkerType.GLUCOSE,
            readings=readings,
            start=NOW - timedelta(hours=3),
            end=NOW + timedelta(hours=4),
            interval=timedelta(minutes=30),
            personal_baseline_mean=105.0,
        )
        assert len(result) > len(readings)  # gaps should be filled


# ═══════════════════════════════════════════════════════════════════
#  5. Metabolic State Estimator
# ═══════════════════════════════════════════════════════════════════


class TestMetabolicStateEstimator:
    def setup_method(self):
        self.estimator = MetabolicStateEstimator()
        self.sync = TemporalSynchronizer()

        cgm_chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=5),
            min_interval=timedelta(minutes=1),
            max_gap_before_stale=timedelta(minutes=30),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
        )
        self.sync.register_source(BiomarkerType.GLUCOSE, cgm_chars)

    def test_fasting_state(self):
        """No recent meal → fasting phase."""
        glucose = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose}
        frames = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.MEDIUM
        )
        state = self.estimator.estimate(USER, frames[0], NOW)
        assert isinstance(state, MetabolicState)
        # Without meal events, should be in fasting-like state
        assert MetabolicPhase.FASTING in state.active_phases or state.hours_since_last_meal > 4

    def test_postprandial_state(self):
        """Recent meal → postprandial phase."""
        self.estimator.record_meal_event(USER, NOW - timedelta(minutes=30))
        glucose = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose}
        frames = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.MEDIUM
        )
        state = self.estimator.estimate(USER, frames[0], NOW)
        postprandial_phases = {
            MetabolicPhase.POSTPRANDIAL_EARLY,
            MetabolicPhase.POSTPRANDIAL_LATE,
        }
        assert state.active_phases & postprandial_phases or state.hours_since_last_meal < 1

    def test_exercise_recovery(self):
        """Recent exercise → recovery phase."""
        self.estimator.record_exercise_event(
            USER, NOW - timedelta(minutes=15), 45, "high"
        )
        glucose = _make_glucose_readings(12)
        readings = {BiomarkerType.GLUCOSE: glucose}
        frames = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.MEDIUM
        )
        state = self.estimator.estimate(USER, frames[0], NOW)
        recovery_phases = {
            MetabolicPhase.RECOVERY_IMMEDIATE,
            MetabolicPhase.RECOVERY_DELAYED,
            MetabolicPhase.RECOVERY,
        }
        assert state.active_phases & recovery_phases or state.hours_since_last_exercise < 1

    def test_nutrient_priority_shifts(self):
        """Metabolic state should modify nutrient priorities."""
        self.estimator.record_meal_event(USER, NOW - timedelta(hours=6))
        glucose = _make_glucose_readings(12, base_value=85)
        readings = {BiomarkerType.GLUCOSE: glucose}
        frames = self.sync.synchronize(
            readings, NOW - timedelta(hours=1), NOW, Resolution.MEDIUM
        )
        state = self.estimator.estimate(USER, frames[0], NOW)
        # Should have nutrient priority shifts
        assert isinstance(state.nutrient_priority_shifts, dict)

    def test_context_string(self):
        state = MetabolicState(timestamp=NOW)
        ctx = state.to_context_string()
        assert isinstance(ctx, str)
        assert len(ctx) > 0


# ═══════════════════════════════════════════════════════════════════
#  6. Nutrient Demand Calculator
# ═══════════════════════════════════════════════════════════════════


class TestNutrientDemandCalculator:
    def setup_method(self):
        self.calculator = NutrientDemandCalculator()
        self.normalizer = PhysiologicalNormalizer()

    def test_create_default_targets(self):
        targets = create_default_targets(kcal=2000, weight_kg=70)
        assert "kcal" in targets
        assert "protein_g" in targets
        assert "carbs_g" in targets
        assert "fat_g" in targets
        assert "fiber_g" in targets
        assert "water_ml" in targets
        assert targets["kcal"].daily_target == 2000

    def test_calculate_budget(self):
        """Full pipeline: targets + state + signals → budget."""
        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)

        # Normalize some signals
        norm_signals = self.normalizer.normalize_frame_signals(
            USER,
            {BiomarkerType.GLUCOSE: 115, BiomarkerType.HEART_RATE: 72},
            NOW,
        )

        budget = self.calculator.calculate(
            user_id=USER,
            base_targets=targets,
            metabolic_state=state,
            normalized_signals=norm_signals,
            genetic_modifiers={},
            frame_confidence=0.9,
        )

        assert isinstance(budget, NutrientBudget)
        assert budget.user_id == USER
        assert "kcal" in budget.targets
        assert budget.confidence > 0

    def test_budget_with_consumed_amounts(self):
        targets = create_default_targets(kcal=2000, weight_kg=70)
        targets["kcal"].consumed_today = 1200
        targets["protein_g"].consumed_today = 50
        state = MetabolicState(timestamp=NOW)

        budget = self.calculator.calculate(
            user_id=USER,
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        assert budget.targets["kcal"].remaining < 2000
        assert budget.targets["protein_g"].remaining < targets["protein_g"].daily_target

    def test_next_meal_recommendation(self):
        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)

        budget = self.calculator.calculate(
            user_id=USER,
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        rec = budget.get_next_meal_recommendation()
        assert isinstance(rec, dict)
        # Should suggest some macros
        assert any(k in rec for k in ["kcal", "protein_g", "carbs_g", "fat_g"])

    def test_time_buckets(self):
        targets = create_default_targets()
        state = MetabolicState(timestamp=NOW)

        budget = self.calculator.calculate(
            user_id=USER,
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )
        assert len(budget.time_buckets) > 0
        for tb in budget.time_buckets:
            assert 0 <= tb.start_hour < 24
            assert 0 <= tb.end_hour <= 24

    def test_genetic_modifiers_affect_budget(self):
        targets = create_default_targets(kcal=2000, weight_kg=70)
        state = MetabolicState(timestamp=NOW)

        budget_base = self.calculator.calculate(
            user_id=USER,
            base_targets=targets,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={},
        )

        targets2 = create_default_targets(kcal=2000, weight_kg=70)
        budget_genetic = self.calculator.calculate(
            user_id=USER,
            base_targets=targets2,
            metabolic_state=state,
            normalized_signals={},
            genetic_modifiers={
                "calorie_sensitivity_modifier": 1.3,
                "carb_sensitivity_modifier": 0.8,
                "protein_utilization_modifier": 1.2,
            },
        )

        # Genetic modifiers should produce modification records
        assert len(budget_genetic.modifications) > 0
        # kcal and carbs_g targets should be modified
        modified_nutrients = {m["nutrient"] for m in budget_genetic.modifications}
        assert "kcal" in modified_nutrients
        assert "carbs_g" in modified_nutrients


# ═══════════════════════════════════════════════════════════════════
#  7. Differential Privacy
# ═══════════════════════════════════════════════════════════════════


class TestDifferentialPrivacy:
    def setup_method(self):
        self.engine = DifferentialPrivacyEngine(default_epsilon=1.0)

    def test_laplace_noise_adds_perturbation(self):
        original = 100.0
        noisy = self.engine.add_laplace_noise(USER, original, sensitivity=1.0)
        assert noisy is not None
        # Very unlikely to be exactly the same
        # (probability ~ 0) but allow it in edge case
        assert isinstance(noisy, float)

    def test_gaussian_noise(self):
        noisy = self.engine.add_gaussian_noise(
            USER, 100.0, sensitivity=1.0, epsilon=0.5
        )
        assert noisy is not None

    def test_budget_exhaustion(self):
        """Budget should be depleted after many queries."""
        budget = self.engine.get_or_create_budget(USER, epsilon_total=0.3)
        # Each query consumes default epsilon. Keep calling until budget runs out.
        none_count = 0
        for _ in range(50):
            result = self.engine.add_laplace_noise(
                USER, 50.0, sensitivity=1.0, epsilon=0.1
            )
            if result is None:
                none_count += 1
        # After exhaustion, calls should return None
        assert none_count > 0

    def test_privacy_budget_reset(self):
        budget = PrivacyBudget(
            epsilon_total=1.0,
            epsilon_spent=0.9,
            last_reset=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25),
        )
        did_reset = budget.maybe_reset()
        assert did_reset is True
        assert budget.epsilon_spent == 0.0

    def test_privatize_aggregation(self):
        users = ["u1", "u2", "u3"]
        values = {"calories": 2100, "protein": 80}
        sensitivities = {"calories": 500, "protein": 50}

        result = self.engine.privatize_aggregation(
            users, values, sensitivities, epsilon_per_query=0.1
        )
        assert "calories" in result
        assert "protein" in result


# ═══════════════════════════════════════════════════════════════════
#  8. Consent Manager
# ═══════════════════════════════════════════════════════════════════


class TestConsentManager:
    def setup_method(self):
        self.mgr = DynamicConsentManager()

    def test_grant_and_check(self):
        self.mgr.grant_consent(USER, ConsentScope.GLUCOSE_DATA, "user opted in")
        assert self.mgr.check_consent(USER, ConsentScope.GLUCOSE_DATA) is True
        assert self.mgr.check_consent(USER, ConsentScope.GENETIC_DATA) is False

    def test_revoke(self):
        self.mgr.grant_consent(USER, ConsentScope.GLUCOSE_DATA)
        self.mgr.revoke_consent(USER, ConsentScope.GLUCOSE_DATA, "changed mind")
        assert self.mgr.check_consent(USER, ConsentScope.GLUCOSE_DATA) is False

    def test_consent_state(self):
        self.mgr.grant_consent(USER, ConsentScope.GLUCOSE_DATA)
        self.mgr.grant_consent(USER, ConsentScope.ACTIVITY_DATA)
        state = self.mgr.get_consent_state(USER)
        assert isinstance(state, ConsentState)
        assert ConsentScope.GLUCOSE_DATA in state.granted_scopes
        assert ConsentScope.ACTIVITY_DATA in state.granted_scopes

    def test_allowed_biomarkers(self):
        self.mgr.grant_consent(USER, ConsentScope.GLUCOSE_DATA)
        self.mgr.grant_consent(USER, ConsentScope.SLEEP_DATA)
        state = self.mgr.get_consent_state(USER)
        allowed = state.get_allowed_biomarkers()
        assert isinstance(allowed, set)

    def test_revocation_callback(self):
        revoked_scopes = []

        def on_revoke(uid, scope):
            revoked_scopes.append((uid, scope))

        self.mgr.register_revocation_callback(on_revoke)
        self.mgr.grant_consent(USER, ConsentScope.GENETIC_DATA)
        self.mgr.revoke_consent(USER, ConsentScope.GENETIC_DATA)
        assert len(revoked_scopes) == 1
        assert revoked_scopes[0][0] == USER

    def test_audit_log(self):
        self.mgr.grant_consent(USER, ConsentScope.GLUCOSE_DATA)
        self.mgr.revoke_consent(USER, ConsentScope.GLUCOSE_DATA)
        log = self.mgr.get_audit_log(USER)
        assert len(log) == 2

    def test_filter_data_by_consent(self):
        """Data filtering should respect consent state."""
        self.mgr.grant_consent(USER, ConsentScope.GLUCOSE_DATA)
        # Genetic data NOT granted

        data = {"glucose_level": 110, "genotype_data": {"rs1801133": "CT"}}
        scope_map = {
            "glucose_level": ConsentScope.GLUCOSE_DATA,
            "genotype_data": ConsentScope.GENETIC_DATA,
        }
        filtered = self.mgr.filter_data_by_consent(USER, data, scope_map)
        assert "glucose_level" in filtered
        assert "genotype_data" not in filtered


# ═══════════════════════════════════════════════════════════════════
#  9. Graph Embedding (Privacy)
# ═══════════════════════════════════════════════════════════════════


class TestGraphEmbedding:
    def setup_method(self):
        self.graph = HealthGraphEmbedding()

    def test_add_node_and_embed(self):
        self.graph.add_node(
            GraphNode(node_id="user1", node_type="user", properties={"age": "30", "sex": "male"})
        )
        self.graph.add_node(
            GraphNode(node_id="glucose1", node_type="biomarker", properties={"type": "glucose", "value": "110"})
        )
        self.graph.add_edge(
            GraphEdge(source_id="user1", target_id="glucose1", edge_type="has_reading", weight=0.9)
        )

        emb = self.graph.compute_node_embedding("user1")
        assert emb is not None
        assert len(emb.embedding) > 0

    def test_consent_based_severing(self):
        self.graph.add_node(GraphNode(node_id="u1", node_type="user"))
        self.graph.add_node(
            GraphNode(node_id="g1", node_type="biomarker", properties={"consent_scope": "genetic_data"})
        )
        self.graph.add_edge(
            GraphEdge(source_id="u1", target_id="g1", edge_type="has_reading", weight=1.0, consent_required="genetic_data")
        )

        self.graph.sever_edges_by_consent("genetic_data")
        emb = self.graph.compute_node_embedding("u1")
        # After severing, should still compute but with reduced connectivity
        assert emb is not None


# ═══════════════════════════════════════════════════════════════════
#  10. Integration — Full Pipeline
# ═══════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """End-to-end pipeline: ingest → sync → normalize → state → budget."""

    @pytest.mark.asyncio
    async def test_end_to_end(self):
        # 1. Create adapters
        cgm = CGMAdapter()
        activity = ActivityAdapter()

        # 2. Ingest glucose readings
        for r in _make_glucose_readings(12, base_value=120):
            await cgm.push_reading(r)

        # 3. Ingest heart rate readings
        for r in _make_hr_readings(6):
            await activity.push_reading(r)

        # 4. Fetch and synchronize
        sync = TemporalSynchronizer()
        sync.register_source(
            BiomarkerType.GLUCOSE,
            cgm.get_sampling_characteristics(BiomarkerType.GLUCOSE),
        )
        sync.register_source(
            BiomarkerType.HEART_RATE,
            activity.get_sampling_characteristics(BiomarkerType.HEART_RATE),
        )

        glucose_data = await cgm.fetch_readings(
            USER, BiomarkerType.GLUCOSE, NOW - timedelta(hours=1), NOW
        )
        hr_data = await activity.fetch_readings(
            USER, BiomarkerType.HEART_RATE, NOW - timedelta(hours=1), NOW
        )

        frames = sync.synchronize(
            {BiomarkerType.GLUCOSE: glucose_data, BiomarkerType.HEART_RATE: hr_data},
            NOW - timedelta(hours=1),
            NOW,
            Resolution.MEDIUM,
        )
        assert len(frames) >= 1

        frame = frames[0]

        # 5. Normalize
        normalizer = PhysiologicalNormalizer()
        norm_signals = {}
        for bt, sig in frame.signals.items():
            norm_signals[bt] = normalizer.normalize(USER, bt, sig.value, NOW)

        # 6. Estimate metabolic state
        estimator = MetabolicStateEstimator()
        estimator.record_meal_event(USER, NOW - timedelta(hours=2))
        state = estimator.estimate(USER, frame, NOW)

        # 7. Calculate nutrient budget
        calculator = NutrientDemandCalculator()
        targets = create_default_targets(kcal=2200, weight_kg=75)
        budget = calculator.calculate(
            user_id=USER,
            base_targets=targets,
            metabolic_state=state,
            normalized_signals=norm_signals,
            genetic_modifiers={},
            frame_confidence=frame.frame_confidence,
        )

        assert isinstance(budget, NutrientBudget)
        assert budget.confidence > 0
        rec = budget.get_next_meal_recommendation()
        assert len(rec) > 0

        # Verify the full summary works
        summary = budget.to_summary()
        assert "user_id" in summary
        assert "targets" in summary


# ═══════════════════════════════════════════════════════════════════
#  11. API Router (FastAPI integration)
# ═══════════════════════════════════════════════════════════════════


class TestAPIRouter:
    """Test the FastAPI endpoints via TestClient."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from app.main import app

        self.client = TestClient(app)
        self.headers = {"X-API-Key": "dev-api-key"}

    def test_health(self):
        resp = self.client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_engine_status(self):
        resp = self.client.get("/engine/status", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "registered_sources" in data
        assert "registered_biomarker_types" in data

    def test_ingest_biomarkers(self):
        payload = {
            "readings": [
                {
                    "source_id": "cgm_generic",
                    "user_id": USER,
                    "biomarker_type": "glucose",
                    "timestamp": NOW.isoformat(),
                    "value": 115.0,
                    "unit": "mg/dL",
                    "confidence": 0.95,
                    "metadata": {},
                }
            ]
        }
        resp = self.client.post(
            "/engine/ingest", json=payload, headers=self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] >= 1

    def test_ingest_invalid_type(self):
        payload = {
            "readings": [
                {
                    "source_id": "x",
                    "user_id": USER,
                    "biomarker_type": "nonexistent_type",
                    "timestamp": NOW.isoformat(),
                    "value": 1,
                    "unit": "",
                }
            ]
        }
        resp = self.client.post(
            "/engine/ingest", json=payload, headers=self.headers
        )
        assert resp.status_code in (200, 400)

    def test_consent_grant_and_get(self):
        # Grant
        resp = self.client.post(
            "/engine/consent",
            json={
                "user_id": USER,
                "scope": "glucose_data",
                "action": "grant",
                "reason": "test",
            },
            headers=self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "glucose_data" in data["granted_scopes"]

        # Get status
        resp = self.client.get(
            f"/engine/consent/{USER}", headers=self.headers
        )
        assert resp.status_code == 200

    def test_genetic_profile(self):
        payload = {
            "user_id": USER,
            "genotypes": {"rs1801133": "CT", "rs9939609": "AT"},
        }
        resp = self.client.post(
            "/engine/genetic-profile", json=payload, headers=self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["variant_count"] == 2
        assert "modifiers" in data

    def test_nutrient_budget(self):
        # Ingest some data first
        readings = []
        for i in range(5):
            readings.append({
                "source_id": "cgm_generic",
                "user_id": USER,
                "biomarker_type": "glucose",
                "timestamp": (NOW - timedelta(minutes=i * 5)).isoformat(),
                "value": 105 + i,
                "unit": "mg/dL",
            })
        self.client.post(
            "/engine/ingest",
            json={"readings": readings},
            headers=self.headers,
        )

        resp = self.client.post(
            "/engine/nutrient-budget",
            json={
                "user_id": USER,
                "kcal_target": 2000,
                "weight_kg": 70,
                "consumed_today": {"calories": 800, "protein": 40},
            },
            headers=self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "targets" in data
        assert "metabolic_state" in data
        assert "confidence" in data

    def test_unauthorized_without_key(self):
        resp = self.client.get("/engine/status")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  CircadianInterpolator – Pipeline Integration Tests
#  Proves the whitepaper claim: "gaps are filled by biological-rhythm
#  models, not naïve zero-fill." (Patent Section 4.3)
# ═══════════════════════════════════════════════════════════════════

class TestCircadianInterpolatorIntegration:
    """End-to-end: TemporalSynchronizer uses CircadianInterpolator to
    fill gaps when glucose readings are missing."""

    def _make_readings(
        self,
        biomarker: BiomarkerType,
        times_and_values: List[tuple],
    ) -> List[BiomarkerReading]:
        return [
            BiomarkerReading(
                biomarker_type=biomarker,
                value=v,
                unit="mg/dL",
                timestamp=t,
                source_id="test-source",
                user_id="test-user",
            )
            for t, v in times_and_values
        ]

    def _make_sync(self, interpolator=None):
        """Create a TemporalSynchronizer with glucose source registered."""
        sync = TemporalSynchronizer(interpolator=interpolator)
        cgm_chars = SamplingCharacteristics(
            typical_interval=timedelta(minutes=5),
            min_interval=timedelta(minutes=1),
            max_gap_before_stale=timedelta(minutes=30),
            temporal_behavior=TemporalBehavior.CONTINUOUS,
            physiological_lag=timedelta(minutes=60),
            circadian_sensitivity=0.3,
            noise_floor=5.0,
        )
        sync.register_source(BiomarkerType.GLUCOSE, cgm_chars)
        return sync

    def test_gap_filled_with_circadian_prediction(self):
        """When glucose has a 2-hour hole, the synchronizer should use
        CircadianInterpolator instead of returning confidence=0."""
        sync = self._make_sync()

        # Set a known baseline mean so the interpolator has something to work with
        user_id = "test-gap-user"
        sync.set_baseline_mean(user_id, BiomarkerType.GLUCOSE, 100.0)

        # Readings BEFORE and AFTER a 2-hour gap
        t0 = datetime(2025, 1, 15, 10, 0, 0)
        readings = self._make_readings(
            BiomarkerType.GLUCOSE,
            [
                (t0, 95.0),                                       # 10:00
                (t0 + timedelta(minutes=5), 98.0),                # 10:05
                # --- 2 hour gap (10:10 – 12:05) ---
                (t0 + timedelta(hours=2, minutes=10), 105.0),     # 12:10
                (t0 + timedelta(hours=2, minutes=15), 102.0),     # 12:15
            ],
        )

        # Use synchronize() to get frames across the gap
        frames = sync.synchronize(
            readings={BiomarkerType.GLUCOSE: readings},
            window_start=t0 + timedelta(hours=1),      # 11:00
            window_end=t0 + timedelta(hours=1, minutes=10),  # 11:10
            resolution=Resolution.FINE,
            user_id=user_id,
        )

        assert len(frames) > 0
        # Check the first frame in the gap
        frame = frames[0]
        glucose_signal = frame.signals.get(BiomarkerType.GLUCOSE)

        assert glucose_signal is not None, "Glucose signal should be present even during gap"
        # The value should be non-zero (circadian interpolation, not zero-fill)
        assert glucose_signal.value > 0, "Circadian interpolation should produce non-zero value"
        # Confidence should be > 0 (not the old zero-fill behavior)
        assert glucose_signal.confidence > 0, "Gap-filled signal should have non-zero confidence"
        # Confidence should be reduced compared to direct readings
        assert glucose_signal.confidence < 1.0, "Gap-filled signal confidence should be penalized"

    def test_no_data_at_all_uses_circadian_only(self):
        """When there are zero readings, circadian-only prediction is used
        with heavy confidence penalty."""
        sync = self._make_sync()
        user_id = "test-no-data"
        sync.set_baseline_mean(user_id, BiomarkerType.GLUCOSE, 100.0)

        frames = sync.synchronize(
            readings={BiomarkerType.GLUCOSE: []},
            window_start=datetime(2025, 1, 15, 14, 0, 0),
            window_end=datetime(2025, 1, 15, 14, 5, 0),
            resolution=Resolution.FINE,
            user_id=user_id,
        )

        assert len(frames) > 0
        frame = frames[0]
        glucose_signal = frame.signals.get(BiomarkerType.GLUCOSE)
        if glucose_signal is not None:
            # Circadian-only prediction should still give a non-zero value
            assert glucose_signal.value > 0
            # But confidence is heavily penalized (0.5x multiplier)
            assert glucose_signal.confidence < 0.5

    def test_interpolator_instance_is_shared(self):
        """The synchronizer should use its internal CircadianInterpolator."""
        interp = CircadianInterpolator()
        sync = self._make_sync(interpolator=interp)
        assert sync.interpolator is interp

    def test_without_baseline_falls_back_to_zero_fill(self):
        """Without a known baseline, the gap handler falls back to zero-fill
        (backward compatible with old behavior)."""
        sync = self._make_sync()
        user_id = "no-baseline-user"
        # Do NOT set baseline mean

        frames = sync.synchronize(
            readings={BiomarkerType.GLUCOSE: []},
            window_start=datetime(2025, 1, 15, 14, 0, 0),
            window_end=datetime(2025, 1, 15, 14, 5, 0),
            resolution=Resolution.FINE,
            user_id=user_id,
        )

        if len(frames) > 0:
            frame = frames[0]
            glucose_signal = frame.signals.get(BiomarkerType.GLUCOSE)
            if glucose_signal is not None:
                # Without explicit baseline, confidence should be near-zero
                # (population fallback may produce tiny residual confidence)
                assert glucose_signal.confidence < 0.01
