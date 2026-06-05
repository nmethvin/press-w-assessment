from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app import storage
from app.agent.tools import TOOLS, check_recipe_fit_for_user, external_food_search, get_user_profile, search_recipe_catalog
from app.domain.policy import ensure_allergen_notice, refusal_for_policy
from app.domain.recipes import check_recipe_fit
from app.domain.responses import (
    AssistantContent,
    RecipeCandidate,
    RecipeSuggestion,
    build_recipe_suggestion,
    render_assistant_content,
    validate_recipe_candidate,
)


FAST_MODEL_ENV = "PANTRYPAL_FAST_MODEL"
SMART_MODEL_ENV = "PANTRYPAL_SMART_MODEL"
DEFAULT_FAST_MODEL = "gpt-4o-mini"
DEFAULT_SMART_MODEL = "gpt-4o"
SMART_TERMS = {
    "dinner party",
    "hosting",
    "menu",
    "meal plan",
    "week",
    "pairing",
    "wine",
    "multi-course",
    "three course",
    "3 course",
    "complex",
    "compare",
    "plan",
    "guests",
}


SYSTEM_PROMPT = """You are PantryPal, a household cooking assistant with a warm, opinionated friend-who-cooks voice.

Scope:
- Help with household cooking, ingredients, equipment, meal planning, substitutions, wine pairings, and hosting menus.
- Do not answer unrelated requests.
- Do not provide medical, therapeutic, or condition-specific nutrition advice.
- Do not determine whether a user's specific food is safe to eat. Give general guidance and direct to authoritative sources.

Tool discipline:
- Use tools when profile, pantry, equipment, recipe fit, substitutions, or external references would improve correctness.
- For recipe suggestions, check the user's profile and recipe fit before recommending.
- If you invent a recipe that is not from the catalog, call validate_recipe_candidate with the full ingredient and required equipment list before recommending it.
- Use exact saved pantry item names when they apply. If a required component is an alternative group, name it generically, e.g. "pizza base".
- If equipment or ingredients are missing, offer a workaround or similar feasible option.
- Keep answers concise and useful.

Allergen consistency:
- Any recipe or ingredient suggestion must include an allergen reminder unless the product layer already supplies one.
"""


def _load_model(model_name: str):
    provider = os.getenv("PANTRYPAL_MODEL_PROVIDER", "openai").lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, temperature=0.3)
    return None


def route_model(message: str, policy: str) -> Dict[str, str]:
    """Choose a model tier based on request complexity and safety policy."""
    fast_model = os.getenv(FAST_MODEL_ENV) or os.getenv("OPENAI_MODEL") or DEFAULT_FAST_MODEL
    smart_model = os.getenv(SMART_MODEL_ENV) or DEFAULT_SMART_MODEL

    if policy in {"off_topic", "medical", "food_safety"}:
        return {
            "tier": "none",
            "model": "deterministic-policy",
            "reason": f"{policy} handled without an LLM call",
        }

    text = message.lower()
    if any(term in text for term in SMART_TERMS) or len(message.split()) >= 28:
        return {
            "tier": "smart",
            "model": smart_model,
            "reason": "complex planning or food-adjacent request",
        }

    return {
        "tier": "fast",
        "model": fast_model,
        "reason": "simple household cooking request",
    }


class PantryPalAgent:
    def __init__(self) -> None:
        self.fast_model_name = os.getenv(FAST_MODEL_ENV) or os.getenv("OPENAI_MODEL") or DEFAULT_FAST_MODEL
        self.smart_model_name = os.getenv(SMART_MODEL_ENV) or DEFAULT_SMART_MODEL
        self.fast_model = _load_model(self.fast_model_name)
        self.smart_model = _load_model(self.smart_model_name)
        self.fast_graph = (
            create_react_agent(self.fast_model, TOOLS, state_modifier=SYSTEM_PROMPT) if self.fast_model else None
        )
        self.smart_graph = (
            create_react_agent(self.smart_model, TOOLS, state_modifier=SYSTEM_PROMPT) if self.smart_model else None
        )

    def invoke(
        self,
        message: str,
        user_id: str,
        policy: str,
        recent_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        refusal = refusal_for_policy(policy)
        trace: List[Dict[str, Any]] = []
        routing = route_model(message, policy)
        trace.append({"router": routing})

        if policy == "food_safety":
            search_result = external_food_search.invoke(
                {"query": "USDA FoodSafety.gov safe leftovers food storage guidance"}
            )
            trace.append({"tool": "external_food_search", "input": "USDA FoodSafety.gov safe leftovers food storage guidance", "output": search_result})
            return {
                "message": (
                    "I cannot tell you whether your specific food is safe to eat. When in doubt, throw it out. "
                    "For general guidance, check USDA FSIS or FoodSafety.gov for storage times, temperatures, and leftover handling."
                ),
                "content": AssistantContent(
                    response_type="refusal",
                    intro=(
                        "I cannot tell you whether your specific food is safe to eat. When in doubt, throw it out. "
                        "For general guidance, check USDA FSIS or FoodSafety.gov for storage times, temperatures, and leftover handling."
                    ),
                    safety_notes=[],
                ).model_dump(),
                "trace": trace,
                "policy": policy,
                "model": routing["model"],
                "model_tier": routing["tier"],
                "routing_reason": routing["reason"],
            }

        if refusal:
            content = AssistantContent(response_type="refusal", intro=refusal, allergen_notice="")
            return {
                "message": refusal,
                "content": content.model_dump(),
                "trace": trace,
                "policy": policy,
                "model": routing["model"],
                "model_tier": routing["tier"],
                "routing_reason": routing["reason"],
            }

        graph = self.smart_graph if routing["tier"] == "smart" else self.fast_graph
        if graph:
            history_messages = _to_langchain_history(recent_messages or [])
            result = graph.invoke(
                {
                    "messages": [
                        SystemMessage(content=f"Current user_id is {user_id}."),
                        *history_messages,
                        HumanMessage(content=message),
                    ]
                },
                config={"configurable": {"thread_id": user_id}},
            )
            messages: list[BaseMessage] = result["messages"]
            trace.extend(_extract_trace(messages))
            content = next((msg.content for msg in reversed(messages) if isinstance(msg, AIMessage)), "")
            content = remove_unsafe_allergen_claims(str(content))
            structured_content, structured_trace = structure_response_from_candidate_tool(trace)
            if not structured_content:
                structured_content, structured_trace = structure_response_from_catalog_mentions(content, user_id)
            if not structured_content:
                structured_content, structured_trace = self._structure_non_catalog_recipe(
                    content,
                    user_id,
                    routing["tier"],
                )
            trace.extend(structured_trace)
            if structured_content:
                rendered_content = render_assistant_content(structured_content)
                content_payload = structured_content.model_dump()
            else:
                rendered_content, validation_trace = enforce_recipe_fit_for_response(content, user_id)
                trace.extend(validation_trace)
                content_payload = AssistantContent(
                    response_type="general",
                    intro=rendered_content,
                ).model_dump()
            return {
                "message": ensure_allergen_notice(rendered_content),
                "content": content_payload,
                "trace": trace,
                "policy": policy,
                "model": routing["model"],
                "model_tier": routing["tier"],
                "routing_reason": routing["reason"],
            }

        return self._offline_agent(message, user_id, policy, routing, recent_messages or [])

    def _structure_non_catalog_recipe(
        self,
        content: str,
        user_id: str,
        tier: str,
    ) -> tuple[Optional[AssistantContent], List[Dict[str, Any]]]:
        model = self.smart_model if tier == "smart" else self.fast_model
        if not model or "recipe" not in content.lower() and "ingredients" not in content.lower():
            return None, []

        profile = storage.get_profile(user_id)
        formatter = model.with_structured_output(RecipeCandidate, method="function_calling")
        prompt = (
            "Extract exactly one proposed recipe candidate from the assistant draft below. "
            "Use concise canonical ingredient names. When an ingredient is already in the saved pantry, "
            "use the exact saved pantry term. If the recipe requires a category the user lacks, keep it generic "
            "such as 'pizza base'. Do not invent ingredients that are not required.\n\n"
            f"Saved pantry: {profile.pantry}\n"
            f"Saved equipment: {profile.equipment}\n\n"
            f"Assistant draft:\n{content}"
        )
        try:
            candidate = formatter.invoke(prompt)
        except Exception as exc:
            return None, [{"validator": "structured_candidate_extraction", "error": str(exc)}]

        suggestion = validate_recipe_candidate(candidate, profile)
        trace = [
            {
                "validator": "structured_candidate_extraction",
                "recipe_name": suggestion.title,
                "can_make": suggestion.can_make,
                "missing_equipment": suggestion.missing_equipment,
                "missing_ingredients": suggestion.missing_ingredients,
            }
        ]
        intro = "I checked that proposed recipe against your saved pantry and equipment."
        return AssistantContent(response_type="recipe", intro=intro, recipes=[suggestion]), trace

    def _offline_agent(
        self,
        message: str,
        user_id: str,
        policy: str,
        routing: Dict[str, str],
        recent_messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Deterministic fallback for local demos without an LLM key."""
        trace: List[Dict[str, Any]] = [{"router": routing}]
        profile = get_user_profile.invoke({"user_id": user_id})
        trace.append({"tool": "get_user_profile", "input": {"user_id": user_id}, "output": profile})

        recipe_query = _resolve_follow_up_query(message, recent_messages)
        recipes = search_recipe_catalog.invoke({"query": recipe_query, "tags": profile.get("preferences", []), "limit": 3})
        trace.append({"tool": "search_recipe_catalog", "input": {"query": recipe_query}, "output": recipes})

        if not recipes:
            answer = "I can help with that food question, but I do not have a strong recipe match in the demo catalog yet."
            content = AssistantContent(response_type="general", intro=answer)
            return {
                "message": answer,
                "content": content.model_dump(),
                "trace": trace,
                "policy": policy,
                "mode": "offline_fallback",
                "model": routing["model"],
                "model_tier": routing["tier"],
                "routing_reason": routing["reason"],
            }

        chosen = recipes[0]
        fit = check_recipe_fit_for_user.invoke({"recipe_id": chosen["id"], "user_id": user_id})
        trace.append({"tool": "check_recipe_fit_for_user", "input": {"recipe_id": chosen["id"]}, "output": fit})

        if fit.get("can_make"):
            steps = "\n".join(f"- {step}" for step in chosen["steps"])
            answer = (
                f"Make {chosen['name']}. It fits your current pantry and equipment.\n\n"
                f"{chosen['summary']}\n\n{steps}"
            )
        else:
            similar_text = ""
            workaround_text = ""
            if "oven" in fit.get("missing_equipment", []) and "chicken" in message.lower():
                alt = search_recipe_catalog.invoke({"query": "skillet chicken", "tags": ["stovetop"], "limit": 1})
                trace.append({"tool": "search_recipe_catalog", "input": {"query": "skillet chicken"}, "output": alt})
                if alt:
                    similar_text = f" A better fit is {alt[0]['name']}, which keeps the chicken-dinner idea on the stovetop."
            if fit.get("workarounds"):
                workaround_text = f" Workaround: {fit['workarounds'][0]}"
            answer = (
                f"I would not make {chosen['name']} as written: you are missing "
                f"{', '.join(fit.get('missing_equipment') or fit.get('missing_ingredients') or ['a requirement'])}."
                f"{similar_text}{workaround_text} I can help adapt it instead of leaving you with a dead end."
            )

        recipe = storage.get_recipe(chosen["id"])
        structured_content = None
        if recipe:
            profile = storage.get_profile(user_id)
            structured_content = AssistantContent(
                response_type="recipe",
                intro="Here is the best fit I found after checking your saved pantry and equipment.",
                recipes=[build_recipe_suggestion(recipe, profile)],
            )
            answer = render_assistant_content(structured_content)

        return {
            "message": ensure_allergen_notice(answer),
            "content": structured_content.model_dump() if structured_content else AssistantContent(
                response_type="general",
                intro=answer,
            ).model_dump(),
            "trace": trace,
            "policy": policy,
            "mode": "offline_fallback",
            "model": routing["model"],
            "model_tier": routing["tier"],
            "routing_reason": routing["reason"],
        }


def _extract_trace(messages: list[BaseMessage]) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    for message in messages:
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                trace.append({"tool": call.get("name"), "input": call.get("args"), "id": call.get("id")})
        elif isinstance(message, ToolMessage):
            trace.append({"tool_result": message.name, "output": message.content, "id": message.tool_call_id})
    return trace


def _to_langchain_history(recent_messages: List[Dict[str, str]]) -> List[BaseMessage]:
    history: List[BaseMessage] = []
    for item in recent_messages[-6:]:
        if item["role"] == "user":
            history.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant":
            history.append(AIMessage(content=item["content"]))
    return history


def _resolve_follow_up_query(message: str, recent_messages: List[Dict[str, str]]) -> str:
    text = message.lower().strip()
    if text not in {"suggest one", "recommend one", "pick one", "yes", "sure", "please"}:
        return message
    for item in reversed(recent_messages):
        if item["role"] == "user":
            return f"{item['content']} {message}"
    return message


def enforce_recipe_fit_for_response(content: str, user_id: str) -> tuple[str, List[Dict[str, Any]]]:
    profile = storage.get_profile(user_id)
    corrections: List[str] = []
    trace: List[Dict[str, Any]] = []
    mentioned_catalog_recipe = False

    for recipe in storage.list_recipes():
        if recipe.name.lower() not in content.lower():
            continue
        mentioned_catalog_recipe = True
        fit = check_recipe_fit(recipe, profile.pantry, profile.equipment)
        trace.append(
            {
                "validator": "recipe_fit",
                "recipe_id": recipe.id,
                "recipe_name": recipe.name,
                "can_make": fit.can_make,
                "missing_equipment": fit.missing_equipment,
                "missing_ingredients": fit.missing_ingredients,
            }
        )
        if fit.missing_equipment:
            workaround = f" Workaround: {fit.workarounds[0]}" if fit.workarounds else ""
            corrections.append(
                f"- **{recipe.name}** requires {', '.join(fit.missing_equipment)}, which is not in your saved equipment.{workaround}"
            )
        if fit.missing_ingredients:
            substitutions = (
                " Substitutions: "
                + "; ".join(f"{ingredient}: {substitute}" for ingredient, substitute in fit.substitutions.items())
                if fit.substitutions
                else ""
            )
            corrections.append(
                f"- **{recipe.name}** is missing ingredients from your saved pantry: {', '.join(fit.missing_ingredients)}.{substitutions}"
            )

    if not mentioned_catalog_recipe:
        generic_correction, generic_trace = validate_listed_requirements(content, profile.pantry, profile.equipment)
        trace.extend(generic_trace)
        corrections.extend(generic_correction)

    if not corrections:
        return content, trace

    correction_text = (
        "\n\n### Fit check\n"
        "I need to correct the fit check before you cook:\n"
        + "\n".join(corrections)
    )
    return f"{content.rstrip()}{correction_text}", trace


def structure_response_from_catalog_mentions(content: str, user_id: str) -> tuple[Optional[AssistantContent], List[Dict[str, Any]]]:
    profile = storage.get_profile(user_id)
    suggestions = []
    trace: List[Dict[str, Any]] = []
    for recipe in storage.list_recipes():
        if recipe.name.lower() not in content.lower():
            continue
        suggestion = build_recipe_suggestion(recipe, profile)
        suggestions.append(suggestion)
        trace.append(
            {
                "validator": "structured_recipe",
                "recipe_id": recipe.id,
                "recipe_name": recipe.name,
                "can_make": suggestion.can_make,
                "missing_equipment": suggestion.missing_equipment,
                "missing_ingredients": suggestion.missing_ingredients,
            }
        )
    if not suggestions:
        return None, trace
    intro = "I checked those recipe ideas against your saved pantry and equipment."
    return AssistantContent(response_type="options" if len(suggestions) > 1 else "recipe", intro=intro, recipes=suggestions), trace


def structure_response_from_candidate_tool(trace: List[Dict[str, Any]]) -> tuple[Optional[AssistantContent], List[Dict[str, Any]]]:
    suggestions = []
    validator_trace: List[Dict[str, Any]] = []
    for item in trace:
        if item.get("tool_result") != "validate_recipe_candidate":
            continue
        try:
            suggestion = RecipeSuggestion.model_validate_json(item["output"])
        except Exception:
            continue
        suggestions.append(suggestion)
        validator_trace.append(
            {
                "validator": "structured_candidate",
                "recipe_name": suggestion.title,
                "can_make": suggestion.can_make,
                "missing_equipment": suggestion.missing_equipment,
                "missing_ingredients": suggestion.missing_ingredients,
            }
        )
    if not suggestions:
        return None, validator_trace
    if any(not suggestion.can_make for suggestion in suggestions):
        intro = "I checked that idea against your saved pantry and equipment before recommending it."
    else:
        intro = "This recipe candidate fits your saved pantry and equipment."
    return AssistantContent(response_type="options" if len(suggestions) > 1 else "recipe", intro=intro, recipes=suggestions), validator_trace


PANTRY_STAPLES = {"salt", "pepper", "water", "stock", "oil", "olive oil"}
EQUIPMENT_EQUIVALENTS = {
    "baking sheet": {"sheet pan"},
    "pizza stone": {"sheet pan", "baking sheet"},
    "pizza cutter": {"knife"},
    "rolling pin": set(),
}


def validate_listed_requirements(
    content: str,
    pantry: List[str],
    equipment: List[str],
) -> tuple[List[str], List[Dict[str, Any]]]:
    listed_ingredients = extract_markdown_section_items(
        content,
        {"ingredients", "ingredient", "pizza dough", "dough", "toppings"},
    )
    listed_equipment = extract_markdown_section_items(content, {"equipment", "equipment needed", "required equipment"})
    pantry_set = {item.lower() for item in pantry}
    equipment_set = {item.lower() for item in equipment}

    missing_ingredients = [
        item for item in listed_ingredients if item.lower() not in pantry_set and item.lower() not in PANTRY_STAPLES
    ]
    missing_equipment = [item for item in listed_equipment if not has_equipment(item, equipment_set)]

    corrections: List[str] = []
    trace: List[Dict[str, Any]] = []
    if listed_ingredients or listed_equipment:
        trace.append(
            {
                "validator": "listed_requirements",
                "listed_ingredients": listed_ingredients,
                "listed_equipment": listed_equipment,
                "missing_ingredients": missing_ingredients,
                "missing_equipment": missing_equipment,
            }
        )
    if missing_ingredients:
        corrections.append(
            "- The suggested recipe lists ingredients missing from your saved pantry: "
            + ", ".join(missing_ingredients)
            + "."
        )
    if missing_equipment:
        corrections.append(
            "- The suggested recipe lists equipment missing from your saved kitchen: "
            + ", ".join(missing_equipment)
            + "."
        )
    return corrections, trace


def has_equipment(item: str, equipment_set: set[str]) -> bool:
    normalized = item.lower()
    if normalized in equipment_set:
        return True
    equivalents = EQUIPMENT_EQUIVALENTS.get(normalized, set())
    return bool(equivalents & equipment_set)


def extract_markdown_section_items(content: str, headings: set[str]) -> List[str]:
    items: List[str] = []
    in_section = False
    section_has_items = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            if in_section and section_has_items:
                in_section = False
                section_has_items = False
            continue
        heading_text = re.sub(r"^#{1,4}\s*", "", line).rstrip(":").strip().lower()
        if heading_matches(heading_text, headings):
            in_section = True
            section_has_items = False
            inline = line.split(":", 1)
            if len(inline) == 2 and inline[1].strip():
                items.extend(split_inline_items(inline[1]))
                section_has_items = True
            continue
        if in_section and re.match(r"^(#{1,4}\s*)?[A-Za-z][A-Za-z ]+:", line):
            candidate_heading = re.sub(r"^#{1,4}\s*", "", line).split(":", 1)[0].strip().lower()
            if not heading_matches(candidate_heading, headings):
                in_section = False
                section_has_items = False
                continue
        if in_section and re.match(r"^(#{1,4}\s*)?(steps|instructions|tips|substitutions|required equipment|equipment needed|equipment)\b", line, re.IGNORECASE):
            next_heading = re.sub(r"^#{1,4}\s*", "", line).split(":", 1)[0].strip().lower()
            in_section = heading_matches(next_heading, headings)
            section_has_items = False
            if not in_section:
                continue
        if in_section:
            item = parse_requirement_line(line)
            if item:
                items.append(item)
                section_has_items = True
    return dedupe_preserving_order(items)


def heading_matches(heading_text: str, headings: set[str]) -> bool:
    if heading_text in headings:
        return True
    if "ingredients" in headings and "ingredients" in heading_text:
        return True
    if "equipment" in headings and "equipment" in heading_text:
        return True
    return False


def split_inline_items(value: str) -> List[str]:
    return [clean_requirement_item(item) for item in re.split(r",|;", value) if clean_requirement_item(item)]


def parse_requirement_line(line: str) -> Optional[str]:
    stripped = re.sub(r"^[-*]\s*", "", line)
    stripped = re.sub(r"^\d+\.\s*", "", stripped)
    return clean_requirement_item(stripped)


def clean_requirement_item(item: str) -> str:
    item = re.sub(r"\*\*", "", item)
    item = item.split("(", 1)[0]
    item = item.split(":", 1)[0]
    item = re.sub(r"\b(optional|store-bought|homemade|fresh|sliced|canned)\b", "", item, flags=re.IGNORECASE)
    return " ".join(item.strip(" -.,").split())


def dedupe_preserving_order(items: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for item in items:
        key = item.lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def remove_unsafe_allergen_claims(content: str) -> str:
    patterns = [
        r"[^.!?]*looks safe based on what you['’]ve shared[.!?]\s*",
        r"[^.!?]*should be safe based on what you['’]ve shared[.!?]\s*",
    ]
    cleaned = content
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned
