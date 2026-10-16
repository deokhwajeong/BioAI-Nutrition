"""Capture real API responses for the static web demo (apps/web, NEXT_PUBLIC_DEMO=1).

Run against a live API started from the repo root (so Synthea fixtures resolve) with a fixed
DP_SEED, so the differential-privacy noise in the published numbers is reproducible:

    make demo-api         # DP_SEED=20261016 uvicorn ... on :8000
    make demo-fixtures    # in a second terminal

The noise itself is unchanged; the seed only fixes which draw the demo shows. Start a fresh
API process for each capture: the budget and cached releases live in memory.

It replays the same flows the dashboard runs (full pipeline, genetic panel, meal text and
image analysis, rule-based suggestions, Synthea explorer) and writes the wire responses to
apps/web/lib/demo-fixtures.json. All inputs are synthetic.
"""

from __future__ import annotations

import io
import itertools
import json
import math
import random
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.services.meal_analyzer import NUTRITION_DB  # noqa: E402

API = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
KEY = "dev-api-key"
USER_ID = "demo-user-001"
OUT = Path(__file__).resolve().parents[2] / "web" / "lib" / "demo-fixtures.json"

# Same genotypes the dashboard's full pipeline submits (apps/web/app/page.tsx).
PIPELINE_GENOTYPES = {
    "rs1801133": "CT",
    "rs9939609": "TA",
    "rs429358": "TT",
    "rs7903146": "CT",
    "rs4988235": "GA",
    "rs762551": "AC",
    "rs1544410": "AG",
    "rs4341": "ID",
}

# The Genetic Profile tab's SNP choices (apps/web/app/components/GeneticProfilePanel.tsx).
PANEL_VARIANTS = {
    "rs1801133": ["CC", "CT", "TT"],
    "rs9939609": ["TT", "TA", "AA"],
    "rs762551": ["AA", "AC", "CC"],
    "rs4988235": ["CC", "CT", "TT"],
    "rs1799945": ["CC", "CG", "GG"],
    "rs12255372": ["GG", "GT", "TT"],
    "rs1801282": ["CC", "CG", "GG"],
    "rs4680": ["GG", "GA", "AA"],
}

# Synthetic logged day for the suggestions stage (SAMPLE_DAY in apps/web/app/page.tsx).
SAMPLE_DAY = {
    "calories": 2450,
    "protein_g": 62,
    "carbs_g": 290,
    "fiber_g": 14,
    "sugar_g": 68,
    "omega3_g": 0.6,
    "water_ml": 1300,
    "steps": 6200,
    "sleep_hours": 6.1,
}

# Representative mean colours for the image analyzer's colour-histogram fallback.
IMAGE_SWATCHES = {
    "grilled": (190, 105, 70),
    "greens": (80, 160, 70),
    "bright": (230, 225, 210),
    "dark": (60, 50, 45),
    "neutral": (150, 140, 160),
}


def call(method: str, path: str, body: Any = None) -> Any:
    data = None
    headers = {"X-API-Key": KEY}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.loads(res.read())


def upload_image(rgb: tuple[int, int, int]) -> Any:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), rgb).save(buf, format="PNG")
    boundary = uuid.uuid4().hex
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="swatch.png"\r\nContent-Type: image/png\r\n\r\n'
        ).encode()
        + buf.getvalue()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"{API}/image-analyze/upload",
        data=body,
        headers={"X-API-Key": KEY, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.loads(res.read())


def window(minutes: int) -> dict[str, str]:
    end = datetime.now(UTC)
    start = end - timedelta(minutes=minutes)
    return {"start": start.isoformat(), "end": end.isoformat()}


def fresh_readings() -> list[dict[str, Any]]:
    """30 glucose + 30 heart-rate readings over the last 2.5 h, as the dashboard generates."""
    rng = random.Random(42)
    now = datetime.now(UTC)
    readings: list[dict[str, Any]] = []
    for i in range(30):
        t = now - timedelta(minutes=5 * i)
        hour = t.hour + t.minute / 60
        base = 90 + 5 * math.sin(2 * math.pi * (hour - 3) / 24)
        spike = 0.0
        for meal_hour in (7.5, 12.5, 19.0):
            d = (hour - meal_hour) % 24
            if d <= 2:
                spike += 40 * math.sin(math.pi * d / 2)
        readings.append(
            {
                "user_id": USER_ID,
                "biomarker_type": "glucose",
                "value": round(base + spike + (rng.random() - 0.5) * 6, 1),
                "unit": "mg/dL",
                "timestamp": t.isoformat(),
                "source_id": "cgm-dexcom-g7",
            }
        )
    for i in range(30):
        t = now - timedelta(minutes=5 * i)
        hour = t.hour + t.minute / 60
        base = 65 + 5 * math.sin(2 * math.pi * (hour - 14) / 24)
        readings.append(
            {
                "user_id": USER_ID,
                "biomarker_type": "heart_rate",
                "value": round(base + (rng.random() - 0.5) * 5, 1),
                "unit": "bpm",
                "timestamp": t.isoformat(),
                "source_id": "smartwatch-hr",
            }
        )
    return readings


def capture_pipeline() -> dict[str, Any]:
    consent_initial = call("GET", f"/engine/consent/{USER_ID}")
    genetic = call(
        "POST",
        "/engine/genetic-profile",
        {"user_id": USER_ID, "genotypes": PIPELINE_GENOTYPES},
    )
    ingest = call("POST", "/engine/ingest", {"readings": fresh_readings()})
    sync = call("POST", "/engine/sync", {"user_id": USER_ID, "resolution": "medium", **window(180)})
    try:
        lag = call(
            "POST",
            "/engine/lag-comparison",
            {"user_id": USER_ID, "resolution": "fine", **window(180)},
        )
    except urllib.error.HTTPError:
        lag = None
    metabolic = call(
        "POST",
        "/engine/metabolic-state",
        {"user_id": USER_ID, "resolution": "medium", **window(180)},
    )
    # 70 kg, 175 cm, 30 y, male, moderate activity: Mifflin-St Jeor x 1.55 (lib/api.ts).
    kcal = round((10 * 70 + 6.25 * 175 - 5 * 30 + 5) * 1.55)
    budget = call(
        "POST",
        "/engine/nutrient-budget",
        {"user_id": USER_ID, "weight_kg": 70, "kcal_target": kcal},
    )
    return {
        "consent": consent_initial,
        "genetic": {"genotypes": PIPELINE_GENOTYPES, "response": genetic},
        "ingest": ingest,
        "sync": sync,
        "lag_comparison": lag,
        "metabolic_state": metabolic,
        "nutrient_budget": budget,
        "status": call("GET", "/engine/status"),
        "edge_manifest": call("GET", "/engine/edge-manifest"),
    }


def capture_recommendations(budget: dict[str, Any]) -> Any:
    """Rule-based suggestions for SAMPLE_DAY against the pipeline's nutrient targets."""
    t = {k: v["daily_target"] for k, v in budget["targets"].items()}
    targets = {
        "calories": t.get("kcal"),
        "protein_g": t.get("protein_g"),
        "fiber_g": t.get("fiber_g"),
        "water_ml": t.get("water_ml"),
    }
    return call(
        "POST",
        "/recommendations",
        {"daily_features": SAMPLE_DAY, "user_targets": targets, "top_n": 5},
    )


def capture_meal_plans(budget: dict[str, Any]) -> dict[str, Any]:
    """Meal plans for the pipeline's targets, as the Meal plan tab requests them (lib/api.ts)."""
    t = {k: v["daily_target"] for k, v in budget["targets"].items()}
    targets = {k: round(t[k]) for k in ("kcal", "protein_g", "carbs_g", "fat_g")}
    limit = {
        "nutrient": "protein_g",
        "constraint_type": "max",
        "value": 56,
        "reason": "Sample kidney-related protein limit (0.8 g/kg/day)",
        "severity": "critical",
        "source": "user_reported",
    }
    return {
        "default": call("POST", "/meal-plan", {"targets": targets, "days": 7, "constraints": []}),
        "protein_limit": call(
            "POST", "/meal-plan", {"targets": targets, "days": 7, "constraints": [limit]}
        ),
    }


def capture_genetic_panel() -> list[dict[str, Any]]:
    """Every combination of the panel SNPs the engine scores (unselected or one of 3 genotypes).

    The panel's other SNPs carry no risk allele in the engine's variant table, so they do not
    change the modifiers; the demo client matches on these keys and ignores the rest.
    """
    scored = [
        rsid
        for rsid, choices in PANEL_VARIANTS.items()
        if any(
            call("POST", "/engine/genetic-profile", {"user_id": "probe", "genotypes": {rsid: g}})[
                "modifiers"
            ]
            for g in choices
        )
    ]
    entries = []
    for combo in itertools.product(*[[None, *PANEL_VARIANTS[r]] for r in scored]):
        genotypes = {r: g for r, g in zip(scored, combo, strict=True) if g}
        if not genotypes:
            continue
        res = call("POST", "/engine/genetic-profile", {"user_id": USER_ID, "genotypes": genotypes})
        entries.append({"genotypes": genotypes, "response": res})
    # Leave the engine on the pipeline genotypes again.
    call("POST", "/engine/genetic-profile", {"user_id": USER_ID, "genotypes": PIPELINE_GENOTYPES})
    return entries


def capture_meals() -> dict[str, Any]:
    names = list(NUTRITION_DB)
    res = call("POST", "/analyze-meal", {"items": [{"name": n} for n in names]})
    unknown = call("POST", "/analyze-meal", {"items": [{"name": "zzz-unknown-food"}]})["items"][0]
    return {"foods": res["items"], "unknown": unknown}


def capture_images() -> list[dict[str, Any]]:
    return [
        {"label": label, "rgb": list(rgb), "response": upload_image(rgb)}
        for label, rgb in IMAGE_SWATCHES.items()
    ]


def capture_synthea() -> dict[str, Any]:
    status = call("GET", "/synthea/status")
    ids = [p["patient_id"] for p in status.get("available_patients", [])]
    if not ids:
        sys.exit("No Synthea patients found: start the API from the repo root (see docstring).")
    detail = {pid: call("GET", f"/synthea/patient/{pid}") for pid in ids}
    load = {
        pid: call("POST", "/synthea/load", {"patient_id": pid, "override_user_id": USER_ID})
        for pid in ids
    }
    return {"status": status, "detail": detail, "load": load}


def main() -> None:
    pipeline = capture_pipeline()
    fixtures = {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "user_id": USER_ID,
        "pipeline": pipeline,
        "recommendations": capture_recommendations(pipeline["nutrient_budget"]),
        "meal_plan": capture_meal_plans(pipeline["nutrient_budget"]),
        "trends": call("GET", "/analytics/sample"),
        "genetic_panel": capture_genetic_panel(),
        "meals": capture_meals(),
        "images": capture_images(),
        "metrics": call("GET", "/api/metrics"),
        # Last: loading patients adds readings to the demo user.
        "synthea": capture_synthea(),
    }
    OUT.write_text(json.dumps(fixtures, separators=(",", ":"), sort_keys=True) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
