from app.agent.graph import enforce_recipe_fit_for_response, remove_unsafe_allergen_claims
from app.domain.profile import ProfileUpdate
from app.storage import init_db, update_profile


def test_response_validator_flags_recipes_requiring_missing_equipment() -> None:
    init_db()
    user_id = "validator-test"
    update_profile(
        user_id,
        ProfileUpdate(
            pantry=["chicken", "potatoes", "carrots", "olive oil", "herbs", "tomatoes", "garlic", "bread"],
            equipment=["stovetop", "pan", "knife"],
            preferences=["stovetop"],
            allergies=[],
        ),
    )

    content = "Try Chicken Potato Stew or Tomato Garlic Soup."
    corrected, trace = enforce_recipe_fit_for_response(content, user_id)

    assert "### Equipment check" in corrected
    assert "Chicken Potato Stew" in corrected
    assert "Tomato Garlic Soup" in corrected
    assert "requires pot" in corrected
    assert any(item.get("validator") == "recipe_fit" for item in trace)


def test_response_validator_removes_allergen_safety_claims() -> None:
    content = "Just a reminder to keep an eye on allergens, but this recipe looks safe based on what you've shared. Enjoy!"

    cleaned = remove_unsafe_allergen_claims(content)

    assert "looks safe" not in cleaned.lower()
    assert "Enjoy!" in cleaned
