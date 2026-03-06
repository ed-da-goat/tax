"""
Tests for Client Portal endpoints (CP1-CP4).

Covers:
- Portal users (create, list) — CPA_OWNER only for create
- Messages (send, list, mark read)
- Questionnaires (create, list, get, send, submit)
- Signature requests (create, list, sign)
- Permission checks
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CPA_OWNER_ID = uuid.uuid4()
ASSOCIATE_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _override_as_associate():
    async def _dep():
        return CurrentUser(user_id=str(ASSOCIATE_ID), role="ASSOCIATE")
    return _dep


def _make_portal_user(**overrides):
    return SimpleNamespace(
        id=overrides.get("id", uuid.uuid4()),
        client_id=overrides.get("client_id", uuid.uuid4()),
        contact_id=overrides.get("contact_id", None),
        email=overrides.get("email", "client@example.com"),
        full_name=overrides.get("full_name", "Client User"),
        is_active=overrides.get("is_active", True),
        last_login_at=overrides.get("last_login_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_message(**overrides):
    return SimpleNamespace(
        id=overrides.get("id", uuid.uuid4()),
        client_id=overrides.get("client_id", uuid.uuid4()),
        thread_id=overrides.get("thread_id", None),
        subject=overrides.get("subject", "Tax docs needed"),
        body=overrides.get("body", "Please upload your W-2"),
        sender_type=overrides.get("sender_type", "STAFF"),
        sender_user_id=overrides.get("sender_user_id", CPA_OWNER_ID),
        sender_portal_user_id=overrides.get("sender_portal_user_id", None),
        is_read=overrides.get("is_read", False),
        read_at=overrides.get("read_at", None),
        has_attachments=overrides.get("has_attachments", False),
        deleted_at=overrides.get("deleted_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_questionnaire(**overrides):
    return SimpleNamespace(
        id=overrides.get("id", uuid.uuid4()),
        client_id=overrides.get("client_id", uuid.uuid4()),
        title=overrides.get("title", "Tax Year 2025 Checklist"),
        description=overrides.get("description", None),
        questionnaire_type=overrides.get("questionnaire_type", "tax_organizer"),
        tax_year=overrides.get("tax_year", 2025),
        status=overrides.get("status", "DRAFT"),
        sent_at=overrides.get("sent_at", None),
        submitted_at=overrides.get("submitted_at", None),
        reviewed_at=overrides.get("reviewed_at", None),
        questions=overrides.get("questions", []),
        deleted_at=overrides.get("deleted_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_signature_request(**overrides):
    return SimpleNamespace(
        id=overrides.get("id", uuid.uuid4()),
        client_id=overrides.get("client_id", uuid.uuid4()),
        document_id=overrides.get("document_id", None),
        engagement_id=overrides.get("engagement_id", None),
        signer_name=overrides.get("signer_name", "Client User"),
        signer_email=overrides.get("signer_email", "client@example.com"),
        status=overrides.get("status", "PENDING"),
        signed_at=overrides.get("signed_at", None),
        expires_at=overrides.get("expires_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: Portal Users
# ---------------------------------------------------------------------------


class TestPortalUsers:

    @patch("app.routers.portal.PortalService")
    async def test_create_portal_user_cpa_owner(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            pu = _make_portal_user()
            mock_svc.create_portal_user = AsyncMock(return_value=pu)

            response = await client.post(
                "/api/v1/portal-users",
                json={
                    "client_id": str(uuid.uuid4()),
                    "email": "client@example.com",
                    "full_name": "Client User",
                    "password": "Secure1!pass",
                },
            )
            assert response.status_code == 201
            assert response.json()["email"] == "client@example.com"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_create_portal_user(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            response = await client.post(
                "/api/v1/portal-users",
                json={
                    "client_id": str(uuid.uuid4()),
                    "email": "client@example.com",
                    "full_name": "Client User",
                    "password": "Secure1!pass",
                },
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_list_portal_users(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            pu = _make_portal_user()
            mock_svc.list_portal_users = AsyncMock(return_value=[pu])

            response = await client.get("/api/v1/portal-users")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Messages
# ---------------------------------------------------------------------------


class TestMessages:

    @patch("app.routers.portal.PortalService")
    async def test_send_message(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            msg = _make_message()
            mock_svc.send_message = AsyncMock(return_value=msg)

            response = await client.post(
                "/api/v1/messages",
                json={
                    "client_id": str(uuid.uuid4()),
                    "body": "Please upload your W-2",
                },
            )
            assert response.status_code == 201
            assert response.json()["body"] == "Please upload your W-2"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_list_messages(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            msg = _make_message()
            mock_svc.list_messages = AsyncMock(return_value=([msg], 1))

            cid = uuid.uuid4()
            response = await client.get(f"/api/v1/messages/{cid}")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_mark_message_read(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            msg = _make_message(is_read=True, read_at=NOW)
            mock_svc.mark_read = AsyncMock(return_value=msg)

            msg_id = uuid.uuid4()
            response = await client.post(f"/api/v1/messages/{msg_id}/read")
            assert response.status_code == 200
            assert response.json()["is_read"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Questionnaires
# ---------------------------------------------------------------------------


class TestQuestionnaires:

    @patch("app.routers.portal.PortalService")
    async def test_create_questionnaire(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            q = _make_questionnaire()
            mock_svc.create_questionnaire = AsyncMock(return_value=q)

            response = await client.post(
                "/api/v1/questionnaires",
                json={
                    "client_id": str(uuid.uuid4()),
                    "title": "Tax Year 2025 Checklist",
                    "questionnaire_type": "tax_organizer",
                },
            )
            assert response.status_code == 201
            assert response.json()["title"] == "Tax Year 2025 Checklist"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_list_questionnaires(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            q = _make_questionnaire()
            mock_svc.list_questionnaires = AsyncMock(return_value=([q], 1))

            response = await client.get("/api/v1/questionnaires")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_get_questionnaire(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            q_id = uuid.uuid4()
            q = _make_questionnaire(id=q_id)
            mock_svc.get_questionnaire = AsyncMock(return_value=q)

            response = await client.get(f"/api/v1/questionnaires/{q_id}")
            assert response.status_code == 200
            assert response.json()["id"] == str(q_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_send_questionnaire(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            q = _make_questionnaire(status="SENT", sent_at=NOW)
            mock_svc.send_questionnaire = AsyncMock(return_value=q)

            q_id = uuid.uuid4()
            response = await client.post(f"/api/v1/questionnaires/{q_id}/send")
            assert response.status_code == 200
            assert response.json()["status"] == "SENT"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_submit_questionnaire(self, mock_svc, client: AsyncClient):
        """Submit does not require auth (portal user submits via link)."""
        q = _make_questionnaire(status="SUBMITTED", submitted_at=NOW)
        mock_svc.submit_responses = AsyncMock(return_value=q)

        q_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/questionnaires/{q_id}/submit",
            json={"responses": []},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "SUBMITTED"


# ---------------------------------------------------------------------------
# Tests: Signature Requests
# ---------------------------------------------------------------------------


class TestSignatures:

    @patch("app.routers.portal.PortalService")
    async def test_create_signature_request(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            sig = _make_signature_request()
            mock_svc.create_signature_request = AsyncMock(return_value=sig)

            response = await client.post(
                "/api/v1/signatures",
                json={
                    "client_id": str(uuid.uuid4()),
                    "signer_name": "Client User",
                    "signer_email": "client@example.com",
                },
            )
            assert response.status_code == 201
            assert response.json()["signer_name"] == "Client User"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_create_signature(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            response = await client.post(
                "/api/v1/signatures",
                json={
                    "client_id": str(uuid.uuid4()),
                    "signer_name": "Client User",
                    "signer_email": "client@example.com",
                },
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_list_signatures(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            sig = _make_signature_request()
            mock_svc.list_signature_requests = AsyncMock(return_value=[sig])

            response = await client.get("/api/v1/signatures")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.portal.PortalService")
    async def test_sign_document(self, mock_svc, client: AsyncClient):
        """Signing does not require auth (signer uses token)."""
        sig = _make_signature_request(status="SIGNED", signed_at=NOW)
        mock_svc.sign_document = AsyncMock(return_value=sig)

        response = await client.post(
            "/api/v1/signatures/tok_abc123/sign",
            json={"signature_data": "base64encoded..."},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "SIGNED"
