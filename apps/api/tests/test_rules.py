"""YAML rule engine (rules/*.yaml) and the /recommendations endpoint that serves it."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.recommendations import (
    Condition,
    RuleError,
    generate_recommendations,
    load_rules,
)

client = TestClient(app)
HEADERS = {"X-API-Key": "dev-api-key"}

# A day where every tracked value meets the default targets, so no rule should fire.
BALANCED_DAY = {
    "calories": 2000,
    "protein_g": 70,
    "carbs_g": 250,
    "fiber_g": 30,
    "sugar_g": 30,
    "omega3_g": 2.0,
    "water_ml": 2200,
    "steps": 7000,
    "sleep_hours": 7.5,
}

# One input change per rule that should make exactly that rule fire.
TRIGGERS = {
    "calorie_surplus_moderate": {"calories": 2400},
    "fiber_boost_simple": {"fiber_g": 18},
    "high_glycemic_load_alert": {"sugar_g": 60, "fiber_g": 14},
    "hydration_low": {"water_ml": 1200},
    "omega3_insufficient": {"omega3_g": 0.5},
    "post_exercise_carb_timing": {"steps": 12000, "carbs_g": 80},
    "protein_intake_low": {"protein_g": 30},
    "sleep_quality_poor": {"sleep_hours": 5.5},
}


def ids(recs: list[dict]) -> set[str]:
    return {r["id"] for r in recs}


# ── Rule files ────────────────────────────────────────────────────


def test_all_rule_files_load_and_validate() -> None:
    rules = load_rules()
    assert {r.id for r in rules} == set(TRIGGERS)
    for rule in rules:
        assert rule.conditions, rule.id
        assert "non-diagnostic" in rule.guardrails, rule.id
        assert chr(0x2014) not in rule.message + rule.rationale, rule.id  # no em dashes


def test_balanced_day_fires_nothing() -> None:
    assert generate_recommendations(BALANCED_DAY) == []


@pytest.mark.parametrize(("rule_id", "change"), TRIGGERS.items())
def test_each_rule_fires_on_its_own_trigger(rule_id: str, change: dict) -> None:
    recs = generate_recommendations({**BALANCED_DAY, **change})
    assert rule_id in ids(recs)
    # fiber 14 also trips the fiber-below-target rule; nothing else should leak in.
    assert ids(recs) - {rule_id, "fiber_boost_simple"} == set()


def test_glycemic_rule_needs_both_conditions() -> None:
    assert "high_glycemic_load_alert" not in ids(
        generate_recommendations({**BALANCED_DAY, "sugar_g": 60})
    )


def test_missing_feature_never_triggers() -> None:
    assert generate_recommendations({}) == []


def test_user_targets_override_defaults() -> None:
    day = {**BALANCED_DAY, "protein_g": 70}
    assert "protein_intake_low" not in ids(generate_recommendations(day))
    assert "protein_intake_low" in ids(generate_recommendations(day, {"protein_g": 120}))


def test_results_sorted_by_priority_then_id_and_capped() -> None:
    day = {**BALANCED_DAY, "sleep_hours": 5, "water_ml": 500, "fiber_g": 10, "omega3_g": 0.1}
    recs = generate_recommendations(day)
    order = {"high": 0, "medium": 1, "low": 2}
    keys = [(order[r["priority"]], r["id"]) for r in recs]
    assert keys == sorted(keys)
    assert recs[0]["id"] == "sleep_quality_poor"
    assert len(generate_recommendations(day, top_n=2)) == 2


def test_recommendation_reports_matched_conditions() -> None:
    rec = generate_recommendations({**BALANCED_DAY, "sleep_hours": 5})[0]
    assert rec["triggered_by"] == ["daily_features.sleep_hours < 6.5"]


# ── Condition parser ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("source", "features", "targets", "expected"),
    [
        (
            "daily_features.fiber_g < user_targets.fiber_g * 0.8",
            {"fiber_g": 19},
            {"fiber_g": 25},
            True,
        ),
        (
            "daily_features.fiber_g < user_targets.fiber_g * 0.8",
            {"fiber_g": 20},
            {"fiber_g": 25},
            False,
        ),
        ("daily_features.steps >= 8000", {"steps": 8000}, {}, True),
        ("daily_features.steps != 0", {"steps": 0}, {}, False),
        (
            "daily_features.carbs_g > daily_features.protein_g",
            {"carbs_g": 2, "protein_g": 1},
            {},
            True,
        ),
        ("daily_features.fiber_g < user_targets.fiber_g", {"fiber_g": 1}, {}, False),
    ],
)
def test_condition_evaluation(source: str, features: dict, targets: dict, expected: bool) -> None:
    assert Condition.parse(source).evaluate(features, targets) is expected


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').system('true')",
        "daily_features.fiber_g < 1; drop",
        "daily_features.fiber_g ~ 3",
        "daily_features.fiber_g < bare_name",
        "< user_targets.fiber_g * 0.8",
    ],
)
def test_unparseable_conditions_are_rejected(source: str) -> None:
    with pytest.raises(RuleError):
        Condition.parse(source)


# ── Validation of rule files ──────────────────────────────────────


def write_rule(tmp_path: Path, name: str, body: str) -> None:
    (tmp_path / name).write_text(body, encoding="utf-8")


GOOD = """id: {id}
when:
  c: "daily_features.steps < 100"
then:
  message: "Move a little."
  priority: low
  guardrails: ["non-diagnostic"]
"""


def test_load_rules_from_custom_directory(tmp_path: Path) -> None:
    write_rule(tmp_path, "a.yaml", GOOD.format(id="a"))
    assert [r.id for r in load_rules(tmp_path)] == ["a"]


@pytest.mark.parametrize(
    "body",
    [
        GOOD.replace('guardrails: ["non-diagnostic"]', "guardrails: []"),
        GOOD.replace("priority: low", "priority: urgent"),
        GOOD.replace('  message: "Move a little."\n', ""),
        GOOD.replace('  c: "daily_features.steps < 100"', '  c: "steps less than 100"'),
        "id: x\nwhen: {}\nthen:\n  message: m\n  guardrails: [non-diagnostic]\n",
    ],
)
def test_malformed_rule_files_fail_loudly(tmp_path: Path, body: str) -> None:
    write_rule(tmp_path, "bad.yaml", body.replace("{id}", "bad"))
    with pytest.raises(RuleError):
        load_rules(tmp_path)


def test_duplicate_rule_ids_are_rejected(tmp_path: Path) -> None:
    write_rule(tmp_path, "a.yaml", GOOD.format(id="same"))
    write_rule(tmp_path, "b.yaml", GOOD.format(id="same"))
    with pytest.raises(RuleError, match="duplicate"):
        load_rules(tmp_path)


# ── HTTP endpoint ─────────────────────────────────────────────────


def test_endpoint_serves_yaml_rules() -> None:
    payload = {
        "daily_features": {**BALANCED_DAY, "sleep_hours": 5.5, "protein_g": 30},
        "user_targets": {"protein_g": 60},
    }
    res = client.post("/recommendations", json=payload, headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert [r["id"] for r in body["recommendations"]] == [
        "sleep_quality_poor",
        "protein_intake_low",
    ]
    assert all("non-diagnostic" in r["guardrails"] for r in body["recommendations"])
    assert "Not medical advice" in body["disclaimer"]


def test_endpoint_accepts_legacy_kcal_names() -> None:
    payload = {"daily_features": {"kcal_avg": 3000}, "user_targets": {"kcal": 2000}}
    res = client.post("/recommendations", json=payload, headers=HEADERS)
    assert [r["id"] for r in res.json()["recommendations"]] == ["calorie_surplus_moderate"]


def test_endpoint_targets_optional_and_top_n_validated() -> None:
    ok = client.post(
        "/recommendations",
        json={"daily_features": {"sleep_hours": 4, "water_ml": 100}, "top_n": 1},
        headers=HEADERS,
    )
    assert [r["id"] for r in ok.json()["recommendations"]] == ["sleep_quality_poor"]
    bad = client.post("/recommendations", json={"daily_features": {}, "top_n": 0}, headers=HEADERS)
    assert bad.status_code == 422


def test_endpoint_requires_api_key() -> None:
    assert client.post("/recommendations", json={"daily_features": {}}).status_code == 401
