"""
Service billing API endpoints (PM2).

Endpoints:
    POST   /api/v1/service-invoices                       — Create invoice
    POST   /api/v1/service-invoices/from-time             — Create from time entries
    GET    /api/v1/service-invoices                       — List invoices
    GET    /api/v1/service-invoices/{id}                  — Get invoice
    POST   /api/v1/service-invoices/{id}/send             — Send invoice
    POST   /api/v1/service-invoices/{id}/payments         — Record payment
    POST   /api/v1/service-invoices/{id}/void             — Void invoice
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.service_invoice import (
    ServiceInvoiceCreate, ServiceInvoiceResponse, ServiceInvoiceList,
    ServiceInvoicePaymentCreate,
)
from app.services.service_billing import ServiceBillingService

router = APIRouter()


@router.post("", response_model=ServiceInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: ServiceInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    invoice = await ServiceBillingService.create_invoice(db, data, current_user)
    return ServiceInvoiceResponse.model_validate(invoice)


@router.post("/from-time", response_model=ServiceInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_from_time(
    client_id: UUID,
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    invoice = await ServiceBillingService.create_invoice_from_time(
        db, client_id, date_from, date_to, current_user
    )
    return ServiceInvoiceResponse.model_validate(invoice)


@router.get("", response_model=ServiceInvoiceList)
async def list_invoices(
    client_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await ServiceBillingService.list_invoices(
        db, client_id, status_filter, skip, limit
    )
    return ServiceInvoiceList(
        items=[ServiceInvoiceResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{invoice_id}", response_model=ServiceInvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    invoice = await ServiceBillingService.get_invoice(db, invoice_id)
    return ServiceInvoiceResponse.model_validate(invoice)


@router.post("/{invoice_id}/send", response_model=ServiceInvoiceResponse)
async def send_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    invoice = await ServiceBillingService.send_invoice(db, invoice_id, current_user)
    return ServiceInvoiceResponse.model_validate(invoice)


@router.post("/{invoice_id}/payments", response_model=ServiceInvoiceResponse)
async def record_payment(
    invoice_id: UUID,
    data: ServiceInvoicePaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    invoice = await ServiceBillingService.record_payment(db, invoice_id, data, current_user)
    return ServiceInvoiceResponse.model_validate(invoice)


@router.post("/{invoice_id}/void", response_model=ServiceInvoiceResponse)
async def void_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    invoice = await ServiceBillingService.void_invoice(db, invoice_id, current_user)
    return ServiceInvoiceResponse.model_validate(invoice)
