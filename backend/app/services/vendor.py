"""
Business logic for Vendor management (Module T1 — Accounts Payable).

Compliance (CLAUDE.md):
- Rule #2: Soft deletes only — archive sets deleted_at, never hard-deletes.
- Rule #4: Client isolation — every query filters by client_id.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorUpdate


class VendorService:
    """Service layer for vendor CRUD operations."""

    @staticmethod
    async def create_vendor(
        db: AsyncSession,
        client_id: UUID,
        data: VendorCreate,
    ) -> Vendor:
        """
        Create a new vendor for a client.

        Both roles may create vendors.
        """
        vendor = Vendor(
            client_id=client_id,
            name=data.name,
            address=data.address,
            city=data.city,
            state=data.state,
            zip=data.zip,
            phone=data.phone,
            email=str(data.email) if data.email else None,
        )
        db.add(vendor)
        await db.flush()
        await db.refresh(vendor)
        return vendor

    @staticmethod
    async def get_vendor(
        db: AsyncSession,
        client_id: UUID,
        vendor_id: UUID,
    ) -> Vendor | None:
        """
        Retrieve a single vendor by ID, filtered by client_id.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = select(Vendor).where(
            Vendor.id == vendor_id,
            Vendor.client_id == client_id,
            Vendor.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_vendors(
        db: AsyncSession,
        client_id: UUID,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
    ) -> tuple[list[Vendor], int]:
        """
        List vendors for a client with optional name search and pagination.

        Compliance (rule #4): ALWAYS filters by client_id.
        Always excludes soft-deleted records.
        """
        base = select(Vendor).where(
            Vendor.client_id == client_id,
            Vendor.deleted_at.is_(None),
        )

        if search:
            base = base.where(Vendor.name.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Vendor.name).offset(skip).limit(limit)
        result = await db.execute(stmt)
        vendors = list(result.scalars().all())

        return vendors, total

    @staticmethod
    async def update_vendor(
        db: AsyncSession,
        client_id: UUID,
        vendor_id: UUID,
        data: VendorUpdate,
    ) -> Vendor | None:
        """
        Update an existing vendor.

        Compliance (rule #4): ALWAYS filters by client_id.
        Returns None if vendor not found or soft-deleted.
        """
        vendor = await VendorService.get_vendor(db, client_id, vendor_id)
        if vendor is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"])
        for field, value in update_data.items():
            setattr(vendor, field, value)

        await db.flush()
        await db.refresh(vendor)
        return vendor

    @staticmethod
    async def archive_vendor(
        db: AsyncSession,
        client_id: UUID,
        vendor_id: UUID,
    ) -> Vendor | None:
        """
        Soft-delete a vendor by setting deleted_at.

        Compliance (CLAUDE.md rule #2): Records are never hard-deleted.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        vendor = await VendorService.get_vendor(db, client_id, vendor_id)
        if vendor is None:
            return None

        vendor.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(vendor)
        return vendor
