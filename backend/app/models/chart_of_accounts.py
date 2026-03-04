"""
SQLAlchemy ORM model for the chart_of_accounts table (module F2).

Maps to the existing PostgreSQL table created by 001_initial_schema.sql.
Compliance (CLAUDE.md rule #4): client_id is non-nullable on every row.
Compliance (CLAUDE.md rule #2): soft deletes only via deleted_at.
"""

import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class ChartOfAccounts(Base, TimestampMixin, SoftDeleteMixin):
    """
    Chart of Accounts model.

    Each row is an account belonging to a specific client.
    The (client_id, account_number) pair is unique.
    """

    __tablename__ = "chart_of_accounts"

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
    account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        Enum(
            "ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE",
            name="account_type",
            create_type=False,  # Enum already exists in DB
        ),
        nullable=False,
    )
    sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("client_id", "account_number", name="chart_of_accounts_client_id_account_number_key"),
    )
