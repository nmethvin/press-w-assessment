from app.agent.graph import (
    enforce_recipe_fit_for_response,
    extract_markdown_section_items,
    remove_unsafe_allergen_claims,
    structure_response_from_catalog_mentions,
)
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

    assert "### Fit check" in corrected
    assert "Chicken Potato Stew" in corrected
    assert "Tomato Garlic Soup" in corrected
    assert "requires pot" in corrected
    assert any(item.get("validator") == "recipe_fit" for item in trace)


def test_catalog_mentions_become_structured_recipe_fit() -> None:
    init_db()
    user_id = "structured-validator-test"
    update_profile(
        user_id,
        ProfileUpdate(
            pantry=["chicken", "potatoes", "carrots", "olive oil", "herbs"],
            equipment=["stovetop", "pan", "knife"],
            preferences=["stovetop"],
            allergies=[],
        ),
    )

    content, trace = structure_response_from_catalog_mentions("Try Chicken Potato Stew tonight.", user_id)

    assert content is not None
    assert content.recipes[0].title == "Chicken Potato Stew"
    assert content.recipes[0].missing_equipment == ["pot"]
    assert content.recipes[0].workarounds
    assert any(item.get("validator") == "structured_recipe" for item in trace)


def test_response_validator_removes_allergen_safety_claims() -> None:
    content = "Just a reminder to keep an eye on allergens, but this recipe looks safe based on what you've shared. Enjoy!"

    cleaned = remove_unsafe_allergen_claims(content)

    assert "looks safe" not in cleaned.lower()
    assert "Enjoy!" in cleaned


def test_response_validator_flags_non_catalog_missing_pizza_ingredients() -> None:
    init_db()
    user_id = "pizza-validator-test"
    update_profile(
        user_id,
        ProfileUpdate(
            pantry=["olive oil", "salt"],
            equipment=["oven", "knife"],
            preferences=[],
            allergies=[],
        ),
    )

    content = """Homemade Margherita Pizza

Ingredients:
- Pizza dough
- Tomato sauce
- Fresh mozzarella cheese
- Fresh basil leaves
- Olive oil
- Salt

Equipment Needed:
- Oven
- Baking sheet or pizza stone
- Knife or pizza cutter
"""

    corrected, trace = enforce_recipe_fit_for_response(content, user_id)

    assert "### Fit check" in corrected
    assert "Pizza dough" in corrected
    assert "Tomato sauce" in corrected
    assert "Fresh mozzarella cheese" in corrected
    assert any(item.get("validator") == "listed_requirements" for item in trace)


def test_extract_markdown_section_items_handles_plain_headings() -> None:
    content = """Ingredients:
- Pizza dough
- Tomato sauce

Steps:
1. Bake it.
"""

    assert extract_markdown_section_items(content, {"ingredients"}) == ["Pizza dough", "Tomato sauce"]


def test_extract_markdown_section_items_stops_after_list_section() -> None:
    content = """### Equipment:
- **Mixing bowl**
- **Rolling pin**

If you need help with substitutions, let me know!
"""

    assert extract_markdown_section_items(content, {"equipment"}) == ["Mixing bowl", "Rolling pin"]


def test_response_validator_flags_pizza_subsection_ingredients() -> None:
    init_db()
    user_id = "pizza-subsection-validator-test"
    update_profile(
        user_id,
        ProfileUpdate(
            pantry=["olive oil", "salt"],
            equipment=["oven", "knife"],
            preferences=[],
            allergies=[],
        ),
    )

    content = """### Pizza Dough Ingredients:
- **Flour**
- **Yeast**
- **Water**
- **Sugar**

### Toppings:
- **Tomato sauce**
- **Cheese**

### Equipment:
- **Mixing bowl**
- **Rolling pin**
"""

    corrected, trace = enforce_recipe_fit_for_response(content, user_id)

    assert "Flour" in corrected
    assert "Yeast" in corrected
    assert "Tomato sauce" in corrected
    assert "Mixing bowl" in corrected
    assert any(item.get("validator") == "listed_requirements" for item in trace)
