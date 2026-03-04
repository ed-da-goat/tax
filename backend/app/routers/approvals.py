"""
API router for Transaction Approval Workflow (module T4).

Provides endpoints for the approval queue, batch approve/reject,
individual rejection, and approval history.

Compliance (CLAUDE.md):
- Rule #5: Only CPA_OWNER can approve or reject entries.
- Rule #6: Defense in depth — role checks at BOTH route and function level.
- Rule #4: Client isolation enforced on per-client endpoints.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.schemas.approval import (
    ApprovalHistoryResponse,
    ApprovalQueueFilters,
    ApprovalQueueResponse,
    BatchApprovalRequest,
    BatchApprovalResponse,
    RejectionRequest,
    RejectionResponse,
)
from app.services.approval import ApprovalService

router = APIRouter()


@router.get(
    "/approvals",
    response_model=ApprovalQueueResponse,
    summary="Get the approval queue",
)
async def get_approval_queue(
    client_id: uuid.UUID | None = Query(None, description="Filter by client"),
    date_from: date | None = Query(None, description="Filter entries from this date"),
    date_to: date | None = Query(None, description="Filter entries up to this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ApprovalQueueResponse:
    """
    Get all PENDING_APPROVAL journal entries as a queue.

    CPA_OWNER sees all clients. ASSOCIATE sees only their own entries.
    """
    items, total = await ApprovalService.get_approval_queue(
        db,
        current_user=user,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return ApprovalQueueResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        filters=ApprovalQueueFilters(
            client_id=client_id,
            date_from=date_from,
            date_to=date_to,
        ),
    )


@router.post(
    "/approvals/batch",
    response_model=BatchApprovalResponse,
    summary="Batch approve/reject journal entries",
)
async def batch_approve(
    request: BatchApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> BatchApprovalResponse:
    """
    Process multiple approve/reject actions in a single request.

    CPA_OWNER ONLY. Each action is processed independently.

    Compliance (rule #5): Only CPA_OWNER can approve or reject.
    Compliance (rule #6): Defense in depth — route + function level checks.
    """
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    results = await ApprovalService.batch_process(db, user, request.actions)
    await db.commit()

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    return BatchApprovalResponse(
        results=results,
        total_processed=len(results),
        total_succeeded=succeeded,
        total_failed=failed,
    )


@router.post(
    "/clients/{client_id}/journal-entries/{entry_id}/reject",
    response_model=RejectionResponse,
    summary="Reject a journal entry",
)
async def reject_journal_entry(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    request: RejectionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> RejectionResponse:
    """
    Reject a PENDING_APPROVAL entry, moving it back to DRAFT with a note.

    CPA_OWNER ONLY. The rejection note explains why the entry was rejected.

    Compliance (rule #5): Only CPA_OWNER can reject.
    Compliance (rule #6): Defense in depth — route + function level checks.
    """
    # Defense in depth: function-level role check
    verify_role(user, "CPA_OWNER")

    from datetime import datetime, timezone

    entry = await ApprovalService.reject_entry(
        db, client_id, entry_id, user, request.note
    )
    await db.commit()

    return RejectionResponse(
        entry_id=entry.id,
        status=entry.status.value,
        rejection_note=request.note,
        rejected_by=uuid.UUID(user.user_id),
        rejected_at=entry.updated_at,
    )


@router.get(
    "/clients/{client_id}/journal-entries/{entry_id}/history",
    response_model=ApprovalHistoryResponse,
    summary="Get approval history for a journal entry",
)
async def get_approval_history(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ApprovalHistoryResponse:
    """
    Get the full approval history (status changes) for a journal entry.

    Both roles allowed — useful for tracking where an entry is in the workflow.

    Compliance (rule #4): Entry must belong to the specified client.
    """
    history = await ApprovalService.get_approval_history(db, client_id, entry_id)
    return ApprovalHistoryResponse(
        entry_id=entry_id,
        history=history,
    )
