"""
API router for financial reports (modules R1-R5).

R1: Profit & Loss (per client, date range)
R2: Balance Sheet (per client, as-of date)
R3: Cash Flow Statement (per client, date range)
R4: PDF export for all reports (CPA_OWNER only)
R5: Firm-level dashboard (all clients, key metrics)

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — client_id from URL path in every query.
- Rule #5: Only POSTED entries contribute to report figures.
- R4 PDF export: CPA_OWNER only (per CLAUDE.md module spec).
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.schemas.aging import APAgingReport, ARAgingReport
from app.schemas.reporting import (
    BalanceSheetReport,
    CashFlowReport,
    FirmDashboard,
    ProfitLossReport,
)
from app.services.aging import AgingService
from app.services.reporting import ReportingService

router = APIRouter()


# ---------------------------------------------------------------------------
# R1 — Profit & Loss
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/profit-loss",
    response_model=ProfitLossReport,
    summary="Generate Profit & Loss report",
)
async def get_profit_loss(
    client_id: uuid.UUID,
    period_start: date = Query(..., description="Start of reporting period"),
    period_end: date = Query(..., description="End of reporting period"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ProfitLossReport:
    """Generate P&L for a client within a date range. Both roles allowed."""
    return await ReportingService.get_profit_loss(db, client_id, period_start, period_end)


# ---------------------------------------------------------------------------
# R2 — Balance Sheet
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/balance-sheet",
    response_model=BalanceSheetReport,
    summary="Generate Balance Sheet report",
)
async def get_balance_sheet(
    client_id: uuid.UUID,
    as_of_date: date = Query(..., description="Balance sheet as-of date"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BalanceSheetReport:
    """Generate Balance Sheet as of a specific date. Both roles allowed."""
    return await ReportingService.get_balance_sheet(db, client_id, as_of_date)


# ---------------------------------------------------------------------------
# R3 — Cash Flow Statement
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/cash-flow",
    response_model=CashFlowReport,
    summary="Generate Cash Flow Statement",
)
async def get_cash_flow(
    client_id: uuid.UUID,
    period_start: date = Query(..., description="Start of reporting period"),
    period_end: date = Query(..., description="End of reporting period"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CashFlowReport:
    """Generate Cash Flow Statement for a client. Both roles allowed."""
    return await ReportingService.get_cash_flow(db, client_id, period_start, period_end)


# ---------------------------------------------------------------------------
# R4 — PDF Export (CPA_OWNER only)
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/profit-loss/pdf",
    summary="Export Profit & Loss as PDF",
    response_class=Response,
)
async def export_profit_loss_pdf(
    client_id: uuid.UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Export P&L as PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    report = await ReportingService.get_profit_loss(db, client_id, period_start, period_end)
    pdf_bytes = await ReportingService.generate_report_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=pnl_{client_id}_{period_start}_{period_end}.pdf"},
    )


@router.get(
    "/clients/{client_id}/balance-sheet/pdf",
    summary="Export Balance Sheet as PDF",
    response_class=Response,
)
async def export_balance_sheet_pdf(
    client_id: uuid.UUID,
    as_of_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Export Balance Sheet as PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    report = await ReportingService.get_balance_sheet(db, client_id, as_of_date)
    pdf_bytes = await ReportingService.generate_report_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bs_{client_id}_{as_of_date}.pdf"},
    )


@router.get(
    "/clients/{client_id}/cash-flow/pdf",
    summary="Export Cash Flow Statement as PDF",
    response_class=Response,
)
async def export_cash_flow_pdf(
    client_id: uuid.UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Export Cash Flow as PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    report = await ReportingService.get_cash_flow(db, client_id, period_start, period_end)
    pdf_bytes = await ReportingService.generate_report_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cf_{client_id}_{period_start}_{period_end}.pdf"},
    )


# ---------------------------------------------------------------------------
# R5 — Firm Dashboard
# ---------------------------------------------------------------------------


@router.get(
    "/dashboard",
    response_model=FirmDashboard,
    summary="Get firm-level dashboard metrics",
)
async def get_firm_dashboard(
    period_start: date | None = Query(None, description="Optional period start filter"),
    period_end: date | None = Query(None, description="Optional period end filter"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> FirmDashboard:
    """Get aggregated metrics across all active clients. Both roles allowed."""
    return await ReportingService.get_firm_dashboard(db, period_start, period_end)


# ---------------------------------------------------------------------------
# AR Aging Report
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/ar-aging",
    response_model=ARAgingReport,
    summary="Generate AR Aging Report",
)
async def get_ar_aging(
    client_id: uuid.UUID,
    as_of_date: date = Query(default=None, description="As-of date (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ARAgingReport:
    """Generate AR aging report. Both roles allowed."""
    if as_of_date is None:
        as_of_date = date.today()
    return await AgingService.get_ar_aging(db, client_id, as_of_date)


@router.get(
    "/clients/{client_id}/ar-aging/pdf",
    summary="Export AR Aging Report as PDF",
    response_class=Response,
)
async def export_ar_aging_pdf(
    client_id: uuid.UUID,
    as_of_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Export AR Aging as PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    if as_of_date is None:
        as_of_date = date.today()
    report = await AgingService.get_ar_aging(db, client_id, as_of_date)
    pdf_bytes = await AgingService.generate_aging_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ar_aging_{client_id}_{as_of_date}.pdf"},
    )


# ---------------------------------------------------------------------------
# AP Aging Report
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/ap-aging",
    response_model=APAgingReport,
    summary="Generate AP Aging Report",
)
async def get_ap_aging(
    client_id: uuid.UUID,
    as_of_date: date = Query(default=None, description="As-of date (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> APAgingReport:
    """Generate AP aging report. Both roles allowed."""
    if as_of_date is None:
        as_of_date = date.today()
    return await AgingService.get_ap_aging(db, client_id, as_of_date)


@router.get(
    "/clients/{client_id}/ap-aging/pdf",
    summary="Export AP Aging Report as PDF",
    response_class=Response,
)
async def export_ap_aging_pdf(
    client_id: uuid.UUID,
    as_of_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Export AP Aging as PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    if as_of_date is None:
        as_of_date = date.today()
    report = await AgingService.get_ap_aging(db, client_id, as_of_date)
    pdf_bytes = await AgingService.generate_aging_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ap_aging_{client_id}_{as_of_date}.pdf"},
    )
