"""
API router for Direct Deposit (Phase 8A).

Endpoints:
- Employee bank account CRUD (nested under employees)
- NACHA file generation for finalized payroll runs
- Prenote generation for new accounts
- Direct deposit batch status tracking

Compliance (CLAUDE.md):
- Rule #4: Client isolation via client_id path parameter.
- Rule #6: NACHA generation requires CPA_OWNER.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.direct_deposit import (
    DDBatchList,
    DDBatchResponse,
    DDBatchStatus,
    EmployeeBankAccountCreate,
    EmployeeBankAccountList,
    EmployeeBankAccountResponse,
    EmployeeBankAccountUpdate,
    NACHAGenerateRequest,
)
from app.services.payroll.direct_deposit_service import DirectDepositService

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _account_to_response(acct) -> EmployeeBankAccountResponse:
    """Convert an EmployeeBankAccount ORM model to a response schema."""
    # Mask account number: show last 4 digits only
    try:
        raw = acct.account_number_encrypted.decode("utf-8")
        masked = "****" + raw[-4:] if len(raw) >= 4 else "****"
    except Exception:
        masked = "****"

    return EmployeeBankAccountResponse(
        id=acct.id,
        created_at=acct.created_at,
        updated_at=acct.updated_at,
        employee_id=acct.employee_id,
        client_id=acct.client_id,
        account_holder_name=acct.account_holder_name,
        account_number_masked=masked,
        routing_number=acct.routing_number,
        account_type=acct.account_type,
        is_primary=acct.is_primary,
        enrollment_date=acct.enrollment_date,
        authorization_on_file=acct.authorization_on_file,
        prenote_status=acct.prenote_status,
        prenote_sent_at=acct.prenote_sent_at,
        prenote_verified_at=acct.prenote_verified_at,
    )


def _batch_to_response(batch) -> DDBatchResponse:
    return DDBatchResponse(
        id=batch.id,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        payroll_run_id=batch.payroll_run_id,
        client_id=batch.client_id,
        batch_number=batch.batch_number,
        entry_count=batch.entry_count,
        total_credit_amount=batch.total_credit_amount,
        company_name=batch.company_name,
        company_id=batch.company_id,
        status=batch.status,
        generated_at=batch.generated_at,
        downloaded_at=batch.downloaded_at,
        submitted_at=batch.submitted_at,
        confirmed_at=batch.confirmed_at,
        generated_by=batch.generated_by,
    )


# ---------------------------------------------------------------------------
# Employee Bank Account endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/employees/{employee_id}/bank-accounts",
    response_model=EmployeeBankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll an employee in direct deposit",
)
async def create_bank_account(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    data: EmployeeBankAccountCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeBankAccountResponse:
    acct = await DirectDepositService.create_bank_account(
        db, client_id, employee_id, data,
    )
    await db.commit()
    return _account_to_response(acct)


@router.get(
    "/employees/{employee_id}/bank-accounts",
    response_model=EmployeeBankAccountList,
    summary="List bank accounts for an employee",
)
async def list_bank_accounts(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeBankAccountList:
    accounts, total = await DirectDepositService.list_bank_accounts(
        db, client_id, employee_id,
    )
    return EmployeeBankAccountList(
        items=[_account_to_response(a) for a in accounts],
        total=total,
    )


@router.get(
    "/employees/{employee_id}/bank-accounts/{account_id}",
    response_model=EmployeeBankAccountResponse,
    summary="Get a single bank account",
)
async def get_bank_account(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeBankAccountResponse:
    acct = await DirectDepositService.get_bank_account(
        db, client_id, employee_id, account_id,
    )
    if acct is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    return _account_to_response(acct)


@router.patch(
    "/employees/{employee_id}/bank-accounts/{account_id}",
    response_model=EmployeeBankAccountResponse,
    summary="Update a bank account",
)
async def update_bank_account(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    account_id: uuid.UUID,
    data: EmployeeBankAccountUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EmployeeBankAccountResponse:
    acct = await DirectDepositService.update_bank_account(
        db, client_id, employee_id, account_id, data,
    )
    if acct is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    await db.commit()
    return _account_to_response(acct)


@router.delete(
    "/employees/{employee_id}/bank-accounts/{account_id}",
    response_model=EmployeeBankAccountResponse,
    summary="Remove a bank account (soft delete)",
)
async def delete_bank_account(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> EmployeeBankAccountResponse:
    acct = await DirectDepositService.soft_delete_bank_account(
        db, client_id, employee_id, account_id,
    )
    if acct is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    await db.commit()
    return _account_to_response(acct)


# ---------------------------------------------------------------------------
# NACHA File Generation endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/payroll/{run_id}/nacha",
    summary="Generate NACHA file for a finalized payroll run (CPA_OWNER only)",
    responses={200: {"content": {"text/plain": {}}}},
)
async def generate_nacha_file(
    client_id: uuid.UUID,
    run_id: uuid.UUID,
    config: NACHAGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """
    Generate a NACHA/ACH file for direct deposit.

    Returns the NACHA file content as text/plain for download.
    The CPA uploads this file to their bank's commercial portal.
    """
    nacha_content, batch = await DirectDepositService.generate_nacha_file(
        db, client_id, run_id, config, user,
    )
    await db.commit()

    filename = f"payroll_dd_{run_id}_{batch.batch_number}.ach"

    return Response(
        content=nacha_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/employees/{employee_id}/prenote",
    summary="Generate prenote (test) NACHA file for a new DD account (CPA_OWNER only)",
    responses={200: {"content": {"text/plain": {}}}},
)
async def generate_prenote(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    config: NACHAGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """
    Generate a prenote (zero-dollar test transaction) NACHA file.

    Upload this to your bank to verify the employee's account info.
    Wait 3 business days, then mark the account as verified.
    """
    nacha_content = await DirectDepositService.generate_prenote_file(
        db, client_id, employee_id, config, user,
    )
    await db.commit()

    filename = f"prenote_{employee_id}.ach"

    return Response(
        content=nacha_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Batch tracking endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/direct-deposit-batches",
    response_model=DDBatchList,
    summary="List direct deposit batches for a client",
)
async def list_batches(
    client_id: uuid.UUID,
    run_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DDBatchList:
    batches, total = await DirectDepositService.list_batches(db, client_id, run_id)
    return DDBatchList(
        items=[_batch_to_response(b) for b in batches],
        total=total,
    )


@router.get(
    "/direct-deposit-batches/{batch_id}",
    response_model=DDBatchResponse,
    summary="Get a single direct deposit batch",
)
async def get_batch(
    client_id: uuid.UUID,
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DDBatchResponse:
    batch = await DirectDepositService.get_batch(db, client_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return _batch_to_response(batch)


@router.patch(
    "/direct-deposit-batches/{batch_id}/status",
    response_model=DDBatchResponse,
    summary="Update batch status (CPA_OWNER only)",
)
async def update_batch_status(
    client_id: uuid.UUID,
    batch_id: uuid.UUID,
    new_status: DDBatchStatus = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> DDBatchResponse:
    batch = await DirectDepositService.update_batch_status(
        db, client_id, batch_id, new_status.value, user,
    )
    await db.commit()
    return _batch_to_response(batch)
