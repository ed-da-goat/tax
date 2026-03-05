"""
Service layer for Document Management (module D1).

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.

Files are stored under /data/documents/[client_id]/ per CLAUDE.md spec.
"""

import os
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.models.document import Document
from app.schemas.document import DocumentUpdate

# Base path for document storage
DOCUMENT_BASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "data", "documents",
)


class DocumentService:
    """Business logic for document upload and management."""

    @staticmethod
    async def upload(
        db: AsyncSession,
        client_id: uuid.UUID,
        file: UploadFile,
        current_user: CurrentUser,
        description: str | None = None,
        tags: list[str] | None = None,
        journal_entry_id: uuid.UUID | None = None,
    ) -> Document:
        """
        Upload a document and store it on the local filesystem.

        Files are stored under /data/documents/{client_id}/{filename}.
        If a file with the same name exists, a UUID suffix is appended.
        """
        # Validate file type
        allowed_types = {
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/tiff",
            "image/webp",
        }
        content_type = file.content_type or "application/octet-stream"
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{content_type}' not allowed. Allowed types: PDF, JPEG, PNG, GIF, TIFF, WebP",
            )

        # Create client directory if needed
        client_dir = os.path.join(DOCUMENT_BASE_PATH, str(client_id))
        os.makedirs(client_dir, exist_ok=True)

        # Determine safe filename
        original_name = file.filename or "unnamed"
        # Sanitize filename
        safe_name = "".join(
            c for c in original_name if c.isalnum() or c in ".-_ "
        ).strip()
        if not safe_name:
            safe_name = "document"

        # Add UUID suffix to prevent overwrites
        name_base, ext = os.path.splitext(safe_name)
        unique_name = f"{name_base}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(client_dir, unique_name)

        # Read file content with size limit (50 MB max)
        MAX_FILE_SIZE = 50 * 1024 * 1024
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large ({file_size // (1024*1024)} MB). Maximum is 50 MB.",
            )
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file. Please select a valid document.",
            )

        with open(file_path, "wb") as f:
            f.write(content)

        # Store relative path in DB
        relative_path = os.path.join("data", "documents", str(client_id), unique_name)

        doc = Document(
            client_id=client_id,
            file_name=original_name,
            file_path=relative_path,
            file_type=content_type,
            file_size_bytes=file_size,
            description=description,
            tags=tags,
            uploaded_by=uuid.UUID(current_user.user_id),
            journal_entry_id=journal_entry_id,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def get(
        db: AsyncSession,
        client_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document | None:
        """
        Get a single document by ID.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = select(Document).where(
            Document.id == document_id,
            Document.client_id == client_id,
            Document.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        tags: list[str] | None = None,
        file_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Document], int]:
        """
        List documents for a client with optional filters.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        base = select(Document).where(
            Document.client_id == client_id,
            Document.deleted_at.is_(None),
        )

        if tags:
            # Filter documents that contain ANY of the specified tags
            base = base.where(Document.tags.overlap(tags))
        if file_type:
            base = base.where(Document.file_type == file_type)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def search(
        db: AsyncSession,
        client_id: uuid.UUID,
        query: str | None = None,
        tags: list[str] | None = None,
        file_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Document], int]:
        """
        Search documents by text query, tags, type, and date range (module D3).

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        base = select(Document).where(
            Document.client_id == client_id,
            Document.deleted_at.is_(None),
        )

        if query:
            search_pattern = f"%{query}%"
            base = base.where(
                or_(
                    Document.file_name.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                )
            )
        if tags:
            base = base.where(Document.tags.overlap(tags))
        if file_type:
            base = base.where(Document.file_type == file_type)
        if date_from:
            base = base.where(func.date(Document.created_at) >= date_from)
        if date_to:
            base = base.where(func.date(Document.created_at) <= date_to)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def update(
        db: AsyncSession,
        client_id: uuid.UUID,
        document_id: uuid.UUID,
        data: DocumentUpdate,
    ) -> Document | None:
        doc = await DocumentService.get(db, client_id, document_id)
        if doc is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(doc, field, value)

        doc.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        client_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document | None:
        """
        Soft delete a document.

        Compliance (rule #2): Never hard delete.
        Note: The physical file is NOT deleted (preserves audit trail).
        """
        doc = await DocumentService.get(db, client_id, document_id)
        if doc is None:
            return None

        doc.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    def get_file_path(document: Document) -> str:
        """Get the absolute filesystem path for a document."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        # Strip leading / so os.path.join works correctly with project_root
        rel_path = document.file_path.lstrip("/")
        return os.path.join(project_root, rel_path)
