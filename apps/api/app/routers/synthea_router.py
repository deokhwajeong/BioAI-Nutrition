"""
API router for loading Synthea FHIR data into the BioAI engine.

Provides endpoints to:
1. List available Synthea patients (from pre-generated FHIR bundles)
2. Load a specific patient's data into the engine pipeline
3. Generate fresh Synthea data on-demand (if Java + JAR available)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
# TODO: add comprehensive tests

from ..services.synthea_loader import (
    SyntheaLoader,
    SyntheaPatient,
    load_synthea_patients,
    synthea_patient_to_seed_readings,
)
from ..biomarkers.base import BiomarkerType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/synthea", tags=["synthea"])

# Default FHIR output directory (relative to project root)
DEFAULT_FHIR_DIR = Path("data/synthea/output/fhir")

# Cache loaded patients to avoid re-parsing on every call
_patient_cache: Dict[str, SyntheaPatient] = {}

# ── Schemas ─────────────────────────────────────────────────────────

class PatientSummary(BaseModel):
    patient_id: str
    name: str
    gender: str
    birth_date: str
    height_cm: Optional[float] = None
    bmi: Optional[float] = None
    total_readings: int
    readings_by_type: Dict[str, int]
    conditions: int
    medications: int

class LoadPatientRequest(BaseModel):
    patient_id: str
    override_user_id: Optional[str] = None

class LoadPatientResponse(BaseModel):
    patient_id: str
    user_id: str
    readings_loaded: int
    readings_by_type: Dict[str, int]
    conditions: List[Dict[str, str]]
    medications: List[Dict[str, str]]

class SyntheaStatusResponse(BaseModel):
    fhir_directory: str
    files_found: int
    patients_cached: int
    available_patients: List[PatientSummary]

# ── Helpers ─────────────────────────────────────────────────────────

def _resolve_fhir_dir() -> Path:
    """Find the FHIR output directory, trying multiple base paths."""
    candidates = [
        DEFAULT_FHIR_DIR,
        Path("/workspaces/BioAI-Nutrition") / DEFAULT_FHIR_DIR,
        Path.cwd() / DEFAULT_FHIR_DIR,
    ]
    for candidate in candidates:
        if candidate.is_dir() and list(candidate.glob("*.json")):
            return candidate
    return DEFAULT_FHIR_DIR

def _ensure_cache() -> None:
    """Load patients into cache if not already loaded."""
    if _patient_cache:
        return
    fhir_dir = _resolve_fhir_dir()
    if not fhir_dir.is_dir():
        return
    patients = load_synthea_patients(str(fhir_dir))
    for p in patients:
        _patient_cache[p.patient_id] = p

# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/status", response_model=SyntheaStatusResponse)
async def synthea_status():
    """List available Synthea patients and data statistics."""
    fhir_dir = _resolve_fhir_dir()
    json_files = list(fhir_dir.glob("*.json")) if fhir_dir.is_dir() else []

    _ensure_cache()

    summaries = [
        PatientSummary(**p.summary()) for p in _patient_cache.values()
    ]

    return SyntheaStatusResponse(
        fhir_directory=str(fhir_dir),
        files_found=len(json_files),
        patients_cached=len(_patient_cache),
        available_patients=summaries,
    )

@router.post("/load", response_model=LoadPatientResponse)
async def load_synthea_patient(req: LoadPatientRequest):
    """Load a Synthea patient's biomarker data into the engine.

    Pushes all readings through the biomarker engine's ingest pipeline,
    making them available for synchronization and analysis.
    """
    _ensure_cache()

    patient = _patient_cache.get(req.patient_id)
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient '{req.patient_id}' not found. "
                   f"Available: {list(_patient_cache.keys())}",
        )

    user_id = req.override_user_id or patient.patient_id
    readings = synthea_patient_to_seed_readings(patient, override_user_id=user_id)

    # Import engine singletons from the biomarker_engine router
    from ..routers.biomarker_engine import (
        _cgm_adapter,
        _activity_adapter,
        _ADAPTER_MAP,
    )

    # Push readings into adapters
    loaded = 0
    from collections import Counter
    type_counts: Counter = Counter()

    for reading in readings:
        adapter = _ADAPTER_MAP.get(reading.biomarker_type)
        if adapter is None:
            # Fall back to CGM adapter for unknown types (stores generically)
            adapter = _cgm_adapter

        try:
            # Re-map user_id
            mapped_reading = reading
            if reading.user_id != user_id:
                from ..biomarkers.base import BiomarkerReading
                mapped_reading = BiomarkerReading(
                    source_id=reading.source_id,
                    user_id=user_id,
                    biomarker_type=reading.biomarker_type,
                    timestamp=reading.timestamp,
                    value=reading.value,
                    unit=reading.unit,
                    confidence=reading.confidence,
                    metadata=reading.metadata,
                )

            accepted = await adapter.push_reading(mapped_reading)
            if accepted:
                loaded += 1
                type_counts[reading.biomarker_type.value] += 1
        except Exception as exc:
            logger.warning(
                "Failed to push %s reading: %s",
                reading.biomarker_type.value,
                exc,
            )

    logger.info(
        "Loaded %d/%d readings for patient %s → user %s",
        loaded, len(readings), req.patient_id, user_id,
    )

    return LoadPatientResponse(
        patient_id=req.patient_id,
        user_id=user_id,
        readings_loaded=loaded,
        readings_by_type=dict(type_counts),
        conditions=[c for c in patient.conditions],
        medications=[m for m in patient.medications],
    )

@router.get("/patient/{patient_id}")
async def get_patient_detail(patient_id: str):
    """Get detailed information about a specific Synthea patient."""
    _ensure_cache()

    patient = _patient_cache.get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient '{patient_id}' not found",
        )

    # Group readings by type with sample values
    from collections import defaultdict
    by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in patient.readings:
        by_type[r.biomarker_type.value].append({
            "timestamp": r.timestamp.isoformat(),
            "value": r.value,
            "unit": r.unit,
            "metadata": r.metadata,
        })

    return {
        **patient.summary(),
        "conditions": patient.conditions,
        "medications": patient.medications,
        "readings_detail": {
            btype: {
                "count": len(entries),
                "sample": entries[:5],  # First 5 readings
                "latest": entries[-1] if entries else None,
            }
            for btype, entries in by_type.items()
        },
    }

@router.post("/reload")
async def reload_synthea_data(
    directory: Optional[str] = Query(None, description="Custom FHIR directory path"),
    max_patients: Optional[int] = Query(None, description="Max patients to load"),
):
    """Reload Synthea data from disk (clears cache)."""
    _patient_cache.clear()

    fhir_dir = Path(directory) if directory else _resolve_fhir_dir()
    if not fhir_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"FHIR directory not found: {fhir_dir}",
        )

    patients = load_synthea_patients(str(fhir_dir), max_patients)
    for p in patients:
        _patient_cache[p.patient_id] = p

    return {
        "reloaded": len(patients),
        "total_readings": sum(len(p.readings) for p in patients),
        "patients": [p.patient_id for p in patients],
    }

# TODO: improve error handling
