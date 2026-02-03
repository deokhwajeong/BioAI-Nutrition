"""
API router for the Biomarker Synchronization Engine.

Exposes the patent-core pipeline through REST endpoints:
1. Ingest heterogeneous biomarker readings
2. Synchronize and normalize data
3. Get real-time metabolic state
4. Calculate nutrient demand budget
5. Manage consent
6. Set genetic profile

This router ties together all engine components into a usable API.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from ..biomarkers.base import BiomarkerReading, BiomarkerType
from ..biomarkers.cgm_adapter import CGMAdapter
from ..biomarkers.activity_adapter import ActivityAdapter
from ..biomarkers.sleep_adapter import SleepAdapter
from ..biomarkers.genetic_adapter import GeneticAdapter
from ..biomarkers.location_adapter import LocationAdapter
from ..engine.temporal_sync import TemporalSynchronizer, Resolution
from ..engine.normalization import PhysiologicalNormalizer, GeneticBaselineCalculator
from ..engine.interpolation import CircadianInterpolator
from ..engine.metabolic_state import MetabolicStateEstimator
from ..engine.nutrient_calculator import (
    NutrientDemandCalculator,
    MedicalConstraint,
    create_default_targets,
)
from ..engine.pipeline import NutritionPipeline, PipelineResult, BIOMARKER_CONSENT_MAP
from ..privacy.consent_manager import DynamicConsentManager, ConsentScope
from ..privacy.differential_privacy import DifferentialPrivacyEngine
from ..privacy.graph_embedding import HealthGraphEmbedding
from ..privacy.edge_processor import EdgeProcessor
from ..schemas.biomarker_schemas import (
    AlignedSignalOut,
    BiomarkerBatchIn,
    BiomarkerIngestionResult,
    BiomarkerReadingIn,
    ConflictResolutionOut,
    ConsentRequest,
    ConsentStatusOut,
    GeneticModifiersOut,
    GeneticProfileIn,
    MedicalConstraintOut,
    MedicalConstraintsRequest,
    MedicalConstraintsResponse,
    MetabolicStateOut,
    ModificationOut,
    NutrientBudgetRequest,
    NutrientBudgetResponse,
    NutrientTargetOut,
    PipelineStatusOut,
    SyncRequest,
    SyncResponse,
    SynchronizedFrameOut,
    TimeBucketOut,
)

router = APIRouter(prefix="/engine", tags=["biomarker-engine"])

# ── Singleton pipeline components ───────────────────────────────────
# In production these would be injected via DI / managed lifecycle.

_cgm_adapter = CGMAdapter()
_activity_adapter = ActivityAdapter()
_sleep_adapter = SleepAdapter()
_genetic_adapter = GeneticAdapter()
_location_adapter = LocationAdapter()

_synchronizer = TemporalSynchronizer()
_normalizer = PhysiologicalNormalizer()
_interpolator = CircadianInterpolator()
_metabolic_estimator = MetabolicStateEstimator()
_nutrient_calculator = NutrientDemandCalculator()
_consent_manager = DynamicConsentManager()
_privacy_engine = DifferentialPrivacyEngine()
_graph_embedding = HealthGraphEmbedding()
_edge_processor = EdgeProcessor(embedding_dim=64, dp_epsilon=1.0)

# ── 5-Stage Pipeline Orchestrator ───────────────────────────────────
# Enforces correct ordering: Sync → Normalize → Interpolate → State → Nutrient
# with consent filtering at entrance and DP noise at exit.
_pipeline = NutritionPipeline(
    synchronizer=_synchronizer,
    normalizer=_normalizer,
    interpolator=_interpolator,
    state_estimator=_metabolic_estimator,
    nutrient_calculator=_nutrient_calculator,
    consent_manager=_consent_manager,
    privacy_engine=_privacy_engine,
)

# Register source characteristics with the synchronizer
_ADAPTER_MAP = {
    BiomarkerType.GLUCOSE: _cgm_adapter,
    BiomarkerType.HEART_RATE: _activity_adapter,
    BiomarkerType.HRV: _activity_adapter,
    BiomarkerType.STEPS: _activity_adapter,
    BiomarkerType.EXERCISE: _activity_adapter,
    BiomarkerType.ACTIVITY_CALORIES: _activity_adapter,
    BiomarkerType.SLEEP: _sleep_adapter,
    BiomarkerType.GENOTYPE: _genetic_adapter,
    BiomarkerType.LOCATION: _location_adapter,
}

for bt, adapter in _ADAPTER_MAP.items():
    try:
        chars = adapter.get_sampling_characteristics(bt)
        _synchronizer.register_source(bt, chars)
    except ValueError:
        pass

# Register consent revocation callback to sever graph edges
_consent_manager.register_revocation_callback(
    lambda user_id, scope: _graph_embedding.sever_edges_by_consent(scope.value)
)

# ── Seed default sample data on module load ─────────────────────────
# This provides 72 hours of realistic biomarker data so the pipeline
# works out-of-the-box. New data ingested via API extends/overrides it.

import asyncio
import logging as _logging

_seed_logger = _logging.getLogger("biomarker_engine.seed")

def _run_seed() -> None:
    """Seed default data synchronously at import time."""
    from ..seed_data import seed_default_data

    async def _do_seed():
        counts = await seed_default_data(
            cgm_adapter=_cgm_adapter,
            activity_adapter=_activity_adapter,
            sleep_adapter=_sleep_adapter,
            genetic_adapter=_genetic_adapter,
            consent_manager=_consent_manager,
            metabolic_estimator=_metabolic_estimator,
            location_adapter=_location_adapter,
        )
        _seed_logger.info("Default sample data seeded: %s", counts)

    try:
        loop = asyncio.get_running_loop()
        # Inside running loop (e.g. uvicorn startup) — create task
        asyncio.ensure_future(_do_seed())
    except RuntimeError:
        # No running loop — run synchronously
        asyncio.run(_do_seed())

_run_seed()

# ── Helper ──────────────────────────────────────────────────────────

def _parse_biomarker_type(raw: str) -> BiomarkerType:
    """Parse a string into a BiomarkerType enum."""
    try:
        return BiomarkerType(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown biomarker type: {raw}. "
            f"Valid: {[b.value for b in BiomarkerType]}",
        )

# ── Endpoints ───────────────────────────────────────────────────────

@router.post(
    "/ingest",
    response_model=BiomarkerIngestionResult,
    summary="Ingest biomarker readings",
    description=(
        "Accept one or more biomarker readings from any supported source. "
        "Readings are validated, enriched, and stored in the appropriate adapter."
    ),
)
async def ingest_biomarkers(
    batch: BiomarkerBatchIn,
) -> BiomarkerIngestionResult:
    accepted = 0
    rejected = 0
    details: List[Dict[str, Any]] = []

    for r in batch.readings:
        bt = _parse_biomarker_type(r.biomarker_type)
        adapter = _ADAPTER_MAP.get(bt)

        if adapter is None:
            rejected += 1
            details.append({
                "index": accepted + rejected - 1,
                "status": "rejected",
                "reason": f"No adapter for {r.biomarker_type}",
            })
            continue

        reading = BiomarkerReading(
            source_id=r.source_id,
            user_id=r.user_id,
            biomarker_type=bt,
            timestamp=r.timestamp,
            value=r.value,
            unit=r.unit,
            confidence=r.confidence,
            metadata=r.metadata,
        )

        ok = await adapter.push_reading(reading)

        if ok:
            accepted += 1
            # Record meal/exercise/sleep events for metabolic state tracking
            if bt == BiomarkerType.MEAL:
                _metabolic_estimator.record_meal_event(r.user_id, r.timestamp)
            elif bt == BiomarkerType.EXERCISE:
                _metabolic_estimator.record_exercise_event(
                    r.user_id,
                    r.timestamp,
                    r.metadata.get("duration_minutes", 30),
                    r.metadata.get("intensity", "moderate"),
                )
            elif bt == BiomarkerType.SLEEP:
                _metabolic_estimator.record_sleep_event(
                    r.user_id,
                    r.timestamp - timedelta(hours=r.value),
                    r.timestamp,
                    r.metadata.get("quality", 0.7),
                )
        else:
            rejected += 1
            details.append({
                "index": accepted + rejected - 1,
                "status": "rejected",
                "reason": "Adapter validation failed",
            })

    return BiomarkerIngestionResult(
        accepted=accepted, rejected=rejected, details=details
    )

@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Synchronize biomarker streams",
    description=(
        "Align heterogeneous biomarker data onto a unified temporal grid "
        "with physiological lag compensation and confidence-weighted aggregation."
    ),
)
async def synchronize_biomarkers(req: SyncRequest) -> SyncResponse:
    resolution_map = {
        "fine": Resolution.FINE,
        "medium": Resolution.MEDIUM,
        "coarse": Resolution.COARSE,
    }
    resolution = resolution_map.get(req.resolution, Resolution.MEDIUM)

    # Gather readings from all adapters (consent-filtered)
    all_readings: Dict[BiomarkerType, List[BiomarkerReading]] = {}

    # Build set of allowed biomarker types based on consent
    allowed_types: set = set()
    for bt, adapter in _ADAPTER_MAP.items():
        # ── Consent gate: skip biomarker types the user has not consented to ──
        required_scope = BIOMARKER_CONSENT_MAP.get(bt)
        if required_scope and not _consent_manager.check_consent(req.user_id, required_scope):
            continue
        allowed_types.add(bt)
        if bt in adapter.supported_biomarkers:
            try:
                readings = await adapter.fetch_readings(
                    req.user_id, bt, req.start, req.end
                )
                if readings:
                    all_readings[bt] = readings
            except Exception:
                pass

    # Synchronize
    frames = _synchronizer.synchronize(
        all_readings, req.start, req.end, resolution,
        user_id=req.user_id,
    )

    # Convert to output — post-filter signals by consent
    frame_outputs = []
    for f in frames:
        signals_out = {}
        for bt, sig in f.signals.items():
            if bt not in allowed_types:
                continue  # Filter out non-consented signals from interpolation
            signals_out[bt.value] = AlignedSignalOut(
                biomarker_type=bt.value,
                value=round(sig.value, 2),
                confidence=round(sig.confidence, 3),
                sample_count=sig.sample_count,
                lag_compensated=sig.lag_compensated,
            )

        # Include lag computation audit in feature vector
        lag_audit = {}
        for lc in f.lag_computations:
            if lc.base_lag_seconds > 0:
                lag_audit[f"{lc.biomarker_type}_lag_seconds"] = lc.effective_lag_seconds
                lag_audit[f"{lc.biomarker_type}_genetic_modifier"] = lc.genetic_modifier
                lag_audit[f"{lc.biomarker_type}_circadian_modifier"] = lc.circadian_modifier

        features = f.to_feature_vector()
        features.update(lag_audit)

        frame_outputs.append(
            SynchronizedFrameOut(
                window_start=f.window_start,
                window_end=f.window_end,
                resolution=f.resolution.value,
                signals=signals_out,
                frame_confidence=round(f.frame_confidence, 3),
                completeness=round(f.completeness, 3),
                feature_vector=features,
            )
        )

    return SyncResponse(
        user_id=req.user_id,
        frames=frame_outputs,
        total_frames=len(frame_outputs),
    )

@router.post(
    "/nutrient-budget",
    response_model=NutrientBudgetResponse,
    summary="Calculate real-time nutrient budget",
    description=(
        "Compute personalized, real-time nutrient demands via the 5-stage "
        "patent pipeline: Sync → Normalize → Interpolate → State → Nutrient. "
        "Consent filtering at entrance. DP noise at exit."
    ),
)
async def calculate_nutrient_budget(
    req: NutrientBudgetRequest,
) -> NutrientBudgetResponse:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=2)

    # Gather readings from all adapters
    all_readings: Dict[BiomarkerType, List[BiomarkerReading]] = {}
    for bt, adapter in _ADAPTER_MAP.items():
        if bt in adapter.supported_biomarkers:
            try:
                readings = await adapter.fetch_readings(
                    req.user_id, bt, window_start, now
                )
                if readings:
                    all_readings[bt] = readings
            except Exception:
                pass

    # Get genetic modifiers
    genetic_mods = _genetic_adapter.compute_metabolic_modifiers(req.user_id)

    # Get environmental modifiers from location data (if consented)
    env_modifiers = _location_adapter.get_environmental_modifiers(req.user_id)
    if _consent_manager.check_consent(req.user_id, ConsentScope.LOCATION_DATA):
        # Apply location-based adjustments to genetic modifiers
        metabolic_mult = env_modifiers.get("metabolic_multiplier", 1.0)
        hydration_mult = env_modifiers.get("hydration_multiplier", 1.0)
        if metabolic_mult != 1.0:
            genetic_mods["altitude_metabolic_modifier"] = metabolic_mult
        if hydration_mult != 1.0:
            genetic_mods["hydration_environment_modifier"] = hydration_mult

    # Execute the 5-stage pipeline (correct ordering enforced)
    # model_training consent controls whether self-calibration feedback
    # loop is enabled (pipeline learns from user data to improve predictions)
    allow_calibration = _consent_manager.check_consent(
        req.user_id, ConsentScope.MODEL_TRAINING
    )
    pipeline_result = _pipeline.execute(
        user_id=req.user_id,
        readings=all_readings,
        genetic_modifiers=genetic_mods,
        kcal_target=req.kcal_target,
        weight_kg=req.weight_kg,
        consumed_today=req.consumed_today,
        window_start=window_start,
        window_end=now,
    )

    # Self-calibration feedback: only if model_training consent is granted
    if allow_calibration and pipeline_result.calibration_results:
        for cal_result in pipeline_result.calibration_results:
            _pipeline_audit = cal_result  # Allow model to self-improve
    elif not allow_calibration:
        # Discard any calibration data generated during pipeline run
        pipeline_result.calibration_results = []
        pipeline_result.calibration_applied = False

    budget = pipeline_result.budget
    metabolic_state = pipeline_result.metabolic_state

    # Build response
    targets_out = {
        name: NutrientTargetOut(
            name=t.name,
            daily_target=round(t.daily_target, 1),
            consumed_today=round(t.consumed_today, 1),
            remaining=round(t.remaining, 1),
            remaining_pct=round(t.remaining_pct * 100, 1),
            unit=t.unit,
        )
        for name, t in budget.targets.items()
    }

    buckets_out = [
        TimeBucketOut(
            start_hour=b.start_hour,
            end_hour=b.end_hour,
            label=b.label,
            carb_pct=b.carb_pct,
            protein_pct=b.protein_pct,
            fat_pct=b.fat_pct,
            water_pct=b.water_pct,
            rationale=b.rationale,
        )
        for b in budget.time_buckets
    ]

    mods_out = [
        ModificationOut(
            step=m.get("step", ""),
            nutrient=m.get("nutrient", ""),
            old_value=m.get("old_value", 0),
            new_value=m.get("new_value", 0),
            reason=m.get("reason", ""),
        )
        for m in budget.modifications
    ]

    return NutrientBudgetResponse(
        timestamp=budget.timestamp,
        user_id=budget.user_id,
        targets=targets_out,
        time_buckets=buckets_out,
        metabolic_state=(
            metabolic_state.to_context_string() if metabolic_state else "unknown"
        ),
        active_phases=(
            [p.value for p in metabolic_state.active_phases]
            if metabolic_state else []
        ),
        modifications=mods_out,
        conflict_resolutions=[
            ConflictResolutionOut(
                nutrient=cr.nutrient,
                conflict_type=cr.conflict_type,
                genetic_recommended=round(cr.genetic_recommended, 1),
                medical_limit=round(cr.medical_limit, 1),
                resolved_value=round(cr.resolved_value, 1),
                winner=cr.winner,
                loser=cr.loser,
                safety_margin=round(cr.safety_margin, 2),
                constraint_reason=cr.constraint_reason,
                severity=cr.severity,
                resolution_rationale=cr.resolution_rationale,
            )
            for cr in budget.conflict_resolutions
        ],
        next_meal_recommendation=budget.get_next_meal_recommendation(),
        confidence=budget.confidence,
    )

@router.post(
    "/metabolic-state",
    response_model=MetabolicStateOut,
    summary="Get current metabolic state",
)
async def get_metabolic_state(req: SyncRequest) -> MetabolicStateOut:
    """Infer the user's current metabolic state from recent biomarker data."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Ensure 'now' matches frame timestamp awareness
    now_aware = now
    all_readings: Dict[BiomarkerType, List[BiomarkerReading]] = {}
    allowed_types: set = set()
    for bt, adapter in _ADAPTER_MAP.items():
        # ── Consent gate ──
        required_scope = BIOMARKER_CONSENT_MAP.get(bt)
        if required_scope and not _consent_manager.check_consent(req.user_id, required_scope):
            continue
        allowed_types.add(bt)
        if bt in adapter.supported_biomarkers:
            try:
                readings = await adapter.fetch_readings(
                    req.user_id, bt, req.start, req.end
                )
                if readings:
                    all_readings[bt] = readings
            except Exception:
                pass

    frames = _synchronizer.synchronize(
        all_readings, req.start, req.end, Resolution.MEDIUM,
        user_id=req.user_id,
    )

    # Post-filter: remove non-consented signals from interpolated frames
    for f in frames:
        f.signals = {bt: sig for bt, sig in f.signals.items() if bt in allowed_types}

    if not frames or not any(f.signals for f in frames):
        from ..engine.metabolic_state import MetabolicState
        state = MetabolicState(timestamp=now)
    else:
        state = _metabolic_estimator.estimate(req.user_id, frames[-1], now_aware)

    return MetabolicStateOut(
        timestamp=state.timestamp,
        active_phases=[p.value for p in state.active_phases],
        primary_phase=state.primary_phase.value,
        phase_intensities={
            p.value: round(v, 3) for p, v in state.phase_intensities.items()
        },
        hours_since_last_meal=round(state.hours_since_last_meal, 2),
        hours_since_last_exercise=round(state.hours_since_last_exercise, 2),
        insulin_sensitivity_estimate=round(
            state.insulin_sensitivity_estimate, 3
        ),
        nutrient_priority_shifts={
            k: round(v, 3) for k, v in state.nutrient_priority_shifts.items()
        },
        decision_log=state.decision_log,
    )

@router.post(
    "/genetic-profile",
    response_model=GeneticModifiersOut,
    summary="Set genetic profile and compute metabolic modifiers",
)
async def set_genetic_profile(
    profile: GeneticProfileIn,
) -> GeneticModifiersOut:
    """Ingest genetic variant data and compute personalized metabolic modifiers."""
    reading = BiomarkerReading(
        source_id="genetic_profile",
        user_id=profile.user_id,
        biomarker_type=BiomarkerType.GENOTYPE,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        value=len(profile.genotypes),
        unit="variants",
        metadata={"genotypes": profile.genotypes},
    )

    ok = await _genetic_adapter.push_reading(reading)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to store genetic profile",
        )

    modifiers = _genetic_adapter.compute_metabolic_modifiers(profile.user_id)
    _normalizer.set_genetic_modifiers(profile.user_id, modifiers)

    # Also propagate genetic modifiers to the lag model for dynamic lag computation
    if _synchronizer.lag_model:
        _synchronizer.lag_model.set_genetic_modifiers(profile.user_id, modifiers)

    # Compute genetic baseline profile
    baseline = GeneticBaselineCalculator.compute(profile.user_id, modifiers)

    return GeneticModifiersOut(
        user_id=profile.user_id,
        variant_count=len(profile.genotypes),
        modifiers=modifiers,
        genetic_baseline=baseline.to_dict() if baseline else None,
    )

@router.post(
    "/consent",
    response_model=ConsentStatusOut,
    summary="Grant or revoke data consent",
)
async def manage_consent(req: ConsentRequest) -> ConsentStatusOut:
    """Grant or revoke consent for specific data scopes."""
    try:
        scope = ConsentScope(req.scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scope: {req.scope}. "
            f"Valid: {[s.value for s in ConsentScope]}",
        )

    if req.action == "grant":
        expires_at = None
        if req.expires_in_hours:
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                hours=req.expires_in_hours
            )
        _consent_manager.grant_consent(
            req.user_id, scope, req.reason, expires_at
        )
    elif req.action == "revoke":
        _consent_manager.revoke_consent(req.user_id, scope, req.reason)
    else:
# Updated: 2026-02-03
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be 'grant' or 'revoke'",
        )

    state = _consent_manager.get_consent_state(req.user_id)
    # Build policy gate status
    policy_gates = {
        "third_party_sharing": {
            "granted": _consent_manager.check_consent(req.user_id, ConsentScope.THIRD_PARTY_SHARING),
            "controls": "Edge processing — transmitting embeddings off-device",
        },
        "research_use": {
            "granted": _consent_manager.check_consent(req.user_id, ConsentScope.RESEARCH_USE),
            "controls": "Lag comparison analytics — research-grade statistical analysis",
        },
        "model_training": {
            "granted": _consent_manager.check_consent(req.user_id, ConsentScope.MODEL_TRAINING),
            "controls": "Self-calibration feedback — model learns from your data to improve predictions",
        },
        "location_data": {
            "granted": _consent_manager.check_consent(req.user_id, ConsentScope.LOCATION_DATA),
            "controls": "Environmental context — altitude/temperature-based nutrient adjustments",
        },
    }
    return ConsentStatusOut(
        user_id=req.user_id,
        granted_scopes=[s.value for s in state.granted_scopes],
        revoked_scopes=[s.value for s in state.revoked_scopes],
        allowed_biomarkers=sorted(state.get_allowed_biomarkers()),
        policy_gates=policy_gates,
    )

@router.get(
    "/consent/{user_id}",
    response_model=ConsentStatusOut,
    summary="Get consent status",
)
async def get_consent_status(user_id: str) -> ConsentStatusOut:
    state = _consent_manager.get_consent_state(user_id)
    # Build policy gate status
    policy_gates = {
        "third_party_sharing": {
            "granted": _consent_manager.check_consent(user_id, ConsentScope.THIRD_PARTY_SHARING),
            "controls": "Edge processing — transmitting embeddings off-device",
        },
        "research_use": {
            "granted": _consent_manager.check_consent(user_id, ConsentScope.RESEARCH_USE),
            "controls": "Lag comparison analytics — research-grade statistical analysis",
        },
        "model_training": {
            "granted": _consent_manager.check_consent(user_id, ConsentScope.MODEL_TRAINING),
            "controls": "Self-calibration feedback — model learns from your data to improve predictions",
        },
        "location_data": {
            "granted": _consent_manager.check_consent(user_id, ConsentScope.LOCATION_DATA),
            "controls": "Environmental context — altitude/temperature-based nutrient adjustments",
        },
    }
    return ConsentStatusOut(
        user_id=user_id,
        granted_scopes=[s.value for s in state.granted_scopes],
        revoked_scopes=[s.value for s in state.revoked_scopes],
        allowed_biomarkers=sorted(state.get_allowed_biomarkers()),
        policy_gates=policy_gates,
    )

@router.get(
    "/status",
    response_model=PipelineStatusOut,
    summary="Pipeline status",
)
async def get_pipeline_status() -> PipelineStatusOut:
    """Get status of the biomarker processing pipeline."""
    return PipelineStatusOut(
        registered_sources=list(
            set(a.source_id for a in _ADAPTER_MAP.values())
        ),
        registered_biomarker_types=[
            bt.value for bt in _synchronizer._characteristics.keys()
        ],
        users_with_data=len(
            set().union(
                *[
                    set(a._readings_store.keys())
                    for a in [_cgm_adapter, _activity_adapter, _sleep_adapter, _location_adapter]
                    if hasattr(a, "_readings_store")
                ]
            )
        ),
        consent_manager_active=True,
        privacy_engine_active=True,
    )

# ── Edge-Processing / On-Device Privacy Endpoints ──────────────────

@router.post(
    "/lag-comparison",
    summary="Before/After t_sync correction comparison",
    description=(
        "Demonstrates the patent-core advantage of physiological lag "
        "compensation by comparing raw temporal alignment vs. the dynamic "
        "lag model: t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c). "
        "Returns Pearson correlation metrics before and after correction."
    ),
)
async def lag_comparison(req: SyncRequest) -> Dict[str, Any]:
    """Compute Before vs After t_sync correction metrics.

    Requires `research_use` consent since lag analysis generates
    research-grade statistical outputs from personal biomarker data.
    """
    import math as _math

    # ── Policy gate: research_use ──
    if not _consent_manager.check_consent(req.user_id, ConsentScope.RESEARCH_USE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Lag comparison produces research-grade analytics from "
                "your biomarker data. Grant 'research_use' consent to proceed."
            ),
        )

    resolution = Resolution.MEDIUM

    # Gather readings (consent-filtered)
    all_readings: Dict[BiomarkerType, List[BiomarkerReading]] = {}
    allowed_types: set = set()
    for bt, adapter in _ADAPTER_MAP.items():
        # ── Consent gate ──
        required_scope = BIOMARKER_CONSENT_MAP.get(bt)
        if required_scope and not _consent_manager.check_consent(req.user_id, required_scope):
            continue
        allowed_types.add(bt)
        if bt in adapter.supported_biomarkers:
            try:
                readings = await adapter.fetch_readings(
                    req.user_id, bt, req.start, req.end
                )
                if readings:
                    all_readings[bt] = readings
            except Exception:
                pass

    # --- WITH lag correction (normal pipeline) ---
    frames_corrected = _synchronizer.synchronize(
        all_readings, req.start, req.end, resolution,
        user_id=req.user_id,
    )
    # Post-filter: remove non-consented signals
    for f in frames_corrected:
        f.signals = {bt: sig for bt, sig in f.signals.items() if bt in allowed_types}

    # --- WITHOUT lag correction (bypass model) ---
    # Temporarily disable genetic modifiers to get base-only comparison
    original_modifiers = dict(_synchronizer.lag_model._genetic_modifiers)
    _synchronizer.lag_model._genetic_modifiers = {}
    frames_uncorrected = _synchronizer.synchronize(
        all_readings, req.start, req.end, resolution,
        user_id=None,  # No user → no genetic/personal lag
    )
    _synchronizer.lag_model._genetic_modifiers = original_modifiers
    # Post-filter uncorrected frames too
    for f in frames_uncorrected:
        f.signals = {bt: sig for bt, sig in f.signals.items() if bt in allowed_types}

    def _compute_correlation(frames, sig_a_type, sig_b_type):
        """Pearson correlation between two signal types across frames."""
        pairs = []
        for f in frames:
            a = f.signals.get(sig_a_type)
            b = f.signals.get(sig_b_type)
            if a and b and a.confidence > 0.3 and b.confidence > 0.3:
                pairs.append((a.value, b.value))
        if len(pairs) < 3:
            return 0.0
        n = len(pairs)
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx = sum(xs) / n
        my = sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in pairs) / n
        sx = _math.sqrt(sum((x - mx) ** 2 for x in xs) / n) or 1e-9
        sy = _math.sqrt(sum((y - my) ** 2 for y in ys) / n) or 1e-9
        return round(cov / (sx * sy), 4)

    # Compute correlations: glucose↔heart_rate (should improve with lag)
    r_before = _compute_correlation(
        frames_uncorrected, BiomarkerType.GLUCOSE, BiomarkerType.HEART_RATE
    )
    r_after = _compute_correlation(
        frames_corrected, BiomarkerType.GLUCOSE, BiomarkerType.HEART_RATE
    )

    # Collect lag audit from corrected frames
    lag_audits = []
    for f in frames_corrected:
        for lc in f.lag_computations:
            if lc.base_lag_seconds > 0:
                lag_audits.append({
                    "biomarker": lc.biomarker_type,
                    "base_lag_s": lc.base_lag_seconds,
                    "genetic_modifier": round(lc.genetic_modifier, 3),
                    "circadian_modifier": round(lc.circadian_modifier, 3),
                    "effective_lag_s": round(lc.effective_lag_seconds, 1),
                    "hour": lc.hour_of_day,
                    "factors": lc.genetic_factors_used,
                })
                break  # One sample per biomarker is enough

    return {
        "comparison": {
            "signal_pair": "glucose ↔ heart_rate",
            "without_t_sync": {
                "correlation_r": r_before,
                "method": "Raw temporal alignment (no physiological lag compensation)",
            },
            "with_t_sync": {
                "correlation_r": r_after,
                "method": "t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)",
            },
            "improvement": round(abs(r_after) - abs(r_before), 4),
        },
        "lag_formula": "t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)",
        "lag_audit_samples": lag_audits,
        "frames_analyzed": {
            "uncorrected": len(frames_uncorrected),
            "corrected": len(frames_corrected),
        },
    }

@router.get(
    "/edge-manifest",
    summary="Get on-device processing manifest",
    description=(
        "Returns the privacy contract describing what computation happens "
        "on-device vs. what data is transmitted to the server. "
        "This manifest is the foundation of the on-device privacy layer."
    ),
)
async def get_edge_manifest() -> Dict[str, Any]:
    """Return the EdgeProcessor privacy manifest."""
    manifest = _edge_processor.get_manifest()
    return {
        "on_device_operations": manifest.on_device_operations,
        "transmitted_fields": manifest.transmitted_fields,
        "retained_on_device": manifest.retained_fields,
        "privacy_guarantees": manifest.privacy_guarantees,
        "compression_ratio": manifest.compression_ratio,
        "dp_epsilon": _edge_processor.dp_epsilon,
        "embedding_dim": _edge_processor.embedding_dim,
    }

@router.post(
    "/edge-process",
    summary="Simulate on-device edge processing",
    description=(
        "Demonstrates the on-device privacy pipeline: raw biomarker data "
        "is processed locally — only non-invertible embeddings and "
        "differentially-private aggregations leave the device."
    ),
)
async def edge_process(req: SyncRequest) -> Dict[str, Any]:
    """Run edge processing on synchronized frames.

    Requires `third_party_sharing` consent since edge-processed embeddings
    are transmitted off-device to the server.
    """
    # ── Policy gate: third_party_sharing ──
    if not _consent_manager.check_consent(req.user_id, ConsentScope.THIRD_PARTY_SHARING):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Edge processing transmits embeddings off-device. "
                "Grant 'third_party_sharing' consent to proceed."
            ),
        )
    resolution_map = {
        "fine": Resolution.FINE,
        "medium": Resolution.MEDIUM,
        "coarse": Resolution.COARSE,
    }
    resolution = resolution_map.get(req.resolution, Resolution.MEDIUM)

    # Gather readings (consent-filtered)
    all_readings: Dict[BiomarkerType, List[BiomarkerReading]] = {}
    allowed_types: set = set()
    for bt, adapter in _ADAPTER_MAP.items():
        # ── Consent gate ──
        required_scope = BIOMARKER_CONSENT_MAP.get(bt)
        if required_scope and not _consent_manager.check_consent(req.user_id, required_scope):
            continue
        allowed_types.add(bt)
        if bt in adapter.supported_biomarkers:
            try:
                readings = await adapter.fetch_readings(
                    req.user_id, bt, req.start, req.end
                )
                if readings:
                    all_readings[bt] = readings
            except Exception:
                pass

    frames = _synchronizer.synchronize(
        all_readings, req.start, req.end, resolution,
        user_id=req.user_id,
    )
    # Post-filter: remove non-consented signals
    for f in frames:
        f.signals = {bt: sig for bt, sig in f.signals.items() if bt in allowed_types}

    if not frames or not any(f.signals for f in frames):
        return {
            "user_id": req.user_id,
            "edge_outputs": [],
            "manifest": _edge_processor.get_manifest().to_dict(),
            "message": "No frames to process",
        }

    # Get genetic modifiers for hashing
    genetic_mods = _genetic_adapter.compute_metabolic_modifiers(req.user_id)

    # Process each frame through edge processor
    edge_outputs = []
    for frame in frames:
        features = frame.to_feature_vector()
        metabolic_label = "unknown"

        # Attempt to estimate metabolic state
        try:
            state = _metabolic_estimator.estimate(
                req.user_id, frame, frame.window_end
            )
            metabolic_label = state.primary_phase.value
        except Exception:
            pass

        output = _edge_processor.process_frame(
            user_id=req.user_id,
            frame_features=features,
            metabolic_label=metabolic_label,
            genetic_modifiers=genetic_mods,
            raw_reading_count=sum(s.sample_count for s in frame.signals.values()),
        )
        edge_outputs.append({
            "window_start": frame.window_start.isoformat(),
            "window_end": frame.window_end.isoformat(),
            "feature_embedding": output.feature_embedding[:8],  # truncate for display
            "embedding_dim": len(output.feature_embedding),
            "dp_aggregations": output.dp_aggregations,
            "metabolic_label": output.metabolic_label,
            "confidence_scores": output.confidence_scores,
            "genetic_modifier_hash": output.genetic_modifier_hash[:16] + "…",
            "raw_data_retained_on_device": True,
        })

    return {
        "user_id": req.user_id,
        "total_frames_processed": len(edge_outputs),
        "edge_outputs": edge_outputs,
        "privacy_manifest": _edge_processor.get_manifest().to_dict(),
    }

# ── Medical Constraints ─────────────────────────────────────────────

@router.post(
    "/medical-constraints",
    response_model=MedicalConstraintsResponse,
    summary="Set medical/safety constraints",
    description=(
        "Set personalized medical constraints that act as hard boundaries "
        "on nutrient targets. Examples: CKD protein limit, hypertension "
        "sodium cap, warfarin vitamin-K consistency."
    ),
)
async def set_medical_constraints(
    req: MedicalConstraintsRequest,
) -> MedicalConstraintsResponse:
    constraints = [
        MedicalConstraint(
            nutrient=c.nutrient,
            constraint_type=c.constraint_type,
            value=c.value,
            reason=c.reason,
            severity=c.severity,
            source=c.source,
        )
        for c in req.constraints
    ]

    _nutrient_calculator.set_medical_constraints(req.user_id, constraints)

    return MedicalConstraintsResponse(
        user_id=req.user_id,
        active_constraints=[
            MedicalConstraintOut(
                nutrient=c.nutrient,
                constraint_type=c.constraint_type,
                value=c.value,
                reason=c.reason,
                severity=c.severity,
                source=c.source,
            )
            for c in constraints
        ],
        count=len(constraints),
    )

@router.get(
    "/medical-constraints/{user_id}",
    response_model=MedicalConstraintsResponse,
    summary="Get active medical constraints",
)
async def get_medical_constraints(user_id: str) -> MedicalConstraintsResponse:
    constraints = _nutrient_calculator._user_constraints.get(user_id, [])
    return MedicalConstraintsResponse(
        user_id=user_id,
        active_constraints=[
            MedicalConstraintOut(
                nutrient=c.nutrient,
                constraint_type=c.constraint_type,
                value=c.value,
                reason=c.reason,
                severity=c.severity,
                source=c.source,
            )
            for c in constraints
        ],
        count=len(constraints),
    )

# FIXME: potential edge case
