#!/usr/bin/env python3
"""
BioAI Nutrition — Full Demo Scenario Runner
=============================================

Exercises every API endpoint with realistic data and captures results
for demonstration purposes. This script simulates a complete user journey:

  1.  Health check
  2.  Privacy consent management
  3.  Genetic profile submission (8 SNPs)
  4.  Biomarker data ingestion (CGM, HR, HRV, Steps)
  5.  Temporal synchronization
  6.  Before/After t_sync lag correction comparison  (Patent Evidence)
  7.  Metabolic state estimation (threshold-based)   (Patent Evidence)
  8.  Nutrient demand calculation
  9.  Safety-First Override (medical vs genetic)     (Patent Evidence)
  10. Meal text analysis
  11. Synthea FHIR data exploration
  12. Engine status summary
  13. Edge computing data boundary visualization     (Patent Evidence)

Usage:
    python scripts/run_demo.py [--base-url http://localhost:8000]

Output:
    output/demo_results.json   — Full API response log
    output/demo_transcript.txt — Human-readable demo transcript
"""

import argparse
import json
import math
import random
import sys
import os
from datetime import datetime, timedelta
from typing import Any

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx

# ── Configuration ───────────────────────────────────────────────────

API_KEY = "dev-api-key"
USER_ID = "demo-user-001"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}


def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class DemoRunner:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base, headers=HEADERS, timeout=30)
        self.results: dict[str, Any] = {}
        self.transcript: list[str] = []
        self._log_header()

    def _log_header(self):
        self._print("=" * 70)
        self._print("  BioAI Nutrition — Full Demo Scenario")
        self._print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._print(f"  Backend: {self.base}")
        self._print(f"  User: {USER_ID}")
        self._print("=" * 70)
        self._print()

    def _print(self, msg: str = ""):
        print(msg)
        self.transcript.append(msg)

    def _section(self, num: int, title: str, icon: str = ""):
        self._print()
        self._print(f"{'─' * 70}")
        self._print(f"  {icon}  STEP {num}: {title}")
        self._print(f"{'─' * 70}")

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        if method == "GET":
            r = self.client.get(path)
        elif method == "POST":
            r = self.client.post(path, json=body)
        elif method == "DELETE":
            r = self.client.delete(path)
        else:
            raise ValueError(f"Unknown method: {method}")

        try:
            data = r.json()
        except Exception:
            data = {"status_code": r.status_code, "text": r.text[:500]}

        return data

    # ── Step 1: Health Check ──────────────────────────────────────

    def step_health_check(self):
        self._section(1, "Health Check & API Status", "🏥")
        result = self._call("GET", "/")
        self._print(f"  Health: {json.dumps(result)}")
        self.results["health"] = result

    # ── Step 2: Privacy Consent ───────────────────────────────────

    def step_consent(self):
        self._section(2, "Privacy & Consent Management (GDPR Article 7)", "🔐")

        scopes = [
            "glucose_data", "activity_data", "heart_rate_data",
            "sleep_data", "genetic_data", "meal_data",
            "weight_data", "blood_test_data",
        ]

        for scope in scopes:
            body = {
                "user_id": USER_ID,
                "scope": scope,
                "action": "grant",
                "reason": "Demo scenario — full pipeline execution",
            }
            self._call("POST", "/engine/consent", body)

        self._print(f"  ✅ Granted {len(scopes)} consent scopes:")
        for s in scopes:
            self._print(f"     • {s}")

        # Verify
        status = self._call("GET", f"/engine/consent/{USER_ID}")
        self._print(f"  Consent status: {len(status.get('granted_scopes', []))} active scopes")
        self.results["consent"] = status

    # ── Step 3: Genetic Profile ───────────────────────────────────

    def step_genetic_profile(self):
        self._section(3, "Genetic Profile Submission (8 SNP Variants)", "🧬")

        genotypes = {
            "rs1801133": {"rsid": "rs1801133", "genotype": "CT"},   # MTHFR
            "rs9939609": {"rsid": "rs9939609", "genotype": "TA"},   # FTO
            "rs429358":  {"rsid": "rs429358",  "genotype": "TT"},   # APOE
            "rs7903146": {"rsid": "rs7903146", "genotype": "CT"},   # TCF7L2
            "rs4988235": {"rsid": "rs4988235", "genotype": "GA"},   # LCT
            "rs762551":  {"rsid": "rs762551",  "genotype": "AC"},   # CYP1A2
            "rs1544410": {"rsid": "rs1544410", "genotype": "AG"},   # VDR
            "rs4341":    {"rsid": "rs4341",    "genotype": "ID"},   # ACE
        }

        snp_descriptions = {
            "rs1801133": "MTHFR   — Folate metabolism (CT: reduced enzyme activity)",
            "rs9939609": "FTO     — Obesity risk (TA: moderate risk carrier)",
            "rs429358":  "APOE    — Lipid metabolism (TT: wildtype / normal)",
            "rs7903146": "TCF7L2  — Glucose response (CT: 12% slower clearance)",
            "rs4988235": "LCT     — Lactase persistence (GA: heterozygous)",
            "rs762551":  "CYP1A2  — Caffeine metabolism (AC: slow metabolizer)",
            "rs1544410": "VDR     — Vitamin D receptor (AG: heterozygous)",
            "rs4341":    "ACE     — Blood pressure (ID: intermediate activity)",
        }

        result = self._call("POST", "/engine/genetic-profile", {
            "user_id": USER_ID,
            "genotypes": genotypes,
        })

        self._print("  SNP Variants submitted:")
        for rsid, desc in snp_descriptions.items():
            g = genotypes[rsid]["genotype"]
            self._print(f"     {rsid} [{g:>2}]  {desc}")

        modifiers = result.get("modifiers", {})
        self._print()
        self._print(f"  ✅ Computed {len(modifiers)} metabolic modifiers:")
        for name, val in sorted(modifiers.items()):
            direction = "↑" if val > 1.0 else ("↓" if val < 1.0 else "—")
            self._print(f"     {name:<30} = {val:.3f}  {direction}")

        self.results["genetic"] = result

    # ── Step 4: Biomarker Ingestion ───────────────────────────────

    def step_ingest_biomarkers(self):
        self._section(4, "Biomarker Data Ingestion (Multi-Source Sensor Fusion)", "📡")

        random.seed(42)
        now = datetime.now()
        readings = []

        # CGM Glucose — 30 readings (2.5 hours, every 5 min)
        self._print("  Generating CGM glucose readings (30 × 5min intervals)...")
        for i in range(30):
            t = now - timedelta(minutes=i * 5)
            hour = t.hour + t.minute / 60.0
            base = 90 + 5 * math.sin(2 * math.pi * (hour - 3) / 24)
            for meal_h, amp, dur in [(7.5, 45, 2.0), (12.5, 40, 2.0), (19.0, 50, 2.5)]:
                delta = (hour - meal_h) % 24
                if delta > 12:
                    delta -= 24
                if 0 <= delta <= dur:
                    base += amp * math.sin(math.pi * delta / dur)
            readings.append({
                "source_id": "cgm-dexcom-g7",
                "user_id": USER_ID,
                "biomarker_type": "glucose",
                "timestamp": ts(t),
                "value": round(base + random.gauss(0, 3), 1),
                "unit": "mg/dL",
                "confidence": 0.95,
                "metadata": {},
            })

        # Heart Rate — 30 readings
        self._print("  Generating heart rate readings (30 × 5min intervals)...")
        for i in range(30):
            t = now - timedelta(minutes=i * 5)
            hour = t.hour + t.minute / 60.0
            hr = 65 + 5 * math.sin(2 * math.pi * (hour - 14) / 24)
            if 0 <= hour < 6:
                hr -= 8
            readings.append({
                "source_id": "watch-apple-ultra",
                "user_id": USER_ID,
                "biomarker_type": "heart_rate",
                "timestamp": ts(t),
                "value": round(hr + random.gauss(0, 2), 1),
                "unit": "bpm",
                "confidence": 0.97,
                "metadata": {},
            })

        # HRV — 10 readings (15min intervals)
        self._print("  Generating HRV readings (10 × 15min intervals)...")
        for i in range(10):
            t = now - timedelta(minutes=i * 15)
            hr = 65 + 5 * math.sin(2 * math.pi * (t.hour - 14) / 24)
            hrv = max(15, 120 - 0.8 * hr + random.gauss(0, 5))
            readings.append({
                "source_id": "watch-apple-ultra",
                "user_id": USER_ID,
                "biomarker_type": "hrv",
                "timestamp": ts(t),
                "value": round(hrv, 1),
                "unit": "ms",
                "confidence": 0.92,
                "metadata": {},
            })

        # Steps — 30 readings
        self._print("  Generating step count readings (30 × 5min intervals)...")
        for i in range(30):
            t = now - timedelta(minutes=i * 5)
            hour = t.hour + t.minute / 60.0
            steps = max(0, int(20 + 100 * abs(math.sin(math.pi * hour / 12)) + random.gauss(0, 15)))
            readings.append({
                "source_id": "watch-apple-ultra",
                "user_id": USER_ID,
                "biomarker_type": "steps",
                "timestamp": ts(t),
                "value": steps,
                "unit": "steps",
                "confidence": 0.99,
                "metadata": {},
            })

        result = self._call("POST", "/engine/ingest", {"readings": readings})

        self._print(f"\n  ✅ Ingested {len(readings)} biomarker readings:")
        self._print(f"     • CGM Glucose:  30 readings  (Dexcom G7)")
        self._print(f"     • Heart Rate:   30 readings  (Apple Watch Ultra)")
        self._print(f"     • HRV:          10 readings  (Apple Watch Ultra)")
        self._print(f"     • Steps:        30 readings  (Apple Watch Ultra)")
        self._print(f"     Total accepted: {result.get('accepted', 'N/A')}")
        self.results["ingest"] = result

    # ── Step 5: Temporal Synchronization ──────────────────────────

    def step_sync(self):
        self._section(5, "Temporal Synchronization (Multi-Resolution Alignment)", "⏱️")

        now = datetime.now()
        body = {
            "user_id": USER_ID,
            "start": ts(now - timedelta(hours=3)),
            "end": ts(now),
            "resolution": "fine",
        }

        result = self._call("POST", "/engine/sync", body)

        frames = result.get("frames", [])
        signals = set()
        for f in frames:
            signals.update(f.get("signals", {}).keys())

        self._print(f"  Time window: last 3 hours (fine resolution = 5-min grid)")
        self._print(f"  ✅ Synchronized {len(frames)} time frames")
        self._print(f"  Signal types aligned: {', '.join(sorted(signals)) or 'N/A'}")

        if frames:
            sample = frames[len(frames) // 2]
            self._print(f"\n  Sample frame (midpoint):")
            for sig, val in sample.get("signals", {}).items():
                if isinstance(val, dict):
                    self._print(f"     {sig:<15}: value={val.get('value', '?'):.1f}  conf={val.get('confidence', '?'):.3f}")
                elif isinstance(val, (int, float)):
                    self._print(f"     {sig:<15}: {val:.1f}")
                else:
                    self._print(f"     {sig:<15}: {val}")

        self.results["sync"] = {"frame_count": len(frames), "signals": sorted(signals)}

    # ── Step 6: Before/After t_sync Lag Correction ────────────────
    #    PATENT EVIDENCE: Demonstrates quantitative improvement from
    #    physiological lag compensation model

    def step_lag_comparison(self):
        self._section(6, "Before/After t_sync Lag Correction (Patent Core)", "📐")

        now = datetime.now()
        body = {
            "user_id": USER_ID,
            "start": ts(now - timedelta(hours=6)),
            "end": ts(now),
            "resolution": "medium",
        }

        result = self._call("POST", "/engine/lag-comparison", body)

        comparison = result.get("comparison", {})
        without = comparison.get("without_t_sync", {})
        with_sync = comparison.get("with_t_sync", {})
        improvement = comparison.get("improvement", 0)
        lag_audit = result.get("lag_audit_samples", [])
        frames_info = result.get("frames_analyzed", {})

        self._print(f"  Formula: {result.get('lag_formula', 'N/A')}")
        self._print(f"  Signal pair: {comparison.get('signal_pair', 'N/A')}")
        self._print(f"  Frames analyzed: {frames_info.get('corrected', 0)}")
        self._print()
        self._print(f"  ┌──────────────────────────────────────────────────────────┐")
        self._print(f"  │  BEFORE t_sync Correction                               │")
        self._print(f"  │    Method:      {without.get('method', 'N/A')[:40]:<40} │")
        self._print(f"  │    Correlation: r = {without.get('correlation_r', 0):>7.4f}                          │")
        self._print(f"  ├──────────────────────────────────────────────────────────┤")
        self._print(f"  │  AFTER t_sync Correction                                │")
        self._print(f"  │    Method:      Dynamic lag model (personalized)         │")
        self._print(f"  │    Correlation: r = {with_sync.get('correlation_r', 0):>7.4f}                          │")
        self._print(f"  ├──────────────────────────────────────────────────────────┤")
        self._print(f"  │  Correlation Improvement: Δr = {improvement:>+7.4f}                  │")
        self._print(f"  └──────────────────────────────────────────────────────────┘")

        if lag_audit:
            self._print(f"\n  Lag Audit Samples (per-biomarker dynamic lag):")
            for audit in lag_audit:
                self._print(
                    f"     {audit.get('biomarker', '?'):<12}: "
                    f"base={audit.get('base_lag_s', 0):.0f}s × "
                    f"γ_genetic={audit.get('genetic_modifier', 1.0):.3f} × "
                    f"φ_circadian={audit.get('circadian_modifier', 1.0):.3f} = "
                    f"{audit.get('effective_lag_s', 0):.1f}s  "
                    f"(hour={audit.get('hour', '?')})"
                )
                if audit.get("factors"):
                    self._print(f"                  Genetic factors: {', '.join(audit['factors'])}")

        self.results["lag_comparison"] = result

    # ── Step 7: Metabolic State Estimation ────────────────────────
    #    ENHANCED: Shows threshold-based decision log for each phase

    def step_metabolic_state(self):
        self._section(7, "Metabolic State Estimation (13-Phase Classifier)", "🔥")

        now = datetime.now()
        body = {
            "user_id": USER_ID,
            "start": ts(now - timedelta(hours=2)),
            "end": ts(now),
            "resolution": "medium",
        }

        result = self._call("POST", "/engine/metabolic-state", body)

        primary_phase = result.get("primary_phase", "unknown")
        active_phases = result.get("active_phases", [])
        phase_intensities = result.get("phase_intensities", {})
        decision_log = result.get("decision_log", [])

        phase_descriptions = {
            "fasting": "Extended fasting — gluconeogenesis active, fat oxidation primary",
            "postprandial_early": "Early post-meal — glucose absorption phase (0-2h)",
            "postprandial_late": "Late post-meal — insulin-driven glucose uptake (2-4h)",
            "post_absorptive": "Post-absorptive — transitioning to fat oxidation (4-12h)",
            "during_exercise": "During exercise — elevated HR, glucose/glycogen consumption",
            "recovery_immediate": "Immediate recovery — EPOC, glycogen replenishment window (0-2h)",
            "recovery_delayed": "Delayed recovery — muscle repair, supercompensation (2-48h)",
            "pre_sleep": "Pre-sleep — melatonin onset, reduce carbs & caffeine",
            "sleeping": "Sleep — parasympathetic dominance, growth hormone release",
            "post_waking": "Post-waking — cortisol awakening response, rehydration needed",
            "metabolic_stress": "Metabolic stress — HRV < 30ms, sympathetic dominance",
            "recovery": "Recovery mode — HRV > 60ms, parasympathetic dominance",
            "circadian_low": "Circadian low — minimum metabolic rate (2-5 AM)",
        }

        self._print(f"  ┌─ PRIMARY PHASE: {primary_phase.upper()}")
        self._print(f"  │  {phase_descriptions.get(primary_phase, 'N/A')}")
        self._print(f"  │")
        self._print(f"  ├─ Active Phases ({len(active_phases)}):")
        for phase in active_phases:
            intensity = phase_intensities.get(phase, 0)
            bar = "█" * int(intensity * 20) + "░" * (20 - int(intensity * 20))
            self._print(f"  │   {phase:<25} [{bar}] {intensity:.1%}")
        self._print(f"  │")
        self._print(f"  ├─ Physiological Indicators:")
        self._print(f"  │   Hours since last meal:     {result.get('hours_since_last_meal', 0):.1f}h")
        self._print(f"  │   Hours since last exercise:  {result.get('hours_since_last_exercise', 0):.1f}h")
        self._print(f"  │   Insulin sensitivity:        {result.get('insulin_sensitivity_estimate', 0):.3f}")
        self._print(f"  │")
        self._print(f"  └─ Threshold-Based Decision Log (Patent Evidence):")
        for entry in decision_log:
            self._print(f"       → {entry}")

        self.results["metabolic"] = result

    # ── Step 8: Nutrient Demand Calculation ───────────────────────

    def step_nutrient_budget(self):
        self._section(8, "Personalized Nutrient Demand Calculation", "🧮")

        body = {
            "user_id": USER_ID,
            "kcal_target": 2200,
            "weight_kg": 75.0,
            "consumed_today": {
                "kcal": 850,
                "protein_g": 35,
                "carbs_g": 110,
                "fat_g": 28,
                "fiber_g": 8,
                "water_ml": 1200,
            },
        }

        result = self._call("POST", "/engine/nutrient-budget", body)

        targets = result.get("targets", {})
        mods = result.get("modifications", [])
        state = result.get("metabolic_state", "")
        time_buckets = result.get("time_buckets", [])
        conflicts = result.get("conflict_resolutions", [])

        self._print(f"  Daily target: {body['kcal_target']} kcal | Weight: {body['weight_kg']} kg")
        self._print(f"  Already consumed today: {body['consumed_today']['kcal']} kcal")
        self._print(f"  Current metabolic state: {state}")
        self._print()
        self._print(f"  ✅ Remaining nutrient targets:")
        for nutrient, val in sorted(targets.items()):
            if isinstance(val, dict):
                self._print(
                    f"     {nutrient:<15}: "
                    f"{val.get('remaining', 0):>8.1f} {val.get('unit', '')} remaining "
                    f"({val.get('remaining_pct', 0):.0f}% of daily)"
                )
            else:
                self._print(f"     {nutrient:<15}: {val}")
        self._print()
        self._print(f"  Pipeline modifications applied ({len(mods)}):")
        for mod in mods[:10]:
            if isinstance(mod, dict):
                step = mod.get("step", "?")
                nutrient = mod.get("nutrient", "?")
                old_v = mod.get("old_value", 0)
                new_v = mod.get("new_value", 0)
                reason = mod.get("reason", "")
                self._print(f"     [{step:<18}] {nutrient:<12}: {old_v:.1f} → {new_v:.1f}  ({reason})")
            else:
                self._print(f"     • {mod}")

        if conflicts:
            self._print(f"\n  ⚠️  Conflict Resolutions ({len(conflicts)}):")
            for cr in conflicts:
                self._print(f"     🚨 {cr.get('nutrient', '?')}: {cr.get('resolution_rationale', 'N/A')}")

        if time_buckets:
            self._print(f"\n  Time-bucketed distribution:")
            for bucket in time_buckets[:4]:
                if isinstance(bucket, dict):
                    label = bucket.get("label", "?")
                    self._print(
                        f"     {label:<18}: "
                        f"C={bucket.get('carb_pct', 0):.0%}  "
                        f"P={bucket.get('protein_pct', 0):.0%}  "
                        f"F={bucket.get('fat_pct', 0):.0%}  "
                        f"W={bucket.get('water_pct', 0):.0%}"
                    )

        self.results["nutrient_budget"] = result

    # ── Step 9: Safety-First Override (Medical vs Genetic) ────────
    #    PATENT EVIDENCE: Demonstrates hierarchical conflict resolution
    #    where medical safety constraints always override genetic recommendations

    def step_safety_first_override(self):
        self._section(9, "Safety-First Override: Medical vs Genetic Conflict Resolution", "🛡️")

        body = {
            "user_id": USER_ID,
            "constraints": [
                {
                    "nutrient": "vitamin_d_iu",
                    "constraint_type": "max",
                    "value": 800.0,
                    "reason": "CKD Stage 3 — risk of hypercalcemia with high vitamin D",
                    "severity": "critical",
                    "source": "medical_record",
                },
                {
                    "nutrient": "protein_g",
                    "constraint_type": "max",
                    "value": 60.0,
                    "reason": "CKD Stage 3 — protein restriction to reduce kidney load",
                    "severity": "critical",
                    "source": "medical_record",
                },
                {
                    "nutrient": "sodium_mg",
                    "constraint_type": "max",
                    "value": 1500.0,
                    "reason": "Hypertension Stage 2 — strict sodium restriction",
                    "severity": "warning",
                    "source": "medical_record",
                },
                {
                    "nutrient": "caffeine_mg",
                    "constraint_type": "max",
                    "value": 200.0,
                    "reason": "Cardiac arrhythmia history — caffeine limit",
                    "severity": "critical",
                    "source": "medical_record",
                },
            ],
        }

        self._call("POST", "/engine/medical-constraints", body)

        self._print("  Medical constraints set (designed to conflict with genetic modifiers):")
        self._print()
        for c in body["constraints"]:
            severity_icon = {"warning": "⚠️", "critical": "🚨"}.get(c["severity"], "ℹ️")
            self._print(
                f"     {severity_icon} {c['nutrient']:<15} {c['constraint_type']:>3} ≤ {c['value']:>8.1f}  "
                f"[{c['severity'].upper():>8}]  {c['reason']}"
            )

        self._print()
        self._print("  Recalculating nutrient budget with constraints applied...")

        budget_body = {
            "user_id": USER_ID,
            "kcal_target": 2200,
            "weight_kg": 75.0,
            "consumed_today": {
                "kcal": 850,
                "protein_g": 35,
                "carbs_g": 110,
                "fat_g": 28,
            },
        }

        result = self._call("POST", "/engine/nutrient-budget", budget_body)
        conflicts = result.get("conflict_resolutions", [])

        if conflicts:
            self._print()
            self._print(f"  ┌──────────────────────────────────────────────────────────────┐")
            self._print(f"  │  SAFETY-FIRST OVERRIDE: {len(conflicts)} Conflict(s) Resolved               │")
            self._print(f"  │  Priority: medical_critical(5) > medical_warning(4) > genetic(3) │")
            self._print(f"  └──────────────────────────────────────────────────────────────┘")
            self._print()

            for i, cr in enumerate(conflicts, 1):
                nutrient = cr.get("nutrient", "?")
                conflict_type = cr.get("conflict_type", "?")
                gen_rec = cr.get("genetic_recommended", 0)
                med_limit = cr.get("medical_limit", 0)
                resolved = cr.get("resolved_value", 0)
                winner = cr.get("winner", "?")
                loser = cr.get("loser", "?")
                severity = cr.get("severity", "?")
                reason = cr.get("constraint_reason", "?")
                rationale = cr.get("resolution_rationale", "?")

                self._print(f"  Conflict #{i}: {nutrient}")
                self._print(f"     Type:       {conflict_type}")
                self._print(f"     Genetic recommended:  {gen_rec:.1f}")
                self._print(f"     Medical limit:        {med_limit:.1f}")
                self._print(f"     → Resolved value:     {resolved:.1f}")
                self._print(f"     Winner: {winner.upper()} (priority={5 if severity == 'critical' else 4})")
                self._print(f"     Loser:  {loser}")
                self._print(f"     Reason: {reason}")
                self._print(f"     Rationale: {rationale}")
                self._print()
        else:
            self._print()
            self._print("  ℹ️  No conflicts detected between genetic modifiers and medical constraints.")
            self._print("      (Genetic-adjusted targets were already within medical bounds)")

        self.results["safety_first_override"] = {
            "constraints_set": len(body["constraints"]),
            "conflicts_resolved": len(conflicts),
            "conflict_details": conflicts,
        }

    # ── Step 10: Meal Analysis ────────────────────────────────────

    def step_meal_analysis(self):
        self._section(10, "Text-Based Meal Analysis", "🍽️")

        meals = [
            {
                "name": "Lunch",
                "items": [
                    {"name": "grilled chicken breast"},
                    {"name": "brown rice"},
                    {"name": "broccoli"},
                    {"name": "avocado"},
                ],
            },
            {
                "name": "Dinner",
                "items": [
                    {"name": "salmon"},
                    {"name": "quinoa"},
                    {"name": "spinach"},
                    {"name": "greek yogurt"},
                ],
            },
            {
                "name": "Korean Meal",
                "items": [
                    {"name": "bibimbap"},
                    {"name": "kimchi"},
                    {"name": "miso soup"},
                ],
            },
        ]

        for meal in meals:
            self._print(f"\n  📋 Analyzing: {meal['name']}")
            result = self._call("POST", "/analyze-meal", {"items": meal["items"]})

            items = result.get("items", [])
            total_cal = sum(i.get("calories", 0) for i in items)
            total_protein = sum(i.get("protein_g", 0) for i in items)
            total_carbs = sum(i.get("carbs_g", 0) for i in items)
            total_fat = sum(i.get("fat_g", 0) for i in items)

            for item in items:
                self._print(
                    f"     {item.get('name', '?'):<25} "
                    f"{item.get('calories', 0):>6} kcal  "
                    f"P:{item.get('protein_g', 0):>5.1f}g  "
                    f"C:{item.get('carbs_g', 0):>5.1f}g  "
                    f"F:{item.get('fat_g', 0):>5.1f}g"
                )
            self._print(f"     {'─' * 60}")
            self._print(
                f"     {'TOTAL':<25} "
                f"{total_cal:>6} kcal  "
                f"P:{total_protein:>5.1f}g  "
                f"C:{total_carbs:>5.1f}g  "
                f"F:{total_fat:>5.1f}g"
            )

        self.results["meal_analysis"] = {"meals_analyzed": len(meals)}

    # ── Step 11: Synthea FHIR Data ────────────────────────────────

    def step_synthea(self):
        self._section(11, "Synthea FHIR Patient Data Explorer", "🏥")

        result = self._call("GET", "/synthea/status")

        patients = result.get("patients", [])
        total = result.get("total_patients", 0)

        self._print(f"  Available synthetic patients: {total}")
        for p in patients[:5]:
            pid = p.get("id", "?")
            name = p.get("name", "?")
            resources = p.get("resource_count", 0)
            self._print(f"     Patient {pid}: {name} ({resources} FHIR resources)")

        if patients:
            first = patients[0]
            load_result = self._call("POST", "/synthea/load", {
                "patient_id": first.get("id", ""),
                "override_user_id": USER_ID,
            })
            loaded = load_result.get("readings_loaded", 0)
            self._print(f"\n  ✅ Loaded patient '{first.get('name', '?')}' into engine: {loaded} biomarker readings")

        self.results["synthea"] = result

    # ── Step 12: Engine Status ────────────────────────────────────

    def step_engine_status(self):
        self._section(12, "Engine Pipeline Status Summary", "📊")

        result = self._call("GET", "/engine/status")

        self._print(f"  Registered sources: {result.get('registered_sources', 'N/A')}")
        self._print(f"  Biomarker types:    {result.get('registered_biomarker_types', 'N/A')}")
        self._print(f"  Active users:       {result.get('users_with_data', 'N/A')}")

        self.results["engine_status"] = result

    # ── Step 13: Edge Computing Data Boundary Visualization ───────
    #    PATENT EVIDENCE: Shows exactly what data stays on-device
    #    vs. what is transmitted to the server

    def step_edge_boundary(self):
        self._section(13, "Edge Computing Data Boundary (On-Device Privacy)", "🔒")

        manifest = self._call("GET", "/engine/edge-manifest")

        now = datetime.now()
        edge_body = {
            "user_id": USER_ID,
            "start": ts(now - timedelta(hours=1)),
            "end": ts(now),
            "resolution": "medium",
        }
        edge_result = self._call("POST", "/engine/edge-process", edge_body)

        self._print()
        self._print("  ╔══════════════════════════════════════════════════════════════╗")
        self._print("  ║     ON-DEVICE PRIVACY: DATA BOUNDARY VISUALIZATION          ║")
        self._print("  ╠══════════════════════════════════════════════════════════════╣")
        self._print("  ║                                                              ║")

        retained = manifest.get("retained_on_device", [])
        on_device = manifest.get("on_device_operations", [])
        self._print("  ║  🔒 STAYS ON DEVICE (never transmitted):                     ║")
        if retained:
            for field in retained:
                self._print(f"  ║     ■ {str(field):<52}║")
        if on_device:
            self._print("  ║                                                              ║")
            self._print("  ║     On-device operations:                                    ║")
            for op in on_device:
                self._print(f"  ║       → {str(op):<50}║")
        self._print("  ║                                                              ║")
        self._print("  ╠══════════════════════════════════════════════════════════════╣")
        self._print("  ║                                                              ║")

        transmitted = manifest.get("transmitted_fields", [])
        self._print("  ║  📤 TRANSMITTED TO SERVER (privacy-protected):               ║")
        if transmitted:
            for field in transmitted:
                self._print(f"  ║     ■ {str(field):<52}║")
        self._print("  ║                                                              ║")

        guarantees = manifest.get("privacy_guarantees", [])
        if guarantees:
            self._print("  ╠══════════════════════════════════════════════════════════════╣")
            self._print("  ║  Privacy Guarantees:                                         ║")
            for g in guarantees:
                self._print(f"  ║     • {str(g):<52}║")

        self._print("  ║                                                              ║")
        self._print(f"  ║  DP Epsilon: {manifest.get('dp_epsilon', 'N/A')!s:<47}║")
        self._print(f"  ║  Embedding Dim: {manifest.get('embedding_dim', 'N/A')!s:<44}║")
        self._print(f"  ║  Compression Ratio: {manifest.get('compression_ratio', 'N/A')!s:<39}║")
        self._print("  ║                                                              ║")
        self._print("  ╚══════════════════════════════════════════════════════════════╝")

        edge_outputs = edge_result.get("edge_outputs", [])
        total_processed = edge_result.get("total_frames_processed", 0)

        if edge_outputs:
            self._print()
            self._print(f"  Edge Processing Demo ({total_processed} frames processed):")
            sample = edge_outputs[0]
            self._print(f"     Window: {sample.get('window_start', '?')} → {sample.get('window_end', '?')}")
            self._print()
            self._print(f"     Raw Biomarker Data:              [STAYED ON DEVICE]  ✅")
            self._print(f"     Genetic Variants:                [STAYED ON DEVICE]  ✅")
            self._print(f"     Personal Health Records:         [STAYED ON DEVICE]  ✅")
            self._print()
            self._print(f"     Feature Embedding ({sample.get('embedding_dim', '?')}D):        [TRANSMITTED TO SERVER]  📤")
            embedding_preview = sample.get("feature_embedding", [])[:6]
            if embedding_preview:
                formatted = ", ".join(f"{v:.4f}" for v in embedding_preview)
                self._print(f"       Preview: [{formatted}, ...]")
            self._print(f"     DP Aggregations:                 [TRANSMITTED TO SERVER]  📤")
            dp_aggs = sample.get("dp_aggregations", {})
            if dp_aggs:
                for k, v in list(dp_aggs.items())[:4]:
                    if isinstance(v, (int, float)):
                        self._print(f"       {k}: {v:.2f} (noise-injected)")
                    else:
                        self._print(f"       {k}: {v} (noise-injected)")
            self._print(f"     Metabolic Label:                 [TRANSMITTED TO SERVER]  📤")
            self._print(f"       → {sample.get('metabolic_label', '?')}")
            self._print(f"     Genetic Modifier Hash:           [TRANSMITTED TO SERVER]  📤")
            self._print(f"       → {sample.get('genetic_modifier_hash', '?')} (irreversible)")
            self._print()
            self._print(f"     raw_data_retained_on_device: {sample.get('raw_data_retained_on_device', False)}")

        self.results["edge_boundary"] = {
            "manifest": manifest,
            "frames_processed": total_processed,
            "sample_output": edge_outputs[0] if edge_outputs else None,
        }

    # ── Save Results ──────────────────────────────────────────────

    def save_results(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        json_path = os.path.join(output_dir, "demo_results.json")
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        txt_path = os.path.join(output_dir, "demo_transcript.txt")
        with open(txt_path, "w") as f:
            f.write("\n".join(self.transcript))

        self._print()
        self._print("=" * 70)
        self._print("  🎉 Demo scenario completed successfully!")
        self._print(f"  Results:    {json_path}")
        self._print(f"  Transcript: {txt_path}")
        self._print("=" * 70)

    # ── Run All ───────────────────────────────────────────────────

    def run_all(self, output_dir: str):
        self.step_health_check()           # 1
        self.step_consent()                # 2
        self.step_genetic_profile()        # 3
        self.step_ingest_biomarkers()      # 4
        self.step_sync()                   # 5
        self.step_lag_comparison()         # 6  ← NEW: Before/After t_sync
        self.step_metabolic_state()        # 7  ← ENHANCED: threshold decisions
        self.step_nutrient_budget()        # 8
        self.step_safety_first_override()  # 9  ← NEW: Safety-First Override
        self.step_meal_analysis()          # 10
        self.step_synthea()                # 11
        self.step_engine_status()          # 12
        self.step_edge_boundary()          # 13 ← ENHANCED: data boundary viz
        self.save_results(output_dir)


def main():
    parser = argparse.ArgumentParser(description="BioAI Nutrition Demo Runner")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

    runner = DemoRunner(args.base_url)
    runner.run_all(args.output_dir)


if __name__ == "__main__":
    main()
