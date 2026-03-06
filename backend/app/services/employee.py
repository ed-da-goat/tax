"""
Service layer for Employee Records (module P1).

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import encrypt_pii
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeService:
    """Business logic for employee CRUD operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: EmployeeCreate,
    ) -> Employee:
        employee = Employee(
            client_id=client_id,
            first_name=data.first_name,
            last_name=data.last_name,
            ssn_encrypted=encrypt_pii(data.ssn),
            filing_status=data.filing_status.value,
            allowances=data.allowances,
            pay_rate=data.pay_rate,
            pay_type=data.pay_type.value,
            hire_date=data.hire_date,
        )
        db.add(employee)
        await db.flush()
        await db.refresh(employee)
        return employee

    @staticmethod
    async def get(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
    ) -> Employee | None:
        """
        Get a single employee by ID.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = select(Employee).where(
            Employee.id == employee_id,
            Employee.client_id == client_id,
            Employee.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Employee], int]:
        """
        List employees for a client with optional active filter.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        base = select(Employee).where(
            Employee.client_id == client_id,
            Employee.deleted_at.is_(None),
        )

        if active_only:
            base = base.where(Employee.is_active.is_(True))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(Employee.last_name, Employee.first_name).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def update(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        data: EmployeeUpdate,
    ) -> Employee | None:
        employee = await EmployeeService.get(db, client_id, employee_id)
        if employee is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        # Encrypt SSN at the service boundary
        if "ssn" in update_data:
            employee.ssn_encrypted = encrypt_pii(update_data.pop("ssn"))
        for field, value in update_data.items():
            if field in ("filing_status", "pay_type") and value is not None:
                value = value.value
            setattr(employee, field, value)

        employee.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(employee)
        return employee

    @staticmethod
    async def terminate(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
        termination_date: date,
    ) -> Employee | None:
        """Terminate an employee (set termination_date and is_active=False)."""
        employee = await EmployeeService.get(db, client_id, employee_id)
        if employee is None:
            return None

        if not employee.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee is already terminated",
            )

        employee.termination_date = termination_date
        employee.is_active = False
        employee.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(employee)
        return employee

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        client_id: uuid.UUID,
        employee_id: uuid.UUID,
    ) -> Employee | None:
        """
        Soft delete an employee.

        Compliance (rule #2): Never hard delete.
        """
        employee = await EmployeeService.get(db, client_id, employee_id)
        if employee is None:
            return None

        employee.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(employee)
        return employee
