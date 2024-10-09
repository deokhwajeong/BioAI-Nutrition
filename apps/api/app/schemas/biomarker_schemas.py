"""
Pydantic schemas for the biomarker synchronization engine API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Biomarker Ingestion ──────────────────────────────────────────────

class BiomarkerReadingIn(BaseModel):
    """Input schema for a single biomarker reading."""

    source_id: str = Field(..., description="Device/service identifier")
    user_id: str
    biomarker_type: str = Field(
        ...,
        description="One of: glucose, heart_rate, hrv, steps, exercise, "
        "meal, sleep, genotype, weight, etc.",
    )
    timestamp: datetime
    value: float
    unit: str = ""
    confidence: float = Field(1.0, ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BiomarkerBatchIn(BaseModel):
    """Batch ingestion of multiple readings."""

    readings: List[BiomarkerReadingIn]

class BiomarkerIngestionResult(BaseModel):
    accepted: int
    rejected: int
    details: List[Dict[str, Any]] = []

# ── Synchronization ─────────────────────────────────────────────────

class SyncRequest(BaseModel):
    """Request to synchronize biomarker data for a user."""

    user_id: str
    start: datetime
    end: datetime
    resolution: str = Field(
        "medium",
        description="Temporal resolution: fine (5min), medium (1hr), coarse (24hr)",
    )

class AlignedSignalOut(BaseModel):
    biomarker_type: str
    value: float
    confidence: float
    sample_count: int
    lag_compensated: bool

class SynchronizedFrameOut(BaseModel):
    window_start: datetime
    window_end: datetime
    resolution: str
    signals: Dict[str, AlignedSignalOut]
    frame_confidence: float
    completeness: float
    feature_vector: Dict[str, float]

class SyncResponse(BaseModel):
    user_id: str
    frames: List[SynchronizedFrameOut]
    total_frames: int

# ── Nutrient Budget ─────────────────────────────────────────────────

class NutrientBudgetRequest(BaseModel):
    """Request a real-time nutrient budget calculation."""

    user_id: str
    # Optional overrides
    kcal_target: float = Field(2000, description="Daily calorie target")
    weight_kg: float = Field(70, description="Body weight in kg")
    consumed_today: Dict[str, float] = Field(
        default_factory=dict,
        description="Already consumed nutrients {name: amount}",
    )

class NutrientTargetOut(BaseModel):
    name: str
    daily_target: float
    consumed_today: float
    remaining: float
    remaining_pct: float
    unit: str

class TimeBucketOut(BaseModel):
    start_hour: int
    end_hour: int
    label: str
    carb_pct: float
    protein_pct: float
    fat_pct: float
    water_pct: float
    rationale: str

class ModificationOut(BaseModel):
    step: str
    nutrient: str
    old_value: float
    new_value: float
    reason: str

class ConflictResolutionOut(BaseModel):
    """Audit record of a Safety-First Override conflict resolution."""

    nutrient: str
    conflict_type: str
    genetic_recommended: float
    medical_limit: float
    resolved_value: float
    winner: str
    loser: str
    safety_margin: float
    constraint_reason: str
    severity: str
    resolution_rationale: str

class NutrientBudgetResponse(BaseModel):
    timestamp: datetime
    user_id: str
    targets: Dict[str, NutrientTargetOut]
    time_buckets: List[TimeBucketOut]
    metabolic_state: str
    active_phases: List[str]
    modifications: List[ModificationOut]
    conflict_resolutions: List[ConflictResolutionOut] = []
    next_meal_recommendation: Dict[str, float]
    confidence: float

# ── Metabolic State ─────────────────────────────────────────────────

class MetabolicStateOut(BaseModel):
    timestamp: datetime
    active_phases: List[str]
    primary_phase: str
    phase_intensities: Dict[str, float]
    hours_since_last_meal: float
    hours_since_last_exercise: float
    insulin_sensitivity_estimate: float
    nutrient_priority_shifts: Dict[str, float]
    decision_log: List[str] = []

# ── Consent ─────────────────────────────────────────────────────────

class ConsentRequest(BaseModel):
    user_id: str
    scope: str
    action: str = Field(
        ..., description="'grant' or 'revoke'"
    )
    reason: str = ""
    expires_in_hours: Optional[float] = None

class ConsentStatusOut(BaseModel):
    user_id: str
    granted_scopes: List[str]
    revoked_scopes: List[str]
    allowed_biomarkers: List[str]
    policy_gates: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Status of policy-level consent gates that control specific "
            "system features. Shows which gates are open/closed and what "
            "each gate controls."
        ),
    )

# ── Genetic Profile ─────────────────────────────────────────────────

class GeneticProfileIn(BaseModel):
    """Input for genetic variant data."""

    user_id: str
    genotypes: Dict[str, str] = Field(
        ...,
        description="SNP ID → genotype mapping, e.g. {'rs1801133': 'CT'}",
    )

class GeneticModifiersOut(BaseModel):
    user_id: str
    variant_count: int
    modifiers: Dict[str, float]
    genetic_baseline: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Genotype-adjusted reference ranges for each biomarker, "
            "enabling z-score normalization relative to the user's "
            "genetic baseline rather than population averages."
        ),
    )

# ── Pipeline Status ─────────────────────────────────────────────────

class PipelineStatusOut(BaseModel):
    """Status of the biomarker processing pipeline."""

    registered_sources: List[str]
    registered_biomarker_types: List[str]
    users_with_data: int
    consent_manager_active: bool
    privacy_engine_active: bool

# ── Medical Constraints ─────────────────────────────────────────────

class MedicalConstraintIn(BaseModel):
    """Input schema for a single medical or safety constraint."""

    nutrient: str = Field(
        ..., description="Target nutrient key, e.g. 'protein_g', 'sodium_mg'"
    )
    constraint_type: str = Field(
        ..., description="One of: 'max', 'min', 'range', 'consistency'"
    )
    value: float = Field(
        ..., description="Constraint value (e.g. max grams per day)"
    )
    reason: str = Field(
        ..., description="Medical reason for the constraint"
    )
    severity: str = Field(
        "warning", description="'warning' or 'critical'"
    )
    source: str = Field(
        "user_reported",
        description="'user_reported', 'medical_record', or 'genetic'",
    )

class MedicalConstraintsRequest(BaseModel):
    """Request to set medical constraints for a user."""

    user_id: str
    constraints: List[MedicalConstraintIn]

class MedicalConstraintOut(BaseModel):
    nutrient: str
    constraint_type: str
    value: float
    reason: str
    severity: str
    source: str

class MedicalConstraintsResponse(BaseModel):
    user_id: str
    active_constraints: List[MedicalConstraintOut]
    count: int

# Updated: 2023-01-04

# TODO: add comprehensive tests
# TODO: optimize this section
# NOTE: reviewed 2024-10-09