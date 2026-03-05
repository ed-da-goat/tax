"""
SQLAlchemy ORM model for client_check_sequences table.

Tracks the next check number for each client. Used by the check
printing feature to auto-increment check numbers atomically.

Compliance (CLAUDE.md rule #4): client_id is non-nullable FK.
Compliance (CLAUDE.md rule #2): Audit trigger on table.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ClientCheckSequence(Base, TimestampMixin):
    __tablename__ = "client_check_sequences"

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
        unique=True,
    )
    next_check_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1001, server_default=text("1001"),
    )
