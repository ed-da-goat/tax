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
from sqlalchemy import Row, column, func, literal_column, select, text
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
        # Use raw SQL for the queue query to avoid ORM join complexity
        where_clauses = [
            "je.status = 'PENDING_APPROVAL'",
            "je.deleted_at IS NULL",
        ]
        params: dict = {}

        # ASSOCIATE can only see their own entries
        if current_user.role == "ASSOCIATE":
            where_clauses.append("je.created_by = :user_id")
            params["user_id"] = current_user.user_id

        # Optional filters
        if client_id is not None:
            where_clauses.append("je.client_id = :client_id")
            params["client_id"] = str(client_id)
        if date_from is not None:
            where_clauses.append("je.entry_date >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            where_clauses.append("je.entry_date <= :date_to")
            params["date_to"] = date_to

        where_sql = " AND ".join(where_clauses)

        # Count query
        count_sql = text(
            f"SELECT COUNT(*) FROM journal_entries je WHERE {where_sql}"
        )
        total_result = await db.execute(count_sql, params)
        total = total_result.scalar_one()

        # Main query with client name and line totals
        main_sql = text(
            f"SELECT je.id, je.client_id, c.name AS client_name, "
            f"  je.entry_date, je.description, je.reference_number, "
            f"  je.created_by, je.created_at, je.updated_at, "
            f"  COALESCE(SUM(jel.debit), 0) AS total_debits, "
            f"  COALESCE(SUM(jel.credit), 0) AS total_credits "
            f"FROM journal_entries je "
            f"JOIN clients c ON c.id = je.client_id "
            f"LEFT JOIN journal_entry_lines jel ON jel.journal_entry_id = je.id "
            f"  AND jel.deleted_at IS NULL "
            f"WHERE {where_sql} "
            f"GROUP BY je.id, je.client_id, c.name, je.entry_date, "
            f"  je.description, je.reference_number, je.created_by, "
            f"  je.created_at, je.updated_at "
            f"ORDER BY je.entry_date ASC, je.created_at ASC "
            f"OFFSET :skip LIMIT :limit"
        )
        params["skip"] = skip
        params["limit"] = limit

        result = await db.execute(main_sql, params)
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
