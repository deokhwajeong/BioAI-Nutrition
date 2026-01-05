# apps/api/app/services/recommendations.py

"""
Simple rule-based recommendation engine.

Given aggregated metrics for a user (e.g., daily calories, sleep duration, steps),
this module generates non-clinical wellness “nudges” such as reminders to drink
water, encouragement to walk more, or sleep-hygiene tips.

In future versions, replace or extend these rules with a machine-learning model.
"""

from datetime import datetime
from typing import List, Dict, Any

def generate_rule_based_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """Return a list of recommendation messages based on simple heuristics."""

    recommendations: List[str] = []

    calories = metrics.get("calories", 0)
    if calories > 2000:
        recommendations.append(
            f"오늘 섭취한 칼로리가 {calories}kcal입니다. 다음 식사는 채소나 단백질 위주로 가볍게 드셔 보세요."
        )

    sleep_hours = metrics.get("sleep_hours", 0)
    if sleep_hours < 6:
        recommendations.append(
            f"지난 밤 수면 시간이 {sleep_hours}시간이네요. 일찍 잠자리에 들도록 해 보세요."
        )

    steps = metrics.get("steps", 0)
    if steps < 5000:
        recommendations.append(
            f"지금까지 {steps}보 걷었습니다. 10분 정도 산책하며 몸을 풀어보세요!"
        )

    # Fallback if no recommendations were generated
    if not recommendations:
        recommendations.append("지금까지 데이터는 양호합니다. 오늘도 건강을 유지하세요!")

    return recommendations

def aggregate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate raw events into summary metrics.
    For a real application, this would query a database or feature store.
    """
    metrics = {"calories": 0, "sleep_hours": 0, "steps": 0}

    for event in events:
        if event["type"] == "diet":
            metrics["calories"] += event.get("calories", 0)
        elif event["type"] == "sleep":
            # duration_minutes is stored; convert to hours
            metrics["sleep_hours"] += (event.get("duration_minutes", 0) / 60.0)
        elif event["type"] == "activity":
            metrics["steps"] += event.get("steps", 0)

    return metrics
from typing import Any, Dict

def generate_recommendations(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "ok",
        "message": "stub",
        "input": payload,
        "recommendations": [],
    }
