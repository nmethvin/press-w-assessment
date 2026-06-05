from app.domain.recipes import SEED_RECIPES, check_recipe_fit, search_recipes


def test_no_oven_blocks_roasted_chicken() -> None:
    recipe = next(item for item in SEED_RECIPES if item.id == "sheet-pan-roasted-chicken")

    result = check_recipe_fit(
        recipe,
        pantry=["chicken", "potatoes", "carrots", "olive oil", "herbs"],
        equipment=["stovetop", "pan", "knife"],
    )

    assert result.can_make is False
    assert "oven" in result.missing_equipment
    assert result.workarounds


def test_one_pan_pasta_fits_limited_kitchen() -> None:
    recipe = next(item for item in SEED_RECIPES if item.id == "one-pan-tomato-pasta")

    result = check_recipe_fit(
        recipe,
        pantry=["pasta", "tomatoes", "garlic", "olive oil", "cheese"],
        equipment=["stovetop", "pan", "knife"],
    )

    assert result.can_make is True
    assert result.missing_equipment == []
    assert result.missing_ingredients == []


def test_recipe_search_prioritizes_direct_recipe_intent_over_preferences() -> None:
    results = search_recipes(
        SEED_RECIPES,
        "I want roasted chicken tonight",
        tags=["fast", "stovetop"],
    )

    assert results[0].id == "sheet-pan-roasted-chicken"
