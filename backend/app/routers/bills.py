"""
Bill management API endpoints (Module T1 — Accounts Payable).

Endpoints:
    POST   /api/v1/clients/{client_id}/bills              — Create bill
    GET    /api/v1/clients/{client_id}/bills              — List bills
    GET    /api/v1/clients/{client_id}/bills/{id}         — Get single bill
    POST   /api/v1/clients/{client_id}/bills/{id}/submit  — Submit for approval
    POST   /api/v1/clients/{client_id}/bills/{id}/approve — Approve (CPA_OWNER)
    POST   /api/v1/clients/{client_id}/bills/{id}/pay     — Record payment
    POST   /api/v1/clients/{client_id}/bills/{id}/void    — Void (CPA_OWNER)

Compliance (CLAUDE.md):
- Rule #4: Client isolation via client_id in URL path.
- Rule #5: Approval workflow — DRAFT -> PENDING_APPROVAL -> APPROVED -> PAID.
- Rule #6: CPA_OWNER-only endpoints checked at route AND function level.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.models.bill import BillStatus
from app.schemas.bill import (
    BillCreate,
    BillList,
    BillPaymentCreate,
    BillResponse,
    BillStatus as BillStatusSchema,
)
from app.services.bill import BillService

router = APIRouter()


@router.post(
    "",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bill(
    client_id: UUID,
    data: BillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BillResponse:
    """Create a new bill with line items. Both roles. Status starts as DRAFT."""
    bill = await BillService.create_bill(db, client_id, data, current_user)
    return BillResponse.model_validate(bill)


@router.get("", response_model=BillList)
async def list_bills(
    client_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    bill_status: BillStatusSchema | None = Query(None, alias="status"),
    vendor_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BillList:
    """List bills for a client with optional filters. Both roles."""
    # Convert schema enum to model enum if present
    model_status = BillStatus(bill_status.value) if bill_status else None
    bills, total = await BillService.list_bills(
        db,
        client_id,
        status_filter=model_status,
        vendor_id=vendor_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return BillList(
        items=[BillResponse.model_validate(b) for b in bills],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
    client_id: UUID,
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BillResponse:
    """Get a single bill by ID with lines and payments. Both roles."""
    bill = await BillService.get_bill(db, client_id, bill_id)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/submit", response_model=BillResponse)
async def submit_bill(
    client_id: UUID,
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BillResponse:
    """Submit a DRAFT bill for approval. Both roles."""
    bill = await BillService.submit_for_approval(db, client_id, bill_id, current_user)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/approve", response_model=BillResponse)
async def approve_bill(
    client_id: UUID,
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> BillResponse:
    """
    Approve a PENDING_APPROVAL bill. CPA_OWNER only.

    Creates a journal entry: debit expense accounts, credit AP.
    """
    bill = await BillService.approve_bill(db, client_id, bill_id, current_user)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/pay", response_model=BillResponse)
async def record_payment(
    client_id: UUID,
    bill_id: UUID,
    data: BillPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BillResponse:
    """Record a payment against an APPROVED bill. Both roles."""
    bill = await BillService.record_payment(db, client_id, bill_id, data, current_user)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    return BillResponse.model_validate(bill)


@router.post("/{bill_id}/void", response_model=BillResponse)
async def void_bill(
    client_id: UUID,
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> BillResponse:
    """Void an APPROVED or PAID bill. CPA_OWNER only."""
    bill = await BillService.void_bill(db, client_id, bill_id, current_user)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )
    return BillResponse.model_validate(bill)
