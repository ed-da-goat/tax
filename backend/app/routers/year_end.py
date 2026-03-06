"""
API router for year-end close workflow (C1).

Endpoints:
- GET  /clients/{id}/year-end/{year}/status  — check if year is open/closed
- GET  /clients/{id}/year-end/{year}/preview  — preview closing entries
- POST /clients/{id}/year-end/{year}/close    — execute year-end close (CPA_OWNER)
- POST /clients/{id}/year-end/{year}/reopen   — reopen a closed year (CPA_OWNER)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.services.year_end import YearEndService

router = APIRouter()


@router.get(
    "/clients/{client_id}/year-end/{fiscal_year}/status",
    summary="Check fiscal year status",
)
async def get_year_status(
    client_id: uuid.UUID,
    fiscal_year: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await YearEndService.get_year_status(db, client_id, fiscal_year)


@router.get(
    "/clients/{client_id}/year-end/{fiscal_year}/preview",
    summary="Preview year-end closing entries",
)
async def preview_close(
    client_id: uuid.UUID,
    fiscal_year: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await YearEndService.preview_closing_entries(db, client_id, fiscal_year)


@router.post(
    "/clients/{client_id}/year-end/{fiscal_year}/close",
    summary="Execute year-end close (CPA_OWNER only)",
)
async def close_year(
    client_id: uuid.UUID,
    fiscal_year: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> dict:
    verify_role(user, "CPA_OWNER")
    try:
        result = await YearEndService.close_year(db, client_id, fiscal_year, user.user_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/clients/{client_id}/year-end/{fiscal_year}/reopen",
    summary="Reopen a closed fiscal year (CPA_OWNER only)",
)
async def reopen_year(
    client_id: uuid.UUID,
    fiscal_year: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> dict:
    verify_role(user, "CPA_OWNER")
    try:
        result = await YearEndService.reopen_year(db, client_id, fiscal_year, user.user_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
