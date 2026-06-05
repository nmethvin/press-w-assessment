from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import storage
from app.agent.graph import PantryPalAgent
from app.domain.policy import classify_message, ensure_allergen_notice
from app.domain.profile import ProfileUpdate, UserProfile


class ChatRequest(BaseModel):
    message: str
    user_id: str = "demo"


class ChatResponse(BaseModel):
    message: str
    content: Optional[Dict[str, Any]] = None
    active_recipe: Optional[Dict[str, Any]] = None
    policy: str
    trace: List[Dict[str, Any]]
    mode: str = "langgraph"
    model: str = "deterministic-policy"
    model_tier: str = "none"
    routing_reason: str = ""


app = FastAPI(title="PantryPal Demo")
agent = PantryPalAgent()
static_dir = Path(__file__).parent / "static"
storage.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    storage.init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profile/{user_id}", response_model=UserProfile)
def get_profile(user_id: str) -> UserProfile:
    return storage.get_profile(user_id)


@app.put("/api/profile/{user_id}", response_model=UserProfile)
def put_profile(user_id: str, update: ProfileUpdate) -> UserProfile:
    return storage.update_profile(user_id, update)


@app.get("/api/active-recipe/{user_id}")
def get_active_recipe(user_id: str) -> Dict[str, Any]:
    return {"active_recipe": storage.get_active_recipe(user_id)}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    recent_messages = storage.get_recent_conversation(request.user_id)
    active_recipe = storage.get_active_recipe(request.user_id)
    active_context = recent_messages + ([{"role": "assistant", "content": str(active_recipe)}] if active_recipe else [])
    policy = classify_message(request.message, active_context)
    storage.add_conversation_message(request.user_id, "user", request.message)
    result = agent.invoke(request.message, request.user_id, policy, recent_messages, active_recipe)
    message = result["message"]
    if result.get("policy", policy) == "food":
        message = ensure_allergen_notice(message)
    if result.get("content", {}).get("recipes"):
        active_recipe = storage.save_active_recipe(request.user_id, result["content"])
    storage.add_conversation_message(request.user_id, "assistant", message)
    return ChatResponse(
        message=message,
        content=result.get("content"),
        active_recipe=active_recipe,
        policy=result.get("policy", policy),
        trace=result.get("trace", []),
        mode=result.get("mode", "langgraph"),
        model=result.get("model", "deterministic-policy"),
        model_tier=result.get("model_tier", "none"),
        routing_reason=result.get("routing_reason", ""),
    )


app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")
