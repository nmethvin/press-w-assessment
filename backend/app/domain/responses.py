from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.policy import ALLERGEN_NOTICE
from app.domain.profile import UserProfile
from app.domain.recipes import Recipe, check_recipe_fit


class RecipeSuggestion(BaseModel):
    title: str
    summary: str = ""
    ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    required_equipment: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    missing_equipment: list[str] = Field(default_factory=list)
    substitutions: list[str] = Field(default_factory=list)
    workarounds: list[str] = Field(default_factory=list)
    can_make: bool = False


class AssistantContent(BaseModel):
    response_type: Literal["recipe", "options", "refusal", "general"] = "general"
    intro: str
    recipes: list[RecipeSuggestion] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    allergen_notice: str = ALLERGEN_NOTICE


def build_recipe_suggestion(recipe: Recipe, profile: UserProfile) -> RecipeSuggestion:
    fit = check_recipe_fit(recipe, profile.pantry, profile.equipment)
    substitutions = [f"{ingredient}: {substitute}" for ingredient, substitute in fit.substitutions.items()]
    return RecipeSuggestion(
        title=recipe.name,
        summary=recipe.summary,
        ingredients=recipe.ingredients,
        steps=recipe.steps,
        required_equipment=recipe.required_equipment,
        missing_ingredients=fit.missing_ingredients,
        missing_equipment=fit.missing_equipment,
        substitutions=substitutions,
        workarounds=fit.workarounds,
        can_make=fit.can_make,
    )


def render_assistant_content(content: AssistantContent) -> str:
    parts = [content.intro]
    for recipe in content.recipes:
        parts.append(render_recipe_suggestion(recipe))
    if content.safety_notes:
        parts.append("### Notes\n" + "\n".join(f"- {note}" for note in content.safety_notes))
    parts.append(content.allergen_notice)
    return "\n\n".join(part for part in parts if part)


def render_recipe_suggestion(recipe: RecipeSuggestion) -> str:
    parts = [f"### {recipe.title}"]
    if recipe.summary:
        parts.append(recipe.summary)
    if recipe.ingredients:
        parts.append("#### Ingredients\n" + "\n".join(f"- {item}" for item in recipe.ingredients))
    if recipe.required_equipment:
        parts.append("#### Required Equipment\n" + "\n".join(f"- {item}" for item in recipe.required_equipment))
    if recipe.steps:
        parts.append("#### Steps\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(recipe.steps, start=1)))
    fit_notes = []
    if recipe.missing_ingredients:
        fit_notes.append("Missing pantry items: " + ", ".join(recipe.missing_ingredients))
    if recipe.missing_equipment:
        fit_notes.append("Missing equipment: " + ", ".join(recipe.missing_equipment))
    if recipe.workarounds:
        fit_notes.extend(f"Workaround: {item}" for item in recipe.workarounds)
    if recipe.substitutions:
        fit_notes.extend(f"Substitution: {item}" for item in recipe.substitutions)
    if fit_notes:
        parts.append("#### Fit Check\n" + "\n".join(f"- {item}" for item in fit_notes))
    return "\n\n".join(parts)
