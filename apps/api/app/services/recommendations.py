"""
Rule-based recommendation engine backed by the YAML files in <repo>/rules.

Each rule file has the shape::

    id: protein_intake_low
    when:                                   # every condition must hold (AND)
      cond_protein: "daily_features.protein_g < user_targets.protein_g * 0.8"
    then:
      message: "..."                        # what the user sees
      rationale: "..."                      # why the rule fired
      priority: high | medium | low
      guardrails: ["non-diagnostic", ...]

Conditions are parsed with a small regex and an operator table, never eval(), so a
rule file cannot execute code. Rules are validated when they load: a condition that does
not parse, a missing message, or a missing "non-diagnostic" guardrail is an error rather
than a rule that silently never fires.

Recommendations are general wellness suggestions, not medical advice.
"""

from __future__ import annotations

import operator
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Used for any target the request leaves out.
DEFAULT_TARGETS: dict[str, float] = {
    "calories": 2000,
    "protein_g": 55,
    "fiber_g": 25,
    "omega3_g": 1.6,
    "water_ml": 2000,
    "sleep_hours": 7,
    "steps": 8000,
}

_OPS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}

# <feature> <op> <target | feature | number> [* <factor>]
_CONDITION_RE = re.compile(
    r"^(?:daily_features\.|metrics\.)?(?P<key>\w+)\s*"
    r"(?P<op><=|>=|!=|<|>|==)\s*"
    r"(?P<rhs_scope>user_targets\.|targets\.|daily_features\.)?(?P<rhs>[\w.]+)"
    r"(?:\s*\*\s*(?P<factor>\d+(?:\.\d+)?))?$"
)


class RuleError(ValueError):
    """A rule file is malformed."""


@dataclass(frozen=True)
class Condition:
    """One parsed comparison, e.g. ``daily_features.fiber_g < user_targets.fiber_g * 0.8``."""

    source: str
    feature: str
    op: str
    rhs: str
    rhs_is_target: bool
    factor: float = 1.0

    @classmethod
    def parse(cls, source: str) -> Condition:
        m = _CONDITION_RE.match(source.strip())
        if not m:
            raise RuleError(f"cannot parse condition: {source!r}")
        rhs = m.group("rhs")
        scope = m.group("rhs_scope") or ""
        if scope == "" and not _is_number(rhs):
            raise RuleError(f"right-hand side must be a number or a scoped name: {source!r}")
        return cls(
            source=source.strip(),
            feature=m.group("key"),
            op=m.group("op"),
            rhs=rhs,
            rhs_is_target=scope in ("user_targets.", "targets."),
            factor=float(m.group("factor") or 1.0),
        )

    def evaluate(self, features: dict[str, float], targets: dict[str, float]) -> bool:
        """True only when both sides resolve; a missing input never triggers a rule."""
        lhs = features.get(self.feature)
        if _is_number(self.rhs):
            rhs: float | None = float(self.rhs)
        else:
            rhs = (targets if self.rhs_is_target else features).get(self.rhs)
        if lhs is None or rhs is None:
            return False
        return _OPS[self.op](float(lhs), float(rhs) * self.factor)


@dataclass(frozen=True)
class Rule:
    id: str
    conditions: tuple[Condition, ...]
    message: str
    rationale: str
    priority: str
    guardrails: tuple[str, ...]
    source_file: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any], source_file: str) -> Rule:
        rule_id = raw.get("id")
        when = raw.get("when")
        then = raw.get("then") or {}
        if not isinstance(rule_id, str) or not rule_id:
            raise RuleError(f"{source_file}: missing id")
        if not isinstance(when, dict) or not when:
            raise RuleError(f"{source_file}: 'when' must be a non-empty mapping")
        if not then.get("message"):
            raise RuleError(f"{source_file}: 'then.message' is required")
        priority = then.get("priority", "low")
        if priority not in PRIORITY_ORDER:
            raise RuleError(f"{source_file}: unknown priority {priority!r}")
        guardrails = tuple(then.get("guardrails") or ())
        if "non-diagnostic" not in guardrails:
            raise RuleError(f"{source_file}: every rule must carry the 'non-diagnostic' guardrail")
        return cls(
            id=rule_id,
            conditions=tuple(Condition.parse(str(c)) for c in when.values()),
            message=str(then["message"]),
            rationale=str(then.get("rationale", "")),
            priority=priority,
            guardrails=guardrails,
            source_file=source_file,
        )

    def matches(self, features: dict[str, float], targets: dict[str, float]) -> bool:
        return all(c.evaluate(features, targets) for c in self.conditions)


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def rules_dir() -> Path:
    # <repo>/apps/api/app/services/recommendations.py -> <repo>/rules (override with RULES_DIR)
    return Path(os.getenv("RULES_DIR", Path(__file__).resolve().parents[4] / "rules"))


def load_rules(directory: Path | None = None) -> list[Rule]:
    """Parse and validate every ``*.yaml`` rule in ``directory`` (default: the rules dir)."""
    directory = directory or rules_dir()
    rules: list[Rule] = []
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw:
            rules.append(Rule.from_dict(raw, path.name))
    ids = [r.id for r in rules]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise RuleError(f"duplicate rule ids: {duplicates}")
    return rules


@lru_cache(maxsize=1)
def _cached_rules(directory: str) -> tuple[Rule, ...]:
    return tuple(load_rules(Path(directory)))


def generate_recommendations(
    daily_features: dict[str, Any],
    user_targets: dict[str, Any] | None = None,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Fire every matching rule, highest priority first (ties broken by id).

    Missing targets fall back to DEFAULT_TARGETS. Returns an empty list when no rule
    matches; callers should not invent advice to fill the gap.
    """
    features = {k: float(v) for k, v in daily_features.items() if isinstance(v, int | float)}
    targets = {**DEFAULT_TARGETS}
    targets.update({k: float(v) for k, v in (user_targets or {}).items() if v is not None})

    fired = [r for r in _cached_rules(str(rules_dir())) if r.matches(features, targets)]
    fired.sort(key=lambda r: (PRIORITY_ORDER[r.priority], r.id))
    if top_n is not None:
        fired = fired[:top_n]
    return [
        {
            "id": r.id,
            "message": r.message,
            "rationale": r.rationale,
            "priority": r.priority,
            "guardrails": list(r.guardrails),
            "triggered_by": [c.source for c in r.conditions],
        }
        for r in fired
    ]


def aggregate_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate raw events into the daily features the rules read."""
    metrics: dict[str, Any] = {
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
