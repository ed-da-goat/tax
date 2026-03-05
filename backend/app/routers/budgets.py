"""
Budget management API endpoints (AN2).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetList,
    BudgetVsActualReport,
)
from app.services.budget_service import BudgetService

router = APIRouter()


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    client_id: UUID,
    data: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    budget = await BudgetService.create_budget(db, client_id, data, current_user)
    return BudgetResponse.model_validate(budget)


@router.get("", response_model=BudgetList)
async def list_budgets(
    client_id: UUID,
    fiscal_year: int | None = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await BudgetService.list_budgets(db, client_id, fiscal_year, skip, limit)
    return BudgetList(
        items=[BudgetResponse.model_validate(b) for b in items],
        total=total,
    )


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    client_id: UUID,
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    budget = await BudgetService.get_budget(db, client_id, budget_id)
    return BudgetResponse.model_validate(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    client_id: UUID,
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    await BudgetService.delete_budget(db, client_id, budget_id, current_user)


@router.get("/{budget_id}/vs-actual", response_model=BudgetVsActualReport)
async def budget_vs_actual(
    client_id: UUID,
    budget_id: UUID,
    month_start: int = Query(1, ge=1, le=12),
    month_end: int = Query(12, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await BudgetService.budget_vs_actual(db, client_id, budget_id, month_start, month_end)
