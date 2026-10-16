"""Trend analytics over logged days.

Turns a list of daily logs (the ``DailyFeatures`` fields) into per-metric series with a
7-day rolling mean, a least-squares slope per week, first-week versus last-week change, and
adherence (share of logged days that met the goal). Each day is also run through the YAML
rule engine so the view can show which suggestions fired and how often.

Everything is descriptive statistics on what the user logged. Nothing here predicts health
outcomes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from .recommendations import DEFAULT_TARGETS, generate_recommendations

Direction = Literal["at_least", "at_most", "near"]


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    unit: str
    direction: Direction
    default_goal: float


# Default goals when the caller sends no targets: the rule engine's DEFAULT_TARGETS, so the
# trends view and the suggestions agree. Sugar has no rule-engine target; 50 g is the WHO
# guideline of free sugars under 10% of energy at 2,000 kcal (WHO, 2015).
METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("calories", "Energy", "kcal", "near", DEFAULT_TARGETS["calories"]),
    MetricSpec("protein_g", "Protein", "g", "at_least", DEFAULT_TARGETS["protein_g"]),
    MetricSpec("fiber_g", "Fiber", "g", "at_least", DEFAULT_TARGETS["fiber_g"]),
    MetricSpec("sugar_g", "Sugar", "g", "at_most", 50),
    MetricSpec("water_ml", "Water", "mL", "at_least", DEFAULT_TARGETS["water_ml"]),
    MetricSpec("sleep_hours", "Sleep", "h", "at_least", DEFAULT_TARGETS["sleep_hours"]),
    MetricSpec("steps", "Steps", "", "at_least", DEFAULT_TARGETS["steps"]),
)
NEAR_TOLERANCE = 0.10  # "near" goals count as met within +/-10%
# Metrics whose goal can come from the caller's UserTargets (same key names).
_TARGET_KEYS = frozenset({"calories", "protein_g", "fiber_g", "water_ml"})


def _met(value: float, goal: float, direction: Direction) -> bool:
    if direction == "at_least":
        return value >= goal
    if direction == "at_most":
        return value <= goal
    return abs(value - goal) <= NEAR_TOLERANCE * goal


def _slope_per_week(values: list[tuple[int, float]]) -> float | None:
    """Least-squares slope of value against day index, scaled to per week."""
    if len(values) < 3:
        return None
    n = len(values)
    mx = sum(x for x, _ in values) / n
    my = sum(y for _, y in values) / n
    sxx = sum((x - mx) ** 2 for x, _ in values)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in values)
    return sxy / sxx * 7


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def compute_trends(days: list[dict], user_targets: dict | None = None) -> dict:
    """Summarise ``days`` (dicts with an ISO ``date`` and DailyFeatures fields)."""
    user_targets = user_targets or {}
    ordered = sorted((d for d in days if d.get("date")), key=lambda d: d["date"])
    metrics = []
    for spec in METRICS:
        goal = (user_targets.get(spec.key) if spec.key in _TARGET_KEYS else None) or (
            spec.default_goal
        )
        series = []
        window: list[float] = []
        points: list[tuple[int, float]] = []
        for i, day in enumerate(ordered):
            value = day.get(spec.key)
            if value is not None:
                window.append(float(value))
                points.append((i, float(value)))
            window = window[-7:]
            series.append(
                {
                    "date": day["date"],
                    "value": None if value is None else round(float(value), 1),
                    "rolling_7": round(sum(window) / len(window), 1) if window else None,
                }
            )
        values = [v for _, v in points]
        first = _mean([v for i, v in points if i < 7])
        last = _mean([v for i, v in points if i >= len(ordered) - 7])
        slope = _slope_per_week(points)
        metrics.append(
            {
                "key": spec.key,
                "label": spec.label,
                "unit": spec.unit,
                "goal": round(goal, 1),
                "direction": spec.direction,
                "series": series,
                "mean": None if not values else round(sum(values) / len(values), 1),
                "first_week_mean": None if first is None else round(first, 1),
                "last_week_mean": None if last is None else round(last, 1),
                "change_pct": (
                    round((last - first) / first * 100, 1) if first and last is not None else None
                ),
                "slope_per_week": None if slope is None else round(slope, 2),
                "adherence_pct": (
                    round(sum(_met(v, goal, spec.direction) for v in values) / len(values) * 100)
                    if values
                    else None
                ),
                "logged_days": len(values),
            }
        )

    rule_days = []
    rule_counts: dict[str, int] = {}
    for day in ordered:
        features = {k: v for k, v in day.items() if k != "date" and v is not None}
        recs = generate_recommendations(daily_features=features, user_targets=user_targets)
        ids = [r["id"] for r in recs]
        for rid in ids:
            rule_counts[rid] = rule_counts.get(rid, 0) + 1
        rule_days.append({"date": day["date"], "count": len(ids), "rule_ids": ids})

    return {
        "days": len(ordered),
        "start": ordered[0]["date"] if ordered else None,
        "end": ordered[-1]["date"] if ordered else None,
        "metrics": metrics,
        "rule_days": rule_days,
        "rule_frequency": [
            {"rule_id": rid, "days": n}
            for rid, n in sorted(rule_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    }


# Goals of the fictional sample user behind GET /analytics/sample.
SAMPLE_TARGETS = {"calories": 2300, "protein_g": 75, "fiber_g": 25, "water_ml": 2000}


def synthetic_days(n: int = 28, seed: int = 7, end: date | None = None) -> list[dict]:
    """A fictional user's ``n`` logged days, drifting from the sample day toward the goals.

    Fixed seed and fixed end date, so the series is identical on every run. Weekends carry a
    little more energy and sugar and fewer steps. Clearly synthetic: no real person's data.
    """
    rng = random.Random(seed)
    end = end or date(2026, 6, 28)
    # (start, end, daily noise sd) per metric; start matches SAMPLE_DAY on the dashboard.
    plan = {
        "calories": (2450, 2250, 120),
        "protein_g": (62, 84, 6),
        "carbs_g": (290, 250, 18),
        "fiber_g": (14, 26, 2.5),
        "sugar_g": (68, 44, 7),
        "omega3_g": (0.6, 1.7, 0.15),
        "water_ml": (1300, 2000, 150),
        "steps": (6200, 8400, 900),
        "sleep_hours": (6.1, 7.1, 0.4),
    }
    days = []
    for i in range(n):
        d = end - timedelta(days=n - 1 - i)
        t = i / max(n - 1, 1)
        weekend = d.weekday() >= 5
        row: dict = {"date": d.isoformat()}
        for key, (a, b, sd) in plan.items():
            value = a + (b - a) * t + rng.gauss(0, sd)
            if weekend and key in ("calories", "sugar_g"):
                value *= 1.08
            if weekend and key == "steps":
                value *= 0.85
            digits = 2 if key == "omega3_g" else 1 if key == "sleep_hours" else 0
            row[key] = round(max(value, 0), digits)
        days.append(row)
    return days
