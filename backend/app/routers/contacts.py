"""
Contacts / CRM API endpoints (PM4).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse, ContactList
from app.services.contact_service import ContactService

router = APIRouter()


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    contact = await ContactService.create(db, data, current_user)
    return ContactResponse.model_validate(contact)


@router.get("", response_model=ContactList)
async def list_contacts(
    client_id: UUID | None = None,
    search: str | None = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await ContactService.list_contacts(db, client_id, search, skip, limit)
    return ContactList(
        items=[ContactResponse.model_validate(c) for c in items],
        total=total,
    )


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    contact = await ContactService.get(db, contact_id)
    return ContactResponse.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    contact = await ContactService.update(db, contact_id, data, current_user)
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await ContactService.delete(db, contact_id, current_user)
