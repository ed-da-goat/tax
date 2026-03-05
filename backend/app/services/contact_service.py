"""
Service layer for contacts / CRM (PM4).
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate


class ContactService:

    @staticmethod
    async def create(
        db: AsyncSession, data: ContactCreate, current_user: CurrentUser,
    ) -> Contact:
        contact = Contact(**data.model_dump())
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def list_contacts(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Contact], int]:
        query = select(Contact).where(Contact.deleted_at.is_(None))
        count_q = select(func.count(Contact.id)).where(Contact.deleted_at.is_(None))

        if client_id:
            query = query.where(Contact.client_id == client_id)
            count_q = count_q.where(Contact.client_id == client_id)
        if search:
            like = f"%{search}%"
            search_filter = (
                Contact.first_name.ilike(like) |
                Contact.last_name.ilike(like) |
                Contact.email.ilike(like)
            )
            query = query.where(search_filter)
            count_q = count_q.where(search_filter)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(Contact.last_name, Contact.first_name).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get(db: AsyncSession, contact_id: uuid.UUID) -> Contact:
        result = await db.execute(
            select(Contact).where(
                Contact.id == contact_id, Contact.deleted_at.is_(None)
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact

    @staticmethod
    async def update(
        db: AsyncSession, contact_id: uuid.UUID,
        data: ContactUpdate, current_user: CurrentUser,
    ) -> Contact:
        contact = await ContactService.get(db, contact_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(contact, field, value)
        await db.commit()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def delete(
        db: AsyncSession, contact_id: uuid.UUID, current_user: CurrentUser,
    ) -> None:
        contact = await ContactService.get(db, contact_id)
        contact.deleted_at = datetime.now(timezone.utc)
        await db.commit()
