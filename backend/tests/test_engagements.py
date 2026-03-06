"""
Tests for Engagement Letters & Proposals API endpoints (PM3).

Tests cover:
- Create engagement (any authenticated user)
- List engagements with filters
- Get single engagement
- Update engagement
- Send engagement (CPA_OWNER only)
- Sign engagement (public, no auth)
- Delete engagement (CPA_OWNER only)
- Permission checks (ASSOCIATE gets 403 on send/delete)

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

def _make_engagement(**overrides):
    eng_id = overrides.get("id", uuid.uuid4())
    return MagicMock(
        id=eng_id,
        client_id=overrides.get("client_id", uuid.uuid4()),
        title=overrides.get("title", "2026 Tax Preparation"),
        engagement_type=overrides.get("engagement_type", "TAX_PREPARATION"),
        description=overrides.get("description", "Annual tax preparation services"),
        terms_and_conditions=overrides.get("terms_and_conditions", "Standard terms apply"),
        fee_type=overrides.get("fee_type", "FIXED"),
        fixed_fee=overrides.get("fixed_fee", Decimal("1500.00")),
        hourly_rate=overrides.get("hourly_rate", None),
        estimated_hours=overrides.get("estimated_hours", None),
        retainer_amount=overrides.get("retainer_amount", None),
        start_date=overrides.get("start_date", date(2026, 1, 1)),
        end_date=overrides.get("end_date", date(2026, 12, 31)),
        tax_year=overrides.get("tax_year", 2026),
        status=overrides.get("status", "DRAFT"),
        sent_at=overrides.get("sent_at", None),
        signed_at=overrides.get("signed_at", None),
        signed_by=overrides.get("signed_by", None),
        deleted_at=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Create Engagement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_engagement(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/engagements creates an engagement letter."""
    mock_eng = _make_engagement()
    with patch(
        "app.routers.engagements.EngagementService.create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_eng
        response = await client.post(
            "/api/v1/engagements",
            headers=cpa_owner_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "title": "2026 Tax Preparation",
                "engagement_type": "TAX_PREPARATION",
                "fee_type": "FIXED",
                "fixed_fee": "1500.00",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "tax_year": 2026,
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "2026 Tax Preparation"
    assert data["status"] == "DRAFT"


@pytest.mark.anyio
async def test_create_engagement_associate(client: AsyncClient, associate_headers):
    """POST /api/v1/engagements is accessible to ASSOCIATE (any auth user)."""
    mock_eng = _make_engagement()
    with patch(
        "app.routers.engagements.EngagementService.create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_eng
        response = await client.post(
            "/api/v1/engagements",
            headers=associate_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "title": "2026 Bookkeeping",
                "engagement_type": "BOOKKEEPING",
            },
        )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# List Engagements
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_engagements(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/engagements lists engagement letters."""
    engagements = [_make_engagement() for _ in range(3)]
    with patch(
        "app.routers.engagements.EngagementService.list_engagements",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (engagements, 3)
        response = await client.get("/api/v1/engagements", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.anyio
async def test_list_engagements_with_filters(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/engagements supports client_id and status filters."""
    client_id = uuid.uuid4()
    engagements = [_make_engagement(client_id=client_id, status="SENT")]
    with patch(
        "app.routers.engagements.EngagementService.list_engagements",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (engagements, 1)
        response = await client.get(
            "/api/v1/engagements",
            headers=cpa_owner_headers,
            params={"client_id": str(client_id), "status": "SENT"},
        )
    assert response.status_code == 200
    assert response.json()["total"] == 1


# ---------------------------------------------------------------------------
# Get Engagement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_engagement(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/engagements/{id} returns a single engagement."""
    eng_id = uuid.uuid4()
    mock_eng = _make_engagement(id=eng_id)
    with patch(
        "app.routers.engagements.EngagementService.get",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_eng
        response = await client.get(
            f"/api/v1/engagements/{eng_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(eng_id)


# ---------------------------------------------------------------------------
# Update Engagement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_engagement(client: AsyncClient, cpa_owner_headers):
    """PUT /api/v1/engagements/{id} updates an engagement."""
    eng_id = uuid.uuid4()
    mock_eng = _make_engagement(id=eng_id, title="Updated Title")
    with patch(
        "app.routers.engagements.EngagementService.update",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = mock_eng
        response = await client.put(
            f"/api/v1/engagements/{eng_id}",
            headers=cpa_owner_headers,
            json={"title": "Updated Title"},
        )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


# ---------------------------------------------------------------------------
# Send Engagement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_send_engagement_cpa_owner(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/engagements/{id}/send marks it as sent (CPA_OWNER)."""
    eng_id = uuid.uuid4()
    mock_eng = _make_engagement(
        id=eng_id,
        status="SENT",
        sent_at=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    with patch(
        "app.routers.engagements.EngagementService.send",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = mock_eng
        response = await client.post(
            f"/api/v1/engagements/{eng_id}/send", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["status"] == "SENT"


@pytest.mark.anyio
async def test_send_engagement_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/engagements/{id}/send returns 403 for ASSOCIATE."""
    eng_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/engagements/{eng_id}/send", headers=associate_headers
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Sign Engagement (public)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sign_engagement(client: AsyncClient):
    """POST /api/v1/engagements/{id}/sign signs the engagement (no auth required)."""
    eng_id = uuid.uuid4()
    mock_eng = _make_engagement(
        id=eng_id,
        status="SIGNED",
        signed_at=datetime(2026, 3, 6, tzinfo=timezone.utc),
        signed_by="John Doe",
    )
    with patch(
        "app.routers.engagements.EngagementService.sign",
        new_callable=AsyncMock,
    ) as mock_sign:
        mock_sign.return_value = mock_eng
        response = await client.post(
            f"/api/v1/engagements/{eng_id}/sign",
            json={"signed_by": "John Doe", "signature_data": "base64data"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SIGNED"
    assert data["signed_by"] == "John Doe"


# ---------------------------------------------------------------------------
# Delete Engagement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_engagement_cpa_owner(client: AsyncClient, cpa_owner_headers):
    """DELETE /api/v1/engagements/{id} deletes the engagement (CPA_OWNER)."""
    eng_id = uuid.uuid4()
    with patch(
        "app.routers.engagements.EngagementService.delete",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = None
        response = await client.delete(
            f"/api/v1/engagements/{eng_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 204


@pytest.mark.anyio
async def test_delete_engagement_associate_forbidden(client: AsyncClient, associate_headers):
    """DELETE /api/v1/engagements/{id} returns 403 for ASSOCIATE."""
    eng_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/engagements/{eng_id}", headers=associate_headers
    )
    assert response.status_code == 403
