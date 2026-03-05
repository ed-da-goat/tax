"""
Engagement letters & proposals API endpoints (PM3).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.engagement import (
    EngagementCreate, EngagementUpdate, EngagementResponse, EngagementList,
)
from app.services.engagement_service import EngagementService

router = APIRouter()


@router.post("", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    data: EngagementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    eng = await EngagementService.create(db, data, current_user)
    return EngagementResponse.model_validate(eng)


@router.get("", response_model=EngagementList)
async def list_engagements(
    client_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await EngagementService.list_engagements(
        db, client_id, status_filter, skip, limit
    )
    return EngagementList(
        items=[EngagementResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get("/{engagement_id}", response_model=EngagementResponse)
async def get_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    eng = await EngagementService.get(db, engagement_id)
    return EngagementResponse.model_validate(eng)


@router.put("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    engagement_id: UUID,
    data: EngagementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    eng = await EngagementService.update(db, engagement_id, data, current_user)
    return EngagementResponse.model_validate(eng)


@router.post("/{engagement_id}/send", response_model=EngagementResponse)
async def send_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    eng = await EngagementService.send(db, engagement_id, current_user)
    return EngagementResponse.model_validate(eng)


class SignRequest(BaseModel):
    signed_by: str
    signature_data: str | None = None


@router.post("/{engagement_id}/sign", response_model=EngagementResponse)
async def sign_engagement(
    engagement_id: UUID,
    data: SignRequest,
    db: AsyncSession = Depends(get_db),
):
    eng = await EngagementService.sign(db, engagement_id, data.signed_by, data.signature_data)
    return EngagementResponse.model_validate(eng)


@router.delete("/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    await EngagementService.delete(db, engagement_id, current_user)
