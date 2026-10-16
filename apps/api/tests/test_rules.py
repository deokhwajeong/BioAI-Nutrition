from app.services.recommendations import load_rules


def test_yaml_rules_are_loaded() -> None:
    rules = load_rules()
    assert len(rules) >= 8
    assert all("id" in rule for rule in rules)
