"""
Business logic for Client management (Module F4).

Compliance (CLAUDE.md):
- Rule #2: Soft deletes only — archive sets deleted_at, never hard-deletes.
- Rule #4: Client isolation — every query filters by the requested client_id.
- Role checks: create/update/archive require CPA_OWNER at the function level
  (defense in depth, per CLAUDE.md rule #6 pattern).

All queries filter `deleted_at IS NULL` by default.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.crypto import encrypt_pii
from app.models.client import Client, EntityType
from app.schemas.client import ClientCreate, ClientUpdate


class ClientService:
    """Service layer for client CRUD operations."""

    @staticmethod
    async def create_client(
        db: AsyncSession,
        data: ClientCreate,
        current_user: CurrentUser,
    ) -> Client:
        """
        Create a new client record.

        Requires CPA_OWNER role (function-level check, defense in depth).
        """
        verify_role(current_user, "CPA_OWNER")

        client = Client(
            name=data.name,
            entity_type=EntityType(data.entity_type.value),
            tax_id_encrypted=encrypt_pii(data.tax_id),
            address=data.address,
            city=data.city,
            state=data.state,
            zip=data.zip,
            phone=data.phone,
            email=data.email,
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)
        return client

    @staticmethod
    async def get_client(
        db: AsyncSession,
        client_id: UUID,
    ) -> Client | None:
        """
        Retrieve a single client by ID.

        Returns None if not found or soft-deleted.
        Both roles may call this.
        """
        stmt = select(Client).where(
            Client.id == client_id,
            Client.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_clients(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        entity_type: EntityType | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Client], int]:
        """
        List clients with optional filters, pagination.

        Always excludes soft-deleted records.
        Both roles may call this.

        Returns (list_of_clients, total_count).
        """
        base = select(Client).where(Client.deleted_at.is_(None))

        if entity_type is not None:
            base = base.where(Client.entity_type == entity_type)
        if is_active is not None:
            base = base.where(Client.is_active == is_active)
        if search:
            pattern = f"%{search}%"
            base = base.where(
                or_(
                    Client.name.ilike(pattern),
                    Client.email.ilike(pattern),
                )
            )

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated results
        stmt = base.order_by(Client.name).offset(skip).limit(limit)
        result = await db.execute(stmt)
        clients = list(result.scalars().all())

        return clients, total

    @staticmethod
    async def update_client(
        db: AsyncSession,
        client_id: UUID,
        data: ClientUpdate,
        current_user: CurrentUser,
    ) -> Client | None:
        """
        Update an existing client.

        Requires CPA_OWNER role (function-level check, defense in depth).
        Returns None if client not found or soft-deleted.
        """
        verify_role(current_user, "CPA_OWNER")

        stmt = select(Client).where(
            Client.id == client_id,
            Client.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()

        if client is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Encrypt tax_id at the service boundary
        if "tax_id" in update_data:
            client.tax_id_encrypted = encrypt_pii(update_data.pop("tax_id"))

        for field, value in update_data.items():
            setattr(client, field, value)

        await db.commit()
        await db.refresh(client)
        return client

    @staticmethod
    async def archive_client(
        db: AsyncSession,
        client_id: UUID,
        current_user: CurrentUser,
    ) -> Client | None:
        """
        Soft-delete a client by setting deleted_at.

        Compliance (CLAUDE.md rule #2): Records are never hard-deleted.
        Requires CPA_OWNER role (function-level check, defense in depth).
        Returns None if client not found or already archived.
        """
        verify_role(current_user, "CPA_OWNER")

        stmt = select(Client).where(
            Client.id == client_id,
            Client.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()

        if client is None:
            return None

        client.deleted_at = datetime.now(timezone.utc)
        client.is_active = False
        await db.commit()
        await db.refresh(client)
        return client
