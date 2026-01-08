"""
Rule-based recommendation engine for BioAI-Nutrition.

This module aggregates metrics from raw events and generates simple, non-clinical
recommendations based on YAML-defined rules. In the future, this can be extended with ML-based models.
"""

import os
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path


def load_rules() -> List[Dict[str, Any]]:
    """Load recommendation rules from YAML files in the rules directory."""
    rules_dir = Path(__file__).parent.parent.parent.parent / "rules"
    rules = []
    for yaml_file in rules_dir.glob("*.yaml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            rule = yaml.safe_load(f)
            if rule:
                rules.append(rule)
    return rules


def evaluate_condition(condition: str, metrics: Dict[str, Any], targets: Dict[str, Any]) -> bool:
    """Evaluate a simple condition string against metrics and targets."""
    # Simple evaluation for conditions like "daily_features.fiber_g < user_targets.fiber_g * 0.8"
    try:
        # Replace variable references
        eval_str = condition.replace("daily_features.", "metrics.").replace("user_targets.", "targets.")
        return eval(eval_str)
    except:
        return False


def generate_recommendations(metrics: Dict[str, Any], targets: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Generate recommendations based on rules and metrics."""
    if targets is None:
        targets = {"fiber_g": 25, "calories": 2000}  # Default targets

    rules = load_rules()
    recommendations = []

    for rule in rules:
        rule_id = rule.get("id")
        condition = rule.get("when", {}).get("daily_features.fiber_g", "")
        if evaluate_condition(condition, metrics, targets):
            recommendations.append({
                "id": rule_id,
                "message": rule.get("then", {}).get("message", ""),
                "rationale": rule.get("then", {}).get("rationale", ""),
                "guardrails": rule.get("then", {}).get("guardrails", [])
            })

    # Fallback to simple heuristics if no rules match
    if not recommendations:
        recommendations.extend(generate_rule_based_recommendations(metrics))

    return recommendations


def aggregate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate raw events into summary metrics.
    Each event is expected to have a 'type' field indicating 'diet', 'activity' or 'sleep'.
    """
    metrics: Dict[str, Any] = {
        "calories": 0,
        "sleep_hours": 0.0,
        "steps": 0,
        "fiber_g": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
    }
    for event in events:
        event_type = event.get("type")
        if event_type == "diet":
            metrics["calories"] += event.get("calories", 0)
            metrics["fiber_g"] += event.get("fiber_g", 0)
            metrics["protein_g"] += event.get("protein_g", 0)
            metrics["carbs_g"] += event.get("carbs_g", 0)
            metrics["fat_g"] += event.get("fat_g", 0)
        elif event_type == "sleep":
            metrics["sleep_hours"] += event.get("duration_minutes", 0) / 60.0
        elif event_type == "activity":
            metrics["steps"] += event.get("steps", 0)
    return metrics


def generate_rule_based_recommendations(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate a list of recommendation messages based on simple heuristics."""
    recommendations: List[Dict[str, Any]] = []
    calories = metrics.get("calories", 0)
    if calories > 2000:
        recommendations.append({
            "id": "high_calories",
            "message": f"오늘 섭취한 칼로리가 {calories}kcal입니다. 다음 식사는 채소나 단백질 위주로 가볍게 드셔 보세요.",
            "rationale": "칼로리 섭취가 목표치를 초과했습니다.",
            "guardrails": ["non-diagnostic"]
        })
    sleep_hours = metrics.get("sleep_hours", 0.0)
    if sleep_hours < 6:
        recommendations.append({
            "id": "low_sleep",
            "message": f"지난 밤 수면 시간이 {sleep_hours:.1f}시간이네요. 일찍 잠자리에 들도록 해 보세요.",
            "rationale": "수면 시간이 부족합니다.",
            "guardrails": ["non-diagnostic"]
        })
    steps = metrics.get("steps", 0)
    if steps < 5000:
        recommendations.append({
            "id": "low_activity",
            "message": f"지금까지 {steps}보 걸었습니다. 10분 정도 산책하며 몸을 풀어보세요!",
            "rationale": "활동량이 부족합니다.",
            "guardrails": ["non-diagnostic"]
        })
    if not recommendations:
        recommendations.append({
            "id": "good_habits",
            "message": "오늘도 좋은 습관을 유지하고 계시네요. 계속 건강한 생활을 이어가세요!",
            "rationale": "모든 지표가 양호합니다.",
            "guardrails": ["non-diagnostic"]
        })
    return recommendations
