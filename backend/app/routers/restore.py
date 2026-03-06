"""
API router for soft delete restoration (E5).

Endpoints:
- GET  /archived?type=client         — list archived records
- POST /archived/{type}/{id}/restore  — restore a single record
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_role, verify_role
from app.database import get_db
from app.services.restore import RestoreService

router = APIRouter()


@router.get("/archived", summary="List archived (soft-deleted) records")
async def list_archived(
    type: str = Query(..., description="Entity type: client, vendor, employee, bill, invoice"),
    client_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> list[dict]:
    verify_role(user, "CPA_OWNER")
    try:
        return await RestoreService.list_archived(db, type, client_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/archived/{entity_type}/{record_id}/restore", summary="Restore an archived record")
async def restore_record(
    entity_type: str,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> dict:
    verify_role(user, "CPA_OWNER")
    try:
        result = await RestoreService.restore(db, entity_type, record_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
