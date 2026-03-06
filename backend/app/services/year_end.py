"""
Year-end close service (C1).

Generates closing journal entries to zero out revenue/expense accounts
and transfer net income to Retained Earnings (account 3200).
Tracks fiscal year status per client.
Prevents posting to closed years.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChartOfAccounts,
    JournalEntry, JournalEntryLine, JournalEntryStatus,
)

RETAINED_EARNINGS_ACCT = "3200"


class YearEndService:

    @staticmethod
    async def get_year_status(db: AsyncSession, client_id: uuid.UUID, fiscal_year: int) -> dict:
        """Check if a fiscal year is open or closed for a client."""
        result = await db.execute(text(
            "SELECT je.id FROM journal_entries je "
            "WHERE je.client_id = :cid "
            "AND je.reference_number = :ref "
            "AND je.status = 'POSTED' "
            "AND je.deleted_at IS NULL "
            "LIMIT 1"
        ), {"cid": str(client_id), "ref": f"YEAR-END-CLOSE-{fiscal_year}"})
        closing_entry = result.scalar_one_or_none()
        return {
            "client_id": str(client_id),
            "fiscal_year": fiscal_year,
            "status": "CLOSED" if closing_entry else "OPEN",
            "closing_entry_id": str(closing_entry) if closing_entry else None,
        }

    @staticmethod
    async def check_year_closed(db: AsyncSession, client_id: uuid.UUID, entry_date: date) -> bool:
        """Return True if the fiscal year for entry_date is closed."""
        fiscal_year = entry_date.year
        status = await YearEndService.get_year_status(db, client_id, fiscal_year)
        return status["status"] == "CLOSED"

    @staticmethod
    async def preview_closing_entries(
        db: AsyncSession, client_id: uuid.UUID, fiscal_year: int,
    ) -> dict:
        """Preview what closing entries would be generated without actually posting."""
        year_start = date(fiscal_year, 1, 1)
        year_end = date(fiscal_year, 12, 31)

        # Get all revenue and expense account balances for the year
        result = await db.execute(text(
            "SELECT coa.id, coa.account_number, coa.account_name, coa.account_type, "
            "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
            "    COALESCE(SUM(jel.credit), 0) AS total_credits "
            "FROM chart_of_accounts coa "
            "LEFT JOIN journal_entry_lines jel ON jel.account_id = coa.id "
            "LEFT JOIN journal_entries je ON je.id = jel.journal_entry_id "
            "    AND je.status = 'POSTED' "
            "    AND je.deleted_at IS NULL "
            "    AND je.entry_date >= :start AND je.entry_date <= :end "
            "WHERE coa.client_id = :cid "
            "    AND coa.deleted_at IS NULL "
            "    AND coa.account_type IN ('REVENUE', 'EXPENSE') "
            "GROUP BY coa.id, coa.account_number, coa.account_name, coa.account_type "
            "HAVING COALESCE(SUM(jel.debit), 0) != 0 OR COALESCE(SUM(jel.credit), 0) != 0 "
            "ORDER BY coa.account_number"
        ), {"cid": str(client_id), "start": year_start, "end": year_end})

        rows = result.all()

        closing_lines = []
        total_revenue = Decimal("0")
        total_expenses = Decimal("0")

        for row in rows:
            if row.account_type == "REVENUE":
                # Revenue has credit balance; close by debiting
                balance = row.total_credits - row.total_debits
                if balance != 0:
                    total_revenue += balance
                    closing_lines.append({
                        "account_id": str(row.id),
                        "account_number": row.account_number,
                        "account_name": row.account_name,
                        "account_type": "REVENUE",
                        "balance": float(balance),
                        "debit": float(balance) if balance > 0 else 0,
                        "credit": float(abs(balance)) if balance < 0 else 0,
                    })
            else:  # EXPENSE
                # Expense has debit balance; close by crediting
                balance = row.total_debits - row.total_credits
                if balance != 0:
                    total_expenses += balance
                    closing_lines.append({
                        "account_id": str(row.id),
                        "account_number": row.account_number,
                        "account_name": row.account_name,
                        "account_type": "EXPENSE",
                        "balance": float(balance),
                        "debit": 0,
                        "credit": float(balance) if balance > 0 else 0,
                    })

        net_income = total_revenue - total_expenses

        return {
            "client_id": str(client_id),
            "fiscal_year": fiscal_year,
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "net_income": float(net_income),
            "closing_lines": closing_lines,
            "retained_earnings_entry": {
                "account_number": RETAINED_EARNINGS_ACCT,
                "debit": float(net_income) if net_income < 0 else 0,
                "credit": float(net_income) if net_income > 0 else 0,
            },
        }

    @staticmethod
    async def close_year(
        db: AsyncSession,
        client_id: uuid.UUID,
        fiscal_year: int,
        user_id: uuid.UUID,
    ) -> dict:
        """Execute year-end close: create closing journal entry."""
        # Check not already closed
        status = await YearEndService.get_year_status(db, client_id, fiscal_year)
        if status["status"] == "CLOSED":
            raise ValueError(f"Fiscal year {fiscal_year} is already closed")

        preview = await YearEndService.preview_closing_entries(db, client_id, fiscal_year)

        if not preview["closing_lines"]:
            raise ValueError("No revenue or expense activity to close")

        year_end_date = date(fiscal_year, 12, 31)
        now_utc = datetime.now(timezone.utc)

        # Find retained earnings account for this client
        re_result = await db.execute(
            select(ChartOfAccounts).where(
                ChartOfAccounts.client_id == client_id,
                ChartOfAccounts.account_number == RETAINED_EARNINGS_ACCT,
                ChartOfAccounts.deleted_at.is_(None),
            )
        )
        re_account = re_result.scalar_one_or_none()
        if not re_account:
            raise ValueError(f"Retained Earnings account ({RETAINED_EARNINGS_ACCT}) not found for client")

        # Create the closing journal entry as DRAFT first
        je_id = uuid.uuid4()
        je = JournalEntry(
            id=je_id,
            client_id=client_id,
            entry_date=year_end_date,
            description=f"Year-end closing entry — FY{fiscal_year}",
            reference_number=f"YEAR-END-CLOSE-{fiscal_year}",
            status=JournalEntryStatus.DRAFT,
            created_by=user_id,
            approved_by=user_id,
        )
        db.add(je)
        await db.flush()

        net_income = Decimal(str(preview["net_income"]))

        # Add closing lines for each revenue/expense account
        for line in preview["closing_lines"]:
            acct_id = uuid.UUID(line["account_id"])
            db.add(JournalEntryLine(
                journal_entry_id=je_id,
                account_id=acct_id,
                debit=Decimal(str(line["debit"])),
                credit=Decimal(str(line["credit"])),
            ))

        # Add Retained Earnings line (net income offset)
        if net_income > 0:
            db.add(JournalEntryLine(
                journal_entry_id=je_id,
                account_id=re_account.id,
                debit=Decimal("0"),
                credit=net_income,
            ))
        elif net_income < 0:
            db.add(JournalEntryLine(
                journal_entry_id=je_id,
                account_id=re_account.id,
                debit=abs(net_income),
                credit=Decimal("0"),
            ))

        await db.flush()

        # Now post the entry (triggers balance validation)
        je.status = JournalEntryStatus.POSTED
        await db.flush()

        return {
            "client_id": str(client_id),
            "fiscal_year": fiscal_year,
            "status": "CLOSED",
            "closing_entry_id": str(je_id),
            "net_income": float(net_income),
            "accounts_closed": len(preview["closing_lines"]),
        }

    @staticmethod
    async def reopen_year(
        db: AsyncSession,
        client_id: uuid.UUID,
        fiscal_year: int,
        user_id: uuid.UUID,
    ) -> dict:
        """Reopen a closed fiscal year by voiding the closing entry."""
        status = await YearEndService.get_year_status(db, client_id, fiscal_year)
        if status["status"] != "CLOSED":
            raise ValueError(f"Fiscal year {fiscal_year} is not closed")

        closing_entry_id = uuid.UUID(status["closing_entry_id"])
        result = await db.execute(
            select(JournalEntry).where(JournalEntry.id == closing_entry_id)
        )
        je = result.scalar_one()
        je.status = JournalEntryStatus.VOID
        await db.flush()

        return {
            "client_id": str(client_id),
            "fiscal_year": fiscal_year,
            "status": "OPEN",
            "voided_entry_id": str(closing_entry_id),
        }
