"""
Service layer for firm analytics dashboard (AN1).

Revenue by service, client profitability, WIP, realization rates.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.time_entry import TimeEntry, TimeEntryStatus
from app.models.service_invoice import ServiceInvoice, ServiceInvoiceStatus
from app.models.client import Client
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStatus


class FirmAnalyticsService:

    @staticmethod
    async def revenue_by_service(
        db: AsyncSession, date_from: date, date_to: date,
    ) -> list[dict]:
        """Revenue breakdown by service type."""
        result = await db.execute(
            select(
                TimeEntry.service_type,
                func.sum(TimeEntry.amount).label("total_revenue"),
                func.sum(TimeEntry.duration_minutes).label("total_minutes"),
                func.count(TimeEntry.id).label("entry_count"),
            ).where(
                TimeEntry.status.in_([TimeEntryStatus.APPROVED, TimeEntryStatus.BILLED]),
                TimeEntry.is_billable.is_(True),
                TimeEntry.date >= date_from,
                TimeEntry.date <= date_to,
                TimeEntry.deleted_at.is_(None),
            ).group_by(TimeEntry.service_type)
        )
        return [
            {
                "service_type": row.service_type or "Unclassified",
                "total_revenue": row.total_revenue or Decimal("0"),
                "total_hours": round(Decimal(row.total_minutes or 0) / Decimal("60"), 1),
                "entry_count": row.entry_count,
            }
            for row in result.all()
        ]

    @staticmethod
    async def client_profitability(
        db: AsyncSession, date_from: date, date_to: date,
    ) -> list[dict]:
        """Revenue and hours per client."""
        result = await db.execute(
            select(
                TimeEntry.client_id,
                func.sum(TimeEntry.amount).label("revenue"),
                func.sum(TimeEntry.duration_minutes).label("minutes"),
                func.sum(
                    case((TimeEntry.is_billable.is_(True), TimeEntry.duration_minutes), else_=0)
                ).label("billable_minutes"),
            ).where(
                TimeEntry.date >= date_from,
                TimeEntry.date <= date_to,
                TimeEntry.deleted_at.is_(None),
            ).group_by(TimeEntry.client_id)
        )
        rows = result.all()
        clients = []
        for row in rows:
            client = await db.get(Client, row.client_id)
            total_hrs = Decimal(row.minutes or 0) / Decimal("60")
            billable_hrs = Decimal(row.billable_minutes or 0) / Decimal("60")
            revenue = row.revenue or Decimal("0")
            eff_rate = (revenue / billable_hrs) if billable_hrs > 0 else Decimal("0")
            clients.append({
                "client_id": row.client_id,
                "client_name": client.name if client else "Unknown",
                "total_hours": round(total_hrs, 1),
                "billable_hours": round(billable_hrs, 1),
                "revenue": revenue,
                "effective_rate": round(eff_rate, 2),
            })
        return sorted(clients, key=lambda x: x["revenue"], reverse=True)

    @staticmethod
    async def wip_summary(db: AsyncSession) -> dict:
        """Work-in-progress: approved but unbilled time."""
        result = await db.execute(
            select(
                func.count(TimeEntry.id).label("count"),
                func.sum(TimeEntry.amount).label("total"),
                func.sum(TimeEntry.duration_minutes).label("minutes"),
            ).where(
                TimeEntry.status == TimeEntryStatus.APPROVED,
                TimeEntry.is_billable.is_(True),
                TimeEntry.deleted_at.is_(None),
            )
        )
        row = result.one()
        return {
            "unbilled_entries": row.count or 0,
            "unbilled_amount": row.total or Decimal("0"),
            "unbilled_hours": round(Decimal(row.minutes or 0) / Decimal("60"), 1),
        }

    @staticmethod
    async def realization_rate(
        db: AsyncSession, date_from: date, date_to: date,
    ) -> dict:
        """Compare standard billing to actual collected."""
        standard_result = await db.execute(
            select(func.sum(TimeEntry.amount)).where(
                TimeEntry.is_billable.is_(True),
                TimeEntry.date >= date_from,
                TimeEntry.date <= date_to,
                TimeEntry.deleted_at.is_(None),
            )
        )
        standard_total = standard_result.scalar() or Decimal("0")

        collected_result = await db.execute(
            select(func.sum(ServiceInvoice.amount_paid)).where(
                ServiceInvoice.invoice_date >= date_from,
                ServiceInvoice.invoice_date <= date_to,
                ServiceInvoice.deleted_at.is_(None),
            )
        )
        collected_total = collected_result.scalar() or Decimal("0")

        rate = Decimal("0")
        if standard_total > 0:
            rate = round((collected_total / standard_total) * 100, 1)

        return {
            "standard_billing": standard_total,
            "collected": collected_total,
            "realization_rate_pct": rate,
            "period_start": date_from,
            "period_end": date_to,
        }

    @staticmethod
    async def workflow_summary(db: AsyncSession) -> dict:
        """Active workflow counts by type and status."""
        result = await db.execute(
            select(
                Workflow.workflow_type,
                Workflow.status,
                func.count(Workflow.id).label("count"),
            ).where(
                Workflow.is_template.is_(False),
                Workflow.deleted_at.is_(None),
            ).group_by(Workflow.workflow_type, Workflow.status)
        )
        summary = {}
        for row in result.all():
            wtype = row.workflow_type
            if wtype not in summary:
                summary[wtype] = {"active": 0, "completed": 0, "total": 0}
            summary[wtype]["total"] += row.count
            if row.status == WorkflowStatus.ACTIVE:
                summary[wtype]["active"] += row.count
            elif row.status == WorkflowStatus.COMPLETED:
                summary[wtype]["completed"] += row.count
        return summary

    @staticmethod
    async def firm_dashboard(
        db: AsyncSession, date_from: date, date_to: date,
    ) -> dict:
        """Comprehensive firm dashboard data."""
        revenue = await FirmAnalyticsService.revenue_by_service(db, date_from, date_to)
        wip = await FirmAnalyticsService.wip_summary(db)
        realization = await FirmAnalyticsService.realization_rate(db, date_from, date_to)
        workflows = await FirmAnalyticsService.workflow_summary(db)

        # Outstanding invoices
        inv_result = await db.execute(
            select(
                func.count(ServiceInvoice.id).label("count"),
                func.sum(ServiceInvoice.balance_due).label("total"),
            ).where(
                ServiceInvoice.status.in_([
                    ServiceInvoiceStatus.SENT,
                    ServiceInvoiceStatus.PARTIAL,
                    ServiceInvoiceStatus.OVERDUE,
                ]),
                ServiceInvoice.deleted_at.is_(None),
            )
        )
        inv_row = inv_result.one()

        return {
            "period": {"start": date_from, "end": date_to},
            "revenue_by_service": revenue,
            "total_revenue": sum(r["total_revenue"] for r in revenue),
            "wip": wip,
            "realization": realization,
            "outstanding_invoices": {
                "count": inv_row.count or 0,
                "total_balance": inv_row.total or Decimal("0"),
            },
            "workflows": workflows,
        }
