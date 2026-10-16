"""Models for accounts, profiles, and per-user consent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..privacy.consent_manager import ConsentScope


class Credentials(BaseModel):
    username: str = Field(..., min_length=3, max_length=40, pattern=r"^[a-z0-9_.-]+$")
    password: str = Field(..., min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user_id: str


class Profile(BaseModel):
    weight_kg: float | None = Field(None, gt=20, lt=400)
    height_cm: float | None = Field(None, gt=50, lt=260)
    age: int | None = Field(None, ge=13, le=120)
    sex: Literal["male", "female"] | None = None
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] | None = None


class AccountOut(BaseModel):
    user_id: str
    username: str
    created_at: datetime
    profile: Profile


class ConsentUpdate(BaseModel):
    scope: ConsentScope
    granted: bool


class AccountConsentOut(BaseModel):
    user_id: str
    scopes: dict[str, bool] = Field(description="Every scope the user has decided on")


class DeletionReport(BaseModel):
    user_id: str
    deleted: dict[str, int] = Field(description="Rows removed per table")
