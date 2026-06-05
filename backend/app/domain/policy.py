from __future__ import annotations

from typing import Optional

ALLERGEN_NOTICE = (
    "Allergen note: Please verify every ingredient and label for your household's allergies and sensitivities."
)

FOOD_SCOPE_TERMS = {
    "cook",
    "cooking",
    "recipe",
    "ingredient",
    "ingredients",
    "meal",
    "dinner",
    "lunch",
    "breakfast",
    "pantry",
    "equipment",
    "substitute",
    "substitution",
    "wine",
    "pairing",
    "hosting",
    "menu",
    "food",
    "kitchen",
    "leftovers",
    "chicken",
    "pasta",
    "vegetarian",
    "keto",
    "soup",
    "stew",
    "broth",
    "stock",
    "sauce",
    "salad",
    "sandwich",
    "snack",
    "dessert",
    "bake",
    "roast",
    "grill",
    "stovetop",
    "oven",
    "breakfast",
    "beans",
    "rice",
    "chicken",
    "beef",
    "pork",
    "fish",
    "vegetables",
    "vegetable",
}

MEDICAL_TERMS = {
    "diabetes",
    "diabetic",
    "pregnant",
    "pregnancy",
    "blood pressure",
    "hypertension",
    "cholesterol",
    "weight loss",
    "therapeutic",
    "medical",
}

FOOD_SAFETY_TERMS = {
    "safe to eat",
    "spoiled",
    "spoilage",
    "food poisoning",
    "left out",
    "expired",
    "smells bad",
}

FOLLOW_UP_TERMS = {
    "one",
    "that",
    "those",
    "it",
    "yes",
    "yeah",
    "yep",
    "sure",
    "please",
    "suggest",
    "recommend",
    "pick",
    "make",
}


def classify_message(message: str, recent_messages: Optional[list[dict[str, str]]] = None) -> str:
    text = message.lower()
    if any(term in text for term in FOOD_SAFETY_TERMS):
        return "food_safety"
    if any(term in text for term in MEDICAL_TERMS):
        return "medical"
    tokens = set(text.replace("?", " ").replace(",", " ").split())
    if _is_food_follow_up(tokens, recent_messages or []):
        return "food"
    if tokens and not (tokens & FOOD_SCOPE_TERMS):
        return "off_topic"
    return "food"


def _is_food_follow_up(tokens: set[str], recent_messages: list[dict[str, str]]) -> bool:
    if not tokens or not (tokens & FOLLOW_UP_TERMS):
        return False
    recent_text = " ".join(message["content"].lower() for message in recent_messages[-4:])
    recent_tokens = set(recent_text.replace("?", " ").replace(",", " ").split())
    return bool(recent_tokens & FOOD_SCOPE_TERMS)


def needs_allergen_notice(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in ["recipe", "ingredient", "ingredients", "make", "cook", "substitute"])


def ensure_allergen_notice(text: str) -> str:
    if ALLERGEN_NOTICE.lower() in text.lower():
        return text
    if needs_allergen_notice(text):
        return f"{text.rstrip()}\n\n{ALLERGEN_NOTICE}"
    return text


def refusal_for_policy(policy: str) -> Optional[str]:
    if policy == "medical":
        return (
            "I cannot provide medical or therapeutic nutrition advice. I can help filter recipes by neutral "
            "preferences you choose, like vegetarian, keto, spicy, or nut-free, but please ask a qualified "
            "professional about diet choices for a medical condition."
        )
    if policy == "off_topic":
        return (
            "I am PantryPal, so I stay focused on household cooking, ingredients, kitchen equipment, meal planning, "
            "substitutions, pairings, and hosting menus. Bring me a food question and I am in."
        )
    return None
