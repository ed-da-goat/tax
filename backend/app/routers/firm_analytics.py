"""
Firm analytics dashboard API endpoints (AN1).
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.services.firm_analytics import FirmAnalyticsService

router = APIRouter()


@router.get("/dashboard")
async def firm_dashboard(
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await FirmAnalyticsService.firm_dashboard(db, date_from, date_to)


@router.get("/revenue-by-service")
async def revenue_by_service(
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await FirmAnalyticsService.revenue_by_service(db, date_from, date_to)


@router.get("/client-profitability")
async def client_profitability(
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await FirmAnalyticsService.client_profitability(db, date_from, date_to)


@router.get("/wip")
async def wip_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await FirmAnalyticsService.wip_summary(db)


@router.get("/realization")
async def realization_rate(
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await FirmAnalyticsService.realization_rate(db, date_from, date_to)
