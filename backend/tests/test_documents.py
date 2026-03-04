"""
Tests for Document Management (module D1).

Compliance tests:
- CLIENT ISOLATION (rule #4): Documents scoped to client_id
- AUDIT TRAIL (rule #2): Soft deletes only
- File storage: /data/documents/[client_id]/ path structure

Uses real PostgreSQL session (rolled back after each test).
"""

import io
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.schemas.document import DocumentUpdate
from app.services.document import DocumentService, DOCUMENT_BASE_PATH
from tests.conftest import CPA_OWNER_USER, CPA_OWNER_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_test_client(db: AsyncSession, client_id: uuid.UUID | None = None) -> uuid.UUID:
    cid = client_id or uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, 'SOLE_PROP', true)"
        ),
        {"id": str(cid), "name": f"Test Client {cid}"},
    )
    await db.flush()
    return cid


async def _create_test_user(db: AsyncSession, user_id: str | None = None, role: str = "CPA_OWNER") -> str:
    uid = user_id or str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, role, is_active) "
            "VALUES (:id, :email, :password_hash, :full_name, :role, true)"
        ),
        {
            "id": uid,
            "email": f"user_{uid[:8]}@test.com",
            "password_hash": "$2b$12$test_hash_placeholder_for_testing",
            "full_name": f"Test User {uid[:8]}",
            "role": role,
        },
    )
    await db.flush()
    return uid


def _make_upload_file(
    filename: str = "test.pdf",
    content: bytes = b"%PDF-1.4 fake content",
    content_type: str = "application/pdf",
) -> UploadFile:
    """Create a mock UploadFile for testing."""
    file = UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers={"content-type": content_type},
    )
    return file


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestDocumentUpload:

    @pytest.mark.asyncio
    async def test_upload_pdf(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        upload_file = _make_upload_file()

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            doc = await DocumentService.upload(
                db_session, client_id, upload_file, CPA_OWNER_USER,
                description="Test invoice PDF",
                tags=["invoice", "2024"],
            )

        assert doc.client_id == client_id
        assert doc.file_name == "test.pdf"
        assert doc.file_type == "application/pdf"
        assert doc.description == "Test invoice PDF"
        assert doc.tags == ["invoice", "2024"]
        assert doc.uploaded_by == uuid.UUID(CPA_OWNER_USER_ID)

    @pytest.mark.asyncio
    async def test_upload_image(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        upload_file = _make_upload_file(
            filename="receipt.jpg",
            content=b"\xff\xd8\xff fake jpeg",
            content_type="image/jpeg",
        )

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            doc = await DocumentService.upload(
                db_session, client_id, upload_file, CPA_OWNER_USER,
            )

        assert doc.file_type == "image/jpeg"
        assert "receipt" in doc.file_name

    @pytest.mark.asyncio
    async def test_reject_disallowed_file_type(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        upload_file = _make_upload_file(
            filename="malware.exe",
            content=b"MZ executable",
            content_type="application/x-executable",
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
                await DocumentService.upload(
                    db_session, client_id, upload_file, CPA_OWNER_USER,
                )
        assert exc_info.value.status_code == 400
        assert "not allowed" in exc_info.value.detail


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestDocumentCRUD:

    @pytest.mark.asyncio
    async def test_get_document(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            doc = await DocumentService.upload(
                db_session, client_id,
                _make_upload_file(),
                CPA_OWNER_USER,
            )

        fetched = await DocumentService.get(db_session, client_id, doc.id)
        assert fetched is not None
        assert fetched.id == doc.id

    @pytest.mark.asyncio
    async def test_client_isolation(self, db_session: AsyncSession, tmp_path):
        """Client A's documents are not visible to Client B."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            doc = await DocumentService.upload(
                db_session, client_a,
                _make_upload_file(),
                CPA_OWNER_USER,
            )

        # Client B cannot see Client A's document
        result = await DocumentService.get(db_session, client_b, doc.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_documents(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("doc1.pdf"),
                CPA_OWNER_USER,
                tags=["tax"],
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("doc2.pdf"),
                CPA_OWNER_USER,
                tags=["receipt"],
            )

        docs, total = await DocumentService.list(db_session, client_id)
        assert total == 2
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_list_documents_filter_by_tags(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("tax.pdf"),
                CPA_OWNER_USER,
                tags=["tax", "2024"],
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("receipt.pdf"),
                CPA_OWNER_USER,
                tags=["receipt"],
            )

        docs, total = await DocumentService.list(db_session, client_id, tags=["tax"])
        assert total == 1
        assert docs[0].file_name == "tax.pdf"

    @pytest.mark.asyncio
    async def test_update_document(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            doc = await DocumentService.upload(
                db_session, client_id,
                _make_upload_file(),
                CPA_OWNER_USER,
            )

        updated = await DocumentService.update(
            db_session, client_id, doc.id,
            DocumentUpdate(description="Updated description", tags=["updated"]),
        )
        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.tags == ["updated"]

    @pytest.mark.asyncio
    async def test_soft_delete_document(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            doc = await DocumentService.upload(
                db_session, client_id,
                _make_upload_file(),
                CPA_OWNER_USER,
            )

        deleted = await DocumentService.soft_delete(db_session, client_id, doc.id)
        assert deleted is not None
        assert deleted.deleted_at is not None

        # Should not be visible anymore
        result = await DocumentService.get(db_session, client_id, doc.id)
        assert result is None


# ---------------------------------------------------------------------------
# Document Search tests (module D3)
# ---------------------------------------------------------------------------


class TestDocumentSearch:

    @pytest.mark.asyncio
    async def test_search_by_filename(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("invoice_2024.pdf"),
                CPA_OWNER_USER,
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("receipt_groceries.pdf"),
                CPA_OWNER_USER,
            )

        docs, total = await DocumentService.search(
            db_session, client_id, query="invoice",
        )
        assert total == 1
        assert "invoice" in docs[0].file_name.lower()

    @pytest.mark.asyncio
    async def test_search_by_description(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("doc1.pdf"),
                CPA_OWNER_USER,
                description="Annual tax return 2024",
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("doc2.pdf"),
                CPA_OWNER_USER,
                description="Quarterly payroll report",
            )

        docs, total = await DocumentService.search(
            db_session, client_id, query="payroll",
        )
        assert total == 1
        assert "payroll" in docs[0].description.lower()

    @pytest.mark.asyncio
    async def test_search_by_tags(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("tax.pdf"),
                CPA_OWNER_USER,
                tags=["tax", "2024"],
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("receipt.pdf"),
                CPA_OWNER_USER,
                tags=["receipt", "expense"],
            )

        docs, total = await DocumentService.search(
            db_session, client_id, tags=["tax"],
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_search_by_file_type(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("doc.pdf", content_type="application/pdf"),
                CPA_OWNER_USER,
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("photo.jpg", content=b"\xff\xd8", content_type="image/jpeg"),
                CPA_OWNER_USER,
            )

        docs, total = await DocumentService.search(
            db_session, client_id, file_type="image/jpeg",
        )
        assert total == 1
        assert docs[0].file_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_search_combined_filters(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("invoice.pdf"),
                CPA_OWNER_USER,
                description="Client A invoice",
                tags=["invoice"],
            )
            await DocumentService.upload(
                db_session, client_id,
                _make_upload_file("invoice2.pdf"),
                CPA_OWNER_USER,
                description="Client B invoice",
                tags=["receipt"],
            )

        docs, total = await DocumentService.search(
            db_session, client_id,
            query="invoice",
            tags=["invoice"],
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, db_session: AsyncSession, tmp_path):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        docs, total = await DocumentService.search(
            db_session, client_id, query="nonexistent",
        )
        assert total == 0
        assert docs == []

    @pytest.mark.asyncio
    async def test_search_client_isolation(self, db_session: AsyncSession, tmp_path):
        """Search results must be scoped to client_id."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        with patch("app.services.document.DOCUMENT_BASE_PATH", str(tmp_path)):
            await DocumentService.upload(
                db_session, client_a,
                _make_upload_file("secret.pdf"),
                CPA_OWNER_USER,
                description="Secret document",
            )

        docs, total = await DocumentService.search(
            db_session, client_b, query="secret",
        )
        assert total == 0
