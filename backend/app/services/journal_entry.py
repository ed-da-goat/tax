"""
Service layer for Journal Entries / General Ledger (module F3).

Compliance (CLAUDE.md):
- Rule #1: DOUBLE-ENTRY — debits must equal credits. Enforced at BOTH app
  level (this service) AND DB trigger level (fn_validate_journal_entry_balance).
- Rule #2: AUDIT TRAIL — soft deletes only. Void creates reversing entry.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: APPROVAL WORKFLOW — ASSOCIATE enters DRAFT. Only CPA_OWNER posts.
- Rule #6: PAYROLL/FINANCIAL GATE — role checks at function level (defense in depth).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Row, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryUpdate


class JournalEntryService:
    """Business logic for journal entry CRUD and workflow operations."""

    @staticmethod
    async def create_entry(
        db: AsyncSession,
        data: JournalEntryCreate,
        current_user: CurrentUser,
    ) -> JournalEntry:
        """
        Create a journal entry with lines atomically.

        Status starts as DRAFT regardless of role.
        Validates: at least 2 lines, debits == credits (app-level check;
        DB trigger is the backup).

        Compliance (rule #5): Never auto-post on entry.
        """
        # App-level double-entry check (schema already validated, but defense in depth)
        total_debits = sum(line.debit for line in data.lines)
        total_credits = sum(line.credit for line in data.lines)
        if total_debits != total_credits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unbalanced entry: debits ({total_debits}) != credits ({total_credits}). "
                    f"Double-entry requires equal debits and credits."
                ),
            )

        if len(data.lines) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A journal entry must have at least 2 line items.",
            )

        entry = JournalEntry(
            client_id=data.client_id,
            entry_date=data.entry_date,
            description=data.description,
            reference_number=data.reference_number,
            status=JournalEntryStatus.DRAFT,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(entry)
        await db.flush()

        for line_data in data.lines:
            line = JournalEntryLine(
                journal_entry_id=entry.id,
                account_id=line_data.account_id,
                debit=line_data.debit,
                credit=line_data.credit,
                description=line_data.description,
            )
            db.add(line)

        await db.flush()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_entry(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> JournalEntry | None:
        """
        Retrieve a single journal entry with its lines, filtered by client_id.

        Compliance (rule #4): ALWAYS filters by client_id so that
        Client A cannot retrieve Client B's entries.
        """
        stmt = select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.client_id == client_id,
            JournalEntry.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_entries(
        db: AsyncSession,
        client_id: uuid.UUID,
        status_filter: JournalEntryStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[JournalEntry], int]:
        """
        List journal entries for a client with optional filters and pagination.

        Compliance (rule #4): ALWAYS filters by client_id.
        Always excludes soft-deleted records.
        """
        base = select(JournalEntry).where(
            JournalEntry.client_id == client_id,
            JournalEntry.deleted_at.is_(None),
        )

        if status_filter is not None:
            base = base.where(JournalEntry.status == status_filter)
        if date_from is not None:
            base = base.where(JournalEntry.entry_date >= date_from)
        if date_to is not None:
            base = base.where(JournalEntry.entry_date <= date_to)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated results
        stmt = base.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        entries = list(result.scalars().all())

        return entries, total

    @staticmethod
    async def update_entry(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
        data: JournalEntryUpdate,
    ) -> JournalEntry | None:
        """
        Update description/reference_number of a DRAFT entry only.

        Cannot modify lines after creation. Cannot modify posted/void entries.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        entry = await JournalEntryService.get_entry(db, client_id, entry_id)
        if entry is None:
            return None

        if entry.status != JournalEntryStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify entry in status '{entry.status.value}'. Only DRAFT entries can be updated.",
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entry, field, value)

        entry.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def submit_for_approval(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> JournalEntry | None:
        """
        Transition a journal entry from DRAFT to PENDING_APPROVAL.

        Any role can submit for approval.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        entry = await JournalEntryService.get_entry(db, client_id, entry_id)
        if entry is None:
            return None

        if entry.status != JournalEntryStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit entry in status '{entry.status.value}'. Only DRAFT entries can be submitted.",
            )

        entry.status = JournalEntryStatus.PENDING_APPROVAL
        entry.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def approve_and_post(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> JournalEntry | None:
        """
        Approve and post a journal entry (PENDING_APPROVAL -> POSTED).

        CPA_OWNER ONLY. Defense in depth: function-level role check.
        Sets approved_by and posted_at. DB trigger validates balance.

        Compliance (rule #5): Only CPA_OWNER can post.
        Compliance (rule #6): Role check at function level.
        """
        verify_role(current_user, "CPA_OWNER")

        entry = await JournalEntryService.get_entry(db, client_id, entry_id)
        if entry is None:
            return None

        if entry.status != JournalEntryStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve entry in status '{entry.status.value}'. Only PENDING_APPROVAL entries can be approved.",
            )

        entry.status = JournalEntryStatus.POSTED
        entry.approved_by = uuid.UUID(current_user.user_id)
        # posted_at is set by DB trigger, but set here too for immediate access
        entry.posted_at = datetime.now(timezone.utc)
        entry.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def void_entry(
        db: AsyncSession,
        client_id: uuid.UUID,
        entry_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> tuple[JournalEntry, JournalEntry] | None:
        """
        Void a posted journal entry and create a reversing entry.

        CPA_OWNER ONLY. Defense in depth: function-level role check.
        The original entry status is changed to VOID.
        A new reversing entry is created with debits/credits swapped,
        posted immediately.

        Compliance (rule #2): Never hard delete. Void + reverse instead.
        Compliance (rule #5): Only CPA_OWNER can void.
        Compliance (rule #6): Role check at function level.

        Returns (voided_entry, reversing_entry) or None if not found.
        """
        verify_role(current_user, "CPA_OWNER")

        entry = await JournalEntryService.get_entry(db, client_id, entry_id)
        if entry is None:
            return None

        if entry.status != JournalEntryStatus.POSTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot void entry in status '{entry.status.value}'. Only POSTED entries can be voided.",
            )

        # Mark original as VOID
        entry.status = JournalEntryStatus.VOID
        entry.updated_at = datetime.now(timezone.utc)

        # Create reversing entry as DRAFT first (DB trigger blocks direct POSTED
        # INSERT if lines aren't present yet)
        reversing = JournalEntry(
            client_id=entry.client_id,
            entry_date=date.today(),
            description=f"REVERSAL of entry {entry.id}: {entry.description or ''}".strip(),
            reference_number=f"REV-{entry.reference_number}" if entry.reference_number else None,
            status=JournalEntryStatus.DRAFT,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(reversing)
        await db.flush()

        for line in entry.lines:
            if line.deleted_at is not None:
                continue
            reversing_line = JournalEntryLine(
                journal_entry_id=reversing.id,
                account_id=line.account_id,
                debit=line.credit,   # Swap: original credit becomes debit
                credit=line.debit,   # Swap: original debit becomes credit
                description=f"Reversal: {line.description or ''}".strip(),
            )
            db.add(reversing_line)

        await db.flush()

        # Now transition to POSTED (DB trigger will validate balance)
        reversing.status = JournalEntryStatus.POSTED
        reversing.approved_by = uuid.UUID(current_user.user_id)
        reversing.posted_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(entry)
        await db.refresh(reversing)
        return entry, reversing

    @staticmethod
    async def get_trial_balance(
        db: AsyncSession,
        client_id: uuid.UUID,
    ) -> list[Row]:
        """
        Query trial balance for a specific client (posted entries only).

        NOTE: Uses a direct query instead of v_trial_balance because the
        view's LEFT JOIN structure may include lines from non-posted entries.
        This query uses INNER JOINs to ensure only POSTED entry lines
        contribute to the totals.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = text(
            "SELECT "
            "    coa.client_id, "
            "    coa.account_number, "
            "    coa.account_name, "
            "    coa.account_type, "
            "    coa.sub_type, "
            "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
            "    COALESCE(SUM(jel.credit), 0) AS total_credits, "
            "    COALESCE(SUM(jel.debit), 0) - COALESCE(SUM(jel.credit), 0) AS balance "
            "FROM chart_of_accounts coa "
            "LEFT JOIN ( "
            "    journal_entry_lines jel "
            "    INNER JOIN journal_entries je "
            "        ON je.id = jel.journal_entry_id "
            "        AND je.status = 'POSTED' "
            "        AND je.deleted_at IS NULL "
            ") ON jel.account_id = coa.id "
            "    AND jel.deleted_at IS NULL "
            "WHERE coa.client_id = :client_id "
            "    AND coa.deleted_at IS NULL "
            "    AND coa.is_active = TRUE "
            "GROUP BY coa.client_id, coa.account_number, coa.account_name, "
            "         coa.account_type, coa.sub_type "
            "ORDER BY coa.account_number"
        )
        result = await db.execute(stmt, {"client_id": str(client_id)})
        return list(result.all())
