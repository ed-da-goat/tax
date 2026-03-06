"""
Direct Deposit service layer (Phase 8A).

Manages employee bank accounts, NACHA file generation, and batch tracking.

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #6: PAYROLL GATE — NACHA generation requires CPA_OWNER + FINALIZED payroll.

NACHA compliance:
- Employee authorization must be on file before generating ACH entries.
- Prenote (zero-dollar test) recommended before first live deposit.
- Account numbers encrypted at rest.
- Georgia law (O.C.G.A. 34-7-2): Employee consent is mandatory for direct deposit.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.direct_deposit_batch import DirectDepositBatch
from app.models.employee import Employee
from app.models.employee_bank_account import EmployeeBankAccount
from app.models.payroll import PayrollItem, PayrollRun
from app.schemas.direct_deposit import (
    EmployeeBankAccountCreate,
    EmployeeBankAccountUpdate,
    NACHAGenerateRequest,
)

from app.crypto import decrypt_pii, encrypt_pii

from .nacha_generator import NACHAEntry, NACHAFileGenerator


class DirectDepositService:
    """Business logic for employee bank accounts and NACHA file generation."""

    # -------------------------------------------------------------------
    # Employee Bank Account CRUD
    # -------------------------------------------------------------------

    @staticmethod
    async def create_bank_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        data: EmployeeBankAccountCreate,
    ) -> EmployeeBankAccount:
        """
        Enroll an employee in direct deposit.

        Compliance (rule #4): Scoped to client_id.
        Georgia law (O.C.G.A. 34-7-2): Consent is mandatory.
        """
        # Verify employee belongs to this client
        emp = await _get_employee_or_raise(db, client_id, employee_id)

        # If setting as primary, unset any existing primary account
        if data.is_primary:
            await _unset_primary_accounts(db, employee_id)

        account = EmployeeBankAccount(
            employee_id=employee_id,
            client_id=client_id,
            account_holder_name=data.account_holder_name,
            account_number_encrypted=encrypt_pii(data.account_number),
            routing_number=data.routing_number,
            account_type=data.account_type.value,
            is_primary=data.is_primary,
            enrollment_date=data.enrollment_date or date.today(),
            authorization_on_file=data.authorization_on_file,
            prenote_status="PENDING",
        )
        db.add(account)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def get_bank_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> EmployeeBankAccount | None:
        stmt = select(EmployeeBankAccount).where(
            EmployeeBankAccount.id == account_id,
            EmployeeBankAccount.employee_id == employee_id,
            EmployeeBankAccount.client_id == client_id,
            EmployeeBankAccount.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_bank_accounts(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
    ) -> tuple[list[EmployeeBankAccount], int]:
        base = select(EmployeeBankAccount).where(
            EmployeeBankAccount.employee_id == employee_id,
            EmployeeBankAccount.client_id == client_id,
            EmployeeBankAccount.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(EmployeeBankAccount.is_primary.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def update_bank_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        account_id: uuid.UUID,
        data: EmployeeBankAccountUpdate,
    ) -> EmployeeBankAccount | None:
        account = await DirectDepositService.get_bank_account(
            db, client_id, employee_id, account_id,
        )
        if account is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle account number encryption
        if "account_number" in update_data and update_data["account_number"] is not None:
            account.account_number_encrypted = encrypt_pii(update_data.pop("account_number"))
            # Reset prenote when account number changes
            account.prenote_status = "PENDING"
            account.prenote_sent_at = None
            account.prenote_verified_at = None

        # Handle is_primary toggle
        if update_data.get("is_primary"):
            await _unset_primary_accounts(db, employee_id)

        # Handle enum values
        if "account_type" in update_data and update_data["account_type"] is not None:
            update_data["account_type"] = update_data["account_type"].value

        for field, value in update_data.items():
            setattr(account, field, value)

        account.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def soft_delete_bank_account(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> EmployeeBankAccount | None:
        account = await DirectDepositService.get_bank_account(
            db, client_id, employee_id, account_id,
        )
        if account is None:
            return None
        account.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(account)
        return account

    # -------------------------------------------------------------------
    # NACHA File Generation
    # -------------------------------------------------------------------

    @staticmethod
    async def generate_nacha_file(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID,
        config: NACHAGenerateRequest,
        user: CurrentUser,
    ) -> tuple[str, DirectDepositBatch]:
        """
        Generate a NACHA file for a finalized payroll run.

        Returns (nacha_file_content, batch_record).

        Compliance (rule #6): CPA_OWNER only (defense in depth).
        """
        verify_role(user, "CPA_OWNER")

        # Verify payroll run is FINALIZED
        run = await _get_finalized_run_or_raise(db, client_id, run_id)

        # Get all payroll items with employee bank accounts
        entries = await _build_nacha_entries(
            db, client_id, run, config.odfi_routing_number,
        )

        if not entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No employees with authorized direct deposit accounts found for this payroll run",
            )

        # Generate NACHA file
        generator = NACHAFileGenerator(
            immediate_destination=config.odfi_routing_number,
            immediate_origin=config.company_id,
            destination_name=config.odfi_name,
            origin_name=config.company_name,
            file_creation_date=date.today(),
            file_id_modifier=config.file_id_modifier,
        )

        total_credit = sum(e.amount for e in entries)

        generator.add_batch(
            company_name=config.company_name,
            company_id=config.company_id,
            effective_entry_date=config.effective_entry_date,
            entries=entries,
        )

        nacha_content = generator.generate()

        # Count existing batches for this run to determine batch number
        count_stmt = select(func.count()).select_from(
            select(DirectDepositBatch).where(
                DirectDepositBatch.payroll_run_id == run_id,
                DirectDepositBatch.deleted_at.is_(None),
            ).subquery()
        )
        existing_count = (await db.execute(count_stmt)).scalar_one()

        # Create batch tracking record
        batch = DirectDepositBatch(
            payroll_run_id=run_id,
            client_id=client_id,
            batch_number=existing_count + 1,
            file_id_modifier=config.file_id_modifier,
            entry_count=len(entries),
            total_credit_amount=Decimal(total_credit) / 100,
            company_name=config.company_name[:16],
            company_id=config.company_id[:10],
            status="GENERATED",
            generated_by=uuid.UUID(user.user_id),
        )
        db.add(batch)
        await db.flush()
        await db.refresh(batch)

        return nacha_content, batch

    @staticmethod
    async def generate_prenote_file(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        config: NACHAGenerateRequest,
        user: CurrentUser,
    ) -> str:
        """
        Generate a prenote (zero-dollar test) NACHA file for a single employee.

        Prenotes verify account validity before the first live deposit.
        NACHA recommends waiting 3 business days after prenote submission
        before sending live entries.
        """
        verify_role(user, "CPA_OWNER")

        # Get the employee's primary bank account
        stmt = select(EmployeeBankAccount).where(
            EmployeeBankAccount.employee_id == employee_id,
            EmployeeBankAccount.client_id == client_id,
            EmployeeBankAccount.is_primary.is_(True),
            EmployeeBankAccount.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No primary bank account found for this employee",
            )

        # Get employee name
        emp = await _get_employee_or_raise(db, client_id, employee_id)

        tx_code = NACHAFileGenerator.transaction_code_for(
            account.account_type, is_prenote=True,
        )

        entry = NACHAEntry(
            transaction_code=tx_code,
            routing_number=account.routing_number,
            account_number=decrypt_pii(account.account_number_encrypted) or "",
            amount=0,  # Prenote is always $0.00
            individual_id=str(employee_id)[:15],
            individual_name=f"{emp.last_name} {emp.first_name}"[:22].upper(),
            trace_number=config.odfi_routing_number[:8] + "0000001",
        )

        generator = NACHAFileGenerator(
            immediate_destination=config.odfi_routing_number,
            immediate_origin=config.company_id,
            destination_name=config.odfi_name,
            origin_name=config.company_name,
            file_creation_date=date.today(),
            file_id_modifier=config.file_id_modifier,
        )

        generator.add_batch(
            company_name=config.company_name,
            company_id=config.company_id,
            effective_entry_date=config.effective_entry_date,
            entries=[entry],
            entry_description="PRENOTE",
        )

        # Mark prenote as sent
        account.prenote_sent_at = datetime.now(timezone.utc)
        account.updated_at = datetime.now(timezone.utc)
        await db.flush()

        return generator.generate()

    # -------------------------------------------------------------------
    # Batch status management
    # -------------------------------------------------------------------

    @staticmethod
    async def get_batch(
        db: AsyncSession,
        client_id: uuid.UUID,
        batch_id: uuid.UUID,
    ) -> DirectDepositBatch | None:
        stmt = select(DirectDepositBatch).where(
            DirectDepositBatch.id == batch_id,
            DirectDepositBatch.client_id == client_id,
            DirectDepositBatch.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_batches(
        db: AsyncSession,
        client_id: uuid.UUID,
        run_id: uuid.UUID | None = None,
    ) -> tuple[list[DirectDepositBatch], int]:
        base = select(DirectDepositBatch).where(
            DirectDepositBatch.client_id == client_id,
            DirectDepositBatch.deleted_at.is_(None),
        )
        if run_id:
            base = base.where(DirectDepositBatch.payroll_run_id == run_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(DirectDepositBatch.generated_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def update_batch_status(
        db: AsyncSession,
        client_id: uuid.UUID,
        batch_id: uuid.UUID,
        new_status: str,
        user: CurrentUser,
    ) -> DirectDepositBatch:
        verify_role(user, "CPA_OWNER")

        batch = await DirectDepositService.get_batch(db, client_id, batch_id)
        if batch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Direct deposit batch not found",
            )

        now = datetime.now(timezone.utc)
        batch.status = new_status
        batch.updated_at = now

        if new_status == "DOWNLOADED":
            batch.downloaded_at = now
        elif new_status == "SUBMITTED":
            batch.submitted_at = now
        elif new_status == "CONFIRMED":
            batch.confirmed_at = now

        await db.flush()
        await db.refresh(batch)
        return batch


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------


async def _get_employee_or_raise(
    db: AsyncSession,
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> Employee:
    stmt = select(Employee).where(
        Employee.id == employee_id,
        Employee.client_id == client_id,
        Employee.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found for this client",
        )
    return employee


async def _unset_primary_accounts(
    db: AsyncSession,
    employee_id: uuid.UUID,
) -> None:
    """Unset is_primary on all existing bank accounts for this employee."""
    stmt = select(EmployeeBankAccount).where(
        EmployeeBankAccount.employee_id == employee_id,
        EmployeeBankAccount.is_primary.is_(True),
        EmployeeBankAccount.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    for acct in result.scalars().all():
        acct.is_primary = False
        acct.updated_at = datetime.now(timezone.utc)


async def _get_finalized_run_or_raise(
    db: AsyncSession,
    client_id: uuid.UUID,
    run_id: uuid.UUID,
) -> PayrollRun:
    stmt = select(PayrollRun).where(
        PayrollRun.id == run_id,
        PayrollRun.client_id == client_id,
        PayrollRun.status == "FINALIZED",
        PayrollRun.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finalized payroll run not found. Only FINALIZED runs can generate NACHA files.",
        )
    return run


async def _build_nacha_entries(
    db: AsyncSession,
    client_id: uuid.UUID,
    run: PayrollRun,
    odfi_routing: str,
) -> list[NACHAEntry]:
    """
    Build NACHA entry detail records for all employees in a payroll run
    who have authorized direct deposit accounts.
    """
    entries: list[NACHAEntry] = []
    sequence = 0

    for item in run.items:
        if item.deleted_at is not None or item.net_pay <= 0:
            continue

        # Get primary bank account for this employee
        stmt = select(EmployeeBankAccount).where(
            EmployeeBankAccount.employee_id == item.employee_id,
            EmployeeBankAccount.client_id == client_id,
            EmployeeBankAccount.is_primary.is_(True),
            EmployeeBankAccount.authorization_on_file.is_(True),
            EmployeeBankAccount.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if account is None:
            continue  # Skip employees without authorized DD accounts

        # Get employee name
        emp_stmt = select(Employee).where(Employee.id == item.employee_id)
        emp_result = await db.execute(emp_stmt)
        employee = emp_result.scalar_one_or_none()
        if employee is None:
            continue

        sequence += 1
        tx_code = NACHAFileGenerator.transaction_code_for(account.account_type)

        entries.append(NACHAEntry(
            transaction_code=tx_code,
            routing_number=account.routing_number,
            account_number=decrypt_pii(account.account_number_encrypted) or "",
            amount=NACHAFileGenerator.amount_to_cents(item.net_pay),
            individual_id=str(item.employee_id)[:15],
            individual_name=f"{employee.last_name} {employee.first_name}"[:22].upper(),
            trace_number=odfi_routing[:8] + str(sequence).rjust(7, "0"),
        ))

    return entries
