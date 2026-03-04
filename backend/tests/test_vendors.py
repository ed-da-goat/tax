"""
Tests for Vendor management (module T1 — Accounts Payable).

Compliance tests:
- CLIENT ISOLATION (rule #4): Vendor queries scoped by client_id
- AUDIT TRAIL (rule #2): Soft deletes only via deleted_at
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.vendor import VendorService
from app.schemas.vendor import VendorCreate, VendorUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_test_client(db: AsyncSession, client_id: uuid.UUID | None = None) -> uuid.UUID:
    """Insert a minimal client row and return its UUID."""
    cid = client_id or uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, 'SOLE_PROP', true)"
        ),
        {"id": str(cid), "name": f"Test Client {cid}"},
    )
    await db.flush()
    return cid


# ---------------------------------------------------------------------------
# Vendor CRUD tests
# ---------------------------------------------------------------------------


class TestVendorCRUD:
    """Test basic vendor CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_vendor(self, db_session: AsyncSession) -> None:
        """Create a vendor and verify all fields are stored."""
        client_id = await _create_test_client(db_session)
        data = VendorCreate(
            name="Office Supplies Inc",
            address="123 Main St",
            city="Atlanta",
            state="GA",
            zip="30301",
            phone="404-555-0100",
            email="orders@officesupplies.com",
        )
        vendor = await VendorService.create_vendor(db_session, client_id, data)

        assert vendor.id is not None
        assert vendor.client_id == client_id
        assert vendor.name == "Office Supplies Inc"
        assert vendor.city == "Atlanta"
        assert vendor.state == "GA"
        assert vendor.email == "orders@officesupplies.com"
        assert vendor.deleted_at is None

    @pytest.mark.asyncio
    async def test_get_vendor(self, db_session: AsyncSession) -> None:
        """Retrieve a vendor by ID."""
        client_id = await _create_test_client(db_session)
        data = VendorCreate(name="Test Vendor")
        vendor = await VendorService.create_vendor(db_session, client_id, data)

        fetched = await VendorService.get_vendor(db_session, client_id, vendor.id)
        assert fetched is not None
        assert fetched.id == vendor.id
        assert fetched.name == "Test Vendor"

    @pytest.mark.asyncio
    async def test_get_vendor_not_found(self, db_session: AsyncSession) -> None:
        """get_vendor returns None for a non-existent vendor."""
        client_id = await _create_test_client(db_session)
        result = await VendorService.get_vendor(db_session, client_id, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_vendors(self, db_session: AsyncSession) -> None:
        """List vendors for a client with pagination."""
        client_id = await _create_test_client(db_session)
        for i in range(3):
            await VendorService.create_vendor(
                db_session, client_id, VendorCreate(name=f"Vendor {i}")
            )

        vendors, total = await VendorService.list_vendors(db_session, client_id)
        assert total == 3
        assert len(vendors) == 3

    @pytest.mark.asyncio
    async def test_list_vendors_search(self, db_session: AsyncSession) -> None:
        """Search vendors by name."""
        client_id = await _create_test_client(db_session)
        await VendorService.create_vendor(
            db_session, client_id, VendorCreate(name="Alpha Corp")
        )
        await VendorService.create_vendor(
            db_session, client_id, VendorCreate(name="Beta LLC")
        )

        vendors, total = await VendorService.list_vendors(
            db_session, client_id, search="Alpha"
        )
        assert total == 1
        assert vendors[0].name == "Alpha Corp"

    @pytest.mark.asyncio
    async def test_update_vendor(self, db_session: AsyncSession) -> None:
        """Update a vendor's fields."""
        client_id = await _create_test_client(db_session)
        vendor = await VendorService.create_vendor(
            db_session, client_id, VendorCreate(name="Old Name")
        )
        updated = await VendorService.update_vendor(
            db_session, client_id, vendor.id, VendorUpdate(name="New Name")
        )
        assert updated is not None
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_vendor_not_found(self, db_session: AsyncSession) -> None:
        """update_vendor returns None for a non-existent vendor."""
        client_id = await _create_test_client(db_session)
        result = await VendorService.update_vendor(
            db_session, client_id, uuid.uuid4(), VendorUpdate(name="Nope")
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_archive_vendor(self, db_session: AsyncSession) -> None:
        """Soft-delete a vendor by setting deleted_at."""
        client_id = await _create_test_client(db_session)
        vendor = await VendorService.create_vendor(
            db_session, client_id, VendorCreate(name="To Archive")
        )
        archived = await VendorService.archive_vendor(db_session, client_id, vendor.id)
        assert archived is not None
        assert archived.deleted_at is not None

        # Should not appear in get or list
        assert await VendorService.get_vendor(db_session, client_id, vendor.id) is None
        vendors, total = await VendorService.list_vendors(db_session, client_id)
        assert total == 0


class TestVendorClientIsolation:
    """Test that vendor queries enforce client_id isolation."""

    @pytest.mark.asyncio
    async def test_vendor_client_isolation(self, db_session: AsyncSession) -> None:
        """Client A's vendor must not be visible via Client B's client_id."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        vendor = await VendorService.create_vendor(
            db_session, client_a, VendorCreate(name="Client A Vendor")
        )

        # Client B cannot see Client A's vendor
        assert await VendorService.get_vendor(db_session, client_b, vendor.id) is None

        vendors_b, total_b = await VendorService.list_vendors(db_session, client_b)
        assert total_b == 0

    @pytest.mark.asyncio
    async def test_vendor_update_client_isolation(self, db_session: AsyncSession) -> None:
        """Cannot update a vendor using a different client's client_id."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        vendor = await VendorService.create_vendor(
            db_session, client_a, VendorCreate(name="Original")
        )
        result = await VendorService.update_vendor(
            db_session, client_b, vendor.id, VendorUpdate(name="Hacked")
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_vendor_archive_client_isolation(self, db_session: AsyncSession) -> None:
        """Cannot archive a vendor using a different client's client_id."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        vendor = await VendorService.create_vendor(
            db_session, client_a, VendorCreate(name="Safe Vendor")
        )
        result = await VendorService.archive_vendor(db_session, client_b, vendor.id)
        assert result is None

        # Vendor still exists for client_a
        assert await VendorService.get_vendor(db_session, client_a, vendor.id) is not None
