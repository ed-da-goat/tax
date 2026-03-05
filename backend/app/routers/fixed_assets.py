"""
Fixed asset management API endpoints (AN3).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.fixed_asset import (
    FixedAssetCreate, FixedAssetUpdate, FixedAssetResponse, FixedAssetList,
    FixedAssetDispose, DepreciationSummary,
)
from app.services.fixed_asset_service import FixedAssetService

router = APIRouter()


@router.post("", response_model=FixedAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    client_id: UUID,
    data: FixedAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    asset = await FixedAssetService.create_asset(db, client_id, data, current_user)
    return FixedAssetResponse.model_validate(asset)


@router.get("", response_model=FixedAssetList)
async def list_assets(
    client_id: UUID,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await FixedAssetService.list_assets(db, client_id, status_filter, skip, limit)
    return FixedAssetList(
        items=[FixedAssetResponse.model_validate(a) for a in items],
        total=total,
    )


@router.get("/{asset_id}", response_model=FixedAssetResponse)
async def get_asset(
    client_id: UUID,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    asset = await FixedAssetService.get_asset(db, client_id, asset_id)
    return FixedAssetResponse.model_validate(asset)


@router.post("/{asset_id}/dispose", response_model=FixedAssetResponse)
async def dispose_asset(
    client_id: UUID,
    asset_id: UUID,
    data: FixedAssetDispose,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    asset = await FixedAssetService.dispose_asset(db, client_id, asset_id, data, current_user)
    return FixedAssetResponse.model_validate(asset)


@router.get("/summary/{fiscal_year}", response_model=DepreciationSummary)
async def depreciation_summary(
    client_id: UUID,
    fiscal_year: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    summary = await FixedAssetService.depreciation_summary(db, client_id, fiscal_year)
    return DepreciationSummary(**summary)
