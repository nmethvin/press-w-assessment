from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.agent.tools import TOOLS, check_recipe_fit_for_user, external_food_search, get_user_profile, search_recipe_catalog
from app.domain.policy import ensure_allergen_notice, refusal_for_policy


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
                "trace": trace,
                "policy": policy,
                "model": routing["model"],
                "model_tier": routing["tier"],
                "routing_reason": routing["reason"],
            }

        if refusal:
            return {
                "message": refusal,
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
            return {
                "message": ensure_allergen_notice(str(content)),
                "trace": trace,
                "policy": policy,
                "model": routing["model"],
                "model_tier": routing["tier"],
                "routing_reason": routing["reason"],
            }

        return self._offline_agent(message, user_id, policy, routing, recent_messages or [])

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
            return {
                "message": answer,
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

        return {
            "message": ensure_allergen_notice(answer),
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
