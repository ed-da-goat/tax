"""
API router for recurring transaction templates (C3).

Endpoints:
- GET    /clients/{id}/recurring          — list templates for a client
- POST   /clients/{id}/recurring          — create template
- GET    /clients/{id}/recurring/{tid}     — get template detail
- PATCH  /clients/{id}/recurring/{tid}     — update template
- DELETE /clients/{id}/recurring/{tid}     — soft-delete template
- POST   /recurring/generate              — trigger generation for all due templates
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.services.recurring import RecurringService

router = APIRouter()


class RecurringLineCreate(BaseModel):
    account_id: str
    description: str | None = None
    debit: float = 0
    credit: float = 0


class RecurringTemplateCreate(BaseModel):
    source_type: str = Field(..., pattern="^(JOURNAL_ENTRY|BILL)$")
    description: str
    frequency: str = Field(..., pattern="^(WEEKLY|BIWEEKLY|MONTHLY|QUARTERLY|ANNUALLY)$")
    next_date: str
    end_date: str | None = None
    vendor_id: str | None = None
    max_occurrences: int | None = None
    lines: list[RecurringLineCreate]


class RecurringTemplateUpdate(BaseModel):
    description: str | None = None
    frequency: str | None = None
    next_date: str | None = None
    end_date: str | None = None
    vendor_id: str | None = None
    max_occurrences: int | None = None
    status: str | None = None


@router.get("/clients/{client_id}/recurring", summary="List recurring templates")
async def list_templates(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await RecurringService.list_templates(db, client_id)


@router.post("/clients/{client_id}/recurring", summary="Create recurring template")
async def create_template(
    client_id: uuid.UUID,
    body: RecurringTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        result = await RecurringService.create_template(
            db, client_id, user.user_id, body.model_dump(),
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clients/{client_id}/recurring/{template_id}", summary="Get recurring template")
async def get_template(
    client_id: uuid.UUID,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return await RecurringService.get_template(db, template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/clients/{client_id}/recurring/{template_id}", summary="Update recurring template")
async def update_template(
    client_id: uuid.UUID,
    template_id: uuid.UUID,
    body: RecurringTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        result = await RecurringService.update_template(
            db, template_id, body.model_dump(exclude_unset=True),
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/clients/{client_id}/recurring/{template_id}", summary="Delete recurring template")
async def delete_template(
    client_id: uuid.UUID,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        result = await RecurringService.delete_template(db, template_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/recurring/generate", summary="Generate all due recurring transactions")
async def generate_due(
    as_of: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> dict:
    target_date = date.fromisoformat(as_of) if as_of else None
    result = await RecurringService.generate_due(db, as_of=target_date, user_id=user.user_id)
    await db.commit()
    return result
