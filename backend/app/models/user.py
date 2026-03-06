"""
SQLAlchemy ORM model for the `users` table.

Maps to the existing database table created by migration 001_initial_schema.sql.
Columns: id (UUID), email, password_hash, full_name, role (CPA_OWNER/ASSOCIATE),
is_active, last_login_at, created_at, updated_at, deleted_at.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """ORM model for the users table."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("CPA_OWNER", "ASSOCIATE", name="user_role", create_type=False),
        nullable=False,
        default="ASSOCIATE",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    totp_secret_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
