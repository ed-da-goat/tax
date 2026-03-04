"""
API router for Journal Entries / General Ledger (module F3).

All endpoints are scoped to a client via /clients/{client_id}/journal-entries.

Compliance (CLAUDE.md):
- Client isolation: client_id from URL path is used in every query (rule #4).
- Role enforcement: CPA_OWNER required for approve/void (rule #5, #6).
- Double-entry: enforced at app + DB levels (rule #1).
- Soft deletes only: void creates reversing entry (rule #2).
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.models.journal_entry import JournalEntryStatus
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryList,
    JournalEntryResponse,
    JournalEntryUpdate,
    JournalEntryStatus as SchemaStatus,
    TrialBalanceResponse,
    TrialBalanceRow,
)
from app.services.journal_entry import JournalEntryService

router = APIRouter()


@router.post(
    "/clients/{client_id}/journal-entries",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new journal entry with lines",
)
async def create_journal_entry(
    client_id: uuid.UUID,
    data: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> JournalEntryResponse:
    """
    Create a new journal entry. Both roles allowed.

    ASSOCIATE entries start as DRAFT.
    Compliance (rule #5): Never auto-post on entry.
    Compliance (rule #1): Debits must equal credits.
    """
    # Override client_id from URL path (never trust body for client scoping)
    data.client_id = client_id

    entry = await JournalEntryService.create_entry(db, data, user)
    await db.commit()
    return JournalEntryResponse.model_validate(entry)


@router.get(
    "/clients/{client_id}/journal-entries",
    response_model=JournalEntryList,
    summary="List journal entries for a client",
)
async def list_journal_entries(
    client_id: uuid.UUID,
    status_filter: SchemaStatus | None = Query(None, alias="status"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> JournalEntryList:
    """List journal entries for a client with optional filters. Both roles allowed."""
    model_status = None
    if status_filter is not None:
        model_status = JournalEntryStatus(status_filter.value)

    entries, total = await JournalEntryService.list_entries(
        db, client_id,
        status_filter=model_status,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return JournalEntryList(
        items=[JournalEntryResponse.model_validate(e) for e in entries],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/clients/{client_id}/journal-entries/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Get a single journal entry with its lines",
)
async def get_journal_entry(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> JournalEntryResponse:
    """Get a specific journal entry by ID. Both roles allowed."""
    entry = await JournalEntryService.get_entry(db, client_id, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )
    return JournalEntryResponse.model_validate(entry)


@router.post(
    "/clients/{client_id}/journal-entries/{entry_id}/submit",
    response_model=JournalEntryResponse,
    summary="Submit a journal entry for approval",
)
async def submit_journal_entry(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> JournalEntryResponse:
    """Submit a DRAFT entry for approval. Both roles allowed."""
    entry = await JournalEntryService.submit_for_approval(db, client_id, entry_id, user)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )
    await db.commit()
    return JournalEntryResponse.model_validate(entry)


@router.post(
    "/clients/{client_id}/journal-entries/{entry_id}/approve",
    response_model=JournalEntryResponse,
    summary="Approve and post a journal entry",
)
async def approve_journal_entry(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> JournalEntryResponse:
    """
    Approve and post a PENDING_APPROVAL entry. CPA_OWNER only.

    Compliance (rule #5): Only CPA_OWNER can post.
    Compliance (rule #6): Defense in depth — both route and function level.
    """
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    entry = await JournalEntryService.approve_and_post(db, client_id, entry_id, user)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )
    await db.commit()
    return JournalEntryResponse.model_validate(entry)


@router.post(
    "/clients/{client_id}/journal-entries/{entry_id}/void",
    response_model=JournalEntryResponse,
    summary="Void a posted journal entry (creates reversing entry)",
)
async def void_journal_entry(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> JournalEntryResponse:
    """
    Void a POSTED entry and create a reversing entry. CPA_OWNER only.

    Compliance (rule #2): Never hard delete. Creates reversing entry.
    Compliance (rule #5): Only CPA_OWNER can void.
    Compliance (rule #6): Defense in depth — both route and function level.
    """
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    result = await JournalEntryService.void_entry(db, client_id, entry_id, user)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )
    voided_entry, _reversing_entry = result
    await db.commit()
    return JournalEntryResponse.model_validate(voided_entry)


@router.get(
    "/clients/{client_id}/trial-balance",
    response_model=TrialBalanceResponse,
    summary="Get trial balance for a client",
)
async def get_trial_balance(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TrialBalanceResponse:
    """
    Get the trial balance for a client (posted entries only).

    Both roles allowed.
    Compliance (rule #4): ALWAYS filters by client_id.
    """
    rows = await JournalEntryService.get_trial_balance(db, client_id)

    trial_rows = [
        TrialBalanceRow(
            client_id=row.client_id,
            account_number=row.account_number,
            account_name=row.account_name,
            account_type=row.account_type,
            sub_type=row.sub_type,
            total_debits=row.total_debits,
            total_credits=row.total_credits,
            balance=row.balance,
        )
        for row in rows
    ]

    total_debits = sum(r.total_debits for r in trial_rows)
    total_credits = sum(r.total_credits for r in trial_rows)

    return TrialBalanceResponse(
        client_id=client_id,
        rows=trial_rows,
        total_debits=total_debits,
        total_credits=total_credits,
    )
