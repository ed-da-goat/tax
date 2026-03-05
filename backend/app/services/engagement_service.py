"""
Service layer for engagement letters & proposals (PM3).
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.engagement import Engagement, EngagementStatus
from app.schemas.engagement import EngagementCreate, EngagementUpdate


class EngagementService:

    @staticmethod
    async def create(
        db: AsyncSession, data: EngagementCreate, current_user: CurrentUser,
    ) -> Engagement:
        engagement = Engagement(
            client_id=data.client_id,
            title=data.title,
            engagement_type=data.engagement_type,
            description=data.description,
            terms_and_conditions=data.terms_and_conditions,
            fee_type=data.fee_type,
            fixed_fee=data.fixed_fee,
            hourly_rate=data.hourly_rate,
            estimated_hours=data.estimated_hours,
            retainer_amount=data.retainer_amount,
            start_date=data.start_date,
            end_date=data.end_date,
            tax_year=data.tax_year,
            status=EngagementStatus.DRAFT,
        )
        db.add(engagement)
        await db.commit()
        await db.refresh(engagement)
        return engagement

    @staticmethod
    async def list_engagements(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Engagement], int]:
        query = select(Engagement).where(Engagement.deleted_at.is_(None))
        count_q = select(func.count(Engagement.id)).where(Engagement.deleted_at.is_(None))

        if client_id:
            query = query.where(Engagement.client_id == client_id)
            count_q = count_q.where(Engagement.client_id == client_id)
        if status_filter:
            query = query.where(Engagement.status == status_filter)
            count_q = count_q.where(Engagement.status == status_filter)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(Engagement.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get(db: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
        result = await db.execute(
            select(Engagement).where(
                Engagement.id == engagement_id, Engagement.deleted_at.is_(None)
            )
        )
        eng = result.scalar_one_or_none()
        if not eng:
            raise HTTPException(status_code=404, detail="Engagement not found")
        return eng

    @staticmethod
    async def update(
        db: AsyncSession, engagement_id: uuid.UUID,
        data: EngagementUpdate, current_user: CurrentUser,
    ) -> Engagement:
        eng = await EngagementService.get(db, engagement_id)
        if eng.status not in (EngagementStatus.DRAFT, EngagementStatus.SENT):
            raise HTTPException(status_code=400, detail="Cannot edit signed/declined engagement")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(eng, field, value)
        await db.commit()
        await db.refresh(eng)
        return eng

    @staticmethod
    async def send(
        db: AsyncSession, engagement_id: uuid.UUID, current_user: CurrentUser,
    ) -> Engagement:
        verify_role(current_user, "CPA_OWNER")
        eng = await EngagementService.get(db, engagement_id)
        if eng.status != EngagementStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Must be DRAFT to send")
        eng.status = EngagementStatus.SENT
        eng.sent_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(eng)
        return eng

    @staticmethod
    async def sign(
        db: AsyncSession, engagement_id: uuid.UUID,
        signed_by: str, signature_data: str | None = None,
    ) -> Engagement:
        eng = await EngagementService.get(db, engagement_id)
        if eng.status not in (EngagementStatus.SENT, EngagementStatus.VIEWED):
            raise HTTPException(status_code=400, detail="Engagement must be SENT or VIEWED to sign")
        eng.status = EngagementStatus.SIGNED
        eng.signed_at = datetime.now(timezone.utc)
        eng.signed_by = signed_by
        eng.signature_data = signature_data
        await db.commit()
        await db.refresh(eng)
        return eng

    @staticmethod
    async def delete(
        db: AsyncSession, engagement_id: uuid.UUID, current_user: CurrentUser,
    ) -> None:
        verify_role(current_user, "CPA_OWNER")
        eng = await EngagementService.get(db, engagement_id)
        eng.deleted_at = datetime.now(timezone.utc)
        await db.commit()
