from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from app import storage
from app.domain.profile import ProfileUpdate
from app.domain.recipes import check_recipe_fit, search_recipes
from app.domain.responses import RecipeCandidate, validate_recipe_candidate as validate_candidate


@tool
def get_user_profile(user_id: str = "demo") -> dict:
    """Read the user's persisted household pantry, equipment, preferences, and allergies."""
    return storage.get_profile(user_id).model_dump()


@tool
def update_user_profile(
    user_id: str = "demo",
    pantry: Optional[list[str]] = None,
    equipment: Optional[list[str]] = None,
    preferences: Optional[list[str]] = None,
    allergies: Optional[list[str]] = None,
) -> dict:
    """Persist explicit household pantry, equipment, preference, and allergy updates."""
    profile = storage.update_profile(
        user_id,
        ProfileUpdate(pantry=pantry, equipment=equipment, preferences=preferences, allergies=allergies),
    )
    return profile.model_dump()


@tool
def search_recipe_catalog(query: str, tags: Optional[list[str]] = None, limit: int = 3) -> list[dict]:
    """Search PantryPal's structured recipe catalog for candidate household recipes."""
    recipes = search_recipes(storage.list_recipes(), query=query, tags=tags)
    return [recipe.__dict__ for recipe in recipes[:limit]]


@tool
def check_recipe_fit_for_user(recipe_id: str, user_id: str = "demo") -> dict:
    """Check whether a structured recipe fits the user's persisted pantry and equipment."""
    recipe = storage.get_recipe(recipe_id)
    if recipe is None:
        return {"error": f"Recipe {recipe_id} was not found."}
    profile = storage.get_profile(user_id)
    return check_recipe_fit(recipe, profile.pantry, profile.equipment).__dict__


@tool
def suggest_workarounds(recipe_id: str, user_id: str = "demo") -> dict:
    """Suggest missing-ingredient substitutions, equipment workarounds, or similar recipes."""
    recipe = storage.get_recipe(recipe_id)
    if recipe is None:
        return {"error": f"Recipe {recipe_id} was not found."}
    profile = storage.get_profile(user_id)
    fit = check_recipe_fit(recipe, profile.pantry, profile.equipment)
    similar = []
    if not fit.can_make:
        candidates = search_recipes(storage.list_recipes(), query=" ".join(recipe.tags + recipe.ingredients), tags=recipe.tags)
        for candidate in candidates:
            if candidate.id == recipe.id:
                continue
            candidate_fit = check_recipe_fit(candidate, profile.pantry, profile.equipment)
            if not candidate_fit.missing_equipment:
                similar.append({"recipe": candidate.__dict__, "fit": candidate_fit.__dict__})
            if len(similar) >= 2:
                break
    return {"fit": fit.__dict__, "similar_options": similar}


@tool
def validate_recipe_candidate(
    title: str,
    ingredients: list[str],
    required_equipment: list[str],
    steps: list[str],
    user_id: str = "demo",
    summary: str = "",
) -> dict:
    """Validate an invented recipe candidate against the user's saved pantry and equipment before recommending it."""
    profile = storage.get_profile(user_id)
    candidate = RecipeCandidate(
        title=title,
        summary=summary,
        ingredients=ingredients,
        required_equipment=required_equipment,
        steps=steps,
    )
    return validate_candidate(candidate, profile).model_dump()


@tool
def external_food_search(query: str) -> dict:
    """Search external sources for food/cooking references, especially authoritative safety guidance."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        return {
            "query": query,
            "results": [
                {"title": item.get("title"), "href": item.get("href"), "body": item.get("body")}
                for item in results
            ],
        }
    except Exception as exc:  # pragma: no cover - depends on network/package runtime
        return {
            "query": query,
            "results": [
                {
                    "title": "USDA Food Safety and Inspection Service",
                    "href": "https://www.fsis.usda.gov/food-safety",
                    "body": "Authoritative food safety guidance from USDA FSIS.",
                },
                {
                    "title": "FoodSafety.gov",
                    "href": "https://www.foodsafety.gov/",
                    "body": "US government food safety information and safe-handling guidance.",
                },
            ],
            "warning": f"Live search unavailable: {exc}",
        }


TOOLS = [
    get_user_profile,
    update_user_profile,
    search_recipe_catalog,
    check_recipe_fit_for_user,
    suggest_workarounds,
    validate_recipe_candidate,
    external_food_search,
]
