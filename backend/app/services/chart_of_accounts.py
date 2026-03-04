"""
Service layer for Chart of Accounts (module F2).

All queries enforce client_id filtering (CLAUDE.md compliance rule #4).
All queries filter deleted_at IS NULL unless explicitly overridden.
Soft deletes only (CLAUDE.md compliance rule #2).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chart_of_accounts import ChartOfAccounts
from app.schemas.chart_of_accounts import AccountCreate, AccountUpdate

# Template client UUID for cloning seed accounts
TEMPLATE_CLIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class ChartOfAccountsService:
    """Business logic for chart of accounts CRUD operations."""

    @staticmethod
    async def create_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: AccountCreate,
    ) -> ChartOfAccounts:
        """
        Create a new account for a specific client.

        Compliance: client_id is always set from the URL path,
        never from user-supplied body data.
        """
        account = ChartOfAccounts(
            client_id=client_id,
            account_number=data.account_number,
            account_name=data.account_name,
            account_type=data.account_type.value,
            sub_type=data.sub_type,
            is_active=data.is_active,
        )
        db.add(account)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def get_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> ChartOfAccounts | None:
        """
        Retrieve a single account by ID, filtered by client_id.

        Compliance (rule #4): ALWAYS filters by client_id so that
        Client A cannot retrieve Client B's accounts.
        """
        stmt = (
            select(ChartOfAccounts)
            .where(
                ChartOfAccounts.id == account_id,
                ChartOfAccounts.client_id == client_id,
                ChartOfAccounts.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_accounts(
        db: AsyncSession,
        client_id: uuid.UUID,
        account_type: str | None = None,
        is_active: bool | None = None,
    ) -> list[ChartOfAccounts]:
        """
        List all accounts for a client, with optional filters.

        Compliance (rule #4): ALWAYS filters by client_id.
        Always excludes soft-deleted records.
        """
        stmt = (
            select(ChartOfAccounts)
            .where(
                ChartOfAccounts.client_id == client_id,
                ChartOfAccounts.deleted_at.is_(None),
            )
            .order_by(ChartOfAccounts.account_number)
        )
        if account_type is not None:
            stmt = stmt.where(ChartOfAccounts.account_type == account_type)
        if is_active is not None:
            stmt = stmt.where(ChartOfAccounts.is_active == is_active)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        account_id: uuid.UUID,
        data: AccountUpdate,
    ) -> ChartOfAccounts | None:
        """
        Update an existing account. Only non-None fields are applied.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        account = await ChartOfAccountsService.get_account(db, client_id, account_id)
        if account is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "account_type" and value is not None:
                value = value.value if hasattr(value, "value") else value
            setattr(account, field, value)

        account.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def deactivate_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> ChartOfAccounts | None:
        """
        Soft-delete an account by setting deleted_at.

        Compliance (rule #2): Records are NEVER hard-deleted.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        account = await ChartOfAccountsService.get_account(db, client_id, account_id)
        if account is None:
            return None

        account.deleted_at = datetime.now(timezone.utc)
        account.is_active = False
        account.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def clone_template_accounts(
        db: AsyncSession,
        client_id: uuid.UUID,
    ) -> list[ChartOfAccounts]:
        """
        Copy all accounts from the TEMPLATE client to a new client.

        This is used during client onboarding to seed a standard
        Georgia chart of accounts.

        Compliance (rule #4): Template accounts are read with
        client_id = TEMPLATE_CLIENT_ID, new accounts are written
        with the target client_id.
        """
        # Fetch all active template accounts
        stmt = (
            select(ChartOfAccounts)
            .where(
                ChartOfAccounts.client_id == TEMPLATE_CLIENT_ID,
                ChartOfAccounts.deleted_at.is_(None),
                ChartOfAccounts.is_active.is_(True),
            )
            .order_by(ChartOfAccounts.account_number)
        )
        result = await db.execute(stmt)
        template_accounts = result.scalars().all()

        cloned: list[ChartOfAccounts] = []
        for template in template_accounts:
            new_account = ChartOfAccounts(
                client_id=client_id,
                account_number=template.account_number,
                account_name=template.account_name,
                account_type=template.account_type,
                sub_type=template.sub_type,
                is_active=True,
            )
            db.add(new_account)
            cloned.append(new_account)

        await db.flush()
        # Refresh all cloned accounts to get server-generated fields
        for account in cloned:
            await db.refresh(account)

        return cloned
