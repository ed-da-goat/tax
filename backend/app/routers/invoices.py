"""
API router for Invoices / Accounts Receivable (module T2).

All endpoints are scoped to a client via /clients/{client_id}/invoices.

Compliance (CLAUDE.md):
- Client isolation: client_id from URL path is used in every query (rule #4).
- Role enforcement: CPA_OWNER required for approve/void (rule #5, #6).
- Soft deletes only: void creates reversing entry (rule #2).
- Invoices do not affect GL until approved and sent.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceList,
    InvoicePaymentCreate,
    InvoiceResponse,
    InvoiceStatus as SchemaStatus,
)
from app.services.invoice import InvoiceService

router = APIRouter()


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new invoice with line items",
)
async def create_invoice(
    client_id: uuid.UUID,
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InvoiceResponse:
    """
    Create a new invoice. Both roles allowed. Status starts as DRAFT.

    Compliance (rule #5): Never auto-post on entry.
    """
    invoice = await InvoiceService.create_invoice(db, client_id, data, user)
    await db.commit()
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "",
    response_model=InvoiceList,
    summary="List invoices for a client",
)
async def list_invoices(
    client_id: uuid.UUID,
    status_filter: SchemaStatus | None = Query(None, alias="status"),
    customer_name: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InvoiceList:
    """List invoices for a client with optional filters. Both roles allowed."""
    model_status = None
    if status_filter is not None:
        model_status = InvoiceStatus(status_filter.value)

    invoices, total = await InvoiceService.list_invoices(
        db, client_id,
        status_filter=model_status,
        customer_name=customer_name,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return InvoiceList(
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get a single invoice with lines and payments",
)
async def get_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InvoiceResponse:
    """Get a specific invoice by ID. Both roles allowed."""
    invoice = await InvoiceService.get_invoice(db, client_id, invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/submit",
    response_model=InvoiceResponse,
    summary="Submit an invoice for approval",
)
async def submit_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InvoiceResponse:
    """Submit a DRAFT invoice for approval. Both roles allowed."""
    invoice = await InvoiceService.submit_for_approval(db, client_id, invoice_id, user)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    await db.commit()
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/approve",
    response_model=InvoiceResponse,
    summary="Approve and send an invoice",
)
async def approve_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    ar_account_id: uuid.UUID = Query(..., description="Accounts Receivable account ID"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> InvoiceResponse:
    """
    Approve and send a PENDING_APPROVAL invoice. CPA_OWNER only.

    Creates journal entry: debit AR, credit revenue accounts.
    Compliance (rule #5): Only CPA_OWNER can approve.
    Compliance (rule #6): Defense in depth — both route and function level.
    """
    # Defense in depth: function-level role check inside service
    invoice = await InvoiceService.approve_and_send(
        db, client_id, invoice_id, user, ar_account_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    await db.commit()
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/pay",
    response_model=InvoiceResponse,
    summary="Record a payment against an invoice",
)
async def record_payment(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    data: InvoicePaymentCreate,
    cash_account_id: uuid.UUID = Query(..., description="Cash account ID"),
    ar_account_id: uuid.UUID = Query(..., description="Accounts Receivable account ID"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InvoiceResponse:
    """
    Record a payment against an invoice. Both roles allowed.

    Creates journal entry: debit cash, credit AR.
    If fully paid, status transitions to PAID.
    """
    invoice = await InvoiceService.record_payment(
        db, client_id, invoice_id, data, user, cash_account_id, ar_account_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    await db.commit()
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/void",
    response_model=InvoiceResponse,
    summary="Void an invoice (creates reversing journal entry)",
)
async def void_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    ar_account_id: uuid.UUID = Query(..., description="Accounts Receivable account ID"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> InvoiceResponse:
    """
    Void a SENT or OVERDUE invoice. CPA_OWNER only.

    Creates reversing journal entry.
    Compliance (rule #2): Never hard delete. Creates reversing entry.
    Compliance (rule #5): Only CPA_OWNER can void.
    Compliance (rule #6): Defense in depth — both route and function level.
    """
    # Defense in depth: function-level role check inside service
    invoice = await InvoiceService.void_invoice(
        db, client_id, invoice_id, user, ar_account_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    await db.commit()
    return InvoiceResponse.model_validate(invoice)
