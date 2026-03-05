"""
SQLAlchemy ORM model for the vendors table (module T1 — Accounts Payable).

Maps to the existing PostgreSQL `vendors` table created by 001_initial_schema.sql.
Compliance (CLAUDE.md rule #4): client_id is non-nullable FK on every row.
Compliance (CLAUDE.md rule #2): Soft deletes only via deleted_at.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, LargeBinary, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Vendor(Base, TimestampMixin, SoftDeleteMixin):
    """
    Vendor record for accounts payable.

    Each vendor belongs to a single client (client isolation).
    Used as a payee on bills.
    """

    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_1099_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False,
    )
