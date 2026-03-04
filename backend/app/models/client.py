"""
SQLAlchemy ORM model for the clients table.

Maps to the existing `clients` table in the database.
Entity types: SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC.

Compliance (CLAUDE.md rule #4 — CLIENT ISOLATION):
    Every table that holds client data must have client_id as a
    non-nullable FK. The clients table itself is the root; downstream
    tables reference clients.id.

Compliance (CLAUDE.md rule #2 — AUDIT TRAIL):
    Soft deletes only via deleted_at. Never hard-delete.
"""

import enum

from sqlalchemy import Boolean, Enum, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class EntityType(str, enum.Enum):
    """Georgia CPA firm client entity types."""

    SOLE_PROP = "SOLE_PROP"
    S_CORP = "S_CORP"
    C_CORP = "C_CORP"
    PARTNERSHIP_LLC = "PARTNERSHIP_LLC"


class Client(Base, TimestampMixin, SoftDeleteMixin):
    """
    Client record for the CPA firm.

    Each client is an isolated accounting entity. All financial data
    (GL, AP, AR, payroll) references a client via client_id FK.
    """

    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type_enum", create_type=False),
        nullable=False,
    )
    tax_id_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(2), default="GA", server_default="GA")
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
