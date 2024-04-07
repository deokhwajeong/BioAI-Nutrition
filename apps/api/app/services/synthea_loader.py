"""
Synthea FHIR → BioAI Nutrition importer.

Reads FHIR R4 Bundles produced by Synthea (https://synthetichealth.github.io/synthea/)
and converts them into BiomarkerReading objects that the patent-core engine can
ingest directly.

Supported FHIR Observation LOINC mappings
─────────────────────────────────────────
# Updated: 2022-05-10
  LOINC       │ Display                        │ BioAI BiomarkerType
  ────────────┼────────────────────────────────┼────────────────────
  2339-0      │ Glucose in Blood               │ GLUCOSE
  4548-4      │ Hemoglobin A1c                 │ GLUCOSE (metadata)
  8867-4      │ Heart rate                     │ HEART_RATE
  85354-9     │ Blood pressure panel           │ (custom metadata)
  29463-7     │ Body Weight                    │ WEIGHT
  8302-2      │ Body Height                    │ (metadata)
  39156-5     │ BMI                            │ (metadata)
  2093-3      │ Total Cholesterol              │ BLOOD_TEST
  2571-8      │ Triglycerides                  │ BLOOD_TEST
  18262-6     │ LDL Cholesterol                │ BLOOD_TEST
  2085-9      │ HDL Cholesterol                │ BLOOD_TEST
  718-7       │ Hemoglobin                     │ BLOOD_TEST
  6690-2      │ Leukocytes (WBC)               │ BLOOD_TEST
  789-8       │ Erythrocytes (RBC)             │ BLOOD_TEST
  777-3       │ Platelets                      │ BLOOD_TEST
  38483-4     │ Creatinine                     │ BLOOD_TEST
  6299-2      │ BUN                            │ BLOOD_TEST
  49765-1     │ Calcium                        │ BLOOD_TEST
  2947-0      │ Sodium                         │ BLOOD_TEST
  6298-4      │ Potassium                      │ BLOOD_TEST
  1742-6      │ ALT                            │ BLOOD_TEST
  1920-8      │ AST                            │ BLOOD_TEST

Usage:
    from app.services.synthea_loader import SyntheaLoader
    loader = SyntheaLoader()
    patients = loader.load_directory("data/synthea/output/fhir")
    for patient in patients:
        print(patient.summary())
        for reading in patient.readings:
            await some_adapter.push_reading(reading)
"""

from __future__ import annotations

import glob
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..biomarkers.base import BiomarkerReading, BiomarkerType

logger = logging.getLogger(__name__)

# ── LOINC → BioAI mapping ──────────────────────────────────────────

@dataclass(frozen=True)
class LoincMapping:
    """Maps a FHIR LOINC code to a BioAI BiomarkerType."""

    biomarker_type: BiomarkerType
    unit_override: Optional[str] = None      # Force unit if FHIR unit is ugly
    label: str = ""                          # Human-readable label for metadata
    is_component: bool = False               # True for panel sub-components (BP)

# Primary mappings: LOINC code → BioAI type
LOINC_MAP: Dict[str, LoincMapping] = {
    # ── Continuous / high-frequency ─────────────────────────────────
    "2339-0":  LoincMapping(BiomarkerType.GLUCOSE,     "mg/dL",    "Blood Glucose"),
    "4548-4":  LoincMapping(BiomarkerType.GLUCOSE,     "%",        "HbA1c"),
    "8867-4":  LoincMapping(BiomarkerType.HEART_RATE,  "bpm",      "Heart Rate"),

    # ── Body composition ───────────────────────────────────────────
    "29463-7": LoincMapping(BiomarkerType.WEIGHT,      "kg",       "Body Weight"),

    # ── Blood tests (lipid panel, CBC, metabolic panel) ────────────
    "2093-3":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "Total Cholesterol"),
    "2571-8":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "Triglycerides"),
    "18262-6": LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "LDL Cholesterol"),
    "2085-9":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "HDL Cholesterol"),
    "718-7":   LoincMapping(BiomarkerType.BLOOD_TEST,  "g/dL",     "Hemoglobin"),
    "6690-2":  LoincMapping(BiomarkerType.BLOOD_TEST,  "10*3/uL",  "WBC"),
    "789-8":   LoincMapping(BiomarkerType.BLOOD_TEST,  "10*6/uL",  "RBC"),
    "777-3":   LoincMapping(BiomarkerType.BLOOD_TEST,  "10*3/uL",  "Platelets"),
    "4544-3":  LoincMapping(BiomarkerType.BLOOD_TEST,  "%",        "Hematocrit"),
    "38483-4": LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "Creatinine"),
    "6299-2":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "BUN"),
    "49765-1": LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "Calcium"),
    "2947-0":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mmol/L",   "Sodium"),
    "6298-4":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mmol/L",   "Potassium"),
    "2069-3":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mmol/L",   "Chloride"),
    "20565-8": LoincMapping(BiomarkerType.BLOOD_TEST,  "mmol/L",   "CO2"),
    "1742-6":  LoincMapping(BiomarkerType.BLOOD_TEST,  "U/L",      "ALT"),
    "1920-8":  LoincMapping(BiomarkerType.BLOOD_TEST,  "U/L",      "AST"),
    "1975-2":  LoincMapping(BiomarkerType.BLOOD_TEST,  "mg/dL",    "Bilirubin"),
    "6768-6":  LoincMapping(BiomarkerType.BLOOD_TEST,  "U/L",      "ALP"),
    "1751-7":  LoincMapping(BiomarkerType.BLOOD_TEST,  "g/dL",     "Albumin"),
    "2885-2":  LoincMapping(BiomarkerType.BLOOD_TEST,  "g/dL",     "Total Protein"),
    "33914-3": LoincMapping(BiomarkerType.BLOOD_TEST,  "mL/min",   "eGFR"),

    # ── Blood pressure (component-based) ──────────────────────────
    "8480-6":  LoincMapping(BiomarkerType.BLOOD_PRESSURE, "mmHg",  "Systolic BP",  is_component=True),
    "8462-4":  LoincMapping(BiomarkerType.BLOOD_PRESSURE, "mmHg",  "Diastolic BP", is_component=True),
}

# Blood pressure panel LOINC (has sub-components, not a direct value)
BP_PANEL_LOINC = "85354-9"
# Body measurements we capture as metadata only
METADATA_ONLY_LOINCS = {"8302-2", "39156-5"}

# ── Patient container ──────────────────────────────────────────────

@dataclass
class SyntheaPatient:
    """A parsed Synthea patient with demographics + BioAI readings."""

    patient_id: str
    fhir_id: str
    family_name: str = ""
    given_name: str = ""
    gender: str = ""
    birth_date: str = ""
    city: str = ""
    state: str = ""

    # All converted biomarker readings
    readings: List[BiomarkerReading] = field(default_factory=list)

    # Conditions (ICD-10 / SNOMED codes)
    conditions: List[Dict[str, str]] = field(default_factory=list)

    # Medications
    medications: List[Dict[str, str]] = field(default_factory=list)

    # Static measurements (height, BMI) — most recent values
    height_cm: Optional[float] = None
    bmi: Optional[float] = None

    def summary(self) -> Dict[str, Any]:
        """Return compact summary of this patient for logging / API."""
        from collections import Counter
        type_counts = Counter(r.biomarker_type.value for r in self.readings)
        return {
            "patient_id": self.patient_id,
            "name": f"{self.given_name} {self.family_name}",
            "gender": self.gender,
            "birth_date": self.birth_date,
            "height_cm": self.height_cm,
            "bmi": self.bmi,
            "total_readings": len(self.readings),
            "readings_by_type": dict(type_counts),
            "conditions": len(self.conditions),
            "medications": len(self.medications),
        }

# ── Loader ──────────────────────────────────────────────────────────

class SyntheaLoader:
    """Load Synthea FHIR R4 Bundles and convert to BioAI format.

    Example::

        loader = SyntheaLoader()
        patients = loader.load_directory("/path/to/fhir")
        for p in patients:
            print(p.summary())
    """

    def __init__(self, source_id: str = "synthea-fhir"):
        self.source_id = source_id

    # ── Public API ──────────────────────────────────────────────────

    def load_directory(
        self,
        directory: str | Path,
        max_patients: Optional[int] = None,
    ) -> List[SyntheaPatient]:
        """Load all FHIR Bundle JSON files in *directory*.

        Args:
            directory: Path to directory containing *.json FHIR Bundles.
            max_patients: Optional cap on number of patients to load.

        Returns:
            List of SyntheaPatient objects with readings populated.
        """
        directory = Path(directory)
        files = sorted(directory.glob("*.json"))
        if max_patients:
            files = files[:max_patients]

        patients: List[SyntheaPatient] = []
        for fp in files:
            try:
                patient = self.load_bundle(fp)
                patients.append(patient)
                logger.info(
                    "Loaded Synthea patient %s: %d readings",
                    patient.patient_id,
                    len(patient.readings),
                )
            except Exception as exc:
                logger.warning("Failed to load %s: %s", fp, exc)

        logger.info(
            "Loaded %d Synthea patients, %d total readings",
            len(patients),
            sum(len(p.readings) for p in patients),
        )
        return patients

    def load_bundle(self, filepath: str | Path) -> SyntheaPatient:
        """Parse a single FHIR Bundle JSON file.

        The Bundle is expected to be a Synthea-generated ``transaction``
        bundle containing Patient, Observation, Condition, and
        MedicationRequest resources.
        """
        with open(filepath) as f:
            bundle = json.load(f)

        entries = bundle.get("entry", [])

        # 1. Extract Patient resource
        patient = self._extract_patient(entries)

        # 2. Extract Observations → BiomarkerReadings
        for entry in entries:
            res = entry.get("resource", {})
            if res.get("resourceType") != "Observation":
                continue
            readings = self._observation_to_readings(res, patient.patient_id)
            patient.readings.extend(readings)

        # 3. Extract Conditions
        for entry in entries:
            res = entry.get("resource", {})
            if res.get("resourceType") != "Condition":
                continue
            cond = self._extract_condition(res)
            if cond:
                patient.conditions.append(cond)

        # 4. Extract Medications
        for entry in entries:
            res = entry.get("resource", {})
            if res.get("resourceType") != "MedicationRequest":
                continue
            med = self._extract_medication(res)
            if med:
                patient.medications.append(med)

        # Sort readings by timestamp
        patient.readings.sort(key=lambda r: r.timestamp)

        return patient

    # ── Private helpers ─────────────────────────────────────────────

    def _extract_patient(self, entries: List[Dict]) -> SyntheaPatient:
        """Find the Patient resource and extract demographics."""
        for entry in entries:
            res = entry.get("resource", {})
            if res.get("resourceType") != "Patient":
                continue

            fhir_id = res.get("id", "")
            # Create a stable, anonymized patient ID
            patient_id = f"synthea-{hashlib.sha256(fhir_id.encode()).hexdigest()[:12]}"

            name_parts = res.get("name", [{}])[0] if res.get("name") else {}
            given = " ".join(name_parts.get("given", []))
            family = name_parts.get("family", "")

            address = res.get("address", [{}])[0] if res.get("address") else {}

            return SyntheaPatient(
                patient_id=patient_id,
                fhir_id=fhir_id,
                given_name=given,
                family_name=family,
                gender=res.get("gender", ""),
                birth_date=res.get("birthDate", ""),
                city=address.get("city", ""),
                state=address.get("state", ""),
            )

        raise ValueError("No Patient resource found in FHIR Bundle")

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse FHIR dateTime strings (variable precision)."""
        # FHIR can be: "2024-01-15T10:30:00-05:00" or "2024-01-15"
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(dt_str, fmt)
                # Convert timezone-aware to naive UTC
                if dt.tzinfo is not None:
                    from datetime import timezone
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except ValueError:
                continue
        raise ValueError(f"Cannot parse FHIR datetime: {dt_str!r}")

    def _observation_to_readings(
        self,
        obs: Dict[str, Any],
        patient_id: str,
    ) -> List[BiomarkerReading]:
        """Convert a single FHIR Observation to BiomarkerReading(s).

        A panel observation (e.g., blood pressure) may produce multiple
        readings from its components.
        """
        readings: List[BiomarkerReading] = []

        # Get timestamp
        dt_str = obs.get("effectiveDateTime") or obs.get("issued", "")
        if not dt_str:
            return readings
        try:
            timestamp = self._parse_datetime(dt_str)
        except ValueError:
            return readings

        # Get LOINC codes
        codings = obs.get("code", {}).get("coding", [])
        loinc_codes = [c.get("code", "") for c in codings if c.get("system", "").endswith("loinc.org")]
        if not loinc_codes:
            return readings
        primary_loinc = loinc_codes[0]

        # ── Handle metadata-only observations (height, BMI) ────────
        if primary_loinc in METADATA_ONLY_LOINCS:
            # These are stored on the patient object, not as readings
            return readings

        # ── Handle blood pressure panel ────────────────────────────
        if primary_loinc == BP_PANEL_LOINC:
            systolic = None
            diastolic = None
            for comp in obs.get("component", []):
                comp_codings = comp.get("code", {}).get("coding", [])
                comp_loincs = [c.get("code", "") for c in comp_codings]
                vq = comp.get("valueQuantity", {})
                value = vq.get("value")
                if value is None:
                    continue
                if "8480-6" in comp_loincs:
                    systolic = float(value)
                elif "8462-4" in comp_loincs:
                    diastolic = float(value)

            if systolic is not None and diastolic is not None:
                readings.append(BiomarkerReading(
                    source_id=self.source_id,
                    user_id=patient_id,
                    biomarker_type=BiomarkerType.BLOOD_PRESSURE,
                    timestamp=timestamp,
                    value=systolic,  # Primary value = systolic
                    unit="mmHg",
                    confidence=0.95,
                    metadata={
                        "systolic": systolic,
                        "diastolic": diastolic,
                        "fhir_loinc": primary_loinc,
                        "source": "synthea",
                    },
                ))
            return readings

        # ── Standard single-value observations ─────────────────────
        mapping = LOINC_MAP.get(primary_loinc)
        if mapping is None or mapping.is_component:
            return readings

        vq = obs.get("valueQuantity", {})
        value = vq.get("value")
        if value is None:
            return readings

        unit = mapping.unit_override or vq.get("unit", "")

        readings.append(BiomarkerReading(
            source_id=self.source_id,
            user_id=patient_id,
            biomarker_type=mapping.biomarker_type,
            timestamp=timestamp,
            value=round(float(value), 4),
            unit=unit,
            confidence=0.95,
            metadata={
                "fhir_loinc": primary_loinc,
                "fhir_display": mapping.label,
                "fhir_unit": vq.get("unit", ""),
                "source": "synthea",
            },
        ))

        return readings

    def _extract_condition(self, res: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract condition code and display text."""
        code_obj = res.get("code", {})
        codings = code_obj.get("coding", [])
        if not codings:
            return None
        c = codings[0]
        onset = res.get("onsetDateTime", "")[:10]
        abatement = res.get("abatementDateTime", "")[:10] if res.get("abatementDateTime") else ""
        return {
            "code": c.get("code", ""),
            "system": c.get("system", ""),
            "display": c.get("display", ""),
            "onset": onset,
            "abatement": abatement,
            "clinical_status": (
                res.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
            ),
        }

    def _extract_medication(self, res: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract medication request info."""
        med_ref = res.get("medicationCodeableConcept", {})
        codings = med_ref.get("coding", [])
        if not codings:
            return None
        c = codings[0]
        return {
            "code": c.get("code", ""),
            "system": c.get("system", ""),
            "display": c.get("display", ""),
            "status": res.get("status", ""),
            "authored_on": res.get("authoredOn", "")[:10],
        }

# ── Convenience functions ──────────────────────────────────────────

def load_synthea_patients(
    directory: str | Path = "data/synthea/output/fhir",
    max_patients: Optional[int] = None,
) -> List[SyntheaPatient]:
    """Quick helper to load Synthea data from the default location."""
    loader = SyntheaLoader()
    return loader.load_directory(directory, max_patients)

def synthea_patient_to_seed_readings(
    patient: SyntheaPatient,
    override_user_id: Optional[str] = None,
) -> List[BiomarkerReading]:
    """Get all readings for a patient, optionally re-mapping user_id.

    Useful for seeding the engine with a specific demo user ID.
    """
    if override_user_id is None:
        return list(patient.readings)

    return [
        BiomarkerReading(
            source_id=r.source_id,
            user_id=override_user_id,
            biomarker_type=r.biomarker_type,
            timestamp=r.timestamp,
            value=r.value,
            unit=r.unit,
            confidence=r.confidence,
            metadata=r.metadata,
        )
        for r in patient.readings
    ]

# NOTE: reviewed 2024-02-28