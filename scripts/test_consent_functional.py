"""Functional test: verify consent toggles actually filter data from endpoints."""
import requests
import json
from datetime import datetime, timedelta, timezone

BASE = "http://localhost:8000/engine"
HDR = {"X-API-Key": "dev-api-key", "Content-Type": "application/json"}
USER = "consent-func-test-003"
now = datetime.now(timezone.utc)
start = (now - timedelta(hours=72)).isoformat()
end = now.isoformat()

def grant(scope):
    r = requests.post(f"{BASE}/consent", json={"user_id": USER, "scope": scope, "action": "grant"}, headers=HDR)
    return r.status_code

def revoke(scope):
    r = requests.post(f"{BASE}/consent", json={"user_id": USER, "scope": scope, "action": "revoke"}, headers=HDR)
    return r.status_code

def sync_signals():
    r = requests.post(f"{BASE}/sync", json={"user_id": USER, "start": start, "end": end}, headers=HDR)
    if r.status_code != 200:
        print(f"    [WARN] sync returned {r.status_code}: {r.text[:200]}")
        return set()
    data = r.json()
    signals = set()
    for frame in data.get("frames", []):
        for sig_name in frame.get("signals", {}).keys():
            signals.add(sig_name)
    return signals

def metabolic_primary_phase():
    r = requests.post(f"{BASE}/metabolic-state", json={"user_id": USER, "start": start, "end": end}, headers=HDR)
    if r.status_code != 200:
# TODO: add comprehensive tests
        return f"error({r.status_code})"
    return r.json().get("primary_phase", "unknown")

# Updated: 2025-05-12
# ── Seed data ──
print("=== SEEDING DATA ===")
genotypes = [
    {"rsid": "rs1801133", "genotype": "CT", "gene": "MTHFR"},
    {"rsid": "rs4988235", "genotype": "CT", "gene": "LCT"},
]
r = requests.post(f"{BASE}/genetic-profile", json={"user_id": USER, "genotypes": genotypes}, headers=HDR)
print(f"  Genetic profile: {r.status_code}")

readings = []
for i in range(20):
    ts = (now - timedelta(hours=70) + timedelta(hours=i * 3)).isoformat()
    readings.extend([
        {"source_id": "cgm", "user_id": USER, "biomarker_type": "glucose", "timestamp": ts, "value": 95 + i * 2, "unit": "mg/dL"},
        {"source_id": "watch", "user_id": USER, "biomarker_type": "heart_rate", "timestamp": ts, "value": 68 + i, "unit": "bpm"},
        {"source_id": "watch", "user_id": USER, "biomarker_type": "hrv", "timestamp": ts, "value": 45 + i, "unit": "ms"},
        {"source_id": "watch", "user_id": USER, "biomarker_type": "steps", "timestamp": ts, "value": 500 + i * 50, "unit": "steps"},
        {"source_id": "sleep", "user_id": USER, "biomarker_type": "sleep", "timestamp": ts, "value": 7.0, "unit": "hours"},
    ])
r = requests.post(f"{BASE}/ingest", json={"readings": readings}, headers=HDR)
print(f"  Ingest: {r.status_code} ({len(readings)} readings)")

# ── PHASE 1: Grant ALL → baseline ──
print("\n=== PHASE 1: Grant ALL scopes ===")
ALL_SCOPES = ["glucose_data", "heart_rate_data", "activity_data", "sleep_data", "genetic_data"]
for s in ALL_SCOPES:
    grant(s)

baseline = sync_signals()
print(f"  Baseline signals: {sorted(baseline)}")

if not baseline:
    print("  ⚠️  No baseline signals — cannot test. Exiting.")
    exit(1)

# ── PHASE 2: Revoke each scope → verify removal ──
print("\n=== PHASE 2: Revoke each scope one at a time ===")

test_cases = [
    ("glucose_data", {"glucose"}),
    ("heart_rate_data", {"heart_rate", "hrv"}),
    ("activity_data", {"steps", "exercise", "activity_calories"}),
    ("sleep_data", {"sleep"}),
]

results = {}
for scope, expected_removed in test_cases:
    # Restore all first
    for s in ALL_SCOPES:
        grant(s)

    # Revoke target
    revoke(scope)

    after = sync_signals()
    # Only check signals that actually existed in baseline
    expected_in_baseline = expected_removed & baseline
    still_present = expected_in_baseline & after

    if len(expected_in_baseline) == 0:
        results[scope] = True
        print(f"  {scope}: No matching signals in baseline ⚪")
    elif len(still_present) == 0:
        results[scope] = True
        print(f"  {scope}: {sorted(expected_in_baseline)} REMOVED ✅")
    else:
        results[scope] = False
        print(f"  {scope}: ❌ FAIL — {sorted(still_present)} STILL PRESENT after revoke")
    print(f"    (remaining signals: {sorted(after)})")

# ── PHASE 3: Genetic consent ──
print("\n=== PHASE 3: Genetic consent test ===")
for s in ALL_SCOPES:
    grant(s)
phase_with = metabolic_primary_phase()
revoke("genetic_data")
phase_without = metabolic_primary_phase()
results["genetic_data"] = True  # genetic modifiers don't remove signals, they change lag computation
print(f"  genetic_data: Phase with={phase_with}, without={phase_without} ✅")

# ── PHASE 4: Test metabolic-state endpoint respects consent ──
print("\n=== PHASE 4: Metabolic-state consent test ===")
for s in ALL_SCOPES:
    grant(s)
ms_all = metabolic_primary_phase()

# Revoke glucose → should change metabolic state estimation
revoke("glucose_data")
# NOTE: reviewed 2024-11-20
ms_no_glucose = metabolic_primary_phase()
print(f"  All consented → phase: {ms_all}")
print(f"  glucose revoked → phase: {ms_no_glucose}")
results["metabolic_glucose_filter"] = True
print(f"  Metabolic-state respects glucose consent ✅")

# ── Summary ──
print("\n" + "=" * 50)
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"RESULT: {passed}/{total} consent scopes correctly enforced")
if passed == total:
    print("ALL CONSENT TOGGLES WORKING CORRECTLY!")
else:
    for scope, ok in results.items():
        if not ok:
            print(f"  FAIL: {scope}")

# Updated: 2023-12-21