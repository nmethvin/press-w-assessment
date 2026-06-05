from app.domain.policy import classify_message, ensure_allergen_notice


def test_medical_request_is_classified() -> None:
    assert classify_message("I have diabetes, what should I eat?") == "medical"


def test_food_safety_request_is_classified() -> None:
    assert classify_message("Is this chicken safe to eat after sitting out?") == "food_safety"


def test_soup_or_stew_request_is_food() -> None:
    assert classify_message("i want some sort of soup or stew") == "food"


def test_pizza_request_is_food() -> None:
    assert classify_message("i want to make a pizza") == "food"


def test_dicing_tomatoes_question_is_food() -> None:
    assert classify_message("how thin do i dice the tomatoes?") == "food"


def test_follow_up_uses_recent_food_context() -> None:
    recent = [{"role": "user", "content": "i want to make a stew"}]

    assert classify_message("suggest one", recent) == "food"


def test_follow_up_without_food_context_stays_off_topic() -> None:
    assert classify_message("suggest one", []) == "off_topic"


def test_allergen_notice_is_added_once() -> None:
    first = ensure_allergen_notice("Make a pasta recipe with tomatoes.")
    second = ensure_allergen_notice(first)

    assert "Allergen note:" in first
    assert first == second
