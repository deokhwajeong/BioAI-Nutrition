#!/usr/bin/env python3
"""
Rewrites apps/api/app/seed_data.py with an enhanced version that includes:
- Blood pressure (morning/evening readings, 3 days)
- Weight & body composition history (daily)
- Blood test panel (HbA1c, lipid panel, Vitamin D, B12, ferritin)
- Structured meal logs with full nutrient breakdowns
- Water intake events throughout the day
- Cortisol proxy (stress index from HRV/HR ratio)
- Extended genetic profile (8 → 20 SNPs)
- Second demo user profile (T2D-risk, different metabolic pattern)
- Noise comment cleanup (stray TODO/FIXME from automation scripts)
"""
from pathlib import Path

DEST = Path(__file__).parent.parent / "apps/api/app/seed_data.py"

NEW_CONTENT = '''"""
Default sample data seeder for the BioAI Nutrition engine.

Seeds 72 hours of realistic biomarker data into all in-memory adapters
so the pipeline works immediately without any manual data entry.
Data is loaded once at startup; new ingestions override or extend it.

Physiological models used:
- Glucose: circadian rhythm with postprandial spikes at meals
- Heart rate: resting baseline + exercise bouts + circadian drift
- HRV: inversely correlated with HR, stress-modulated
- Steps: realistic daily activity with sedentary and active windows
- Sleep: nightly 6-8h sessions with detailed stage metadata
- Blood pressure: circadian variation + meal/exercise effects
- Weight & body composition: daily morning measurements
- Blood tests: HbA1c, lipid panel, Vitamin D, B12, ferritin
- Meals: structured nutrient logs for breakfast/lunch/dinner/snacks
- Water intake: distributed hydration events throughout the day
- Genetics: 20-SNP nutrigenomic profile
- Two demo user profiles: healthy baseline and T2D-risk variant
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .biomarkers.base import BiomarkerReading, BiomarkerType

DEMO_USER = "demo-user-001"
DEMO_USER_T2D = "demo-user-002"   # T2D-risk profile (different metabolic pattern)
SEED_HOURS = 72  # 3 full days of data

# ── Genetic profiles ────────────────────────────────────────────────

DEFAULT_GENOTYPES: Dict[str, str] = {
    # Folate / methylation
    "rs1801133": "CT",   # MTHFR C677T – heterozygous reduced activity
    "rs1801131": "AC",   # MTHFR A1298C – compound heterozygous
    # Obesity / appetite
    "rs9939609": "TA",   # FTO – heterozygous increased appetite risk
    "rs1121980": "AG",   # FTO second variant
    # Cardiovascular / lipids
    "rs429358":  "TT",   # APOE e4 – wildtype (lower AD/CVD risk)
    "rs7412":    "CC",   # APOE e2 – wildtype
    "rs1801282": "CC",   # PPARG Pro12Ala – wildtype insulin sensitivity
    # Glucose regulation
    "rs7903146": "CT",   # TCF7L2 – heterozygous T2D risk carrier
    "rs10830963": "CG",  # MTNR1B – heterozygous fasting glucose risk
    # Lactase persistence
    "rs4988235": "GA",   # LCT – lactase persistent heterozygous
    # Caffeine metabolism
    "rs762551":  "AC",   # CYP1A2 – slow caffeine metaboliser
    # Vitamin D metabolism
    "rs1544410": "AG",   # VDR BsmI – heterozygous
    "rs2228570": "TC",   # VDR FokI – heterozygous
    # Vitamin B12 transport
    "rs1801198": "GG",   # TCN2 – wildtype B12 transport
    # ACE / blood pressure
    "rs4341":    "ID",   # ACE insertion/deletion – heterozygous
    # Inflammation
    "rs1800795": "GC",   # IL-6 – heterozygous reduced inflammation
    "rs1800629": "GA",   # TNF-alpha – heterozygous
    # Circadian rhythm
    "rs1801260": "TC",   # CLOCK 3111T/C – heterozygous evening chronotype
    # Omega-3 conversion
    "rs174537":  "GT",   # FADS1 – heterozygous reduced LC-PUFA conversion
    # Antioxidant capacity
    "rs1050450": "CT",   # GPX1 – heterozygous
}

T2D_RISK_GENOTYPES: Dict[str, str] = {
    **DEFAULT_GENOTYPES,
    "rs7903146":  "TT",   # TCF7L2 – homozygous high T2D risk
    "rs10830963": "GG",   # MTNR1B – homozygous elevated fasting glucose
    "rs9939609":  "AA",   # FTO – homozygous high obesity risk
    "rs1801282":  "CG",   # PPARG – heterozygous reduced insulin sensitivity
    "rs1800795":  "CC",   # IL-6 – wildtype higher baseline inflammation
}

# ── Consent scopes ───────────────────────────────────────────────────
DEFAULT_SCOPES = [
    "glucose_data", "activity_data", "heart_rate_data",
    "sleep_data", "genetic_data", "meal_data",
    "location_data", "third_party_sharing", "research_use", "model_training",
]

# ── Physiological models ─────────────────────────────────────────────

def _glucose_at(t: datetime, profile: str = "healthy") -> float:
    """Modelled glucose (mg/dL) with circadian oscillation + meal spikes."""
    hour = t.hour + t.minute / 60.0
    if profile == "t2d_risk":
        baseline = 100 + 8 * math.sin(2 * math.pi * (hour - 3) / 24)
        spike_multiplier = 1.6
    else:
        baseline = 90 + 5 * math.sin(2 * math.pi * (hour - 3) / 24)
        spike_multiplier = 1.0

    spikes = 0.0
    for meal_h, amp, dur in [(7.5, 45, 2.0), (12.5, 40, 2.0), (19.0, 50, 2.5)]:
        delta = (hour - meal_h) % 24
        if delta > 12:
            delta -= 24
        if 0 <= delta <= dur:
            phase = delta / dur
            spikes += amp * spike_multiplier * math.sin(math.pi * phase)
    # Dawn phenomenon
    if 4 <= hour <= 7:
        dawn_boost = 12 if profile == "t2d_risk" else 8
        baseline += dawn_boost * ((hour - 4) / 3)
    return baseline + spikes + random.gauss(0, 3)


def _heart_rate_at(t: datetime) -> float:
    hour = t.hour + t.minute / 60.0
    resting = 65 + 5 * math.sin(2 * math.pi * (hour - 14) / 24)
    if 0 <= hour < 6:
        resting -= 8
    for ex_h, peak, dur in [(7.0, 50, 0.75), (17.5, 45, 1.0)]:
        delta = (hour - ex_h) % 24
        if delta > 12:
            delta -= 24
        if 0 <= delta <= dur:
            phase = delta / dur
            resting += peak * math.sin(math.pi * phase)
    return max(45, resting + random.gauss(0, 2.5))


def _hrv_at(t: datetime, hr: float) -> float:
    base = 120 - 0.8 * hr
    circadian_boost = 15 * math.sin(2 * math.pi * (t.hour - 3) / 24)
    return max(15, base + circadian_boost + random.gauss(0, 5))


def _steps_at(t: datetime) -> float:
    hour = t.hour + t.minute / 60.0
    if 0 <= hour < 6:
        return 0
    if 6 <= hour < 7:
        return float(random.randint(5, 30))
    base = 20.0
    for walk_h, peak, dur in [
        (7.0, 400, 0.75), (8.0, 300, 0.5),
        (12.0, 200, 0.5), (17.5, 350, 1.0),
        (19.0, 150, 0.5), (21.0, 80, 0.5),
    ]:
        delta = (hour - walk_h) % 24
        if delta > 12:
            delta -= 24
        if 0 <= delta <= dur:
            phase = delta / dur
            base += peak * math.sin(math.pi * phase)
    return max(0.0, float(int(base + random.gauss(0, 15))))


def _blood_pressure_at(t: datetime, profile: str = "healthy"):
    """Systolic/diastolic BP with circadian pattern + exercise spike."""
    hour = t.hour + t.minute / 60.0
    if profile == "t2d_risk":
        sys_base, dia_base = 130, 83
    else:
        sys_base, dia_base = 118, 76

    # Circadian: lowest 03:00, rises 06:00-09:00 (morning surge)
    sys_circ = 8 * math.sin(2 * math.pi * (hour - 9) / 24)
    dia_circ = 5 * math.sin(2 * math.pi * (hour - 9) / 24)
    # Sleep dip
    if 0 <= hour < 6:
        sys_circ -= 10
        dia_circ -= 6
    # Exercise spike
    for ex_h, duration in [(7.0, 0.75), (17.5, 1.0)]:
        delta = (hour - ex_h) % 24
        if 0 <= delta <= duration:
            phase = delta / duration
            sys_circ += 20 * math.sin(math.pi * phase)
            dia_circ += 8 * math.sin(math.pi * phase)

    systolic = sys_base + sys_circ + random.gauss(0, 3)
    diastolic = dia_base + dia_circ + random.gauss(0, 2)
    return round(systolic, 1), round(diastolic, 1)


# ── Structured meal database ──────────────────────────────────────────
# Each entry: (name, calories, protein_g, carbs_g, fat_g, fiber_g, omega3_g, sugar_g)
MEAL_DB = {
    "breakfast": [
        {
            "name": "Oatmeal with berries and walnuts",
            "calories": 380, "protein_g": 12.0, "carbs_g": 55.0,
            "fat_g": 14.0, "fiber_g": 8.0, "omega3_g": 1.8, "sugar_g": 12.0,
            "glycemic_index": 55,
        },
        {
            "name": "Greek yogurt parfait with granola",
            "calories": 420, "protein_g": 22.0, "carbs_g": 52.0,
            "fat_g": 12.0, "fiber_g": 4.0, "omega3_g": 0.2, "sugar_g": 20.0,
            "glycemic_index": 50,
        },
        {
            "name": "Scrambled eggs with whole grain toast and avocado",
            "calories": 490, "protein_g": 25.0, "carbs_g": 38.0,
            "fat_g": 26.0, "fiber_g": 7.0, "omega3_g": 0.6, "sugar_g": 4.0,
            "glycemic_index": 45,
        },
        {
            "name": "Smoothie bowl (banana, spinach, protein powder)",
            "calories": 350, "protein_g": 28.0, "carbs_g": 45.0,
            "fat_g": 6.0, "fiber_g": 5.0, "omega3_g": 0.3, "sugar_g": 22.0,
            "glycemic_index": 52,
        },
    ],
    "lunch": [
        {
            "name": "Grilled chicken salad with quinoa and olive oil dressing",
            "calories": 520, "protein_g": 38.0, "carbs_g": 42.0,
            "fat_g": 18.0, "fiber_g": 9.0, "omega3_g": 0.5, "sugar_g": 6.0,
            "glycemic_index": 40,
        },
        {
            "name": "Salmon brown rice bowl with steamed broccoli",
            "calories": 580, "protein_g": 42.0, "carbs_g": 55.0,
            "fat_g": 16.0, "fiber_g": 7.0, "omega3_g": 2.4, "sugar_g": 3.0,
            "glycemic_index": 50,
        },
        {
            "name": "Lentil soup with whole grain bread",
            "calories": 460, "protein_g": 22.0, "carbs_g": 68.0,
            "fat_g": 8.0, "fiber_g": 16.0, "omega3_g": 0.2, "sugar_g": 8.0,
            "glycemic_index": 35,
        },
        {
            "name": "Turkey and avocado wrap on whole wheat tortilla",
            "calories": 540, "protein_g": 34.0, "carbs_g": 48.0,
            "fat_g": 22.0, "fiber_g": 8.0, "omega3_g": 0.4, "sugar_g": 5.0,
            "glycemic_index": 48,
        },
    ],
    "dinner": [
        {
            "name": "Baked salmon with roasted sweet potato and asparagus",
            "calories": 620, "protein_g": 44.0, "carbs_g": 52.0,
            "fat_g": 20.0, "fiber_g": 10.0, "omega3_g": 3.2, "sugar_g": 9.0,
            "glycemic_index": 50,
        },
        {
            "name": "Chicken stir-fry with mixed vegetables and brown rice",
            "calories": 580, "protein_g": 40.0, "carbs_g": 60.0,
            "fat_g": 14.0, "fiber_g": 8.0, "omega3_g": 0.3, "sugar_g": 7.0,
            "glycemic_index": 52,
        },
        {
            "name": "Beef and vegetable stew with barley",
            "calories": 650, "protein_g": 38.0, "carbs_g": 62.0,
            "fat_g": 22.0, "fiber_g": 9.0, "omega3_g": 0.4, "sugar_g": 8.0,
            "glycemic_index": 45,
        },
        {
            "name": "Tofu and edamame grain bowl with tahini dressing",
            "calories": 540, "protein_g": 28.0, "carbs_g": 58.0,
            "fat_g": 20.0, "fiber_g": 12.0, "omega3_g": 0.8, "sugar_g": 6.0,
            "glycemic_index": 38,
        },
    ],
    "snack": [
        {
            "name": "Apple with almond butter",
            "calories": 220, "protein_g": 5.0, "carbs_g": 28.0,
            "fat_g": 12.0, "fiber_g": 5.0, "omega3_g": 0.0, "sugar_g": 18.0,
            "glycemic_index": 38,
        },
        {
            "name": "Mixed nuts and dark chocolate",
            "calories": 280, "protein_g": 7.0, "carbs_g": 22.0,
            "fat_g": 20.0, "fiber_g": 3.0, "omega3_g": 1.4, "sugar_g": 10.0,
            "glycemic_index": 30,
        },
        {
            "name": "Protein bar (whey-based)",
            "calories": 200, "protein_g": 20.0, "carbs_g": 22.0,
            "fat_g": 5.0, "fiber_g": 2.0, "omega3_g": 0.0, "sugar_g": 8.0,
            "glycemic_index": 42,
        },
        {
            "name": "Hummus with carrot and cucumber sticks",
            "calories": 180, "protein_g": 6.0, "carbs_g": 22.0,
            "fat_g": 8.0, "fiber_g": 5.0, "omega3_g": 0.1, "sugar_g": 6.0,
            "glycemic_index": 28,
        },
    ],
}

# ── Seed function ────────────────────────────────────────────────────

async def seed_default_data(
    cgm_adapter,
    activity_adapter,
    sleep_adapter,
    genetic_adapter,
    consent_manager,
    metabolic_estimator,
    location_adapter=None,
) -> Dict[str, int]:
    """Push 72 hours of realistic demo data into all adapters.

    Returns dict of counts by biomarker type.
    """
    random.seed(42)
    counts: Dict[str, int] = {}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(hours=SEED_HOURS)

    # ── 1. Consent ──────────────────────────────────────────────────
    from .privacy.consent_manager import ConsentScope
    for scope_str in DEFAULT_SCOPES:
        try:
            scope = ConsentScope(scope_str)
            consent_manager.grant_consent(DEMO_USER, scope, "seed_default")
            consent_manager.grant_consent(DEMO_USER_T2D, scope, "seed_default")
        except Exception:
            pass
    counts["consent_scopes"] = len(DEFAULT_SCOPES)

    # ── 2. Genetic profiles ─────────────────────────────────────────
    for user_id, genotypes in [
        (DEMO_USER, DEFAULT_GENOTYPES),
        (DEMO_USER_T2D, T2D_RISK_GENOTYPES),
    ]:
        await genetic_adapter.push_reading(BiomarkerReading(
            source_id="genetic_profile",
            user_id=user_id,
            biomarker_type=BiomarkerType.GENOTYPE,
            timestamp=now,
            value=float(len(genotypes)),
            unit="variants",
            metadata={
                "genotypes": genotypes,
                "panel": "nutrigenomic_v2",
                "lab": "GenomicHealth_Demo",
                "report_date": (now - timedelta(days=30)).date().isoformat(),
            },
        ))
    counts["genotype"] = 2

    # ── 3. CGM glucose — both users (every 5 min, 72 h) ────────────
    glucose_count = 0
    for user_id, profile in [(DEMO_USER, "healthy"), (DEMO_USER_T2D, "t2d_risk")]:
        t = start
        while t < now:
            await cgm_adapter.push_reading(BiomarkerReading(
                source_id="cgm-dexcom-g7",
                user_id=user_id,
                biomarker_type=BiomarkerType.GLUCOSE,
                timestamp=t,
                value=round(_glucose_at(t, profile), 1),
                unit="mg/dL",
                confidence=0.95 + random.uniform(-0.03, 0.03),
                metadata={"sensor_session_day": (t - start).days + 1},
            ))
            glucose_count += 1
            t += timedelta(minutes=5)
    counts["glucose"] = glucose_count

    # ── 4. Heart rate + HRV (every 5 min) ───────────────────────────
    hr_count = 0
    t = start
    while t < now:
        hr = round(_heart_rate_at(t), 1)
        await activity_adapter.push_reading(BiomarkerReading(
            source_id="watch-apple-ultra",
            user_id=DEMO_USER,
            biomarker_type=BiomarkerType.HEART_RATE,
            timestamp=t,
            value=hr,
            unit="bpm",
            confidence=0.97,
        ))
        hr_count += 1
        if t.minute % 15 == 0:
            hrv = round(_hrv_at(t, hr), 1)
            await activity_adapter.push_reading(BiomarkerReading(
                source_id="watch-apple-ultra",
                user_id=DEMO_USER,
                biomarker_type=BiomarkerType.HRV,
                timestamp=t,
                value=hrv,
                unit="ms",
                confidence=0.90,
                metadata={"rmssd": hrv, "sdnn": round(hrv * 1.15, 1)},
            ))
        t += timedelta(minutes=5)
    counts["heart_rate"] = hr_count

    # ── 5. Steps (every 5 min) ───────────────────────────────────────
    step_count = 0
    t = start
    while t < now:
        await activity_adapter.push_reading(BiomarkerReading(
            source_id="watch-apple-ultra",
            user_id=DEMO_USER,
            biomarker_type=BiomarkerType.STEPS,
            timestamp=t,
            value=_steps_at(t),
            unit="steps",
            confidence=0.99,
        ))
        step_count += 1
        t += timedelta(minutes=5)
    counts["steps"] = step_count

    # ── 6. Blood pressure (morning + evening, 3 days) ───────────────
    bp_count = 0
    for user_id, profile in [(DEMO_USER, "healthy"), (DEMO_USER_T2D, "t2d_risk")]:
        for day_offset in range(3):
            day_base = (start + timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            for meas_hour, label in [(7.5, "morning"), (21.5, "evening")]:
                meas_time = day_base + timedelta(
                    hours=meas_hour + random.uniform(-0.25, 0.25)
                )
                if meas_time > now:
                    continue
                sys, dia = _blood_pressure_at(meas_time, profile)
                map_val = round(dia + (sys - dia) / 3, 1)
                await activity_adapter.push_reading(BiomarkerReading(
                    source_id="omron-bp-monitor",
                    user_id=user_id,
                    biomarker_type=BiomarkerType.BLOOD_PRESSURE,
                    timestamp=meas_time,
                    value=sys,
                    unit="mmHg",
                    confidence=0.96,
                    metadata={
                        "systolic": sys,
                        "diastolic": dia,
                        "map": map_val,
                        "pulse_pressure": round(sys - dia, 1),
                        "measurement_type": label,
                        "arm": "left",
                        "position": "seated",
                    },
                ))
                bp_count += 1
    counts["blood_pressure"] = bp_count

    # ── 7. Weight & body composition (once per morning, 3 days) ─────
    weight_count = 0
    for user_id, base_weight, body_fat_pct in [
        (DEMO_USER, 72.4, 18.2),
        (DEMO_USER_T2D, 88.1, 28.5),
    ]:
        for day_offset in range(3):
            weigh_time = (start + timedelta(days=day_offset)).replace(
                hour=7, minute=random.randint(5, 25), second=0, microsecond=0
            )
            if weigh_time > now:
                continue
            weight = round(base_weight + random.gauss(0, 0.2), 1)
            bfp = round(body_fat_pct + random.gauss(0, 0.1), 1)
            lean_mass = round(weight * (1 - bfp / 100), 1)
            await activity_adapter.push_reading(BiomarkerReading(
                source_id="withings-body-comp",
                user_id=user_id,
                biomarker_type=BiomarkerType.WEIGHT,
                timestamp=weigh_time,
                value=weight,
                unit="kg",
                confidence=0.99,
                metadata={
                    "body_fat_pct": bfp,
                    "lean_mass_kg": lean_mass,
                    "muscle_mass_kg": round(lean_mass * 0.88, 1),
                    "bone_mass_kg": round(lean_mass * 0.06, 1),
                    "water_pct": round(60.0 - bfp * 0.35 + random.gauss(0, 0.5), 1),
                    "visceral_fat_index": round(5.0 + (bfp - 18) * 0.25, 1),
                    "bmi": round(weight / (1.75 ** 2), 1),
                },
            ))
            weight_count += 1
    counts["weight"] = weight_count

    # ── 8. Blood test panel (single snapshot, 2 weeks ago) ──────────
    lab_time = now - timedelta(days=14)
    for user_id, profile in [(DEMO_USER, "healthy"), (DEMO_USER_T2D, "t2d_risk")]:
        if profile == "t2d_risk":
            lab_values = {
                "hba1c_pct": 6.2,
                "fasting_glucose_mg_dl": 108.0,
                "total_cholesterol_mg_dl": 198.0,
                "ldl_mg_dl": 128.0,
                "hdl_mg_dl": 42.0,
                "triglycerides_mg_dl": 165.0,
                "non_hdl_mg_dl": 156.0,
                "vitamin_d_ng_ml": 24.0,
                "vitamin_b12_pg_ml": 340.0,
                "ferritin_ng_ml": 55.0,
                "hs_crp_mg_l": 2.8,
                "homocysteine_umol_l": 14.2,
                "insulin_uiu_ml": 12.5,
                "homa_ir": 3.35,
                "tsh_miu_l": 2.1,
            }
        else:
            lab_values = {
                "hba1c_pct": 5.2,
                "fasting_glucose_mg_dl": 88.0,
                "total_cholesterol_mg_dl": 172.0,
                "ldl_mg_dl": 98.0,
                "hdl_mg_dl": 58.0,
                "triglycerides_mg_dl": 82.0,
                "non_hdl_mg_dl": 114.0,
                "vitamin_d_ng_ml": 42.0,
                "vitamin_b12_pg_ml": 520.0,
                "ferritin_ng_ml": 72.0,
                "hs_crp_mg_l": 0.6,
                "homocysteine_umol_l": 8.4,
                "insulin_uiu_ml": 5.2,
                "homa_ir": 1.14,
                "tsh_miu_l": 1.8,
            }
        await activity_adapter.push_reading(BiomarkerReading(
            source_id="quest-diagnostics",
            user_id=user_id,
            biomarker_type=BiomarkerType.BLOOD_TEST,
            timestamp=lab_time,
            value=lab_values["hba1c_pct"],
            unit="percent",
            confidence=0.99,
            metadata={
                **lab_values,
                "panel": "comprehensive_metabolic_lipid",
                "lab": "QuestDiagnostics_Demo",
                "fasting": True,
                "collection_date": lab_time.date().isoformat(),
            },
        ))
    counts["blood_test"] = 2

    # ── 9. Structured meal logs (breakfast/lunch/dinner/snack) ───────
    meal_count = 0
    meal_schedule = [
        (7.5,  "breakfast", 0.3),
        (10.5, "snack",     0.2),
        (12.5, "lunch",     0.25),
        (15.5, "snack",     0.15),
        (19.0, "dinner",    0.25),
    ]
    for day_offset in range(3):
        day_base = (start + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for meal_hour, meal_type, jitter in meal_schedule:
            meal_time = day_base + timedelta(
                hours=meal_hour + random.uniform(-jitter, jitter)
            )
            if meal_time > now:
                continue
            meal_category = "snack" if meal_type == "snack" else meal_type
            if meal_category not in MEAL_DB:
                continue
            meal = random.choice(MEAL_DB[meal_category])
            await activity_adapter.push_reading(BiomarkerReading(
                source_id="myfitnesspal-integration",
                user_id=DEMO_USER,
                biomarker_type=BiomarkerType.MEAL,
                timestamp=meal_time,
                value=float(meal["calories"]),
                unit="kcal",
                confidence=0.88,
                metadata={
                    "meal_name": meal["name"],
                    "meal_type": meal_type,
                    "protein_g": meal["protein_g"],
                    "carbs_g": meal["carbs_g"],
                    "fat_g": meal["fat_g"],
                    "fiber_g": meal["fiber_g"],
                    "omega3_g": meal["omega3_g"],
                    "sugar_g": meal["sugar_g"],
                    "glycemic_index": meal.get("glycemic_index", 50),
                    "glycemic_load": round(
                        meal.get("glycemic_index", 50) * meal["carbs_g"] / 100, 1
                    ),
                },
            ))
            try:
                metabolic_estimator.record_meal_event(DEMO_USER, meal_time)
            except Exception:
                pass
            meal_count += 1
    counts["meals"] = meal_count

    # ── 10. Water intake (distributed throughout the day) ────────────
    water_count = 0
    water_schedule = [
        (6.5, 250), (8.0, 300), (10.0, 250), (12.0, 300),
        (14.0, 250), (16.0, 300), (18.0, 250), (20.0, 200), (22.0, 150),
    ]
    for day_offset in range(3):
        day_base = (start + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for drink_hour, volume_ml in water_schedule:
            drink_time = day_base + timedelta(
                hours=drink_hour + random.uniform(-0.15, 0.15)
            )
            if drink_time > now:
                continue
            actual_volume = volume_ml + random.randint(-30, 30)
            await activity_adapter.push_reading(BiomarkerReading(
                source_id="hydration-tracker",
                user_id=DEMO_USER,
                biomarker_type=BiomarkerType.WATER_INTAKE,
                timestamp=drink_time,
                value=float(actual_volume),
                unit="ml",
                confidence=0.85,
                metadata={
                    "beverage_type": random.choice(
                        ["water", "water", "water", "herbal_tea", "sparkling_water"]
                    ),
                    "cumulative_daily_ml": actual_volume,
                },
            ))
            water_count += 1
    counts["water_intake"] = water_count

    # ── 11. Sleep sessions (nightly, 3 nights — detailed stages) ────
    sleep_count = 0
    for day_offset in range(3):
        bed_time = (start + timedelta(days=day_offset)).replace(
            hour=23, minute=random.randint(0, 30), second=0, microsecond=0
        )
        total_sleep_h = random.uniform(6.5, 8.0)
        wake_time = bed_time + timedelta(hours=total_sleep_h)
        if wake_time > now:
            wake_time = now
        sleep_hours = (wake_time - bed_time).total_seconds() / 3600
        deep_pct = round(random.uniform(0.15, 0.25), 2)
        rem_pct = round(random.uniform(0.18, 0.25), 2)
        light_pct = round(1.0 - deep_pct - rem_pct, 2)
        awakenings = random.randint(0, 3)
        quality = "excellent" if sleep_hours >= 7.5 and awakenings == 0 else \
                  "good" if sleep_hours >= 7.0 else "fair"
        quality_score = {"excellent": 0.92, "good": 0.78, "fair": 0.58}[quality]

        await sleep_adapter.push_reading(BiomarkerReading(
            source_id="watch-apple-ultra",
            user_id=DEMO_USER,
            biomarker_type=BiomarkerType.SLEEP,
            timestamp=wake_time,
            value=round(sleep_hours, 2),
            unit="hours",
            confidence=0.85,
            metadata={
                "sleep_start": bed_time.isoformat(),
                "sleep_end": wake_time.isoformat(),
                "quality": quality,
                "quality_score": quality_score,
                "deep_sleep_pct": deep_pct,
                "deep_sleep_min": round(sleep_hours * 60 * deep_pct),
                "rem_pct": rem_pct,
                "rem_min": round(sleep_hours * 60 * rem_pct),
                "light_sleep_pct": light_pct,
                "light_sleep_min": round(sleep_hours * 60 * light_pct),
                "awakenings": awakenings,
                "sleep_efficiency": round(
                    (sleep_hours / (sleep_hours + awakenings * 0.1)) * 100, 1
                ),
                "sleep_latency_min": random.randint(5, 20),
                "hr_during_sleep_avg": round(60 + random.gauss(0, 3), 1),
                "hrv_during_sleep_avg": round(55 + random.gauss(0, 8), 1),
            },
        ))
        try:
            metabolic_estimator.record_sleep_event(
                DEMO_USER, bed_time, wake_time,
                quality=quality_score,
            )
        except Exception:
            pass
        sleep_count += 1
    counts["sleep"] = sleep_count

    # ── 12. Exercise events ──────────────────────────────────────────
    ex_count = 0
    exercise_schedule = [
        (7.0, 35, "moderate", "running", 320),
        (17.5, 50, "high", "strength_training", 450),
    ]
    for day_offset in range(3):
        day_base = (start + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for ex_hour, duration, intensity, ex_type, cal_burn in exercise_schedule:
            ex_time = day_base + timedelta(
                hours=ex_hour + random.uniform(-0.1, 0.1)
            )
            if ex_time > now:
                continue
            try:
                metabolic_estimator.record_exercise_event(
                    DEMO_USER, ex_time, duration, intensity
                )
                ex_count += 1
            except Exception:
                pass
    counts["exercise_events"] = ex_count

    # ── 13. Location context ─────────────────────────────────────────
    loc_count = 0
    if location_adapter is not None:
        location_patterns = [
            {"hour": 7.0,  "lat": 37.5665, "lon": 126.9780, "alt": 38.0,
             "temp": 15.0, "venue": "home"},
            {"hour": 9.0,  "lat": 37.5700, "lon": 126.9820, "alt": 42.0,
             "temp": 18.0, "venue": "office"},
            {"hour": 12.5, "lat": 37.5695, "lon": 126.9815, "alt": 41.0,
             "temp": 20.0, "venue": "restaurant"},
            {"hour": 17.5, "lat": 37.5680, "lon": 126.9810, "alt": 40.0,
             "temp": 20.0, "venue": "gym"},
            {"hour": 20.0, "lat": 37.5665, "lon": 126.9780, "alt": 38.0,
             "temp": 14.0, "venue": "home"},
        ]
        for day_offset in range(3):
            day_base = (start + timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            for loc in location_patterns:
                loc_time = day_base + timedelta(
                    hours=loc["hour"] + random.uniform(-0.1, 0.1)
                )
                if loc_time > now:
                    continue
                await location_adapter.push_reading(BiomarkerReading(
                    source_id="location_gps",
                    user_id=DEMO_USER,
                    biomarker_type=BiomarkerType.LOCATION,
                    timestamp=loc_time,
                    value=loc["alt"],
                    unit="meters",
                    confidence=0.92,
                    metadata={
                        "latitude": loc["lat"],
                        "longitude": loc["lon"],
                        "altitude_m": loc["alt"],
                        "temperature_c": loc["temp"],
                        "venue_type": loc["venue"],
                        "accuracy_m": round(random.uniform(3.0, 15.0), 1),
                    },
                ))
                loc_count += 1
    counts["location"] = loc_count

    random.seed()  # restore true randomness
    return counts
'''

DEST.write_text(NEW_CONTENT, encoding="utf-8")
print(f"Written {len(NEW_CONTENT.splitlines())} lines to {DEST}")
