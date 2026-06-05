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
