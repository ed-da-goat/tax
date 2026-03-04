"""
API router for Employee Records (module P1).

Endpoints are scoped to /clients/{client_id}/employees.

Compliance (CLAUDE.md):
- Client isolation: client_id from URL path (rule #4).
- Soft deletes only (rule #2).
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeList,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee import EmployeeService

router = APIRouter()


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee record",
)
async def create_employee(
    client_id: uuid.UUID,
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeResponse:
    employee = await EmployeeService.create(db, client_id, data)
    await db.commit()
    return EmployeeResponse.model_validate(employee)


@router.get(
    "",
    response_model=EmployeeList,
    summary="List employees for a client",
)
async def list_employees(
    client_id: uuid.UUID,
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeList:
    employees, total = await EmployeeService.list(
        db, client_id, active_only=active_only, skip=skip, limit=limit,
    )
    return EmployeeList(
        items=[EmployeeResponse.model_validate(e) for e in employees],
        total=total,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get a single employee",
)
async def get_employee(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeResponse:
    employee = await EmployeeService.get(db, client_id, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return EmployeeResponse.model_validate(employee)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update an employee record",
)
async def update_employee(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeResponse:
    employee = await EmployeeService.update(db, client_id, employee_id, data)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await db.commit()
    return EmployeeResponse.model_validate(employee)


@router.post(
    "/{employee_id}/terminate",
    response_model=EmployeeResponse,
    summary="Terminate an employee",
)
async def terminate_employee(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    termination_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> EmployeeResponse:
    """Terminate an employee. CPA_OWNER only."""
    employee = await EmployeeService.terminate(db, client_id, employee_id, termination_date)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await db.commit()
    return EmployeeResponse.model_validate(employee)


@router.delete(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Soft-delete an employee",
)
async def delete_employee(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> EmployeeResponse:
    employee = await EmployeeService.soft_delete(db, client_id, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await db.commit()
    return EmployeeResponse.model_validate(employee)
