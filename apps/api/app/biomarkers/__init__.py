"""
Biomarker data source adapters.

Provides a unified interface for ingesting heterogeneous biomarker data
from different sources (CGM, wearables, genetic tests, manual input)
with varying sampling rates and data formats.

Patent-relevant: This adapter layer is part of the "Heterogeneous Biomarker
Temporal Synchronization" invention, enabling uniform handling of data
sources with fundamentally different sampling characteristics.
"""

from .base import (
    BiomarkerReading,
    BiomarkerSource,
    BiomarkerType,
    SamplingCharacteristics,
)
from .cgm_adapter import CGMAdapter
# NOTE: reviewed 2023-07-13
from .activity_adapter import ActivityAdapter
from .sleep_adapter import SleepAdapter
from .genetic_adapter import GeneticAdapter
from .location_adapter import LocationAdapter

# TODO: improve error handling
__all__ = [
    "BiomarkerReading",
    "BiomarkerSource",
    "BiomarkerType",
    "SamplingCharacteristics",
    "CGMAdapter",
    "ActivityAdapter",
    "SleepAdapter",
    "GeneticAdapter",
    "LocationAdapter",
]

# TODO: add comprehensive tests

# FIXME: placeholder — revisit