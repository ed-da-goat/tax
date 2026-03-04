"""
Pydantic schemas for Chart of Accounts (module F2).

Request/response models for account CRUD operations.
All accounts are scoped to a client_id for client isolation compliance.
"""

import enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class AccountType(str, enum.Enum):
    """Account type enum matching the PostgreSQL account_type enum."""

    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class AccountCreate(BaseSchema):
    """Schema for creating a new account in the chart of accounts."""

    account_number: str = Field(
        ..., min_length=1, max_length=20, description="Unique account number within the client"
    )
    account_name: str = Field(
        ..., min_length=1, max_length=255, description="Human-readable account name"
    )
    account_type: AccountType = Field(..., description="Account classification")
    sub_type: str | None = Field(
        None, max_length=100, description="Sub-classification (e.g. Current Asset)"
    )
    is_active: bool = Field(True, description="Whether the account is active")


class AccountUpdate(BaseSchema):
    """Schema for updating an existing account. All fields optional."""

    account_number: str | None = Field(None, min_length=1, max_length=20)
    account_name: str | None = Field(None, min_length=1, max_length=255)
    account_type: AccountType | None = None
    sub_type: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class AccountResponse(RecordSchema):
    """Schema for returning a single account."""

    client_id: UUID
    account_number: str
    account_name: str
    account_type: AccountType
    sub_type: str | None = None
    is_active: bool


class AccountList(BaseSchema):
    """Schema for returning a list of accounts."""

    items: list[AccountResponse]
    total: int
