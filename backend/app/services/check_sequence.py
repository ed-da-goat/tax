"""
Atomic check number allocation service.

Uses INSERT ON CONFLICT DO UPDATE RETURNING for atomic check number
increment per client.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — sequences are per-client.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CheckSequenceService:
    """Manages per-client check number sequences."""

    @staticmethod
    async def get_next_check_number(
        db: AsyncSession,
        client_id: uuid.UUID,
    ) -> int:
        """
        Atomically allocate and return the next check number for a client.

        Uses INSERT ON CONFLICT DO UPDATE RETURNING for atomicity.
        Starts at 1001 for new clients.
        """
        stmt = text(
            "INSERT INTO client_check_sequences (client_id, next_check_number) "
            "VALUES (:client_id, 1002) "
            "ON CONFLICT (client_id) DO UPDATE "
            "SET next_check_number = client_check_sequences.next_check_number + 1, "
            "    updated_at = now() "
            "RETURNING next_check_number - 1 AS allocated_number"
        )
        result = await db.execute(stmt, {"client_id": str(client_id)})
        row = result.one()
        return row.allocated_number

    @staticmethod
    async def get_current_sequence(
        db: AsyncSession,
        client_id: uuid.UUID,
    ) -> int:
        """Get the current next check number without allocating."""
        stmt = text(
            "SELECT next_check_number FROM client_check_sequences "
            "WHERE client_id = :client_id"
        )
        result = await db.execute(stmt, {"client_id": str(client_id)})
        row = result.one_or_none()
        if row is None:
            return 1001  # Default starting number
        return row.next_check_number

    @staticmethod
    async def set_next_check_number(
        db: AsyncSession,
        client_id: uuid.UUID,
        next_number: int,
    ) -> int:
        """Set the next check number for a client. Returns the set value."""
        stmt = text(
            "INSERT INTO client_check_sequences (client_id, next_check_number) "
            "VALUES (:client_id, :next_number) "
            "ON CONFLICT (client_id) DO UPDATE "
            "SET next_check_number = :next_number, "
            "    updated_at = now() "
            "RETURNING next_check_number"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "next_number": next_number,
        })
        row = result.one()
        return row.next_check_number
