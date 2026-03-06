"""
Soft delete restoration service (E5).

Provides restore endpoints that clear deleted_at on archived records.
CPA_OWNER only, audit-logged via existing triggers.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, Vendor, Employee, Bill, Invoice


# Map of restorable entity types to their ORM models
RESTORABLE_MODELS = {
    "client": Client,
    "vendor": Vendor,
    "employee": Employee,
    "bill": Bill,
    "invoice": Invoice,
}


class RestoreService:

    @staticmethod
    async def list_archived(
        db: AsyncSession,
        entity_type: str,
        client_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List soft-deleted records of a given entity type."""
        model = RESTORABLE_MODELS.get(entity_type)
        if not model:
            raise ValueError(f"Unknown entity type: {entity_type}")

        q = select(model).where(model.deleted_at.isnot(None))

        if client_id and hasattr(model, "client_id"):
            q = q.where(model.client_id == client_id)

        q = q.order_by(model.deleted_at.desc()).limit(limit)
        result = await db.execute(q)
        records = result.scalars().all()

        return [_record_to_dict(r, entity_type) for r in records]

    @staticmethod
    async def restore(
        db: AsyncSession,
        entity_type: str,
        record_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Restore a soft-deleted record by clearing its deleted_at."""
        model = RESTORABLE_MODELS.get(entity_type)
        if not model:
            raise ValueError(f"Unknown entity type: {entity_type}")

        result = await db.execute(
            select(model).where(model.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError(f"{entity_type} not found")
        if record.deleted_at is None:
            raise ValueError(f"{entity_type} is not archived")

        record.deleted_at = None
        await db.flush()

        return _record_to_dict(record, entity_type)


def _record_to_dict(record, entity_type: str) -> dict[str, Any]:
    """Convert a record to a dict with common fields."""
    d = {
        "id": str(record.id),
        "type": entity_type,
        "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
    }
    if hasattr(record, "name"):
        d["name"] = record.name
    if hasattr(record, "client_id"):
        d["client_id"] = str(record.client_id)
    if hasattr(record, "email"):
        d["email"] = record.email
    if hasattr(record, "first_name") and hasattr(record, "last_name"):
        d["name"] = f"{record.first_name} {record.last_name}"
    if hasattr(record, "bill_number"):
        d["name"] = f"Bill #{record.bill_number}"
    if hasattr(record, "invoice_number"):
        d["name"] = f"Invoice #{record.invoice_number}"
    if hasattr(record, "status"):
        d["status"] = record.status.value if hasattr(record.status, 'value') else str(record.status)
    return d
