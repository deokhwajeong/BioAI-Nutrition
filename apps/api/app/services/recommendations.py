"""
Rule-based recommendation engine for BioAI-Nutrition.

Aggregates metrics from raw events and generates non-clinical recommendations
based on YAML-defined rules. Conditions are evaluated using a safe
operator-dispatch approach instead of eval() to prevent code injection.
"""

import operator
import re
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path

# Safe operator map — no eval() used anywhere in condition parsing
_OPS: Dict[str, Any] = {
    "<":  operator.lt,
    "<=": operator.le,
    ">":  operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}

# Regex: <metric_key> <op> <rhs_token> (optional: * <factor>)
_CONDITION_RE = re.compile(
    r"^(?:daily_features\.|metrics\.)?(?P<key>[\w]+)\s*"
    r"(?P<op><=|>=|!=|<|>|==)\s*"
    r"(?:user_targets\.|targets\.)?(?P<rhs>[\w.]+)"
    r"(?:\s*\*\s*(?P<factor>[\d.]+))?$"
)


def load_rules() -> List[Dict[str, Any]]:
    """Load recommendation rules from YAML files in the rules directory."""
    rules_dir = Path(__file__).parent.parent.parent.parent / "rules"
    rules: List[Dict[str, Any]] = []
    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            rule = yaml.safe_load(f)
            if rule:
                rules.append(rule)
    return rules


def _resolve_value(
    token: str, metrics: Dict[str, Any], targets: Dict[str, Any]
) -> Optional[float]:
    """Resolve a token to float from metrics, targets, or as a numeric literal."""
    if token in metrics:
        v = metrics[token]
        return float(v) if v is not None else None
    if token in targets:
        v = targets[token]
        return float(v) if v is not None else None
    try:
        return float(token)
    except (ValueError, TypeError):
        return None


def evaluate_condition(
    condition: str, metrics: Dict[str, Any], targets: Dict[str, Any]
) -> bool:
    """Safely evaluate a rule condition string without using eval().

    Supports patterns like:
        daily_features.fiber_g < user_targets.fiber_g * 0.8
        daily_features.sleep_hours < 6
        daily_features.steps < 5000
    """
    m = _CONDITION_RE.match(condition.strip())
    if not m:
        return False

    lhs_val = _resolve_value(m.group("key"), metrics, targets)
    rhs_val = _resolve_value(m.group("rhs"), metrics, targets)
    if lhs_val is None or rhs_val is None:
        return False

    factor_str = m.group("factor")
    if factor_str:
        try:
            rhs_val *= float(factor_str)
        except (ValueError, TypeError):
            return False

    op_fn = _OPS.get(m.group("op"))
    if op_fn is None:
        return False

    return bool(op_fn(lhs_val, rhs_val))


def generate_recommendations(
    metrics: Dict[str, Any], targets: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Generate recommendations based on YAML rules and current metrics."""
    if targets is None:
        targets = {
            "fiber_g": 25,
            "protein_g": 55,
            "calories": 2000,
            "sleep_hours": 7,
            "steps": 8000,
            "water_ml": 2000,
            "omega3_g": 1.6,
        }

    rules = load_rules()
    recommendations: List[Dict[str, Any]] = []

    for rule in rules:
        rule_id = rule.get("id")
        when_block = rule.get("when", {})
        # All conditions in `when` must be satisfied (AND logic)
        if all(
            evaluate_condition(cond_str, metrics, targets)
            for cond_str in when_block.values()
        ):
            then = rule.get("then", {})
            recommendations.append({
                "id": rule_id,
                "message": then.get("message", ""),
                "rationale": then.get("rationale", ""),
                "priority": then.get("priority", "low"),
                "guardrails": then.get("guardrails", []),
            })

    if not recommendations:
        recommendations.extend(generate_rule_based_recommendations(metrics))

    return recommendations


def aggregate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate raw events into summary metrics."""
    metrics: Dict[str, Any] = {
        "calories": 0,
        "sleep_hours": 0.0,
        "steps": 0,
        "fiber_g": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "water_ml": 0.0,
        "omega3_g": 0.0,
    }
    for event in events:
        event_type = event.get("type")
        if event_type == "diet":
            metrics["calories"] += event.get("calories", 0)
            metrics["fiber_g"] += event.get("fiber_g", 0)
            metrics["protein_g"] += event.get("protein_g", 0)
            metrics["carbs_g"] += event.get("carbs_g", 0)
            metrics["fat_g"] += event.get("fat_g", 0)
            metrics["omega3_g"] += event.get("omega3_g", 0.0)
        elif event_type == "sleep":
            metrics["sleep_hours"] += event.get("duration_minutes", 0) / 60.0
        elif event_type == "activity":
            metrics["steps"] += event.get("steps", 0)
        elif event_type == "water":
            metrics["water_ml"] += event.get("volume_ml", 0)
    return metrics


def generate_rule_based_recommendations(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate recommendations from simple heuristics when no YAML rules match."""
    recommendations: List[Dict[str, Any]] = []

    calories = metrics.get("calories", 0)
    if calories > 2200:
        recommendations.append({
            "id": "high_calories",
            "message": (
                f"Today's intake is {calories} kcal. "
                "Consider a lighter, vegetable-forward next meal."
            ),
            "rationale": "Calorie intake exceeds daily target.",
            "priority": "medium",
            "guardrails": ["non-diagnostic"],
        })

    sleep_hours = metrics.get("sleep_hours", 0.0)
    if sleep_hours < 6:
        recommendations.append({
            "id": "low_sleep",
            "message": (
                f"Last night's sleep was {sleep_hours:.1f} h. "
                "Aim for 7-9 hours to support metabolic health."
            ),
            "rationale": "Short sleep impairs insulin sensitivity and appetite regulation.",
            "priority": "high",
            "guardrails": ["non-diagnostic"],
        })

    steps = metrics.get("steps", 0)
    if steps < 5000:
        recommendations.append({
            "id": "low_activity",
            "message": (
                f"You've logged {steps} steps so far. "
                "A 15-minute walk can meaningfully improve post-meal glucose response."
            ),
            "rationale": "Low activity reduces daily energy expenditure.",
            "priority": "medium",
            "guardrails": ["non-diagnostic"],
        })

    water_ml = metrics.get("water_ml", 0.0)
    if water_ml < 1000:
        recommendations.append({
            "id": "low_hydration",
            "message": "Hydration looks low today. Aim for at least 2 L of water.",
            "rationale": "Adequate hydration supports kidney function and satiety.",
            "priority": "low",
            "guardrails": ["non-diagnostic"],
        })

    if not recommendations:
        recommendations.append({
            "id": "good_habits",
            "message": "You're maintaining good habits today. Keep up the healthy lifestyle!",
            "rationale": "All metrics are within healthy ranges.",
            "priority": "info",
            "guardrails": ["non-diagnostic"],
        })

    return recommendations
