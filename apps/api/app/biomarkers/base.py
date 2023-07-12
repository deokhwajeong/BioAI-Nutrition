"""
Base interfaces for biomarker data adapters.

Defines the core abstractions for heterogeneous biomarker data ingestion:
- BiomarkerType: Classification of biomarker data categories
- SamplingCharacteristics: Metadata about each source's temporal properties
- BiomarkerReading: Unified data point representation
- BiomarkerSource: Abstract adapter interface

Patent-relevant: The SamplingCharacteristics metadata enables the Temporal
Synchronization Engine to automatically determine how to align data from
sources with fundamentally different temporal behaviors (continuous high-freq
CGM vs. sporadic meal events vs. static genetic data).
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class BiomarkerType(str, Enum):
    """Classification of biomarker data categories."""

    # Continuous high-frequency signals
    GLUCOSE = "glucose"            # CGM: ~5min intervals
    HEART_RATE = "heart_rate"      # Wearable: ~1s–1min
    HRV = "hrv"                    # Heart Rate Variability

    # Activity signals (variable frequency)
    STEPS = "steps"                # Pedometer: aggregated per minute/hour
    ACTIVITY_CALORIES = "activity_calories"
    EXERCISE = "exercise"          # Discrete exercise sessions

    # Discrete event-driven signals
    MEAL = "meal"                  # User-logged meals (irregular)
    WATER_INTAKE = "water_intake"
    MEDICATION = "medication"

    # Low-frequency periodic signals
    SLEEP = "sleep"                # 1x/day summary
    WEIGHT = "weight"              # Manual: days–weeks
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_TEST = "blood_test"      # Months apart

    # Static / quasi-static signals
    GENOTYPE = "genotype"          # One-time genetic test
    ALLERGY = "allergy"            # Rarely changes
    MEDICAL_CONDITION = "medical_condition"

    # Context signals
    LOCATION = "location"          # GPS / geofence (event-driven)


class TemporalBehavior(str, Enum):
    """How the biomarker behaves over time.

    This classification drives the synchronization strategy:
    - CONTINUOUS: Interpolate between readings (e.g., glucose)
    - EVENT: Point-in-time occurrences, no interpolation (e.g., meals)
    - PERIODIC: Regular but infrequent, trend-based fill (e.g., sleep)
    - STATIC: Does not change over time (e.g., genotype)
    """

    CONTINUOUS = "continuous"
    EVENT = "event"
    PERIODIC = "periodic"
    STATIC = "static"


@dataclass(frozen=True)
class SamplingCharacteristics:
    """Metadata describing the temporal properties of a biomarker source.

    Patent-relevant: This structure enables the synchronization engine to
    automatically select the appropriate alignment strategy per source.

    Attributes:
        typical_interval: Expected time between consecutive readings.
        min_interval: Minimum possible interval (hardware limit).
        max_gap_before_stale: After this gap, data is considered stale
            and requires special handling (circadian interpolation).
        temporal_behavior: How the signal behaves between observations.
        physiological_lag: Delay between cause and observable effect.
            E.g., meal → blood glucose peak = 30-120 min.
        circadian_sensitivity: 0.0-1.0, how much the signal varies
            with time of day. High for cortisol, low for genotype.
        noise_floor: Expected measurement noise (used in normalization).
    """

    typical_interval: timedelta
    min_interval: timedelta
    max_gap_before_stale: timedelta
    temporal_behavior: TemporalBehavior
    physiological_lag: timedelta = field(default_factory=lambda: timedelta(0))
    circadian_sensitivity: float = 0.0
    noise_floor: float = 0.0


@dataclass
class BiomarkerReading:
    """A single unified biomarker measurement.

    All heterogeneous data sources are normalized into this common format
    before entering the synchronization engine.

    Attributes:
        source_id: Identifier of the data source (device/service).
        user_id: Anonymized user identifier.
        biomarker_type: What is being measured.
        timestamp: When the reading was taken (UTC).
        value: Primary numeric value (e.g., glucose mg/dL).
        unit: Unit of measurement.
        confidence: 0.0-1.0, reliability of this reading.
        metadata: Source-specific additional data.
        raw_hash: SHA-256 hash of the original raw data for audit.
    """

    source_id: str
    user_id: str
    biomarker_type: BiomarkerType
    timestamp: datetime
    value: float
    unit: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_hash: str = ""

    def __post_init__(self):
        if not self.raw_hash:
            raw = f"{self.source_id}:{self.timestamp.isoformat()}:{self.value}"
            self.raw_hash = hashlib.sha256(raw.encode()).hexdigest()


class BiomarkerSource(ABC):
    """Abstract base class for biomarker data source adapters.

    Each concrete adapter handles:
    1. Connection to the data source (API, file, device)
    2. Parsing source-specific data formats
    3. Conversion to unified BiomarkerReading objects
    4. Reporting its SamplingCharacteristics for synchronization

    Patent-relevant: The adapter pattern with SamplingCharacteristics
    self-declaration enables plug-and-play integration of new data
    sources without modifying the synchronization engine.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this data source."""
        ...

    @property
    @abstractmethod
    def supported_biomarkers(self) -> List[BiomarkerType]:
        """List of biomarker types this source provides."""
        ...

    @abstractmethod
    def get_sampling_characteristics(
        self, biomarker_type: BiomarkerType
    ) -> SamplingCharacteristics:
        """Return temporal metadata for a given biomarker type.

        This is used by the Temporal Synchronization Engine to determine
        how to align and interpolate data from this source.
        """
        ...

    @abstractmethod
    async def fetch_readings(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        start: datetime,
        end: datetime,
    ) -> List[BiomarkerReading]:
        """Fetch readings from this source within a time window.

        Args:
            user_id: The user whose data to fetch.
            biomarker_type: Which biomarker to retrieve.
            start: Start of the time window (inclusive, UTC).
            end: End of the time window (exclusive, UTC).

        Returns:
            List of BiomarkerReading objects, sorted by timestamp.
        """
        ...

    @abstractmethod
    async def push_reading(self, reading: BiomarkerReading) -> bool:
        """Ingest a single reading from an external push source.

        Returns:
            True if the reading was accepted, False if rejected
            (e.g., duplicate, out-of-range, failed validation).
        """
        ...

    def validate_reading(self, reading: BiomarkerReading) -> bool:
        """Basic validation of a reading.

        Override in subclasses for source-specific validation.
        """
        if reading.value is None:
            return False
        if reading.confidence < 0 or reading.confidence > 1:
            return False
        if reading.biomarker_type not in self.supported_biomarkers:
            return False
        return True

# FIXME: potential edge case
