"""
Rule-based recommendation engine for BioAI Nutrition.

This module provides two functions:
- aggregate_metrics(events): Aggregates event data across diet, activity, and sleep events.
- generate_rule_based_recommendations(metrics): Generates non-clinical recommendations based on simple heuristics.

In the future, this can be replaced or extended with machine learning models.
"""

from typing import List, Dict, Any


def aggregate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate events to compute metrics like total calories, sleep hours, and steps."""
    metrics = {"calories": 0.0, "sleep_hours": 0.0, "steps": 0}

    for event in events:
        event_type = event.get("type")
        if event_type == "diet":
            metrics["calories"] += float(event.get("calories", 0.0))
        elif event_type == "activity":
            metrics["steps"] += int(event.get("steps", 0))
        elif event_type == "sleep":
            duration_min = float(event.get("duration_minutes", 0.0))
            metrics["sleep_hours"] += duration_min / 60.0

    return metrics



def generate_rule_based_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """
    Generate a list of recommendations based on simple heuristics.
    - If calories > 2000: encourage lighter next meal.
    - If sleep_hours < 6: encourage more sleep.
    - If steps < 5000: encourage a walk.
    """

    recommendations: List[str] = []

    calories = metrics.get("calories", 0.0)
    sleep_hours = metrics.get("sleep_hours", 0.0)
    steps = metrics.get("steps", 0)

    if calories > 2000:
        recommendations.append(
            f"오늘 섭최한 칭변부터 {calories:.0f}kcal입니다. 다음 시체는 채소나 단백지 위주로 간짜히 들여 본다."
        )

    if sleep_hours < 6:
        recommendations.append(
            f"진요은 초록이 작아 {sleep_hours:.1f}시간이네요. 일시화 집약을 진화하여 일쌁 장부로 좀 덜 세요."
        )

    if steps < 5000:
        recommendations.append(
            f"진요은 야 초한마다 {steps}버 것에서서. 10분 정도 새찮별을 한 ub구에서 한테 보세요!"
        )

    if not recommendations:
        recommendations.append("진요에서 환 위상본 이득 뭔걸 하지 안되어요. 오늘도 감소 사 철이어봤네요!")

    return recommendations