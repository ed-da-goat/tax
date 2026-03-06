"""
Tests for Service Billing API endpoints (PM2).

Tests cover:
- Create invoice (CPA_OWNER only)
- Create invoice from time entries (CPA_OWNER only)
- List invoices (any authenticated user)
- Get single invoice (any authenticated user)
- Send invoice (CPA_OWNER only)
- Record payment (CPA_OWNER only)
- Void invoice (CPA_OWNER only)
- Permission checks (ASSOCIATE gets 403 on mutations)

Uses mock DB and patched service layer.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_invoice_line(**overrides):
    return MagicMock(
        id=overrides.get("id", uuid.uuid4()),
        invoice_id=overrides.get("invoice_id", uuid.uuid4()),
        description=overrides.get("description", "Tax preparation service"),
        quantity=overrides.get("quantity", Decimal("1")),
        unit_price=overrides.get("unit_price", Decimal("500.00")),
        amount=overrides.get("amount", Decimal("500.00")),
        service_type=overrides.get("service_type", "Tax Prep"),
        time_entry_id=overrides.get("time_entry_id", None),
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


def _make_invoice(**overrides):
    inv_id = overrides.get("id", uuid.uuid4())
    return MagicMock(
        id=inv_id,
        client_id=overrides.get("client_id", uuid.uuid4()),
        invoice_number=overrides.get("invoice_number", "SI-0001"),
        invoice_date=overrides.get("invoice_date", date(2026, 3, 1)),
        due_date=overrides.get("due_date", date(2026, 4, 1)),
        subtotal=overrides.get("subtotal", Decimal("500.00")),
        discount_amount=overrides.get("discount_amount", Decimal("0")),
        tax_amount=overrides.get("tax_amount", Decimal("0")),
        total_amount=overrides.get("total_amount", Decimal("500.00")),
        amount_paid=overrides.get("amount_paid", Decimal("0")),
        balance_due=overrides.get("balance_due", Decimal("500.00")),
        status=overrides.get("status", "DRAFT"),
        notes=overrides.get("notes", None),
        terms=overrides.get("terms", None),
        is_recurring=overrides.get("is_recurring", False),
        recurrence_interval=overrides.get("recurrence_interval", None),
        engagement_id=overrides.get("engagement_id", None),
        sent_at=overrides.get("sent_at", None),
        viewed_at=overrides.get("viewed_at", None),
        lines=overrides.get("lines", [_make_invoice_line(invoice_id=inv_id)]),
        payments=overrides.get("payments", []),
        deleted_at=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Create Invoice
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_invoice_cpa_owner(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/service-invoices creates an invoice (CPA_OWNER)."""
    mock_inv = _make_invoice()
    with patch(
        "app.routers.service_billing.ServiceBillingService.create_invoice",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_inv
        response = await client.post(
            "/api/v1/service-invoices",
            headers=cpa_owner_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "invoice_date": "2026-03-01",
                "due_date": "2026-04-01",
                "lines": [
                    {
                        "description": "Tax preparation",
                        "quantity": "1",
                        "unit_price": "500.00",
                    }
                ],
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"] == "SI-0001"
    assert data["status"] == "DRAFT"


@pytest.mark.anyio
async def test_create_invoice_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/service-invoices returns 403 for ASSOCIATE."""
    response = await client.post(
        "/api/v1/service-invoices",
        headers=associate_headers,
        json={
            "client_id": str(uuid.uuid4()),
            "invoice_date": "2026-03-01",
            "due_date": "2026-04-01",
            "lines": [{"description": "Service", "quantity": "1", "unit_price": "100.00"}],
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Create from Time Entries
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_from_time_entries(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/service-invoices/from-time creates invoice from time entries."""
    mock_inv = _make_invoice()
    with patch(
        "app.routers.service_billing.ServiceBillingService.create_invoice_from_time",
        new_callable=AsyncMock,
    ) as mock_from_time:
        mock_from_time.return_value = mock_inv
        response = await client.post(
            "/api/v1/service-invoices/from-time",
            headers=cpa_owner_headers,
            params={
                "client_id": str(uuid.uuid4()),
                "date_from": "2026-02-01",
                "date_to": "2026-02-28",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"


@pytest.mark.anyio
async def test_create_from_time_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/service-invoices/from-time returns 403 for ASSOCIATE."""
    response = await client.post(
        "/api/v1/service-invoices/from-time",
        headers=associate_headers,
        params={
            "client_id": str(uuid.uuid4()),
            "date_from": "2026-02-01",
            "date_to": "2026-02-28",
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_invoices(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/service-invoices lists invoices."""
    invoices = [_make_invoice() for _ in range(2)]
    with patch(
        "app.routers.service_billing.ServiceBillingService.list_invoices",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (invoices, 2)
        response = await client.get(
            "/api/v1/service-invoices", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.anyio
async def test_list_invoices_with_filters(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/service-invoices supports client_id and status filters."""
    client_id = uuid.uuid4()
    invoices = [_make_invoice(client_id=client_id, status="SENT")]
    with patch(
        "app.routers.service_billing.ServiceBillingService.list_invoices",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (invoices, 1)
        response = await client.get(
            "/api/v1/service-invoices",
            headers=cpa_owner_headers,
            params={"client_id": str(client_id), "status": "SENT"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.anyio
async def test_get_invoice(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/service-invoices/{id} returns a single invoice."""
    inv_id = uuid.uuid4()
    mock_inv = _make_invoice(id=inv_id)
    with patch(
        "app.routers.service_billing.ServiceBillingService.get_invoice",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_inv
        response = await client.get(
            f"/api/v1/service-invoices/{inv_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(inv_id)


# ---------------------------------------------------------------------------
# Send Invoice
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_send_invoice(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/service-invoices/{id}/send marks invoice as sent."""
    inv_id = uuid.uuid4()
    mock_inv = _make_invoice(
        id=inv_id,
        status="SENT",
        sent_at=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    with patch(
        "app.routers.service_billing.ServiceBillingService.send_invoice",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = mock_inv
        response = await client.post(
            f"/api/v1/service-invoices/{inv_id}/send", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["status"] == "SENT"


@pytest.mark.anyio
async def test_send_invoice_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/service-invoices/{id}/send returns 403 for ASSOCIATE."""
    inv_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/service-invoices/{inv_id}/send", headers=associate_headers
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Record Payment
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_record_payment(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/service-invoices/{id}/payments records a payment."""
    inv_id = uuid.uuid4()
    mock_inv = _make_invoice(
        id=inv_id,
        status="PAID",
        amount_paid=Decimal("500.00"),
        balance_due=Decimal("0"),
    )
    with patch(
        "app.routers.service_billing.ServiceBillingService.record_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = mock_inv
        response = await client.post(
            f"/api/v1/service-invoices/{inv_id}/payments",
            headers=cpa_owner_headers,
            json={
                "payment_date": "2026-03-15",
                "amount": "500.00",
                "payment_method": "CHECK",
                "reference_number": "CHK-001",
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "PAID"


@pytest.mark.anyio
async def test_record_payment_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/service-invoices/{id}/payments returns 403 for ASSOCIATE."""
    inv_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/service-invoices/{inv_id}/payments",
        headers=associate_headers,
        json={
            "payment_date": "2026-03-15",
            "amount": "100.00",
            "payment_method": "CHECK",
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Void Invoice
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_void_invoice(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/service-invoices/{id}/void voids an invoice."""
    inv_id = uuid.uuid4()
    mock_inv = _make_invoice(id=inv_id, status="VOID")
    with patch(
        "app.routers.service_billing.ServiceBillingService.void_invoice",
        new_callable=AsyncMock,
    ) as mock_void:
        mock_void.return_value = mock_inv
        response = await client.post(
            f"/api/v1/service-invoices/{inv_id}/void", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["status"] == "VOID"


@pytest.mark.anyio
async def test_void_invoice_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/service-invoices/{id}/void returns 403 for ASSOCIATE."""
    inv_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/service-invoices/{inv_id}/void", headers=associate_headers
    )
    assert response.status_code == 403
