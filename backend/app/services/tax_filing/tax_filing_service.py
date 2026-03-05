"""
Tax Filing service layer (Phase 8B).

Manages tax filing submission records and provides integration
with TaxBandits API and Georgia DOR FSET.

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only, submission_data preserved as JSON.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #6: Tax filing submission requires CPA_OWNER (defense in depth).
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.tax_filing import TaxFilingSubmission
from app.schemas.tax_filing import TaxFilingCreate, TaxFilingUpdate


class TaxFilingService:
    """Business logic for tax filing submission tracking."""

    # -------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------

    @staticmethod
    async def create(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: TaxFilingCreate,
        user: CurrentUser,
    ) -> TaxFilingSubmission:
        """
        Create a new tax filing submission record.

        Compliance (rule #6): CPA_OWNER only.
        """
        verify_role(user, "CPA_OWNER")

        submission = TaxFilingSubmission(
            client_id=client_id,
            form_type=data.form_type,
            tax_year=data.tax_year,
            tax_quarter=data.tax_quarter,
            filing_period_start=data.filing_period_start,
            filing_period_end=data.filing_period_end,
            provider=data.provider.value,
            status="DRAFT",
            submission_data=data.submission_data,
            submitted_by=uuid.UUID(user.user_id),
        )
        db.add(submission)
        await db.flush()
        await db.refresh(submission)
        return submission

    @staticmethod
    async def get(
        db: AsyncSession,
        client_id: uuid.UUID,
        submission_id: uuid.UUID,
    ) -> TaxFilingSubmission | None:
        stmt = select(TaxFilingSubmission).where(
            TaxFilingSubmission.id == submission_id,
            TaxFilingSubmission.client_id == client_id,
            TaxFilingSubmission.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        form_type: str | None = None,
        tax_year: int | None = None,
        provider: str | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TaxFilingSubmission], int]:
        base = select(TaxFilingSubmission).where(
            TaxFilingSubmission.client_id == client_id,
            TaxFilingSubmission.deleted_at.is_(None),
        )

        if form_type:
            base = base.where(TaxFilingSubmission.form_type == form_type)
        if tax_year:
            base = base.where(TaxFilingSubmission.tax_year == tax_year)
        if provider:
            base = base.where(TaxFilingSubmission.provider == provider)
        if status_filter:
            base = base.where(TaxFilingSubmission.status == status_filter)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(TaxFilingSubmission.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def update(
        db: AsyncSession,
        client_id: uuid.UUID,
        submission_id: uuid.UUID,
        data: TaxFilingUpdate,
        user: CurrentUser,
    ) -> TaxFilingSubmission | None:
        """
        Update a tax filing submission (status, provider response, etc.).

        Compliance (rule #6): CPA_OWNER only.
        """
        verify_role(user, "CPA_OWNER")

        submission = await TaxFilingService.get(db, client_id, submission_id)
        if submission is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        now = datetime.now(timezone.utc)

        # Handle status-specific timestamps
        if "status" in update_data:
            new_status = update_data["status"]
            if hasattr(new_status, "value"):
                update_data["status"] = new_status.value
                new_status = new_status.value

            if new_status == "SUBMITTED":
                submission.submitted_at = now
            elif new_status == "ACCEPTED":
                submission.accepted_at = now
            elif new_status == "REJECTED":
                submission.rejected_at = now

        for field, value in update_data.items():
            setattr(submission, field, value)

        submission.updated_at = now
        await db.flush()
        await db.refresh(submission)
        return submission

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        client_id: uuid.UUID,
        submission_id: uuid.UUID,
        user: CurrentUser,
    ) -> TaxFilingSubmission | None:
        verify_role(user, "CPA_OWNER")

        submission = await TaxFilingService.get(db, client_id, submission_id)
        if submission is None:
            return None

        if submission.status in ("SUBMITTED", "ACCEPTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete a {submission.status} filing. Only DRAFT or REJECTED filings can be deleted.",
            )

        submission.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(submission)
        return submission
