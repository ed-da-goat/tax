"""
Recurring transactions service (C3).

Manages recurring templates for journal entries and bills.
Auto-generates transactions when their next_date is due.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    RecurringTemplate, RecurringTemplateLine,
    RecurringFrequency, RecurringSourceType, RecurringTemplateStatus,
    JournalEntry, JournalEntryLine, JournalEntryStatus,
    Bill, BillLine, BillStatus,
)


def _advance_date(current: date, frequency: RecurringFrequency) -> date:
    """Compute the next occurrence date based on frequency."""
    if frequency == RecurringFrequency.WEEKLY:
        return current + timedelta(weeks=1)
    elif frequency == RecurringFrequency.BIWEEKLY:
        return current + timedelta(weeks=2)
    elif frequency == RecurringFrequency.MONTHLY:
        return current + relativedelta(months=1)
    elif frequency == RecurringFrequency.QUARTERLY:
        return current + relativedelta(months=3)
    elif frequency == RecurringFrequency.ANNUALLY:
        return current + relativedelta(years=1)
    return current + relativedelta(months=1)


class RecurringService:

    @staticmethod
    async def list_templates(
        db: AsyncSession, client_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """List all recurring templates, optionally filtered by client."""
        q = select(RecurringTemplate).where(RecurringTemplate.deleted_at.is_(None))
        if client_id:
            q = q.where(RecurringTemplate.client_id == client_id)
        q = q.order_by(RecurringTemplate.next_date)
        result = await db.execute(q)
        templates = result.scalars().all()
        return [_template_to_dict(t) for t in templates]

    @staticmethod
    async def get_template(db: AsyncSession, template_id: uuid.UUID) -> dict[str, Any]:
        result = await db.execute(
            select(RecurringTemplate).where(
                RecurringTemplate.id == template_id,
                RecurringTemplate.deleted_at.is_(None),
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("Recurring template not found")
        return _template_to_dict(template)

    @staticmethod
    async def create_template(
        db: AsyncSession,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new recurring template with lines."""
        lines_data = data.pop("lines", [])
        if not lines_data:
            raise ValueError("At least one line is required")

        total = sum(Decimal(str(l.get("debit", 0))) for l in lines_data)

        template = RecurringTemplate(
            client_id=client_id,
            source_type=RecurringSourceType(data["source_type"]),
            description=data["description"],
            frequency=RecurringFrequency(data["frequency"]),
            next_date=date.fromisoformat(data["next_date"]) if isinstance(data["next_date"], str) else data["next_date"],
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") and isinstance(data["end_date"], str) else data.get("end_date"),
            total_amount=total,
            vendor_id=data.get("vendor_id"),
            max_occurrences=data.get("max_occurrences"),
            created_by=user_id,
        )
        db.add(template)
        await db.flush()

        for line in lines_data:
            db.add(RecurringTemplateLine(
                template_id=template.id,
                account_id=uuid.UUID(line["account_id"]) if isinstance(line["account_id"], str) else line["account_id"],
                description=line.get("description"),
                debit=Decimal(str(line.get("debit", 0))),
                credit=Decimal(str(line.get("credit", 0))),
            ))
        await db.flush()

        # Re-fetch to get lines
        result = await db.execute(
            select(RecurringTemplate).where(RecurringTemplate.id == template.id)
        )
        return _template_to_dict(result.scalar_one())

    @staticmethod
    async def update_template(
        db: AsyncSession, template_id: uuid.UUID, data: dict[str, Any],
    ) -> dict[str, Any]:
        result = await db.execute(
            select(RecurringTemplate).where(
                RecurringTemplate.id == template_id,
                RecurringTemplate.deleted_at.is_(None),
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("Recurring template not found")

        for field in ("description", "frequency", "next_date", "end_date", "vendor_id", "max_occurrences", "status"):
            if field in data:
                val = data[field]
                if field == "frequency":
                    val = RecurringFrequency(val)
                elif field == "status":
                    val = RecurringTemplateStatus(val)
                elif field in ("next_date", "end_date") and isinstance(val, str):
                    val = date.fromisoformat(val) if val else None
                setattr(template, field, val)

        await db.flush()
        return _template_to_dict(template)

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: uuid.UUID) -> dict:
        from datetime import datetime, timezone
        result = await db.execute(
            select(RecurringTemplate).where(
                RecurringTemplate.id == template_id,
                RecurringTemplate.deleted_at.is_(None),
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError("Recurring template not found")
        template.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return {"deleted": True, "id": str(template_id)}

    @staticmethod
    async def generate_due(
        db: AsyncSession, as_of: date | None = None, user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Generate transactions for all templates whose next_date <= as_of."""
        if as_of is None:
            as_of = date.today()

        result = await db.execute(
            select(RecurringTemplate).where(and_(
                RecurringTemplate.status == RecurringTemplateStatus.ACTIVE,
                RecurringTemplate.deleted_at.is_(None),
                RecurringTemplate.next_date <= as_of,
            ))
        )
        templates = result.scalars().all()

        generated = []
        for template in templates:
            # Check max occurrences
            if template.max_occurrences and template.occurrences_generated >= template.max_occurrences:
                template.status = RecurringTemplateStatus.EXPIRED
                continue

            # Check end date
            if template.end_date and template.next_date > template.end_date:
                template.status = RecurringTemplateStatus.EXPIRED
                continue

            created_by = user_id or template.created_by

            if template.source_type == RecurringSourceType.JOURNAL_ENTRY:
                entry_id = await _generate_journal_entry(db, template, created_by)
                generated.append({"template_id": str(template.id), "type": "JOURNAL_ENTRY", "entry_id": str(entry_id)})
            elif template.source_type == RecurringSourceType.BILL:
                bill_id = await _generate_bill(db, template, created_by)
                generated.append({"template_id": str(template.id), "type": "BILL", "bill_id": str(bill_id)})

            template.occurrences_generated += 1
            template.last_generated_date = template.next_date
            template.next_date = _advance_date(template.next_date, template.frequency)

            # Check if next occurrence exceeds limits
            if template.end_date and template.next_date > template.end_date:
                template.status = RecurringTemplateStatus.EXPIRED
            if template.max_occurrences and template.occurrences_generated >= template.max_occurrences:
                template.status = RecurringTemplateStatus.EXPIRED

        await db.flush()
        return {"generated": generated, "count": len(generated), "as_of": as_of.isoformat()}


async def _generate_journal_entry(
    db: AsyncSession, template: RecurringTemplate, user_id: uuid.UUID,
) -> uuid.UUID:
    je = JournalEntry(
        client_id=template.client_id,
        entry_date=template.next_date,
        description=f"[Recurring] {template.description}",
        reference_number=f"REC-{template.id.hex[:8]}-{template.occurrences_generated + 1}",
        status=JournalEntryStatus.DRAFT,
        created_by=user_id,
    )
    db.add(je)
    await db.flush()

    for line in template.lines:
        if line.deleted_at:
            continue
        db.add(JournalEntryLine(
            journal_entry_id=je.id,
            account_id=line.account_id,
            debit=line.debit,
            credit=line.credit,
            description=line.description,
        ))
    await db.flush()
    return je.id


async def _generate_bill(
    db: AsyncSession, template: RecurringTemplate, user_id: uuid.UUID,
) -> uuid.UUID:
    bill = Bill(
        client_id=template.client_id,
        vendor_id=template.vendor_id,
        bill_number=f"REC-{template.id.hex[:8]}-{template.occurrences_generated + 1}",
        bill_date=template.next_date,
        due_date=template.next_date + timedelta(days=30),
        total_amount=template.total_amount,
        status=BillStatus.DRAFT,
    )
    db.add(bill)
    await db.flush()

    for line in template.lines:
        if line.deleted_at:
            continue
        db.add(BillLine(
            bill_id=bill.id,
            account_id=line.account_id,
            description=line.description,
            amount=line.debit if line.debit > 0 else line.credit,
        ))
    await db.flush()
    return bill.id


def _template_to_dict(t: RecurringTemplate) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "client_id": str(t.client_id),
        "source_type": t.source_type.value,
        "description": t.description,
        "frequency": t.frequency.value,
        "next_date": t.next_date.isoformat(),
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "total_amount": float(t.total_amount),
        "status": t.status.value,
        "vendor_id": str(t.vendor_id) if t.vendor_id else None,
        "occurrences_generated": t.occurrences_generated,
        "max_occurrences": t.max_occurrences,
        "last_generated_date": t.last_generated_date.isoformat() if t.last_generated_date else None,
        "created_by": str(t.created_by),
        "lines": [
            {
                "id": str(l.id),
                "account_id": str(l.account_id),
                "description": l.description,
                "debit": float(l.debit),
                "credit": float(l.credit),
            }
            for l in t.lines if not l.deleted_at
        ],
    }
