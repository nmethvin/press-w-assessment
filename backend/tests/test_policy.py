from app.domain.policy import classify_message, ensure_allergen_notice


def test_medical_request_is_classified() -> None:
    assert classify_message("I have diabetes, what should I eat?") == "medical"


def test_food_safety_request_is_classified() -> None:
    assert classify_message("Is this chicken safe to eat after sitting out?") == "food_safety"


def test_allergen_notice_is_added_once() -> None:
    first = ensure_allergen_notice("Make a pasta recipe with tomatoes.")
    second = ensure_allergen_notice(first)

    assert "Allergen note:" in first
    assert first == second
