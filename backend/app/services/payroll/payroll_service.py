"""
Payroll service layer (module P6 — approval gate + payroll run management).

Orchestrates payroll run creation, tax calculation, approval workflow,
and finalization.

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: APPROVAL WORKFLOW — payroll starts as DRAFT, must be approved.
- Rule #6: PAYROLL GATE — finalization verifies CPA_OWNER at FUNCTION level
            (defense in depth), not just route level.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.employee import Employee
from app.models.payroll import PayrollItem, PayrollRun
from app.schemas.payroll import PayrollItemCreate, PayrollRunCreate

from .federal_tax import FederalTaxCalculator
from .ga_suta import GeorgiaSUTACalculator
from .ga_withholding import GeorgiaWithholdingCalculator


class PayrollService:
    """
    Business logic for payroll runs — creation, calculation, approval, finalization.

    Defense in depth (CLAUDE.md rule #6):
        All state-changing methods that require CPA_OWNER verify the role
        at the function level via verify_role(), in addition to any
        route-level require_role() dependency.
    """

    # -------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------

    @staticmethod
    async def create_payroll_run(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: PayrollRunCreate,
    ) -> PayrollRun:
        """
        Create a new payroll run in DRAFT status and calculate all taxes.

        Compliance (rule #4): Scoped to client_id.
        Compliance (rule #5): Created as DRAFT — does not affect GL.
        """
        # Create the run
        run = PayrollRun(
            client_id=client_id,
            pay_period_start=data.pay_period_start,
            pay_period_end=data.pay_period_end,
            pay_date=data.pay_date,
            status="DRAFT",
        )
        db.add(run)
        await db.flush()

        # Calculate taxes for each employee
        for item_data in data.employee_items:
            employee = await _get_employee_or_raise(
                db, client_id, item_data.employee_id,
            )

            # Calculate gross pay
            gross_pay = _calculate_gross_pay(
                employee, item_data.hours_worked, data.pay_periods_per_year,
            )

            # Get YTD wages for this employee (for cap calculations)
            ytd_wages = await _get_ytd_wages(db, client_id, employee.id, data.tax_year)

            # P2: Georgia state withholding
            ga_result = GeorgiaWithholdingCalculator.calculate(
                gross_pay_per_period=gross_pay,
                filing_status=employee.filing_status,
                allowances=employee.allowances,
                pay_periods=data.pay_periods_per_year,
                tax_year=data.tax_year,
            )

            # P4: Federal withholding
            fed_result = FederalTaxCalculator.calculate_federal_withholding(
                gross_pay_per_period=gross_pay,
                filing_status=employee.filing_status,
                pay_periods=data.pay_periods_per_year,
                tax_year=data.tax_year,
            )

            # P4: FICA
            fica_result = FederalTaxCalculator.calculate_fica(
                gross_pay=gross_pay,
                ytd_wages=ytd_wages,
                tax_year=data.tax_year,
            )

            # P3: Georgia SUTA (employer-paid)
            suta_result = GeorgiaSUTACalculator.calculate(
                gross_pay=gross_pay,
                ytd_wages=ytd_wages,
                tax_year=data.tax_year,
                custom_rate=data.suta_rate,
            )

            # P4: FUTA (employer-paid)
            futa_result = FederalTaxCalculator.calculate_futa(
                gross_pay=gross_pay,
                ytd_wages=ytd_wages,
            )

            # Net pay = gross - employee-side deductions
            net_pay = (
                gross_pay
                - fed_result.per_period_tax
                - ga_result.per_period_tax
                - fica_result.ss_employee
                - fica_result.medicare_employee
                - fica_result.additional_medicare
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if net_pay < Decimal("0"):
                net_pay = Decimal("0.00")

            item = PayrollItem(
                payroll_run_id=run.id,
                employee_id=employee.id,
                gross_pay=gross_pay,
                federal_withholding=fed_result.per_period_tax,
                state_withholding=ga_result.per_period_tax,
                social_security=fica_result.ss_employee,
                medicare=fica_result.medicare_employee + fica_result.additional_medicare,
                ga_suta=suta_result.suta_amount,
                futa=futa_result.futa_amount,
                net_pay=net_pay,
            )
            db.add(item)

        await db.flush()
        await db.refresh(run)
        return run

    # -------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------

    @staticmethod
    async def get(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> PayrollRun | None:
        """
        Get a payroll run by ID.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = select(PayrollRun).where(
            PayrollRun.id == run_id,
            PayrollRun.client_id == client_id,
            PayrollRun.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PayrollRun], int]:
        """
        List payroll runs for a client.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        base = select(PayrollRun).where(
            PayrollRun.client_id == client_id,
            PayrollRun.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(PayrollRun.pay_date.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    # -------------------------------------------------------------------
    # Submit for approval
    # -------------------------------------------------------------------

    @staticmethod
    async def submit_for_approval(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> PayrollRun:
        """
        Submit a DRAFT payroll run for CPA_OWNER approval.

        Compliance (rule #5): Transitions DRAFT -> PENDING_APPROVAL.
        """
        run = await PayrollService.get(db, client_id, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll run not found",
            )
        if run.status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit: current status is {run.status}, expected DRAFT",
            )

        run.status = "PENDING_APPROVAL"
        run.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(run)
        return run

    # -------------------------------------------------------------------
    # Finalize (CPA_OWNER ONLY — defense in depth per rule #6)
    # -------------------------------------------------------------------

    @staticmethod
    async def finalize(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID,
        user: CurrentUser,
    ) -> PayrollRun:
        """
        Finalize a payroll run. CPA_OWNER only.

        Compliance (rule #6): PAYROLL GATE — verifies CPA_OWNER at the
        FUNCTION level (defense in depth), not just the route level.
        """
        # Defense in depth: function-level role check (CLAUDE.md rule #6)
        verify_role(user, "CPA_OWNER")

        run = await PayrollService.get(db, client_id, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll run not found",
            )
        if run.status != "PENDING_APPROVAL":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot finalize: current status is {run.status}, expected PENDING_APPROVAL",
            )

        run.status = "FINALIZED"
        run.finalized_by = uuid.UUID(user.user_id)
        run.finalized_at = datetime.now(timezone.utc)
        run.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(run)
        return run

    # -------------------------------------------------------------------
    # Void (CPA_OWNER ONLY — defense in depth per rule #6)
    # -------------------------------------------------------------------

    @staticmethod
    async def void(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID,
        user: CurrentUser,
    ) -> PayrollRun:
        """
        Void a finalized payroll run. CPA_OWNER only.

        Compliance (rule #6): Defense in depth — function-level role check.
        Compliance (rule #2): Does not delete — sets status to VOID.
        """
        # Defense in depth: function-level role check
        verify_role(user, "CPA_OWNER")

        run = await PayrollService.get(db, client_id, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll run not found",
            )
        if run.status != "FINALIZED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot void: current status is {run.status}, expected FINALIZED",
            )

        run.status = "VOID"
        run.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(run)
        return run

    # -------------------------------------------------------------------
    # Soft delete (CPA_OWNER ONLY)
    # -------------------------------------------------------------------

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID,
        user: CurrentUser,
    ) -> PayrollRun:
        """
        Soft delete a payroll run. CPA_OWNER only.

        Compliance (rule #2): Never hard delete.
        """
        verify_role(user, "CPA_OWNER")

        run = await PayrollService.get(db, client_id, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll run not found",
            )
        if run.status == "FINALIZED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a finalized payroll run. Void it first.",
            )

        run.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(run)
        return run


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------


async def _get_employee_or_raise(
    db: AsyncSession,
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> Employee:
    """Fetch an active employee or raise 404."""
    stmt = select(Employee).where(
        Employee.id == employee_id,
        Employee.client_id == client_id,
        Employee.deleted_at.is_(None),
        Employee.is_active.is_(True),
    )
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active employee {employee_id} not found for this client",
        )
    return employee


def _calculate_gross_pay(
    employee: Employee,
    hours_worked: Decimal | None,
    pay_periods_per_year: int,
) -> Decimal:
    """Calculate gross pay for one pay period."""
    if employee.pay_type == "HOURLY":
        if hours_worked is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hours worked required for hourly employee {employee.id}",
            )
        return (employee.pay_rate * hours_worked).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
    else:
        # SALARY: divide annual salary by pay periods
        return (employee.pay_rate / pay_periods_per_year).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )


async def _get_ytd_wages(
    db: AsyncSession,
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    tax_year: int,
) -> Decimal:
    """
    Get year-to-date gross wages for an employee from FINALIZED payroll runs.

    Only counts wages from finalized runs in the same tax year.
    """
    from sqlalchemy import extract

    stmt = (
        select(func.coalesce(func.sum(PayrollItem.gross_pay), Decimal("0.00")))
        .join(PayrollRun, PayrollItem.payroll_run_id == PayrollRun.id)
        .where(
            PayrollRun.client_id == client_id,
            PayrollRun.status == "FINALIZED",
            PayrollRun.deleted_at.is_(None),
            PayrollItem.employee_id == employee_id,
            PayrollItem.deleted_at.is_(None),
            extract("year", PayrollRun.pay_date) == tax_year,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one() or Decimal("0.00")
