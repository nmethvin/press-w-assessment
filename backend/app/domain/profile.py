from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str = "demo"
    pantry: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    pantry: Optional[list[str]] = None
    equipment: Optional[list[str]] = None
    preferences: Optional[list[str]] = None
    allergies: Optional[list[str]] = None
