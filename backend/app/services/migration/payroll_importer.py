"""
Payroll history importer for QuickBooks Online migration (module M6).

Imports parsed QBO payroll records into the payroll_runs and payroll_items
tables. Creates one payroll run per import batch with individual items
per employee.

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — no hard deletes, all writes audited via triggers.
- Rule #4: CLIENT ISOLATION — all records tagged with client_id.
- Imported payroll runs are created as FINALIZED (historical data
  approved by CPA_OWNER during migration).
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.payroll import PayrollItem, PayrollRun

from .models import ParsedPayrollRecord


@dataclass
class ImportedPayrollRecord:
    """Record of a successfully imported payroll record."""

    payroll_item_id: uuid.UUID
    employee_name: str
    gross_pay: Decimal


@dataclass
class SkippedPayrollRecord:
    """Record of a payroll record that was skipped during import."""

    original: ParsedPayrollRecord
    reason: str


@dataclass
class PayrollImportResult:
    """Complete result of a payroll import operation."""

    payroll_run_id: uuid.UUID | None = None
    imported: list[ImportedPayrollRecord] = field(default_factory=list)
    skipped: list[SkippedPayrollRecord] = field(default_factory=list)
    total_input: int = 0
    total_imported: int = 0
    total_skipped: int = 0


class PayrollHistoryImporter:
    """
    Imports QBO parsed payroll records into payroll_runs/payroll_items.

    For each batch of payroll records (typically one pay period from QBO),
    creates a single PayrollRun in FINALIZED status with a PayrollItem
    per employee.

    Employee matching is done by name (first + last) since QBO exports
    only provide employee display names.
    """

    def __init__(self, cpa_owner_user_id: str) -> None:
        self._cpa_owner_user_id = cpa_owner_user_id

    async def _resolve_employee(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_name: str,
    ) -> Employee | None:
        """
        Look up an employee by display name for a given client.

        Tries exact match on "first_name last_name" concatenation,
        then tries case-insensitive matching.
        """
        # Parse the display name into first/last
        parts = employee_name.strip().split(None, 1)
        if len(parts) == 2:
            first_name, last_name = parts
        elif len(parts) == 1:
            first_name = parts[0]
            last_name = ""
        else:
            return None

        # Try exact match
        stmt = select(Employee).where(
            Employee.client_id == client_id,
            Employee.first_name == first_name,
            Employee.last_name == last_name,
            Employee.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is not None:
            return employee

        # Try case-insensitive match
        stmt = select(Employee).where(
            Employee.client_id == client_id,
            Employee.first_name.ilike(first_name),
            Employee.last_name.ilike(last_name),
            Employee.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def import_payroll_records(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        records: list[ParsedPayrollRecord],
        pay_period_start: date,
        pay_period_end: date,
        pay_date: date,
    ) -> PayrollImportResult:
        """
        Import a batch of QBO payroll records as a single payroll run.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        client_id : uuid.UUID
            The client these payroll records belong to.
        records : list[ParsedPayrollRecord]
            Payroll records from QBOParser.
        pay_period_start : date
            Start of the pay period.
        pay_period_end : date
            End of the pay period.
        pay_date : date
            Date employees were paid.

        Returns
        -------
        PayrollImportResult
            Contains imported/skipped records and counts.
        """
        result = PayrollImportResult(total_input=len(records))

        if not records:
            return result

        # Create the payroll run as FINALIZED (historical import)
        run = PayrollRun(
            client_id=client_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            pay_date=pay_date,
            status="FINALIZED",
            finalized_by=uuid.UUID(self._cpa_owner_user_id),
            finalized_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.flush()
        result.payroll_run_id = run.id

        for record in records:
            # Resolve employee
            employee = await self._resolve_employee(db, client_id, record.employee)
            if employee is None:
                result.skipped.append(SkippedPayrollRecord(
                    original=record,
                    reason=f"Employee '{record.employee}' not found in employee records",
                ))
                continue

            # Calculate net pay from the record (or use provided value)
            net_pay = record.net_pay
            if net_pay is None:
                # Calculate from gross minus deductions
                deductions = (
                    (record.federal_withholding or Decimal("0.00"))
                    + (record.state_withholding or Decimal("0.00"))
                    + (record.social_security or Decimal("0.00"))
                    + (record.medicare or Decimal("0.00"))
                )
                net_pay = record.gross_pay - deductions

            item = PayrollItem(
                payroll_run_id=run.id,
                employee_id=employee.id,
                gross_pay=record.gross_pay,
                federal_withholding=record.federal_withholding or Decimal("0.00"),
                state_withholding=record.state_withholding or Decimal("0.00"),
                social_security=record.social_security or Decimal("0.00"),
                medicare=record.medicare or Decimal("0.00"),
                ga_suta=record.ga_suta or Decimal("0.00"),
                futa=record.futa or Decimal("0.00"),
                net_pay=net_pay,
            )
            db.add(item)
            await db.flush()

            result.imported.append(ImportedPayrollRecord(
                payroll_item_id=item.id,
                employee_name=record.employee,
                gross_pay=record.gross_pay,
            ))

        result.total_imported = len(result.imported)
        result.total_skipped = len(result.skipped)
        return result
