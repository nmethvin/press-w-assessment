from app.agent.graph import route_model


def test_simple_food_request_uses_fast_model(monkeypatch) -> None:
    monkeypatch.setenv("PANTRYPAL_FAST_MODEL", "fast-test-model")

    route = route_model("what can I make with pasta and tomatoes?", "food")

    assert route["tier"] == "fast"
    assert route["model"] == "fast-test-model"


def test_complex_planning_request_uses_smart_model(monkeypatch) -> None:
    monkeypatch.setenv("PANTRYPAL_SMART_MODEL", "smart-test-model")

    route = route_model("plan a dinner party menu with wine pairing for six guests", "food")

    assert route["tier"] == "smart"
    assert route["model"] == "smart-test-model"


def test_policy_request_bypasses_llm() -> None:
    route = route_model("write my cover letter", "off_topic")

    assert route["tier"] == "none"
    assert route["model"] == "deterministic-policy"
