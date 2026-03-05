"""
Pydantic schemas for authentication and user management endpoints.

Request/response models for:
- Login (email + password -> JWT)
- User CRUD (create, read, update)
"""

from datetime import datetime
from uuid import UUID

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_strength(password: str) -> str:
    """Enforce password complexity: upper, lower, digit, special char."""
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
        raise ValueError("Password must contain at least one special character")
    return password


class LoginRequest(BaseModel):
    """POST /api/v1/auth/login request body."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """User data returned in API responses (never includes password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    """POST /api/v1/auth/login response body."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreate(BaseModel):
    """POST /api/v1/auth/users request body. CPA_OWNER only."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(pattern=r"^(CPA_OWNER|ASSOCIATE)$")

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """POST /api/v1/auth/change-password request body."""

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_complexity(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserUpdate(BaseModel):
    """PUT /api/v1/auth/users/{id} request body. CPA_OWNER only."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, pattern=r"^(CPA_OWNER|ASSOCIATE)$")
    is_active: bool | None = None
