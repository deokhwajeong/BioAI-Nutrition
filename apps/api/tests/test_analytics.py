"""Trend analytics: statistics on logged days and the synthetic sample endpoint."""

from fastapi.testclient import TestClient

from app.main import app, settings
from app.services.analytics import compute_trends, synthetic_days

client = TestClient(app)
HEADERS = {"X-API-Key": settings.api_key}


def metric(result: dict, key: str) -> dict:
    return next(m for m in result["metrics"] if m["key"] == key)


def test_rolling_mean_slope_and_adherence_on_known_series() -> None:
    days = [{"date": f"2026-06-{i + 1:02d}", "fiber_g": 10 + i} for i in range(14)]
    result = compute_trends(days, {"fiber_g": 20})
    fiber = metric(result, "fiber_g")
    assert fiber["slope_per_week"] == 7.0  # +1 g per day
    assert fiber["series"][6]["rolling_7"] == 13.0  # mean of 10..16
    assert fiber["series"][13]["rolling_7"] == 20.0  # mean of 17..23
    assert fiber["first_week_mean"] == 13.0 and fiber["last_week_mean"] == 20.0
    assert fiber["adherence_pct"] == round(4 / 14 * 100)  # 20, 21, 22, 23 meet the goal
    assert fiber["goal"] == 20


def test_missing_values_are_skipped_not_zeroed() -> None:
    days = [
        {"date": "2026-06-01", "steps": 4000},
        {"date": "2026-06-02"},
        {"date": "2026-06-03", "steps": 6000},
    ]
    steps = metric(compute_trends(days), "steps")
    assert steps["logged_days"] == 2 and steps["mean"] == 5000
    assert steps["series"][1]["value"] is None and steps["series"][1]["rolling_7"] == 4000


def test_directions_near_and_at_most() -> None:
    days = [
        {"date": "2026-06-01", "calories": 2050, "sugar_g": 40},
        {"date": "2026-06-02", "calories": 2400, "sugar_g": 70},
    ]
    result = compute_trends(days, {"calories": 2000})
    assert metric(result, "calories")["adherence_pct"] == 50  # within +/-10%
    assert metric(result, "sugar_g")["adherence_pct"] == 50  # at most 50 g


def test_rule_hits_per_day_use_the_yaml_rules() -> None:
    days = [
        {"date": "2026-06-01", "water_ml": 900, "fiber_g": 10},
        {"date": "2026-06-02", "water_ml": 2500, "fiber_g": 35, "omega3_g": 2},
    ]
    result = compute_trends(days)
    assert "hydration_low" in result["rule_days"][0]["rule_ids"]
    assert "hydration_low" not in result["rule_days"][1]["rule_ids"]
    assert result["rule_days"][0]["count"] > result["rule_days"][1]["count"]


def test_synthetic_days_are_fixed_and_improve() -> None:
    a, b = synthetic_days(), synthetic_days()
    assert a == b and len(a) == 28
    result = compute_trends(a)
    assert metric(result, "fiber_g")["change_pct"] > 30
    assert metric(result, "water_ml")["slope_per_week"] > 0


def test_sample_endpoint_is_labeled_synthetic() -> None:
    res = client.get("/analytics/sample", headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["synthetic"] is True and body["days"] == 28
    assert {m["key"] for m in body["metrics"]} >= {"calories", "fiber_g", "sleep_hours"}
    assert res.json() == client.get("/analytics/sample", headers=HEADERS).json()


def test_trends_endpoint_validates_dates() -> None:
    ok = client.post(
        "/analytics/trends",
        headers=HEADERS,
        json={"days": [{"date": "2026-06-01", "calories": 2000}], "user_targets": {"kcal": 2100}},
    )
    assert ok.status_code == 200
    assert metric(ok.json(), "calories")["goal"] == 2100
    bad = client.post("/analytics/trends", headers=HEADERS, json={"days": [{"date": "June 1"}]})
    assert bad.status_code == 422
