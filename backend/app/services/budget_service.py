"""
Service layer for budgeting & forecasting (AN2).

Budget creation, budget vs actual comparison.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select, extract, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.budget import Budget, BudgetLine
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.models.chart_of_accounts import ChartOfAccounts
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:

    @staticmethod
    async def create_budget(
        db: AsyncSession, client_id: uuid.UUID,
        data: BudgetCreate, current_user: CurrentUser,
    ) -> Budget:
        budget = Budget(
            client_id=client_id,
            name=data.name,
            fiscal_year=data.fiscal_year,
            description=data.description,
        )
        db.add(budget)
        await db.flush()

        for line_data in data.lines:
            annual = sum([
                line_data.month_1, line_data.month_2, line_data.month_3,
                line_data.month_4, line_data.month_5, line_data.month_6,
                line_data.month_7, line_data.month_8, line_data.month_9,
                line_data.month_10, line_data.month_11, line_data.month_12,
            ])
            line = BudgetLine(
                budget_id=budget.id,
                account_id=line_data.account_id,
                month_1=line_data.month_1, month_2=line_data.month_2,
                month_3=line_data.month_3, month_4=line_data.month_4,
                month_5=line_data.month_5, month_6=line_data.month_6,
                month_7=line_data.month_7, month_8=line_data.month_8,
                month_9=line_data.month_9, month_10=line_data.month_10,
                month_11=line_data.month_11, month_12=line_data.month_12,
                annual_total=annual,
                notes=line_data.notes,
            )
            db.add(line)

        await db.commit()
        await db.refresh(budget)
        return budget

    @staticmethod
    async def list_budgets(
        db: AsyncSession, client_id: uuid.UUID,
        fiscal_year: int | None = None,
        skip: int = 0, limit: int = 50,
    ) -> tuple[list[Budget], int]:
        query = select(Budget).where(
            Budget.client_id == client_id,
            Budget.deleted_at.is_(None),
        )
        count_q = select(func.count(Budget.id)).where(
            Budget.client_id == client_id,
            Budget.deleted_at.is_(None),
        )
        if fiscal_year:
            query = query.where(Budget.fiscal_year == fiscal_year)
            count_q = count_q.where(Budget.fiscal_year == fiscal_year)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(Budget.fiscal_year.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    @staticmethod
    async def get_budget(
        db: AsyncSession, client_id: uuid.UUID, budget_id: uuid.UUID,
    ) -> Budget:
        result = await db.execute(
            select(Budget).where(
                Budget.id == budget_id,
                Budget.client_id == client_id,
                Budget.deleted_at.is_(None),
            )
        )
        budget = result.scalar_one_or_none()
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        return budget

    @staticmethod
    async def delete_budget(
        db: AsyncSession, client_id: uuid.UUID, budget_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> None:
        verify_role(current_user, "CPA_OWNER")
        budget = await BudgetService.get_budget(db, client_id, budget_id)
        budget.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def budget_vs_actual(
        db: AsyncSession, client_id: uuid.UUID, budget_id: uuid.UUID,
        month_start: int = 1, month_end: int = 12,
    ) -> dict:
        """Compare budget to actual GL entries for given months."""
        budget = await BudgetService.get_budget(db, client_id, budget_id)

        lines = []
        total_budget = Decimal("0")
        total_actual = Decimal("0")

        for bl in budget.lines:
            # Sum budget for requested months
            month_attrs = [f"month_{m}" for m in range(month_start, month_end + 1)]
            budget_amount = sum(getattr(bl, attr) for attr in month_attrs)

            # Get actual from GL
            actual_result = await db.execute(
                select(func.coalesce(
                    func.sum(JournalEntryLine.debit_amount) - func.sum(JournalEntryLine.credit_amount),
                    Decimal("0")
                )).join(
                    JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id
                ).where(
                    JournalEntry.client_id == client_id,
                    JournalEntry.status == JournalEntryStatus.POSTED,
                    JournalEntryLine.account_id == bl.account_id,
                    extract("year", JournalEntry.entry_date) == budget.fiscal_year,
                    extract("month", JournalEntry.entry_date) >= month_start,
                    extract("month", JournalEntry.entry_date) <= month_end,
                )
            )
            actual_amount = actual_result.scalar() or Decimal("0")

            # Get account info
            acct_result = await db.execute(
                select(ChartOfAccounts).where(ChartOfAccounts.id == bl.account_id)
            )
            acct = acct_result.scalar_one_or_none()

            variance = actual_amount - budget_amount
            variance_pct = None
            if budget_amount != 0:
                variance_pct = round((variance / budget_amount) * 100, 1)

            lines.append({
                "account_id": bl.account_id,
                "account_name": acct.account_name if acct else "Unknown",
                "account_number": acct.account_number if acct else "",
                "budget_amount": budget_amount,
                "actual_amount": actual_amount,
                "variance": variance,
                "variance_pct": variance_pct,
            })

            total_budget += budget_amount
            total_actual += actual_amount

        return {
            "client_id": client_id,
            "budget_name": budget.name,
            "fiscal_year": budget.fiscal_year,
            "period_start": f"{budget.fiscal_year}-{month_start:02d}",
            "period_end": f"{budget.fiscal_year}-{month_end:02d}",
            "lines": lines,
            "total_budget": total_budget,
            "total_actual": total_actual,
            "total_variance": total_actual - total_budget,
        }
