from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from app.domain.profile import ProfileUpdate, UserProfile
from app.domain.recipes import Recipe, SEED_RECIPES


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "pantrypal.sqlite3"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                pantry TEXT NOT NULL,
                equipment TEXT NOT NULL,
                preferences TEXT NOT NULL,
                allergies TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS active_recipes (
                user_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for recipe in SEED_RECIPES:
            conn.execute(
                "INSERT OR IGNORE INTO recipes (id, payload) VALUES (?, ?)",
                (recipe.id, json.dumps(recipe.__dict__)),
            )
        conn.commit()


def get_profile(user_id: str = "demo") -> UserProfile:
    with connect() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return UserProfile(
                user_id=row["user_id"],
                pantry=json.loads(row["pantry"]),
                equipment=json.loads(row["equipment"]),
                preferences=json.loads(row["preferences"]),
                allergies=json.loads(row["allergies"]),
            )
        profile = UserProfile(
            user_id=user_id,
            pantry=["pasta", "tomatoes", "garlic", "olive oil", "cheese"],
            equipment=["stovetop", "pan", "knife"],
            preferences=["fast", "household cooking"],
            allergies=[],
        )
        save_profile(profile)
        return profile


def save_profile(profile: UserProfile) -> UserProfile:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO profiles (user_id, pantry, equipment, preferences, allergies)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                pantry = excluded.pantry,
                equipment = excluded.equipment,
                preferences = excluded.preferences,
                allergies = excluded.allergies
            """,
            (
                profile.user_id,
                json.dumps(profile.pantry),
                json.dumps(profile.equipment),
                json.dumps(profile.preferences),
                json.dumps(profile.allergies),
            ),
        )
        conn.commit()
    return profile


def update_profile(user_id: str, update: ProfileUpdate) -> UserProfile:
    current = get_profile(user_id)
    data = current.model_dump()
    for key, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            data[key] = value
    return save_profile(UserProfile(**data))


def list_recipes() -> list[Recipe]:
    with connect() as conn:
        rows = conn.execute("SELECT payload FROM recipes").fetchall()
    return [Recipe(**json.loads(row["payload"])) for row in rows]


def get_recipe(recipe_id: str) -> Optional[Recipe]:
    with connect() as conn:
        row = conn.execute("SELECT payload FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    return Recipe(**json.loads(row["payload"])) if row else None


def add_conversation_message(user_id: str, role: str, content: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO conversation_messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        conn.commit()


def get_recent_conversation(user_id: str, limit: int = 8) -> list[dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM conversation_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def clear_conversation(user_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM conversation_messages WHERE user_id = ?", (user_id,))
        conn.commit()


def save_active_recipe(user_id: str, payload: dict) -> dict:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO active_recipes (user_id, payload, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, json.dumps(payload)),
        )
        conn.commit()
    return payload


def get_active_recipe(user_id: str) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute("SELECT payload FROM active_recipes WHERE user_id = ?", (user_id,)).fetchone()
    return json.loads(row["payload"]) if row else None


def clear_active_recipe(user_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM active_recipes WHERE user_id = ?", (user_id,))
        conn.commit()


def reset_session(user_id: str) -> None:
    clear_conversation(user_id)
    clear_active_recipe(user_id)
