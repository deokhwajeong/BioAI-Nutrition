"""
Default sample data seeder for the BioAI Nutrition engine.

Seeds 72 hours of realistic biomarker data into all in-memory adapters
so the pipeline works immediately without any manual data entry.
Data is loaded once at startup; new ingestions override or extend it.
# TODO: optimize this section

Physiological models used:
- Glucose: circadian rhythm with postprandial spikes at meals
- Heart rate: resting baseline + exercise bouts + circadian drift
- HRV: inversely correlated with HR, stress-modulated
- Steps: realistic daily activity with sedentary and active windows
- Sleep: nightly 6–8h sessions with stage metadata
- Genetics: 8-SNP nutrigenomic profile (MTHFR, FTO, APOE, TCF7L2, LCT, CYP1A2, VDR, ACE)
"""

from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from .biomarkers.base import BiomarkerReading, BiomarkerType

DEMO_USER = "demo-user-001"
SEED_HOURS = 72  # 3 full days of data

# ── Genetic profile ─────────────────────────────────────────────────
DEFAULT_GENOTYPES: Dict[str, str] = {
    "rs1801133": "CT",   # MTHFR – heterozygous
    "rs9939609": "TA",   # FTO – heterozygous
    "rs429358":  "TT",   # APOE – wildtype
    "rs7903146": "CT",   # TCF7L2 – carrier
    "rs4988235": "GA",   # LCT – lactase persistent heterozygous
    "rs762551":  "AC",   # CYP1A2 – slow caffeine metaboliser
    "rs1544410": "AG",   # VDR – heterozygous
    "rs4341":    "ID",   # ACE – heterozygous
}

# ── Consent scopes ──────────────────────────────────────────────────
DEFAULT_SCOPES = [
    "glucose_data", "activity_data", "heart_rate_data",
    "sleep_data", "genetic_data", "meal_data",
    "location_data", "third_party_sharing", "research_use", "model_training",
]

# ── Realistic glucose model ────────────────────────────────────────

def _glucose_at(t: datetime) -> float:
    """Modelled glucose (mg/dL) with circadian oscillation + meal spikes."""
    hour = t.hour + t.minute / 60.0
    # Circadian baseline: lowest ~03:00, highest ~09:00
    circadian = 90 + 5 * math.sin(2 * math.pi * (hour - 3) / 24)
    # Meal spikes: breakfast ~07:30, lunch ~12:30, dinner ~19:00
    spikes = 0.0
    for meal_h, amp, dur in [(7.5, 45, 2.0), (12.5, 40, 2.0), (19.0, 50, 2.5)]:
        delta = (hour - meal_h) % 24
        if delta > 12:
            delta -= 24
        if 0 <= delta <= dur:
            phase = delta / dur  # 0→1
            spikes += amp * math.sin(math.pi * phase)
    # Dawn phenomenon (slight rise 04:00–07:00)
    if 4 <= hour <= 7:
        circadian += 8 * ((hour - 4) / 3)
    return circadian + spikes + random.gauss(0, 3)

def _heart_rate_at(t: datetime) -> float:
    """Resting ~60–70 bpm, circadian variation, exercise bouts."""
    hour = t.hour + t.minute / 60.0
    # Circadian baseline
    resting = 65 + 5 * math.sin(2 * math.pi * (hour - 14) / 24)
    # Sleep reduction
    if 0 <= hour < 6:
        resting -= 8
    # Exercise bouts: ~07:00 (morning jog) and ~17:30 (evening workout)
    for ex_h, peak, dur in [(7.0, 50, 0.75), (17.5, 45, 1.0)]:
        delta = (hour - ex_h) % 24
        if delta > 12:
            delta -= 24
        if 0 <= delta <= dur:
            phase = delta / dur
            resting += peak * math.sin(math.pi * phase)
    return max(45, resting + random.gauss(0, 2.5))

def _hrv_at(t: datetime, hr: float) -> float:
    """HRV (ms) inversely correlated with HR."""
    base = 120 - 0.8 * hr  # higher HR → lower HRV
    circadian_boost = 15 * math.sin(2 * math.pi * (t.hour - 3) / 24)
    return max(15, base + circadian_boost + random.gauss(0, 5))

def _steps_at(t: datetime) -> float:
    """Steps per 5-min window, realistic daily pattern."""
    hour = t.hour + t.minute / 60.0
    if 0 <= hour < 6:  # sleeping
        return 0
    if 6 <= hour < 7:  # waking up
        return random.randint(5, 30)
    # Walking/commute windows
    base = 20
    for walk_h, peak, dur in [(7.0, 400, 0.75), (8.0, 300, 0.5),
                               (12.0, 200, 0.5), (17.5, 350, 1.0),
                               (19.0, 150, 0.5), (21.0, 80, 0.5)]:
        delta = (hour - walk_h) % 24
        if delta > 12:
            delta -= 24
        if 0 <= delta <= dur:
            phase = delta / dur
            base += peak * math.sin(math.pi * phase)
    return max(0, int(base + random.gauss(0, 15)))

# ── Main seed function ──────────────────────────────────────────────

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
    random.seed(42)  # reproducible defaults
    counts: Dict[str, int] = {}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(hours=SEED_HOURS)

    # ── 1. Consent: grant all scopes ────────────────────────────────
    from .privacy.consent_manager import ConsentScope
    for scope_str in DEFAULT_SCOPES:
        try:
            scope = ConsentScope(scope_str)
            consent_manager.grant_consent(DEMO_USER, scope, "seed_default")
        except (ValueError, Exception):
            pass
    counts["consent_scopes"] = len(DEFAULT_SCOPES)

    # ── 2. Genetic profile ──────────────────────────────────────────
    gen_reading = BiomarkerReading(
        source_id="genetic_profile",
        user_id=DEMO_USER,
        biomarker_type=BiomarkerType.GENOTYPE,
        timestamp=now,
        value=len(DEFAULT_GENOTYPES),
        unit="variants",
        metadata={"genotypes": DEFAULT_GENOTYPES},
    )
    await genetic_adapter.push_reading(gen_reading)
    counts["genotype"] = 1

    # ── 3. CGM glucose (every 5 min for 72 h = 864 readings) ───────
    t = start
    glucose_count = 0
    while t < now:
        r = BiomarkerReading(
            source_id="cgm-dexcom-g7",
            user_id=DEMO_USER,
            biomarker_type=BiomarkerType.GLUCOSE,
            timestamp=t,
            value=round(_glucose_at(t), 1),
            unit="mg/dL",
            confidence=0.95 + random.uniform(-0.03, 0.03),
        )
        await cgm_adapter.push_reading(r)
        glucose_count += 1
        t += timedelta(minutes=5)
    counts["glucose"] = glucose_count

    # ── 4. Heart rate (every 5 min = 864 readings) ─────────────────
    t = start
    hr_count = 0
    while t < now:
        hr = round(_heart_rate_at(t), 1)
        r = BiomarkerReading(
            source_id="watch-apple-ultra",
            user_id=DEMO_USER,
            biomarker_type=BiomarkerType.HEART_RATE,
            timestamp=t,
            value=hr,
            unit="bpm",
            confidence=0.97,
        )
        await activity_adapter.push_reading(r)
        hr_count += 1

        # HRV every 15 min
        if t.minute % 15 == 0:
            hrv = round(_hrv_at(t, hr), 1)
            r_hrv = BiomarkerReading(
                source_id="watch-apple-ultra",
                user_id=DEMO_USER,
                biomarker_type=BiomarkerType.HRV,
                timestamp=t,
                value=hrv,
                unit="ms",
                confidence=0.90,
            )
            await activity_adapter.push_reading(r_hrv)

        t += timedelta(minutes=5)
    counts["heart_rate"] = hr_count

    # ── 5. Steps (every 5 min) ─────────────────────────────────────
    t = start
    step_count = 0
    while t < now:
        steps = _steps_at(t)
        r = BiomarkerReading(
            source_id="watch-apple-ultra",
            user_id=DEMO_USER,
            biomarker_type=BiomarkerType.STEPS,
            timestamp=t,
            value=float(steps),
            unit="steps",
            confidence=0.99,
        )
        await activity_adapter.push_reading(r)
        step_count += 1
        t += timedelta(minutes=5)
    counts["steps"] = step_count

    # ── 6. Sleep sessions (1 per night, 3 nights) ──────────────────
    sleep_count = 0
    for day_offset in range(3):
        bed_time = (start + timedelta(days=day_offset)).replace(
            hour=23, minute=random.randint(0, 30), second=0, microsecond=0
        )
        wake_time = bed_time + timedelta(hours=random.uniform(6.5, 8.0))
        if wake_time > now:
            wake_time = now
        sleep_hours = (wake_time - bed_time).total_seconds() / 3600
        quality = random.choice(["good", "fair", "good", "excellent"])
        r = BiomarkerReading(
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
                "deep_sleep_pct": round(random.uniform(0.15, 0.25), 2),
                "rem_pct": round(random.uniform(0.18, 0.25), 2),
                "awakenings": random.randint(0, 3),
            },
        )
        await sleep_adapter.push_reading(r)
        sleep_count += 1
        # Register sleep event with metabolic estimator
        try:
            metabolic_estimator.record_sleep_event(
                DEMO_USER, bed_time, wake_time,
                quality=0.8 if quality in ("good", "excellent") else 0.5,
            )
        except Exception:
            pass
    counts["sleep"] = sleep_count

    # ── 7. Meal events for metabolic estimator ─────────────────────
    meal_count = 0
    for day_offset in range(3):
        day_base = (start + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for meal_hour in [7.5, 12.5, 19.0]:
            meal_time = day_base + timedelta(hours=meal_hour + random.uniform(-0.25, 0.25))
            if meal_time > now:
                continue
            try:
                metabolic_estimator.record_meal_event(DEMO_USER, meal_time)
                meal_count += 1
            except Exception:
                pass
    counts["meal_events"] = meal_count

    # ── 8. Exercise events ─────────────────────────────────────────
    ex_count = 0
    for day_offset in range(3):
        day_base = (start + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Morning jog ~07:00, evening workout ~17:30
        for ex_hour, duration, intensity in [(7.0, 35, "moderate"), (17.5, 50, "high")]:
            ex_time = day_base + timedelta(hours=ex_hour + random.uniform(-0.1, 0.1))
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

    # ── 9. Location context (2-3 per day, simulating daily routine) ─
    loc_count = 0
    if location_adapter is not None:
        # Daily routine: home → office → gym → home
        location_patterns = [
            {"hour": 7.0, "lat": 37.5665, "lon": 126.9780, "alt": 38.0,
             "temp": 15.0, "venue": "home"},
            {"hour": 9.0, "lat": 37.5700, "lon": 126.9820, "alt": 42.0,
             "temp": 18.0, "venue": "office"},
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
                r = BiomarkerReading(
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
                )
                await location_adapter.push_reading(r)
                loc_count += 1
    counts["location"] = loc_count

    random.seed()  # restore true randomness
    return counts

# TODO: add comprehensive tests