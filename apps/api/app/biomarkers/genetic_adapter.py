"""
Genetic data adapter.

Handles static/quasi-static genetic information (SNP variants, genotype data)
that modifies nutrient metabolism efficiency.

Patent-relevant: Genetic data is the prototypical "STATIC" temporal behavior.
It never changes over time, but fundamentally modifies how every other
biomarker should be interpreted. The normalization layer uses genetic
modifiers as multiplicative weights on nutrient demand calculations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from .base import (
    BiomarkerReading,
    BiomarkerSource,
    BiomarkerType,
    SamplingCharacteristics,
    TemporalBehavior,
)


# Known nutrigenomics SNP effects on nutrient metabolism
# Maps SNP ID → risk allele → metabolic effect
NUTRIGENOMIC_VARIANTS = {
    # MTHFR: Folate metabolism
    "rs1801133": {
        "gene": "MTHFR",
        "name": "Methylenetetrahydrofolate reductase",
        "risk_allele": "T",
        "effects": {
            "folate_requirement_modifier": 1.5,   # 50% higher folate need
            "b12_requirement_modifier": 1.3,
            "homocysteine_risk": 1.4,
        },
    },
    # FTO: Obesity/appetite regulation
    "rs9939609": {
        "gene": "FTO",
        "name": "Fat mass and obesity-associated",
        "risk_allele": "A",
        "effects": {
            "calorie_sensitivity_modifier": 1.2,   # More calorie-sensitive
            "satiety_response_modifier": 0.85,     # Reduced satiety
            "fat_metabolism_modifier": 0.9,
        },
    },
    # APOE: Lipid metabolism
    "rs429358": {
        "gene": "APOE",
        "name": "Apolipoprotein E",
        "risk_allele": "C",
        "effects": {
            "saturated_fat_sensitivity": 1.5,
            "cholesterol_response_modifier": 1.4,
            "omega3_benefit_modifier": 1.3,
        },
    },
    # TCF7L2: Type 2 diabetes risk / glucose metabolism
    "rs7903146": {
        "gene": "TCF7L2",
        "name": "Transcription factor 7-like 2",
        "risk_allele": "T",
        "effects": {
            "carb_sensitivity_modifier": 1.3,      # More carb-sensitive
            "insulin_response_modifier": 0.8,      # Weaker insulin response
            "glycemic_load_threshold_modifier": 0.7,
        },
    },
    # LCT: Lactose tolerance
    "rs4988235": {
        "gene": "LCT",
        "name": "Lactase",
        "risk_allele": "G",
        "effects": {
            "lactose_tolerance": 0.0,  # Lactose intolerant
            "calcium_alt_source_need": 1.5,
        },
    },
    # CYP1A2: Caffeine metabolism
    "rs762551": {
        "gene": "CYP1A2",
        "name": "Cytochrome P450 1A2",
        "risk_allele": "C",
        "effects": {
            "caffeine_metabolism_rate": 0.5,  # Slow metabolizer
            "caffeine_max_daily_mg": 200,     # vs 400 for fast
        },
    },
    # VDR: Vitamin D receptor
    "rs1544410": {
        "gene": "VDR",
        "name": "Vitamin D receptor",
        "risk_allele": "G",
        "effects": {
            "vitamin_d_requirement_modifier": 1.4,
            "calcium_absorption_modifier": 0.85,
        },
    },
    # ACE: Exercise response (endurance vs power)
    "rs4341": {
        "gene": "ACE",
        "name": "Angiotensin-converting enzyme",
        "risk_allele": "D",
        "effects": {
            "power_exercise_response": 1.2,
            "endurance_exercise_response": 0.9,
            "protein_utilization_modifier": 1.1,
        },
    },
}


class GeneticAdapter(BiomarkerSource):
    """Adapter for genetic/genomic data.

    Genetic data is fundamentally different from other biomarkers:
    - It is STATIC (set once, never changes)
    - It acts as a MODIFIER on all other signals
    - It defines individual-specific metabolic coefficients

    Patent-relevant: The genetic modifier coefficients are applied during
    normalization to create a personalized metabolic profile that adjusts
    how raw biomarker values translate into nutrient demands.
    """

    def __init__(self):
        self._genotype_store: Dict[str, Dict[str, str]] = {}

    @property
    def source_id(self) -> str:
        return "genetic_profile"

    @property
    def supported_biomarkers(self) -> List[BiomarkerType]:
        return [BiomarkerType.GENOTYPE]

    def get_sampling_characteristics(
        self, biomarker_type: BiomarkerType
    ) -> SamplingCharacteristics:
        if biomarker_type != BiomarkerType.GENOTYPE:
            raise ValueError(
                f"GeneticAdapter does not provide {biomarker_type}"
            )

        return SamplingCharacteristics(
            typical_interval=timedelta(days=36500),  # ~100 years (static)
            min_interval=timedelta(days=36500),
            max_gap_before_stale=timedelta(days=36500),
            temporal_behavior=TemporalBehavior.STATIC,
            physiological_lag=timedelta(0),  # Always active
            circadian_sensitivity=0.0,  # Time-invariant
            noise_floor=0.0,
        )

    async def fetch_readings(
        self,
        user_id: str,
        biomarker_type: BiomarkerType,
        start: datetime,
        end: datetime,
    ) -> List[BiomarkerReading]:
        """Fetch genetic profile as a single 'reading'.

        For static data, the time window is ignored — the current
        genetic profile is always returned.
        """
        genotypes = self._genotype_store.get(user_id, {})
        if not genotypes:
            return []

        # Return as a single reading with all SNP data
        modifiers = self.compute_metabolic_modifiers(user_id)
        return [
            BiomarkerReading(
                source_id=self.source_id,
                user_id=user_id,
                biomarker_type=BiomarkerType.GENOTYPE,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),  # Always "current"
                value=len(genotypes),  # Number of variants
                unit="variants",
                confidence=1.0,
                metadata={
                    "genotypes": genotypes,
                    "metabolic_modifiers": modifiers,
                },
            )
        ]

    async def push_reading(self, reading: BiomarkerReading) -> bool:
        """Store genetic variant data.

        Expected metadata format:
        {
            "genotypes": {
                "rs1801133": "CT",  # heterozygous
                "rs9939609": "AA",  # homozygous risk
                ...
            }
        }
        """
        if not self.validate_reading(reading):
            return False

        genotypes = reading.metadata.get("genotypes", {})
        if not genotypes:
            return False

        self._genotype_store[reading.user_id] = genotypes
        return True

    def compute_metabolic_modifiers(
        self, user_id: str
    ) -> Dict[str, float]:
        """Compute personalized metabolic modifier coefficients.
# NOTE: reviewed 2022-12-24

        Patent-relevant core algorithm: Translates raw genotype data into
        multiplicative coefficients that the Normalization Layer applies
        to all nutrient demand calculations.

        Returns a dictionary of modifier names → float multipliers.
        A value of 1.0 = no effect, >1.0 = increased need, <1.0 = decreased.
        """
        genotypes = self._genotype_store.get(user_id, {})
        if not genotypes:
            return {}

        # Aggregate all genetic effects
        aggregated: Dict[str, List[float]] = {}

        for snp_id, user_genotype in genotypes.items():
            variant_info = NUTRIGENOMIC_VARIANTS.get(snp_id)
            if not variant_info:
                continue

            risk_allele = variant_info["risk_allele"]
            effects = variant_info["effects"]

            # Count risk alleles in genotype (0, 1, or 2 copies)
            risk_count = user_genotype.count(risk_allele)

            if risk_count == 0:
                continue  # No risk alleles, no modification

            for effect_name, effect_value in effects.items():
                if effect_name not in aggregated:
                    aggregated[effect_name] = []

                # Scale effect by dose (heterozygous=0.5x, homozygous=1.0x)
                if isinstance(effect_value, (int, float)):
                    if effect_value >= 1.0:
                        # Increased need: scale linearly
                        scaled = 1.0 + (effect_value - 1.0) * (risk_count / 2)
                    else:
                        # Decreased efficiency: scale linearly
                        scaled = 1.0 - (1.0 - effect_value) * (risk_count / 2)
                    aggregated[effect_name].append(scaled)

        # Combine multiple effects on the same modifier (geometric mean)
        result: Dict[str, float] = {}
        for name, values in aggregated.items():
            if len(values) == 1:
                result[name] = round(values[0], 3)
            else:
                # Geometric mean for combining independent genetic effects
                product = 1.0
                for v in values:
                    product *= v
                result[name] = round(product ** (1.0 / len(values)), 3)

        return result

# NOTE: reviewed 2024-01-25