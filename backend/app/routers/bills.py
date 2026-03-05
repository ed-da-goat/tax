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
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.models.bill import BillStatus
from app.schemas import BaseSchema
from app.schemas.bill import (
    BillCreate,
    BillList,
    BillPaymentCreate,
    BillResponse,
    BillStatus as BillStatusSchema,
)
from app.services.bill import BillService
from app.services.check_printing import CheckData, CheckPrintingService
from app.services.check_sequence import CheckSequenceService

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


# ---------------------------------------------------------------------------
# Check Printing Endpoints
# ---------------------------------------------------------------------------


class CheckSequenceResponse(BaseSchema):
    """Current check sequence for a client."""
    client_id: UUID
    next_check_number: int


class CheckSequenceUpdate(BaseSchema):
    """Set the next check number."""
    next_check_number: int


@router.post(
    "/{bill_id}/payments/{payment_id}/print-check",
    summary="Print check for a bill payment",
    response_class=Response,
)
async def print_check(
    client_id: UUID,
    bill_id: UUID,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """
    Generate a printable check PDF from a bill payment. CPA_OWNER only.

    If the payment already has a check_number, reprints with the same number.
    Otherwise, allocates the next check number atomically.
    """
    verify_role(current_user, "CPA_OWNER")

    bill = await BillService.get_bill(db, client_id, bill_id)
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    payment = next((p for p in bill.payments if p.id == payment_id and p.deleted_at is None), None)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    # Reprint existing or allocate new check number
    if payment.check_number is not None:
        check_num = payment.check_number
    else:
        check_num = await CheckSequenceService.get_next_check_number(db, client_id)
        payment.check_number = check_num
        await db.commit()

    # Get client and vendor info for the check
    from sqlalchemy import text as sql_text
    client_result = await db.execute(
        sql_text("SELECT name, address, city, state, zip FROM clients WHERE id = :cid"),
        {"cid": str(client_id)},
    )
    client_row = client_result.one()
    addr_parts = [p for p in [client_row.address, client_row.city, client_row.state, client_row.zip] if p]

    vendor_result = await db.execute(
        sql_text("SELECT name FROM vendors WHERE id = :vid"),
        {"vid": str(bill.vendor_id)},
    )
    vendor_row = vendor_result.one()

    check_data = CheckData(
        payer_name=client_row.name,
        payer_address=", ".join(addr_parts) if addr_parts else None,
        payee_name=vendor_row.name,
        check_number=check_num,
        check_date=payment.payment_date,
        amount=payment.amount,
        memo=f"Bill #{bill.bill_number}" if bill.bill_number else None,
    )

    pdf_bytes = CheckPrintingService.generate_check_pdf(check_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=check_{check_num}.pdf"},
    )
