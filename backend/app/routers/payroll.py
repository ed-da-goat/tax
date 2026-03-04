"""
API router for Payroll (modules P2-P6).

Endpoints are scoped to /clients/{client_id}/payroll.

Compliance (CLAUDE.md):
- Rule #4: Client isolation via client_id path parameter.
- Rule #5: APPROVAL WORKFLOW — payroll starts DRAFT, must be approved.
- Rule #6: PAYROLL GATE — finalization requires CPA_OWNER at BOTH
           route level (require_role) AND function level (verify_role).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.payroll import (
    PayrollRunCreate,
    PayrollRunList,
    PayrollRunResponse,
    PayrollItemResponse,
    PayrollRunSummary,
)
from app.services.payroll.payroll_service import PayrollService

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_to_response(run) -> PayrollRunResponse:
    """Convert a PayrollRun ORM model to a response schema."""
    return PayrollRunResponse(
        id=run.id,
        created_at=run.created_at,
        updated_at=run.updated_at,
        client_id=run.client_id,
        pay_period_start=run.pay_period_start,
        pay_period_end=run.pay_period_end,
        pay_date=run.pay_date,
        status=run.status,
        finalized_by=run.finalized_by,
        finalized_at=run.finalized_at,
        items=[
            PayrollItemResponse(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                payroll_run_id=item.payroll_run_id,
                employee_id=item.employee_id,
                gross_pay=item.gross_pay,
                federal_withholding=item.federal_withholding,
                state_withholding=item.state_withholding,
                social_security=item.social_security,
                medicare=item.medicare,
                ga_suta=item.ga_suta,
                futa=item.futa,
                net_pay=item.net_pay,
            )
            for item in (run.items or [])
            if item.deleted_at is None
        ],
    )


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a payroll run with tax calculations",
)
async def create_payroll_run(
    client_id: uuid.UUID,
    data: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PayrollRunResponse:
    """Create a DRAFT payroll run with all tax calculations."""
    run = await PayrollService.create_payroll_run(db, client_id, data)
    await db.commit()
    await db.refresh(run)
    return _run_to_response(run)


@router.get(
    "",
    response_model=PayrollRunList,
    summary="List payroll runs for a client",
)
async def list_payroll_runs(
    client_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PayrollRunList:
    runs, total = await PayrollService.list(db, client_id, skip=skip, limit=limit)
    return PayrollRunList(
        items=[_run_to_response(r) for r in runs],
        total=total,
    )


@router.get(
    "/{run_id}",
    response_model=PayrollRunResponse,
    summary="Get a single payroll run",
)
async def get_payroll_run(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PayrollRunResponse:
    run = await PayrollService.get(db, client_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
    return _run_to_response(run)


# ---------------------------------------------------------------------------
# Workflow endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{run_id}/submit",
    response_model=PayrollRunResponse,
    summary="Submit a payroll run for approval",
)
async def submit_payroll_run(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PayrollRunResponse:
    """Submit a DRAFT payroll run for CPA_OWNER approval."""
    run = await PayrollService.submit_for_approval(db, client_id, run_id)
    await db.commit()
    return _run_to_response(run)


@router.post(
    "/{run_id}/finalize",
    response_model=PayrollRunResponse,
    summary="Finalize a payroll run (CPA_OWNER only)",
)
async def finalize_payroll_run(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> PayrollRunResponse:
    """
    Finalize a PENDING_APPROVAL payroll run. CPA_OWNER ONLY.

    Compliance (rule #6): Defense in depth — require_role at route level
    AND verify_role at function level inside PayrollService.finalize().
    """
    run = await PayrollService.finalize(db, client_id, run_id, user)
    await db.commit()
    return _run_to_response(run)


@router.post(
    "/{run_id}/void",
    response_model=PayrollRunResponse,
    summary="Void a finalized payroll run (CPA_OWNER only)",
)
async def void_payroll_run(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> PayrollRunResponse:
    """Void a finalized payroll run. CPA_OWNER ONLY."""
    run = await PayrollService.void(db, client_id, run_id, user)
    await db.commit()
    return _run_to_response(run)


@router.delete(
    "/{run_id}",
    response_model=PayrollRunResponse,
    summary="Soft-delete a payroll run (CPA_OWNER only)",
)
async def delete_payroll_run(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> PayrollRunResponse:
    run = await PayrollService.soft_delete(db, client_id, run_id, user)
    await db.commit()
    return _run_to_response(run)


# ---------------------------------------------------------------------------
# Pay stub PDF endpoint (P5)
# ---------------------------------------------------------------------------

@router.get(
    "/{run_id}/items/{item_id}/pay-stub",
    summary="Download pay stub PDF for a payroll item",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_pay_stub(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Generate and return a PDF pay stub for a specific payroll item."""
    from decimal import Decimal
    from sqlalchemy import select
    from app.models.employee import Employee
    from app.models.client import Client
    from app.services.payroll.pay_stub import PayStubData, PayStubGenerator

    run = await PayrollService.get(db, client_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")

    # Find the specific payroll item
    item = None
    for i in run.items:
        if i.id == item_id and i.deleted_at is None:
            item = i
            break
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll item not found")

    # Get employee info
    emp_stmt = select(Employee).where(
        Employee.id == item.employee_id,
        Employee.client_id == client_id,
    )
    emp_result = await db.execute(emp_stmt)
    employee = emp_result.scalar_one_or_none()

    # Get client info
    client_stmt = select(Client).where(Client.id == client_id)
    client_result = await db.execute(client_stmt)
    client = client_result.scalar_one_or_none()

    stub_data = PayStubData(
        company_name=client.name if client else "Unknown Company",
        employee_name=f"{employee.first_name} {employee.last_name}" if employee else "Unknown",
        employee_id_display=str(item.employee_id)[:8],
        pay_period_start=run.pay_period_start,
        pay_period_end=run.pay_period_end,
        pay_date=run.pay_date,
        pay_rate=employee.pay_rate if employee else Decimal("0"),
        pay_type=employee.pay_type if employee else "HOURLY",
        gross_pay=item.gross_pay,
        federal_withholding=item.federal_withholding,
        state_withholding=item.state_withholding,
        social_security=item.social_security,
        medicare=item.medicare,
        employer_ss=item.social_security,  # Employer matches employee SS
        employer_medicare=item.medicare,
        ga_suta=item.ga_suta,
        futa=item.futa,
        net_pay=item.net_pay,
    )

    pdf_bytes = PayStubGenerator.generate_pdf(stub_data)

    emp_name = f"{employee.last_name}_{employee.first_name}" if employee else "employee"
    filename = f"pay_stub_{emp_name}_{run.pay_date.isoformat()}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
