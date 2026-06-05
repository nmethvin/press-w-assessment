from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.agent.tools import TOOLS, check_recipe_fit_for_user, external_food_search, get_user_profile, search_recipe_catalog
from app.domain.policy import ensure_allergen_notice, refusal_for_policy


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


def _load_model():
    provider = os.getenv("PANTRYPAL_MODEL_PROVIDER", "openai").lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.3)
    return None


class PantryPalAgent:
    def __init__(self) -> None:
        self.model = _load_model()
        self.graph = create_react_agent(self.model, TOOLS, prompt=SYSTEM_PROMPT) if self.model else None

    def invoke(self, message: str, user_id: str, policy: str) -> Dict[str, Any]:
        refusal = refusal_for_policy(policy)
        trace: List[Dict[str, Any]] = []

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
            }

        if refusal:
            return {"message": refusal, "trace": trace, "policy": policy}

        if self.graph:
            result = self.graph.invoke(
                {
                    "messages": [
                        SystemMessage(content=f"Current user_id is {user_id}."),
                        HumanMessage(content=message),
                    ]
                },
                config={"configurable": {"thread_id": user_id}},
            )
            messages: list[BaseMessage] = result["messages"]
            trace = _extract_trace(messages)
            content = next((msg.content for msg in reversed(messages) if isinstance(msg, AIMessage)), "")
            return {"message": ensure_allergen_notice(str(content)), "trace": trace, "policy": policy}

        return self._offline_agent(message, user_id, policy)

    def _offline_agent(self, message: str, user_id: str, policy: str) -> Dict[str, Any]:
        """Deterministic fallback for local demos without an LLM key."""
        trace: List[Dict[str, Any]] = []
        profile = get_user_profile.invoke({"user_id": user_id})
        trace.append({"tool": "get_user_profile", "input": {"user_id": user_id}, "output": profile})

        recipes = search_recipe_catalog.invoke({"query": message, "tags": profile.get("preferences", []), "limit": 3})
        trace.append({"tool": "search_recipe_catalog", "input": {"query": message}, "output": recipes})

        if not recipes:
            answer = "I can help with that food question, but I do not have a strong recipe match in the demo catalog yet."
            return {"message": answer, "trace": trace, "policy": policy, "mode": "offline_fallback"}

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

        return {"message": ensure_allergen_notice(answer), "trace": trace, "policy": policy, "mode": "offline_fallback"}


def _extract_trace(messages: list[BaseMessage]) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    for message in messages:
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                trace.append({"tool": call.get("name"), "input": call.get("args"), "id": call.get("id")})
        elif isinstance(message, ToolMessage):
            trace.append({"tool_result": message.name, "output": message.content, "id": message.tool_call_id})
    return trace
