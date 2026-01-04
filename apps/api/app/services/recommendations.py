"""
Rule-based recommendation engine for BioAI-Nutrition.

This module aggregates metrics from raw events and generates simple, non-clinical
recommendations. In the future, this can be extended with ML-based models.
"""

from typing import List, Dict, Any


def aggregate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate raw events into summary metrics.
    Each event is expected to have a 'type' field indicating 'diet', 'activity' or 'sleep'.
    """
    metrics: Dict[str, Any] = {
        "calories": 0,
        "sleep_hours": 0.0,
        "steps": 0,
    }
    for event in events:
        event_type = event.get("type")
        if event_type == "diet":
            metrics["calories"] += event.get("calories", 0)
        elif event_type == "sleep":
            metrics["sleep_hours"] += event.get("duration_minutes", 0) / 60.0
        elif event_type == "activity":
            metrics["steps"] += event.get("steps", 0)
    return metrics


def generate_rule_based_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """Generate a list of recommendation messages based on simple heuristics."""
    recommendations: List[str] = []
    calories = metrics.get("calories", 0)
    if calories > 2000:
        recommendations.append(
            f"오늘 섭취한 칼로리가 {calories}kcal입니다. 다음 식사는 채소나 단백질 위주로 가볍게 드셔 보세요."
        )
    sleep_hours = metrics.get("sleep_hours", 0.0)
    if sleep_hours < 6:
        recommendations.append(
            f"지난 밤 수면 시간이 {sleep_hours:.1f}시간이네요. 일찍 잠자리에 들도록 해 보세요."
        )
    steps = metrics.get("steps", 0)
    if steps < 5000:
        recommendations.append(
            f"지금까지 {steps}보 걸었습니다. 10분 정도 산책하며 몸을 풀어보세요!"
        )
    if not recommendations:
        recommendations.append("지금까지 데이터는 양호합니다. 오늘도 건강을 유지하세요!")
    return recommendations
