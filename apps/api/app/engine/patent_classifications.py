"""
USPTO/IPC Patent Classification Registry.

Maps each module in this system to its corresponding USPTO/IPC classification
codes, providing a centralized reference for patent prosecution and prior
art analysis.

Strategic Patent Classification Architecture
=============================================

Primary Classification:
    G16H 20/60 — ICT specially adapted for therapies or health-improving
                  plans, e.g. for handling prescriptions, for steering
                  therapy or for monitoring patient compliance relating
                  to nutrition control

Secondary Classifications:

    A. Data Processing & Synchronization
    ────────────────────────────────────
    G06F 16/27  Query processing; Data synchronization
                → Temporal Synchronization Engine: aligns heterogeneous
                  biomarker streams onto a unified temporal grid using
                  physiological-lag-aware time windows.

    G06F 11/34  Performance analysis; Monitoring
                → Adaptive Self-Calibration: continuously monitors
                  prediction accuracy (peak timing) and back-propagates
                  corrections to improve the lag model over time.

    B. Artificial Intelligence & Self-Learning
    ───────────────────────────────────────────
    G06N 20/00  Machine learning
                → Error back-propagation loop: decomposes prediction
                  error ε into three channels (δ_base, δ_circ, κ_genetic)
                  and updates each via adaptive EMA learning.

    G06N 7/01   Probabilistic graphical models; Bayesian networks
                → Gaussian kernel weighted aggregation in temporal sync;
                  confidence-weighted probabilistic data estimation for
                  biomarker fusion under uncertainty.

    C. Privacy & Security
    ─────────────────────
    G06F 21/62  Protecting access to data via access control rules
                → Differential Privacy with sensitivity-tiered ε
                  allocation; dynamic consent management with real-time
                  consent propagation and graph edge severance.

    H04L 9/32   Security protocols for protecting data
                → Edge-cloud boundary architecture: raw data never
                  leaves device; only irreversible feature embeddings,
                  DP-protected aggregations, and categorical labels
                  are transmitted. Multi-layer privacy guarantee.

Technology Center (TC) Strategy
===============================
By pairing G16H 20/60 (health) with G06F/G06N (computing/AI)
classifications, the application emphasizes that this is a
**data processing system innovation** — not merely health advice.
This positioning is critical for:
  • Avoiding § 101 Abstract Idea rejections
  • Targeting TC 2100/3600 (Computer Architecture & Software)
    rather than TC 1600 (Biotechnology)
  • Strengthening claims around algorithmic novelty
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PatentClassification(Enum):
    """USPTO/IPC classification codes relevant to this system."""

    # ── Primary ──
    G16H_20_60 = "G16H 20/60"

    # ── A. Data Processing & Synchronization ──
    G06F_16_27 = "G06F 16/27"
    G06F_11_34 = "G06F 11/34"

    # ── B. AI & Self-Learning ──
    G06N_20_00 = "G06N 20/00"
    G06N_7_01 = "G06N 7/01"

    # ── C. Privacy & Security ──
    G06F_21_62 = "G06F 21/62"
    H04L_9_32 = "H04L 9/32"


@dataclass(frozen=True)
class ClassificationEntry:
    """Links a patent classification to specific system modules."""

    code: PatentClassification
    title: str
    description: str
    modules: List[str]
    claim_keywords: List[str]
    defensive_rationale: str


# ═══════════════════════════════════════════════════════════════════════
# Complete Patent Classification Registry
# ═══════════════════════════════════════════════════════════════════════

PATENT_CLASSIFICATION_REGISTRY: Dict[PatentClassification, ClassificationEntry] = {

    PatentClassification.G16H_20_60: ClassificationEntry(
        code=PatentClassification.G16H_20_60,
        title="ICT for therapies — nutrition control",
        description=(
            "Primary classification covering the overall system: "
            "personalized, real-time nutrient demand computation "
            "integrating multi-source biomarker data."
        ),
        modules=[
            "engine.pipeline.NutritionPipeline",
            "engine.nutrient_calculator.NutrientDemandCalculator",
            "services.recommender",
        ],
        claim_keywords=[
            "personalized nutrition", "real-time nutrient demand",
            "multi-source biomarker integration", "dietary recommendation",
        ],
        defensive_rationale=(
            "Establishes the domain scope. Paired with G06F/G06N codes "
            "to emphasize computational innovation over mere health advice."
        ),
    ),

    PatentClassification.G06F_16_27: ClassificationEntry(
        code=PatentClassification.G06F_16_27,
        title="Query processing; Data synchronization",
        description=(
            "Covers the Temporal Synchronization Engine that aligns "
            "heterogeneous biomarker streams with different sampling rates "
            "onto a unified multi-resolution temporal grid using "
            "physiological-lag-aware time windows. Key formula: "
            "t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)"
        ),
        modules=[
            "engine.temporal_sync.TemporalSynchronizer",
            "engine.temporal_sync.PhysiologicalLagModel",
        ],
        claim_keywords=[
            "temporal synchronization", "physiological lag compensation",
            "multi-resolution temporal grid", "confidence-weighted aggregation",
            "Gaussian kernel weighted average", "staleness decay",
        ],
        defensive_rationale=(
            "Defends the novelty of biologically-motivated data synchronization. "
            "Unlike conventional time-series resampling, this approach uses "
            "physiological lag models with genetic and circadian modifiers."
        ),
    ),

    PatentClassification.G06F_11_34: ClassificationEntry(
        code=PatentClassification.G06F_11_34,
        title="Performance analysis; Monitoring",
        description=(
            "Covers the Adaptive Self-Calibration Engine that monitors "
            "system prediction accuracy by comparing predicted vs. actual "
            "biomarker peak times, computing convergence scores, and "
            "triggering re-calibration when accuracy degrades."
        ),
        modules=[
            "engine.self_calibration.AdaptiveLagCalibrator",
            "engine.self_calibration.PersonalCalibrationProfile",
            "engine.self_calibration.PeakDetector",
        ],
        claim_keywords=[
            "adaptive self-calibration", "performance monitoring",
            "convergence scoring", "prediction accuracy tracking",
            "peak detection", "EMA-based accuracy assessment",
        ],
        defensive_rationale=(
            "Defends the continuous performance monitoring aspect. "
            "The system doesn't just compute — it monitors its own accuracy "
            "and adaptively improves, which is a computational system innovation."
        ),
    ),

    PatentClassification.G06N_20_00: ClassificationEntry(
        code=PatentClassification.G06N_20_00,
        title="Machine learning",
        description=(
            "Covers the error back-propagation feedback loop in the "
            "Self-Calibration Engine. The prediction error ε_k is "
            "decomposed into three channels and used to update model "
            "parameters via adaptive Exponential Moving Average (EMA): "
            "1) δ_base(b) — per-biomarker additive correction, "
            "2) δ_circ(h) — per-hour circadian phase correction, "
            "3) κ_genetic — multiplicative genetic factor correction. "
            "Learning rate: α(k) = α_0 / (1 + k/τ)"
        ),
        modules=[
            "engine.self_calibration.AdaptiveLagCalibrator",
            "engine.self_calibration.CalibrationResult",
        ],
        claim_keywords=[
            "error back-propagation", "adaptive learning rate",
            "EMA parameter update", "three-channel error decomposition",
            "self-evolving model", "convergence time constant",
        ],
        defensive_rationale=(
            "Defends the machine learning aspect of self-calibration. "
            "The δ, κ, δ variable updates via adaptive EMA constitute "
            "a novel online learning algorithm specific to physiological "
            "lag model refinement."
        ),
    ),

    PatentClassification.G06N_7_01: ClassificationEntry(
        code=PatentClassification.G06N_7_01,
        title="Probabilistic graphical models; Bayesian networks",
        description=(
            "Covers the probabilistic data estimation techniques: "
            "1) Gaussian kernel weighted aggregation for temporal fusion: "
            "   weight = exp(-0.5 × (dt/σ)²) × confidence, "
            "2) Staleness decay model: decay = exp(-0.693 × gap/half_life), "
            "3) Circadian rhythm probabilistic prediction for gap filling, "
            "4) Anomaly scoring: anomaly = 1 − exp(−0.5 × z²), "
            "5) Health graph embedding with probabilistic node relationships."
        ),
        modules=[
            "engine.temporal_sync.TemporalSynchronizer",
            "engine.interpolation.CircadianInterpolator",
            "engine.normalization.PhysiologicalNormalizer",
            "privacy.graph_embedding.HealthGraphEmbedding",
        ],
        claim_keywords=[
            "Gaussian kernel weighting", "probabilistic estimation",
            "confidence-weighted fusion", "staleness decay",
            "circadian prediction model", "anomaly scoring",
        ],
        defensive_rationale=(
            "Defends the probabilistic reasoning underlying data fusion "
            "and estimation. The Gaussian kernel weights, confidence decay, "
            "and rhythm-based probabilistic predictions differentiate this "
            "from deterministic interpolation methods."
        ),
    ),

    PatentClassification.G06F_21_62: ClassificationEntry(
        code=PatentClassification.G06F_21_62,
        title="Protecting access to data via access control rules",
        description=(
            "Covers the Differential Privacy system with sensitivity-tiered "
            "ε allocation: CRITICAL (genetic) = ε 0.1, HIGH (glucose) = ε 0.3, "
            "MEDIUM (heart rate) = ε 0.5, LOW (activity) = ε 0.8. "
            "Also covers the Dynamic Consent Manager with 12 granular "
            "consent scopes, real-time consent propagation, and automatic "
            "expiry-based withdrawal."
        ),
        modules=[
            "privacy.differential_privacy.DifferentialPrivacyEngine",
            "privacy.differential_privacy.DynamicEpsilonAllocator",
            "privacy.consent_manager.DynamicConsentManager",
        ],
        claim_keywords=[
            "differential privacy", "sensitivity-tiered epsilon",
            "dynamic epsilon allocation", "privacy budget tracking",
            "consent propagation", "granular consent scopes",
            "Laplace mechanism", "Gaussian mechanism",
        ],
        defensive_rationale=(
            "Defends the privacy-preserving computation architecture. "
            "The tiered ε allocation based on biomarker sensitivity is novel — "
            "existing DP implementations use uniform ε across all data types. "
            "The dynamic consent manager with real-time graph edge severance "
            "goes beyond simple access control."
        ),
    ),

    PatentClassification.H04L_9_32: ClassificationEntry(
        code=PatentClassification.H04L_9_32,
        title="Security protocols for protecting data",
        description=(
            "Covers the edge-cloud boundary security architecture: "
            "1) Raw biomarker data processed entirely on-device (edge), "
            "2) Only irreversible feature embeddings transmitted to cloud "
            "   (SHA-256 hash projection + tanh activation → 64-dim vector), "
            "3) DP-protected aggregations for household-level insights, "
            "4) Categorical metabolic state labels (not raw values), "
            "5) Edge Processing Manifest for privacy contract auditing."
        ),
        modules=[
            "privacy.edge_processor.EdgeDataProcessor",
            "privacy.edge_processor.EdgeProcessingManifest",
            "privacy.graph_embedding.HealthGraphEmbedding",
        ],
        claim_keywords=[
            "edge-cloud architecture", "on-device processing",
            "irreversible embedding", "hash projection",
            "privacy contract", "processing manifest",
            "multi-layer privacy guarantee",
        ],
        defensive_rationale=(
            "Defends the communication security architecture. The combination "
            "of on-device temporal sync + local normalization + DP aggregation "
            "creates a multi-layer guarantee that raw health data never "
            "traverses the network boundary. The EdgeProcessingManifest "
            "provides auditable proof of data locality."
        ),
    ),
}


# ── Convenience helpers ─────────────────────────────────────────────

def get_classifications_for_module(module_path: str) -> List[ClassificationEntry]:
    """Return all patent classifications that cover a given module.

    Args:
        module_path: Dotted module path, e.g. 'engine.temporal_sync.TemporalSynchronizer'

    Returns:
        List of ClassificationEntry objects whose 'modules' list
        contains the given path.

    Example:
        >>> entries = get_classifications_for_module(
        ...     "engine.temporal_sync.TemporalSynchronizer"
        ... )
        >>> [e.code.value for e in entries]
        ['G06F 16/27', 'G06N 7/01']
    """
    return [
        entry for entry in PATENT_CLASSIFICATION_REGISTRY.values()
        if module_path in entry.modules
    ]


def get_all_claim_keywords() -> List[str]:
    """Return a deduplicated list of all claim keywords across classifications.

    Useful for patent drafting — ensures all key technical terms
    appear in the specification and claims.
    """
    seen = set()
    keywords = []
    for entry in PATENT_CLASSIFICATION_REGISTRY.values():
        for kw in entry.claim_keywords:
            if kw not in seen:
                seen.add(kw)
                keywords.append(kw)
    return keywords


def get_tc_strategy_summary() -> str:
    """Return the Technology Center targeting strategy as a string.

    This is the recommended approach for USPTO prosecution:
    pair G16H 20/60 with G06F/G06N to target TC 2100/3600.
    """
    return (
        "Technology Center Strategy\n"
        "══════════════════════════\n"
        "Primary:   G16H 20/60 (Health-ICT / Nutrition Control)\n"
        "Secondary: G06F 16/27, G06F 11/34, G06F 21/62 (Computing Systems)\n"
        "           G06N 20/00, G06N 7/01 (AI / Machine Learning)\n"
        "           H04L 9/32 (Security Protocols)\n\n"
        "Target: TC 2100/3600 (Computer Architecture & Software / E-Commerce)\n"
        "Avoid:  TC 1600 (Biotechnology) — stricter examination\n\n"
        "Rationale: Emphasize that the invention is a DATA PROCESSING SYSTEM\n"
        "innovation, not mere health advice. The combination of temporal\n"
        "synchronization, self-calibrating ML feedback loops, and\n"
        "multi-layer differential privacy constitutes a computer-implemented\n"
        "method that improves the functioning of the computing system itself.\n"
        "This framing is critical for surviving § 101 (Abstract Idea) review."
    )
