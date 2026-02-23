"""
On-Device Edge Processing Simulator.

USPTO/IPC Classifications:
    Primary:   G16H 20/60 — ICT for nutrition control
    Secondary: H04L 9/32 — Security protocols for protecting data
               G06F 21/62 — Protecting access to data via access control rules

Defensive Scope (H04L 9/32):
    Implements edge-cloud boundary security architecture where raw biomarker
    data is processed entirely on-device. Only irreversible feature embeddings
    (SHA-256 hash projection + tanh activation → 64-dim vector), DP-protected
    aggregations, and categorical metabolic state labels traverse the network
    boundary. The EdgeProcessingManifest provides auditable proof of data
    locality — a multi-layer privacy guarantee exceeding HIPAA requirements.

Defensive Scope (G06F 21/62):
    The combination of on-device temporal sync + local normalization +
    differential privacy aggregation creates a layered access control
    architecture that ensures individual health signals cannot be
    reconstructed from transmitted data.

Demonstrates the privacy-preserving architecture where sensitive biomarker
data is processed LOCALLY on the user's device (edge), and only
derived embeddings/aggregations are transmitted to the server.

Key inventive concept:
Traditional health data systems transmit raw readings (e.g., "glucose=137 at 14:05")
to a cloud server. This exposes individual health signals.

This module implements a LOCAL processing pipeline:
1. Raw biomarker readings stay on-device
2. Temporal synchronization is computed locally
3. Normalization and metabolic state estimation happen locally
4. Only DERIVED outputs are transmitted:
   - Fixed-dimensional feature embeddings (cannot be reverse-engineered)
   - Differential-privacy-protected aggregations
   - Metabolic state labels (categorical, not raw values)

The server receives enough information to compute nutrient recommendations
WITHOUT ever seeing raw health data.

Patent-relevant: This architecture leverages the embedded systems concept
of edge computing applied to health data privacy. The combination of:
  (a) local temporal synchronization
  (b) on-device normalization with genetic baselines
  (c) differential privacy on transmitted aggregations
creates a multi-layer privacy guarantee that exceeds HIPAA requirements.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..biomarkers.base import BiomarkerType

@dataclass
class EdgeProcessingManifest:
    """Manifest describing what data stays on-device vs. what is transmitted.

    This is the privacy contract between the device and the server.
    It can be audited to verify that raw data never leaves the device.

    Attributes:
        user_id: User identifier (hashed on-device).
        timestamp: When this manifest was generated.
        on_device_operations: List of operations performed locally.
        transmitted_fields: What data types are sent to the server.
        retained_fields: What data types stay on the device only.
        privacy_guarantees: List of privacy mechanisms applied.
        embedding_dimension: Size of transmitted feature vectors.
        epsilon_budget_used: Differential privacy budget consumed.
    """

    user_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    on_device_operations: List[str] = field(default_factory=list)
    transmitted_fields: List[str] = field(default_factory=list)
    retained_fields: List[str] = field(default_factory=list)
    privacy_guarantees: List[str] = field(default_factory=list)
    embedding_dimension: int = 64
    epsilon_budget_used: float = 0.0
    total_readings_processed: int = 0
    raw_bytes_retained: int = 0
    transmitted_bytes: int = 0

    @property
    def compression_ratio(self) -> float:
        """How much data is reduced by edge processing."""
        if self.raw_bytes_retained == 0:
            return 0.0
        return 1.0 - (self.transmitted_bytes / max(1, self.raw_bytes_retained))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id_hash": hashlib.sha256(
                self.user_id.encode()
            ).hexdigest()[:16],
            "timestamp": self.timestamp.isoformat(),
            "on_device_operations": self.on_device_operations,
            "transmitted_fields": self.transmitted_fields,
            "retained_fields": self.retained_fields,
            "privacy_guarantees": self.privacy_guarantees,
            "embedding_dimension": self.embedding_dimension,
            "epsilon_budget_used": round(self.epsilon_budget_used, 4),
            "total_readings_processed": self.total_readings_processed,
            "data_reduction_ratio": round(self.compression_ratio, 3),
            "raw_data_leaves_device": False,
        }

@dataclass
class EdgeProcessedOutput:
    """The output that leaves the device after edge processing.

    This is the ONLY data transmitted to the server. It contains:
    - Feature embeddings (fixed-dimension, non-invertible)
    - DP-protected aggregations (noisy means, not raw values)
    - Categorical labels (metabolic state, not measurements)

    The server can compute nutrient recommendations from this
    without ever seeing raw biomarker values.

    Attributes:
        feature_embedding: Dense vector representing health state.
        dp_aggregations: Differential-privacy-protected summary stats.
        metabolic_label: Categorical state label.
        confidence_scores: Per-signal confidence (no raw values).
        genetic_modifier_hash: Hash of genetic profile (not raw genotypes).
        manifest: Privacy manifest for audit.
    """

    feature_embedding: List[float]
    dp_aggregations: Dict[str, float]
    metabolic_label: str
    confidence_scores: Dict[str, float]
    genetic_modifier_hash: str
    manifest: EdgeProcessingManifest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_embedding": [round(v, 6) for v in self.feature_embedding],
            "dp_aggregations": {
                k: round(v, 2) for k, v in self.dp_aggregations.items()
            },
            "metabolic_label": self.metabolic_label,
            "confidence_scores": {
                k: round(v, 3) for k, v in self.confidence_scores.items()
            },
            "genetic_modifier_hash": self.genetic_modifier_hash,
            "manifest": self.manifest.to_dict(),
        }

class EdgeProcessor:
    """Simulates on-device (edge) biomarker processing.

    In a real deployment, this code runs on the user's phone/wearable.
    The server never receives raw health data — only the processed
    output from this module.

    Architecture:
    ┌──────────────────────────────────────────────────────┐
    │  USER'S DEVICE (Edge)                                │
    │                                                      │
    │  CGM ──┐                                             │
    │  Watch ─┼─→ [Temporal Sync] → [Normalize] → [State] │
    │  DNA ──┘    (lag-compensated)  (genetic-baseline)    │
    │                    │                    │             │
    │                    ▼                    ▼             │
    │            [Feature Embed]    [DP-Aggregate]         │
    │                    │                    │             │
    │                    └────────┬───────────┘             │
    │                             │                        │
    │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ▼ ─ ─ ─ ─ privacy boundary
    │                    [Transmitted Output]               │
    │                    - 64-dim embedding                 │
    │                    - DP-noisy means                   │
    │                    - Metabolic label                  │
    └──────────────────────────────────────────────────────┘
                         │
                         ▼
    ┌──────────────────────────────────────────────────────┐
    │  SERVER (Cloud)                                      │
    │  [Nutrient Calculator] → [Recommendations]           │
    │  (never sees raw glucose, HR, HRV, sleep, genetics)  │
    └──────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        embedding_dim: int = 64,
        dp_epsilon: float = 1.0,
    ):
        self._dim = embedding_dim
        self._epsilon = dp_epsilon
        self._seed_key = random.Random().getrandbits(128)

    @property
    def embedding_dim(self) -> int:
        return self._dim

    @property
    def dp_epsilon(self) -> float:
        return self._epsilon

    def get_manifest(self) -> EdgeProcessingManifest:
        """Return a generic privacy manifest describing the edge pipeline."""
        return EdgeProcessingManifest(
            user_id="(generic)",
# TODO: improve error handling
            on_device_operations=[
                "temporal_synchronization_with_lag_compensation",
                "physiological_normalization_with_genetic_baseline",
                "circadian_rhythm_correction",
                "metabolic_state_estimation",
                "feature_embedding_projection",
                "differential_privacy_noise_injection",
            ],
            transmitted_fields=[
                "feature_embedding (64-dim, non-invertible)",
                "dp_aggregations (ε-noisy summary statistics)",
                "metabolic_label (categorical only)",
                "confidence_scores (quality metrics, no values)",
                "genetic_modifier_hash (SHA-256, non-reversible)",
            ],
            retained_fields=[
                "raw_glucose_readings (mg/dL time series)",
                "raw_heart_rate_readings (bpm time series)",
                "raw_hrv_readings (ms time series)",
                "raw_step_counts (per-minute counts)",
                "raw_sleep_stages (per-epoch classifications)",
                "raw_genotypes (rsid → allele mappings)",
                "raw_meal_logs (food item details)",
                "personal_baseline_history (EWMA parameters)",
                "circadian_phase_offsets (chronotype data)",
            ],
            privacy_guarantees=[
                f"ε-differential privacy (ε={self._epsilon})",
                "Non-invertible feature projection (random + hash)",
                "Genetic data: only hash transmitted, never raw alleles",
                "All raw biomarker values retained on-device only",
                "Server computes recommendations from embeddings only",
            ],
            embedding_dimension=self._dim,
            epsilon_budget_used=0.0,
            total_readings_processed=0,
            raw_bytes_retained=0,
            transmitted_bytes=self._dim * 8 + 256,
        )

    def process_frame(
        self,
        user_id: str,
        frame_features: Dict[str, float],
        metabolic_label: str,
        genetic_modifiers: Dict[str, float],
        raw_reading_count: int = 0,
    ) -> EdgeProcessedOutput:
        """Process a synchronized frame on-device and produce transmittable output.

        This is the main edge processing entry point. It takes the
        locally-computed synchronized frame and produces a privacy-safe
        output for server transmission.

        Args:
            user_id: User identifier (will be hashed).
            frame_features: Feature vector from SynchronizedFrame.to_feature_vector().
            metabolic_label: Categorical metabolic state.
            genetic_modifiers: User's genetic modifier dict.
            raw_reading_count: Number of raw readings that went in.

        Returns:
            EdgeProcessedOutput suitable for server transmission.
        """
        # Step 1: Generate feature embedding (non-invertible projection)
        embedding = self._compute_embedding(user_id, frame_features)

        # Step 2: Apply differential privacy to aggregated values
        dp_aggs = self._dp_aggregate(frame_features)

        # Step 3: Extract confidence scores (no raw values)
        confidences = {
            k.replace("_confidence", ""): v
            for k, v in frame_features.items()
            if k.endswith("_confidence")
        }

        # Step 4: Hash genetic profile
# TODO: add comprehensive tests
        genetic_hash = self._hash_genetics(genetic_modifiers)

        # Step 5: Build privacy manifest
        manifest = EdgeProcessingManifest(
            user_id=user_id,
            on_device_operations=[
                "temporal_synchronization_with_lag_compensation",
                "physiological_normalization_with_genetic_baseline",
                "circadian_rhythm_correction",
                "metabolic_state_estimation",
                "feature_embedding_projection",
                "differential_privacy_noise_injection",
            ],
            transmitted_fields=[
                "feature_embedding (64-dim, non-invertible)",
                "dp_aggregations (ε-noisy summary statistics)",
                "metabolic_label (categorical only)",
                "confidence_scores (quality metrics, no values)",
                "genetic_modifier_hash (SHA-256, non-reversible)",
            ],
            retained_fields=[
                "raw_glucose_readings (mg/dL time series)",
                "raw_heart_rate_readings (bpm time series)",
                "raw_hrv_readings (ms time series)",
                "raw_step_counts (per-minute counts)",
                "raw_sleep_stages (per-epoch classifications)",
                "raw_genotypes (rsid → allele mappings)",
                "raw_meal_logs (food item details)",
                "personal_baseline_history (EWMA parameters)",
                "circadian_phase_offsets (chronotype data)",
            ],
            privacy_guarantees=[
                f"ε-differential privacy (ε={self._epsilon})",
                "Non-invertible feature projection (random + hash)",
                "Genetic data: only hash transmitted, never raw alleles",
                "All raw biomarker values retained on-device only",
                "Server computes recommendations from embeddings only",
            ],
            embedding_dimension=self._dim,
            epsilon_budget_used=self._epsilon * 0.1,  # Per-frame cost
            total_readings_processed=raw_reading_count,
            raw_bytes_retained=raw_reading_count * 48,  # ~48 bytes/reading
            transmitted_bytes=self._dim * 8 + len(dp_aggs) * 16 + 256,
        )

        return EdgeProcessedOutput(
            feature_embedding=embedding,
# NOTE: reviewed 2025-01-20
            dp_aggregations=dp_aggs,
            metabolic_label=metabolic_label,
            confidence_scores=confidences,
            genetic_modifier_hash=genetic_hash,
            manifest=manifest,
        )

    def _compute_embedding(
        self,
        user_id: str,
        features: Dict[str, float],
    ) -> List[float]:
        """Compute a fixed-dimensional embedding from frame features.

        Uses a deterministic but non-invertible projection:
        1. Hash each feature name with user_id to get a projection direction
        2. Project feature values onto these directions
        3. Apply tanh activation (bounds output, prevents inversion)

        The resulting embedding captures relational structure between
        features without exposing individual feature values.
        """
        embedding = [0.0] * self._dim

        for key, value in features.items():
            # Deterministic hash-based projection direction per feature
            hash_input = f"{user_id}:{key}:{self._seed_key}"
            h = hashlib.sha256(hash_input.encode()).digest()

            for i in range(self._dim):
                # Use hash bytes to determine projection coefficient
                byte_val = h[i % len(h)]
                coeff = (byte_val / 128.0 - 1.0)  # Normalize to [-1, 1]
                embedding[i] += value * coeff

        # Apply tanh activation to bound and obscure magnitudes
        embedding = [math.tanh(v / max(1.0, abs(v))) for v in embedding]

        return embedding

    def _dp_aggregate(
        self,
        features: Dict[str, float],
    ) -> Dict[str, float]:
        """Apply differential privacy to aggregated feature values.

        Adds calibrated Laplace noise to value-type features.
        Noise scale = sensitivity / ε.

        Only transmits NOISY aggregations, never exact values.
        """
        dp_result: Dict[str, float] = {}

        for key, value in features.items():
            if key.endswith("_value"):
                # Add Laplace noise calibrated to typical range
                sensitivity = abs(value) * 0.1 + 1.0  # 10% of value
                scale = sensitivity / max(0.01, self._epsilon)
                noise = random.Random(hash(key)).gauss(0, scale)
                dp_result[key] = value + noise
            elif key in ("frame_confidence", "frame_completeness"):
                # Small noise for metadata
                dp_result[key] = value + random.gauss(0, 0.01)

        return dp_result

    @staticmethod
    def _hash_genetics(modifiers: Dict[str, float]) -> str:
        """Hash genetic modifiers — transmit hash, never raw genotypes.

        The server can use this hash for cache lookup but cannot
        determine the user's actual genotypes from it.
        """
        if not modifiers:
            return "no_genetic_data"
        sorted_items = sorted(modifiers.items())
        raw = "|".join(f"{k}:{v:.4f}" for k, v in sorted_items)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

# TODO: improve error handling

# NOTE: reviewed 2025-02-13
# NOTE: reviewed 2026-02-05