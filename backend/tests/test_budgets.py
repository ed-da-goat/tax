"""
Tests for Budget management endpoints (AN2).

Covers:
- POST   /api/v1/clients/{cid}/budgets          — create budget
- GET    /api/v1/clients/{cid}/budgets           — list budgets
- GET    /api/v1/clients/{cid}/budgets/{id}      — get budget
- DELETE /api/v1/clients/{cid}/budgets/{id}      — delete budget (CPA_OWNER only)
- GET    /api/v1/clients/{cid}/budgets/{id}/vs-actual — budget vs actual report
- Permission checks
"""

import uuid
from datetime import datetime, timezone
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


def _make_budget(budget_id=None, **overrides):
    """Build namespace matching BudgetResponse schema."""
    return SimpleNamespace(
        id=budget_id or uuid.uuid4(),
        client_id=overrides.get("client_id", CLIENT_ID),
        name=overrides.get("name", "FY2026 Operating Budget"),
        fiscal_year=overrides.get("fiscal_year", 2026),
        description=overrides.get("description", None),
        is_active=overrides.get("is_active", True),
        lines=overrides.get("lines", []),
        deleted_at=overrides.get("deleted_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: Create Budget
# ---------------------------------------------------------------------------


class TestCreateBudget:

    @patch("app.routers.budgets.BudgetService")
    async def test_create_budget_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            budget = _make_budget()
            mock_svc.create_budget = AsyncMock(return_value=budget)

            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/budgets?client_id={CLIENT_ID}",
                json={
                    "name": "FY2026 Operating Budget",
                    "fiscal_year": 2026,
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "FY2026 Operating Budget"
            assert data["fiscal_year"] == 2026
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.budgets.BudgetService")
    async def test_associate_can_create_budget(self, mock_svc, client: AsyncClient):
        """Associates can create budgets (draft data entry)."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            budget = _make_budget()
            mock_svc.create_budget = AsyncMock(return_value=budget)

            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/budgets?client_id={CLIENT_ID}",
                json={
                    "name": "FY2026 Operating Budget",
                    "fiscal_year": 2026,
                },
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: List Budgets
# ---------------------------------------------------------------------------


class TestListBudgets:

    @patch("app.routers.budgets.BudgetService")
    async def test_list_budgets(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            b1 = _make_budget(name="FY2025", fiscal_year=2025)
            b2 = _make_budget(name="FY2026")
            mock_svc.list_budgets = AsyncMock(return_value=([b1, b2], 2))

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/budgets?client_id={CLIENT_ID}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.budgets.BudgetService")
    async def test_list_budgets_filter_by_year(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            b = _make_budget(fiscal_year=2026)
            mock_svc.list_budgets = AsyncMock(return_value=([b], 1))

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/budgets?client_id={CLIENT_ID}&fiscal_year=2026"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Get Budget
# ---------------------------------------------------------------------------


class TestGetBudget:

    @patch("app.routers.budgets.BudgetService")
    async def test_get_budget(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            budget_id = uuid.uuid4()
            budget = _make_budget(budget_id=budget_id)
            mock_svc.get_budget = AsyncMock(return_value=budget)

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/budgets/{budget_id}?client_id={CLIENT_ID}"
            )
            assert response.status_code == 200
            assert response.json()["id"] == str(budget_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Delete Budget (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestDeleteBudget:

    @patch("app.routers.budgets.BudgetService")
    async def test_cpa_owner_can_delete(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.delete_budget = AsyncMock(return_value=None)

            budget_id = uuid.uuid4()
            response = await client.delete(
                f"/api/v1/clients/{CLIENT_ID}/budgets/{budget_id}?client_id={CLIENT_ID}"
            )
            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_delete(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            budget_id = uuid.uuid4()
            response = await client.delete(
                f"/api/v1/clients/{CLIENT_ID}/budgets/{budget_id}?client_id={CLIENT_ID}"
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Budget vs Actual
# ---------------------------------------------------------------------------


class TestBudgetVsActual:

    @patch("app.routers.budgets.BudgetService")
    async def test_budget_vs_actual(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            report = SimpleNamespace(
                client_id=CLIENT_ID,
                budget_name="FY2026",
                fiscal_year=2026,
                period_start="January",
                period_end="December",
                lines=[],
                total_budget=Decimal("120000.00"),
                total_actual=Decimal("95000.00"),
                total_variance=Decimal("25000.00"),
            )
            mock_svc.budget_vs_actual = AsyncMock(return_value=report)

            budget_id = uuid.uuid4()
            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/budgets/{budget_id}/vs-actual?client_id={CLIENT_ID}"
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.budgets.BudgetService")
    async def test_budget_vs_actual_with_month_range(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            report = SimpleNamespace(
                client_id=CLIENT_ID,
                budget_name="FY2026",
                fiscal_year=2026,
                period_start="January",
                period_end="March",
                lines=[],
                total_budget=Decimal("30000.00"),
                total_actual=Decimal("28000.00"),
                total_variance=Decimal("2000.00"),
            )
            mock_svc.budget_vs_actual = AsyncMock(return_value=report)

            budget_id = uuid.uuid4()
            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/budgets/{budget_id}/vs-actual"
                f"?client_id={CLIENT_ID}&month_start=1&month_end=3"
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)
