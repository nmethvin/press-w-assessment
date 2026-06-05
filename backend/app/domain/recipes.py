from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    summary: str
    ingredients: list[str]
    required_equipment: list[str]
    optional_equipment: list[str]
    tags: list[str]
    time_minutes: int
    steps: list[str]
    substitutions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FitResult:
    recipe_id: str
    recipe_name: str
    can_make: bool
    missing_ingredients: list[str]
    missing_equipment: list[str]
    substitutions: dict[str, str]
    workarounds: list[str]


SEED_RECIPES: list[Recipe] = [
    Recipe(
        id="one-pan-tomato-pasta",
        name="One-Pan Tomato Pasta",
        summary="A fast stovetop pasta built for limited cookware.",
        ingredients=["pasta", "tomatoes", "garlic", "olive oil", "cheese"],
        required_equipment=["stovetop", "pan", "knife"],
        optional_equipment=["grater"],
        tags=["vegetarian", "fast", "stovetop", "one-pan"],
        time_minutes=25,
        steps=[
            "Warm olive oil in a pan and cook sliced garlic for 30 seconds.",
            "Add tomatoes, pasta, salt, and enough water to barely cover.",
            "Simmer, stirring often, until the pasta is tender and glossy.",
            "Finish with cheese and a little more olive oil.",
        ],
        substitutions={"cheese": "nutritional yeast or breadcrumbs", "tomatoes": "jarred marinara"},
    ),
    Recipe(
        id="skillet-lemon-chicken",
        name="Skillet Lemon Chicken",
        summary="A stovetop alternative when roasted chicken is not feasible.",
        ingredients=["chicken", "lemon", "garlic", "olive oil", "herbs"],
        required_equipment=["stovetop", "pan", "knife"],
        optional_equipment=["thermometer"],
        tags=["chicken", "stovetop", "dinner"],
        time_minutes=30,
        steps=[
            "Pound chicken to an even thickness and season it.",
            "Sear in a hot pan with olive oil until browned.",
            "Add lemon, garlic, and a splash of water; cover briefly to finish.",
            "Rest before slicing.",
        ],
        substitutions={"lemon": "vinegar plus a pinch of sugar", "herbs": "dried oregano or thyme"},
    ),
    Recipe(
        id="sheet-pan-roasted-chicken",
        name="Sheet-Pan Roasted Chicken",
        summary="Classic oven-roasted chicken and vegetables.",
        ingredients=["chicken", "potatoes", "carrots", "olive oil", "herbs"],
        required_equipment=["oven", "sheet pan", "knife"],
        optional_equipment=["thermometer"],
        tags=["chicken", "oven", "dinner"],
        time_minutes=55,
        steps=[
            "Heat oven to 425 F.",
            "Toss chicken and vegetables with oil, herbs, salt, and pepper.",
            "Roast on a sheet pan until browned and cooked through.",
        ],
        substitutions={"potatoes": "sweet potatoes or cauliflower", "carrots": "onions or squash"},
    ),
    Recipe(
        id="chickpea-coconut-curry",
        name="Chickpea Coconut Curry",
        summary="A pantry-friendly curry for rice, flatbread, or noodles.",
        ingredients=["chickpeas", "coconut milk", "curry powder", "onion", "rice"],
        required_equipment=["stovetop", "pot", "knife"],
        optional_equipment=["rice cooker"],
        tags=["vegan", "vegetarian", "stovetop", "keto-adjustable"],
        time_minutes=35,
        steps=[
            "Cook onion in oil until soft.",
            "Add curry powder, chickpeas, and coconut milk.",
            "Simmer until thick, then serve with rice or greens.",
        ],
        substitutions={"rice": "cauliflower rice or greens", "coconut milk": "cream plus water"},
    ),
    Recipe(
        id="blender-smoothie",
        name="Berry Blender Smoothie",
        summary="A quick smoothie that requires a blender.",
        ingredients=["berries", "yogurt", "banana", "milk"],
        required_equipment=["blender"],
        optional_equipment=[],
        tags=["breakfast", "fast"],
        time_minutes=5,
        steps=["Add ingredients to blender.", "Blend until smooth."],
        substitutions={"yogurt": "kefir or silken tofu", "milk": "oat milk or water"},
    ),
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "i",
    "me",
    "my",
    "of",
    "the",
    "to",
    "tonight",
    "want",
    "with",
}


def normalize_items(items: list[str]) -> set[str]:
    return {item.strip().lower() for item in items if item and item.strip()}


def normalize_query_terms(query: str) -> set[str]:
    raw_terms = normalize_items(query.replace(",", " ").replace("?", " ").split())
    return {term for term in raw_terms if term not in STOPWORDS and len(term) > 1}


def search_recipes(recipes: list[Recipe], query: str, tags: Optional[list[str]] = None) -> list[Recipe]:
    query_terms = normalize_query_terms(query)
    tag_filter = normalize_items(tags or [])

    scored: list[tuple[int, int, Recipe]] = []
    for recipe in recipes:
        haystack = normalize_items(
            [recipe.name, recipe.summary, *recipe.ingredients, *recipe.required_equipment, *recipe.tags]
        )
        explicit_score = len(query_terms & haystack)
        name = recipe.name.lower()
        summary = recipe.summary.lower()
        explicit_score += sum(3 for term in query_terms if term in name)
        explicit_score += sum(1 for term in query_terms if term in summary)
        preference_score = 0
        if tag_filter:
            preference_score = len(tag_filter & normalize_items(recipe.tags))
        if explicit_score > 0 or (not query_terms and preference_score > 0):
            scored.append((explicit_score, preference_score, recipe))

    return [
        recipe
        for _, _, recipe in sorted(scored, key=lambda item: (-item[0], -item[1], item[2].time_minutes))
    ]


def check_recipe_fit(recipe: Recipe, pantry: list[str], equipment: list[str]) -> FitResult:
    pantry_set = normalize_items(pantry)
    equipment_set = normalize_items(equipment)
    required_ingredients = normalize_items(recipe.ingredients)
    required_equipment = normalize_items(recipe.required_equipment)

    missing_ingredients = sorted(required_ingredients - pantry_set)
    missing_equipment = sorted(required_equipment - equipment_set)

    substitution_hits = {
        ingredient: substitute
        for ingredient, substitute in recipe.substitutions.items()
        if ingredient.lower() in missing_ingredients
    }
    workarounds = build_workarounds(recipe, missing_equipment)

    return FitResult(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        can_make=not missing_equipment and not missing_ingredients,
        missing_ingredients=missing_ingredients,
        missing_equipment=missing_equipment,
        substitutions=substitution_hits,
        workarounds=workarounds,
    )


def build_workarounds(recipe: Recipe, missing_equipment: list[str]) -> list[str]:
    workarounds: list[str] = []
    missing = normalize_items(missing_equipment)
    if "oven" in missing and "chicken" in normalize_items(recipe.ingredients):
        workarounds.append("Use a skillet chicken method instead of roasting.")
    if "blender" in missing:
        workarounds.append("Choose a no-blender breakfast, or mash soft fruit into yogurt by hand.")
    if "sheet pan" in missing:
        workarounds.append("Use an oven-safe skillet or roasting dish if you have one.")
    return workarounds
