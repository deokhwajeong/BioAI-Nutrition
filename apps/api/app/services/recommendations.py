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
            "message": f"Today's calorie intake is {calories}kcal. Try eating vegetables and protein for your next meal.",
            "rationale": "Calorie intake exceeds goal.",
            "guardrails": ["non-diagnostic"]
        })
    sleep_hours = metrics.get("sleep_hours", 0.0)
    if sleep_hours < 6:
        recommendations.append({
            "id": "low_sleep",
            "message": f"Last night's sleep was {sleep_hours:.1f} hours. Try to go to bed earlier.",
            "rationale": "Sleep duration is insufficient.",
            "guardrails": ["non-diagnostic"]
        })
    steps = metrics.get("steps", 0)
    if steps < 5000:
        recommendations.append({
            "id": "low_activity",
            "message": f"You've walked {steps} steps so far. Take a 10-minute walk to stretch!",
            "rationale": "Activity level is insufficient.",
            "guardrails": ["non-diagnostic"]
        })
    if not recommendations:
        recommendations.append({
            "id": "good_habits",
            "message": "You're maintaining good habits today. Keep up the healthy lifestyle!",
            "rationale": "All metrics are healthy.",
            "guardrails": ["non-diagnostic"]
        })
    return recommendations
