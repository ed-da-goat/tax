"""
Check sequence management endpoints.

Endpoints:
    GET  /api/v1/clients/{client_id}/check-sequence — Get next number
    PUT  /api/v1/clients/{client_id}/check-sequence — Set next number (CPA_OWNER)
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.schemas import BaseSchema
from app.services.check_sequence import CheckSequenceService

router = APIRouter()


class CheckSequenceResponse(BaseSchema):
    client_id: UUID
    next_check_number: int


class CheckSequenceUpdate(BaseSchema):
    next_check_number: int


@router.get("", response_model=CheckSequenceResponse)
async def get_check_sequence(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CheckSequenceResponse:
    """Get the current next check number for a client. Both roles."""
    next_num = await CheckSequenceService.get_current_sequence(db, client_id)
    return CheckSequenceResponse(client_id=client_id, next_check_number=next_num)


@router.put("", response_model=CheckSequenceResponse)
async def set_check_sequence(
    client_id: UUID,
    data: CheckSequenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> CheckSequenceResponse:
    """Set the next check number for a client. CPA_OWNER only."""
    verify_role(current_user, "CPA_OWNER")
    next_num = await CheckSequenceService.set_next_check_number(db, client_id, data.next_check_number)
    await db.commit()
    return CheckSequenceResponse(client_id=client_id, next_check_number=next_num)
