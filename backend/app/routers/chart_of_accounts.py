"""
API router for Chart of Accounts (module F2).

All endpoints are scoped to a client via /clients/{client_id}/accounts.
Compliance (CLAUDE.md):
- Client isolation: client_id from URL path is used in every query (rule #4).
- Role enforcement: CPA_OWNER required for create/update/delete (rule #6).
- Soft deletes only (rule #2).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.schemas.chart_of_accounts import (
    AccountCreate,
    AccountList,
    AccountResponse,
    AccountType,
    AccountUpdate,
)
from app.services.chart_of_accounts import ChartOfAccountsService

router = APIRouter()


@router.post(
    "/clients/{client_id}/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account in the chart of accounts",
)
async def create_account(
    client_id: uuid.UUID,
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> AccountResponse:
    """Create a new account for the specified client. CPA_OWNER only."""
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    try:
        account = await ChartOfAccountsService.create_account(db, client_id, data)
        await db.commit()
        return AccountResponse.model_validate(account)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account number '{data.account_number}' already exists for this client",
        )


@router.get(
    "/clients/{client_id}/accounts",
    response_model=AccountList,
    summary="List accounts for a client",
)
async def list_accounts(
    client_id: uuid.UUID,
    account_type: AccountType | None = Query(None, description="Filter by account type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AccountList:
    """List all accounts for the specified client. Both roles allowed."""
    type_value = account_type.value if account_type is not None else None
    accounts = await ChartOfAccountsService.list_accounts(
        db, client_id, account_type=type_value, is_active=is_active
    )
    return AccountList(
        items=[AccountResponse.model_validate(a) for a in accounts],
        total=len(accounts),
    )


@router.get(
    "/clients/{client_id}/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Get a single account",
)
async def get_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AccountResponse:
    """Get a specific account by ID. Both roles allowed."""
    account = await ChartOfAccountsService.get_account(db, client_id, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return AccountResponse.model_validate(account)


@router.put(
    "/clients/{client_id}/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Update an account",
)
async def update_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> AccountResponse:
    """Update an existing account. CPA_OWNER only."""
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    try:
        account = await ChartOfAccountsService.update_account(db, client_id, account_id, data)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )
        await db.commit()
        return AccountResponse.model_validate(account)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account number already exists for this client",
        )


@router.delete(
    "/clients/{client_id}/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Deactivate (soft-delete) an account",
)
async def deactivate_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> AccountResponse:
    """Soft-delete an account. CPA_OWNER only. Records are never hard-deleted."""
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    account = await ChartOfAccountsService.deactivate_account(db, client_id, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    await db.commit()
    return AccountResponse.model_validate(account)


@router.post(
    "/clients/{client_id}/accounts/clone-template",
    response_model=AccountList,
    status_code=status.HTTP_201_CREATED,
    summary="Clone template accounts to a new client",
)
async def clone_template_accounts(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> AccountList:
    """
    Copy all accounts from the TEMPLATE client to the specified client.
    Used during client onboarding. CPA_OWNER only.
    """
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    try:
        accounts = await ChartOfAccountsService.clone_template_accounts(db, client_id)
        await db.commit()
        return AccountList(
            items=[AccountResponse.model_validate(a) for a in accounts],
            total=len(accounts),
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Some template accounts already exist for this client",
        )
