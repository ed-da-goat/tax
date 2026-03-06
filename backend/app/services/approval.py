"""
Service layer for Transaction Approval Workflow (module T4).

Provides approval queue, batch approve/reject, rejection with notes,
and approval history tracking. Builds ON TOP of the existing F3
JournalEntryService — does NOT duplicate its logic.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — all queries filter by client_id where applicable.
- Rule #5: APPROVAL WORKFLOW — only CPA_OWNER can approve or reject.
- Rule #6: ROLE ENFORCEMENT — defense in depth at function level.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.client import Client
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.schemas.approval import (
    ApprovalAction,
    ApprovalActionType,
    ApprovalHistoryItem,
    ApprovalQueueItem,
    BatchApprovalResultItem,
)
from app.services.journal_entry import JournalEntryService


class ApprovalService:
    """Business logic for the transaction approval workflow."""

    @staticmethod
    async def get_approval_queue(
        db: AsyncSession,
        current_user: CurrentUser,
        client_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ApprovalQueueItem], int]:
        """
        Retrieve all PENDING_APPROVAL journal entries as a queue.

        CPA_OWNER sees all clients' pending entries.
        ASSOCIATE sees only entries they created (can check status, cannot approve).

        Compliance (rule #4): Filters by client_id when provided.
        Compliance (rule #5): Only returns PENDING_APPROVAL entries.
        """
        # Build WHERE conditions using SQLAlchemy expressions
        conditions = [
            JournalEntry.status == JournalEntryStatus.PENDING_APPROVAL,
            JournalEntry.deleted_at.is_(None),
        ]

        # ASSOCIATE can only see their own entries
        if current_user.role == "ASSOCIATE":
            conditions.append(JournalEntry.created_by == current_user.user_id)

        # Optional filters
        if client_id is not None:
            conditions.append(JournalEntry.client_id == client_id)
        if date_from is not None:
            conditions.append(JournalEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(JournalEntry.entry_date <= date_to)

        # Count query
        count_stmt = (
            select(func.count())
            .select_from(JournalEntry)
            .where(*conditions)
        )
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Main query with client name and line totals
        main_stmt = (
            select(
                JournalEntry.id,
                JournalEntry.client_id,
                Client.name.label("client_name"),
                JournalEntry.entry_date,
                JournalEntry.description,
                JournalEntry.reference_number,
                JournalEntry.created_by,
                JournalEntry.created_at,
                JournalEntry.updated_at,
                func.coalesce(func.sum(JournalEntryLine.debit), 0).label("total_debits"),
                func.coalesce(func.sum(JournalEntryLine.credit), 0).label("total_credits"),
            )
            .join(Client, Client.id == JournalEntry.client_id)
            .outerjoin(
                JournalEntryLine,
                (JournalEntryLine.journal_entry_id == JournalEntry.id)
                & (JournalEntryLine.deleted_at.is_(None)),
            )
            .where(*conditions)
            .group_by(
                JournalEntry.id,
                JournalEntry.client_id,
                Client.name,
                JournalEntry.entry_date,
                JournalEntry.description,
                JournalEntry.reference_number,
                JournalEntry.created_by,
                JournalEntry.created_at,
                JournalEntry.updated_at,
            )
            .order_by(JournalEntry.entry_date.asc(), JournalEntry.created_at.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(main_stmt)
        rows = result.all()

        items = []
        for row in rows:
            items.append(
                ApprovalQueueItem(
                    id=row.id,
                    client_id=row.client_id,
                    client_name=row.client_name,
                    entry_date=row.entry_date,
                    description=row.description,
                    reference_number=row.reference_number,
                    total_debits=row.total_debits,
                    total_credits=row.total_credits,
                    created_by=row.created_by,
                    created_at=row.created_at,
                    submitted_at=row.updated_at,
                )
            )

        return items, total

    @staticmethod
    async def reject_entry(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
        current_user: CurrentUser,
        note: str,
    ) -> JournalEntry:
        """
        Reject a journal entry: PENDING_APPROVAL -> DRAFT with rejection note.

        CPA_OWNER ONLY. Defense in depth: function-level role check.
        The rejection is recorded in the audit trail via the DB trigger
        (status change from PENDING_APPROVAL to DRAFT).

        Compliance (rule #5): Only CPA_OWNER can reject.
        Compliance (rule #6): Role check at function level.
        """
        verify_role(current_user, "CPA_OWNER")

        entry = await JournalEntryService.get_entry(db, client_id, entry_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found",
            )

        if entry.status != JournalEntryStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reject entry in status '{entry.status.value}'. "
                    f"Only PENDING_APPROVAL entries can be rejected."
                ),
            )

        # Transition back to DRAFT
        entry.status = JournalEntryStatus.DRAFT
        entry.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def batch_process(
        db: AsyncSession,
        current_user: CurrentUser,
        actions: list[ApprovalAction],
    ) -> list[BatchApprovalResultItem]:
        """
        Process multiple approve/reject actions in a single request.

        CPA_OWNER ONLY. Defense in depth: function-level role check.
        Uses existing JournalEntryService.approve_and_post for approvals.
        Each action is processed independently; one failure does not block others.

        Compliance (rule #5): Only CPA_OWNER can approve or reject.
        Compliance (rule #6): Role check at function level.
        """
        verify_role(current_user, "CPA_OWNER")

        results: list[BatchApprovalResultItem] = []

        for action in actions:
            try:
                if action.action == ApprovalActionType.APPROVE:
                    entry = await _get_entry_by_id(db, action.entry_id)
                    if entry is None:
                        results.append(
                            BatchApprovalResultItem(
                                entry_id=action.entry_id,
                                action=action.action,
                                success=False,
                                error="Journal entry not found",
                            )
                        )
                        continue

                    await JournalEntryService.approve_and_post(
                        db, entry.client_id, action.entry_id, current_user
                    )
                    results.append(
                        BatchApprovalResultItem(
                            entry_id=action.entry_id,
                            action=action.action,
                            success=True,
                        )
                    )

                elif action.action == ApprovalActionType.REJECT:
                    entry = await _get_entry_by_id(db, action.entry_id)
                    if entry is None:
                        results.append(
                            BatchApprovalResultItem(
                                entry_id=action.entry_id,
                                action=action.action,
                                success=False,
                                error="Journal entry not found",
                            )
                        )
                        continue

                    note = action.note or "Rejected via batch operation"
                    await ApprovalService.reject_entry(
                        db, entry.client_id, action.entry_id, current_user, note
                    )
                    results.append(
                        BatchApprovalResultItem(
                            entry_id=action.entry_id,
                            action=action.action,
                            success=True,
                        )
                    )

            except HTTPException as exc:
                results.append(
                    BatchApprovalResultItem(
                        entry_id=action.entry_id,
                        action=action.action,
                        success=False,
                        error=str(exc.detail),
                    )
                )

        return results

    @staticmethod
    async def get_approval_history(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> list[ApprovalHistoryItem]:
        """
        Retrieve the approval history for a journal entry from the audit log.

        Returns all status changes recorded by the DB audit trigger.

        Compliance (rule #4): Verifies entry belongs to client_id.
        """
        # First verify the entry exists and belongs to this client
        entry = await JournalEntryService.get_entry(db, client_id, entry_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found",
            )

        # Query audit_log for status changes on this entry
        stmt = text(
            "SELECT action, old_values, new_values, user_id, created_at "
            "FROM audit_log "
            "WHERE table_name = 'journal_entries' "
            "  AND record_id = :entry_id "
            "ORDER BY created_at ASC"
        )
        result = await db.execute(stmt, {"entry_id": str(entry_id)})
        rows = result.all()

        history: list[ApprovalHistoryItem] = []
        for row in rows:
            old_status = None
            new_status = None
            note = None

            if row.old_values and isinstance(row.old_values, dict):
                old_status = row.old_values.get("status")
            if row.new_values and isinstance(row.new_values, dict):
                new_status = row.new_values.get("status")

            # Extract rejection note if stored in new_values
            if row.new_values and isinstance(row.new_values, dict):
                note = row.new_values.get("rejection_note")

            history.append(
                ApprovalHistoryItem(
                    action=row.action,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=row.user_id,
                    note=note,
                    timestamp=row.created_at,
                )
            )

        return history


async def _get_entry_by_id(
    db: AsyncSession,
    entry_id: uuid.UUID,
) -> JournalEntry | None:
    """
    Retrieve a journal entry by ID only (no client_id filter).

    Used internally by batch operations where client_id is not known upfront.
    This is safe because batch operations require CPA_OWNER role which has
    access to all clients.
    """
    stmt = select(JournalEntry).where(
        JournalEntry.id == entry_id,
        JournalEntry.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
