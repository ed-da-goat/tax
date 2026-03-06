"""
Tests for Fixed Asset management endpoints (AN3).

Covers:
- POST   /api/v1/clients/{cid}/fixed-assets          — create asset
- GET    /api/v1/clients/{cid}/fixed-assets           — list assets
- GET    /api/v1/clients/{cid}/fixed-assets/{id}      — get asset
- POST   /api/v1/clients/{cid}/fixed-assets/{id}/dispose — dispose asset (CPA_OWNER only)
- GET    /api/v1/clients/{cid}/fixed-assets/summary/{year} — depreciation summary
- Permission checks
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CPA_OWNER_ID = uuid.uuid4()
ASSOCIATE_ID = uuid.uuid4()
CLIENT_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _override_as_associate():
    async def _dep():
        return CurrentUser(user_id=str(ASSOCIATE_ID), role="ASSOCIATE")
    return _dep


def _make_asset(asset_id=None, **overrides):
    """Build namespace matching FixedAssetResponse schema."""
    return SimpleNamespace(
        id=asset_id or uuid.uuid4(),
        client_id=overrides.get("client_id", CLIENT_ID),
        asset_name=overrides.get("asset_name", "Office Desk"),
        asset_number=overrides.get("asset_number", "FA-001"),
        description=overrides.get("description", "Standing desk"),
        category=overrides.get("category", "FURNITURE"),
        acquisition_date=overrides.get("acquisition_date", date(2025, 6, 1)),
        acquisition_cost=overrides.get("acquisition_cost", Decimal("1500.00")),
        depreciation_method=overrides.get("depreciation_method", "MACRS_GDS"),
        useful_life_years=overrides.get("useful_life_years", 7),
        salvage_value=overrides.get("salvage_value", Decimal("100.00")),
        macrs_class=overrides.get("macrs_class", "7"),
        bonus_depreciation_pct=overrides.get("bonus_depreciation_pct", Decimal("0")),
        section_179_amount=overrides.get("section_179_amount", Decimal("0")),
        accumulated_depreciation=overrides.get("accumulated_depreciation", Decimal("0.00")),
        book_value=overrides.get("book_value", Decimal("1500.00")),
        status=overrides.get("status", "ACTIVE"),
        disposal_date=overrides.get("disposal_date", None),
        disposal_amount=overrides.get("disposal_amount", None),
        disposal_method=overrides.get("disposal_method", None),
        gain_loss=overrides.get("gain_loss", None),
        location=overrides.get("location", None),
        serial_number=overrides.get("serial_number", None),
        depreciation_schedule=overrides.get("depreciation_schedule", []),
        deleted_at=overrides.get("deleted_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: Create Asset
# ---------------------------------------------------------------------------


class TestCreateAsset:

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_create_asset_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            asset = _make_asset()
            mock_svc.create_asset = AsyncMock(return_value=asset)

            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets?client_id={CLIENT_ID}",
                json={
                    "asset_name": "Office Desk",
                    "acquisition_date": "2025-06-01",
                    "acquisition_cost": 1500.00,
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["asset_name"] == "Office Desk"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_associate_can_create_asset(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            asset = _make_asset()
            mock_svc.create_asset = AsyncMock(return_value=asset)

            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets?client_id={CLIENT_ID}",
                json={
                    "asset_name": "Office Desk",
                    "acquisition_date": "2025-06-01",
                    "acquisition_cost": 1500.00,
                },
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: List Assets
# ---------------------------------------------------------------------------


class TestListAssets:

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_list_assets(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            a1 = _make_asset(asset_name="Desk")
            a2 = _make_asset(asset_name="Computer")
            mock_svc.list_assets = AsyncMock(return_value=([a1, a2], 2))

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets?client_id={CLIENT_ID}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_list_assets_with_status_filter(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_assets = AsyncMock(return_value=([], 0))

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets?client_id={CLIENT_ID}&status=DISPOSED"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Get Asset
# ---------------------------------------------------------------------------


class TestGetAsset:

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_get_asset(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            asset_id = uuid.uuid4()
            asset = _make_asset(asset_id=asset_id)
            mock_svc.get_asset = AsyncMock(return_value=asset)

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets/{asset_id}?client_id={CLIENT_ID}"
            )
            assert response.status_code == 200
            assert response.json()["id"] == str(asset_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Dispose Asset (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestDisposeAsset:

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_dispose_asset_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            asset_id = uuid.uuid4()
            asset = _make_asset(
                asset_id=asset_id,
                status="DISPOSED",
                disposal_date=date(2026, 3, 1),
                disposal_amount=Decimal("500.00"),
                disposal_method="SOLD",
                gain_loss=Decimal("-100.00"),
            )
            mock_svc.dispose_asset = AsyncMock(return_value=asset)

            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets/{asset_id}/dispose?client_id={CLIENT_ID}",
                json={
                    "disposal_date": "2026-03-01",
                    "disposal_amount": 500.00,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "DISPOSED"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_dispose_asset(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            asset_id = uuid.uuid4()
            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets/{asset_id}/dispose?client_id={CLIENT_ID}",
                json={
                    "disposal_date": "2026-03-01",
                    "disposal_amount": 500.00,
                },
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Depreciation Summary
# ---------------------------------------------------------------------------


class TestDepreciationSummary:

    @patch("app.routers.fixed_assets.FixedAssetService")
    async def test_depreciation_summary(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.depreciation_summary = AsyncMock(return_value={
                "client_id": str(CLIENT_ID),
                "fiscal_year": 2026,
                "total_assets": 5,
                "total_cost": Decimal("15000.00"),
                "total_accumulated_depreciation": Decimal("2000.00"),
                "total_book_value": Decimal("13000.00"),
                "current_year_depreciation": Decimal("1500.00"),
            })

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/fixed-assets/summary/2026?client_id={CLIENT_ID}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["fiscal_year"] == 2026
            assert data["total_assets"] == 5
        finally:
            app.dependency_overrides.pop(get_current_user, None)
