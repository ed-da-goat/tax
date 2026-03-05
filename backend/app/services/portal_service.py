"""
Service layer for client portal (CP1-CP4).

Portal users, secure messaging, questionnaires/organizers, e-signatures.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.portal import (
    PortalUser, Message, MessageAttachment, Questionnaire, QuestionnaireStatus,
    QuestionnaireQuestion, QuestionnaireResponse, SignatureRequest, SignatureStatus,
)
from app.schemas.portal import (
    PortalUserCreate, MessageCreate, QuestionnaireCreate, QuestionnaireSubmit,
    SignatureRequestCreate, SignatureSubmit,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PortalService:

    # --- Portal Users ---
    @staticmethod
    async def create_portal_user(
        db: AsyncSession, data: PortalUserCreate, current_user: CurrentUser,
    ) -> PortalUser:
        verify_role(current_user, "CPA_OWNER")
        existing = await db.execute(
            select(PortalUser).where(PortalUser.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        portal_user = PortalUser(
            client_id=data.client_id,
            contact_id=data.contact_id,
            email=data.email,
            password_hash=pwd_context.hash(data.password),
            full_name=data.full_name,
        )
        db.add(portal_user)
        await db.commit()
        await db.refresh(portal_user)
        return portal_user

    @staticmethod
    async def list_portal_users(
        db: AsyncSession, client_id: uuid.UUID | None = None,
    ) -> list[PortalUser]:
        query = select(PortalUser).where(PortalUser.deleted_at.is_(None))
        if client_id:
            query = query.where(PortalUser.client_id == client_id)
        result = await db.execute(query.order_by(PortalUser.full_name))
        return list(result.scalars().all())

    @staticmethod
    async def authenticate_portal_user(
        db: AsyncSession, email: str, password: str,
    ) -> PortalUser:
        result = await db.execute(
            select(PortalUser).where(
                PortalUser.email == email,
                PortalUser.is_active.is_(True),
                PortalUser.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        if not user or not pwd_context.verify(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)
        return user

    # --- Messages ---
    @staticmethod
    async def send_message(
        db: AsyncSession, data: MessageCreate,
        current_user: CurrentUser | None = None,
        portal_user_id: uuid.UUID | None = None,
    ) -> Message:
        sender_type = "STAFF" if current_user else "CLIENT"
        msg = Message(
            client_id=data.client_id,
            thread_id=data.thread_id,
            subject=data.subject,
            body=data.body,
            sender_type=sender_type,
            sender_user_id=current_user.user_id if current_user else None,
            sender_portal_user_id=portal_user_id,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        client_id: uuid.UUID,
        thread_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Message], int]:
        query = select(Message).where(
            Message.client_id == client_id,
            Message.deleted_at.is_(None),
        )
        count_q = select(func.count(Message.id)).where(
            Message.client_id == client_id,
            Message.deleted_at.is_(None),
        )

        if thread_id:
            query = query.where(
                (Message.id == thread_id) | (Message.thread_id == thread_id)
            )
            count_q = count_q.where(
                (Message.id == thread_id) | (Message.thread_id == thread_id)
            )
        else:
            # Show thread starters only
            query = query.where(Message.thread_id.is_(None))
            count_q = count_q.where(Message.thread_id.is_(None))

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(Message.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    @staticmethod
    async def mark_read(
        db: AsyncSession, message_id: uuid.UUID,
    ) -> Message:
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        msg.is_read = True
        msg.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def unread_count(
        db: AsyncSession, client_id: uuid.UUID,
        for_staff: bool = True,
    ) -> int:
        sender_type = "CLIENT" if for_staff else "STAFF"
        result = await db.execute(
            select(func.count(Message.id)).where(
                Message.client_id == client_id,
                Message.sender_type == sender_type,
                Message.is_read.is_(False),
                Message.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

    # --- Questionnaires ---
    @staticmethod
    async def create_questionnaire(
        db: AsyncSession, data: QuestionnaireCreate, current_user: CurrentUser,
    ) -> Questionnaire:
        q = Questionnaire(
            client_id=data.client_id,
            title=data.title,
            description=data.description,
            questionnaire_type=data.questionnaire_type,
            tax_year=data.tax_year,
            status=QuestionnaireStatus.DRAFT,
        )
        db.add(q)
        await db.flush()

        for qd in data.questions:
            question = QuestionnaireQuestion(
                questionnaire_id=q.id,
                question_text=qd.question_text,
                question_type=qd.question_type,
                is_required=qd.is_required,
                sort_order=qd.sort_order,
                options=qd.options,
                section=qd.section,
                help_text=qd.help_text,
            )
            db.add(question)

        await db.commit()
        await db.refresh(q)
        return q

    @staticmethod
    async def list_questionnaires(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Questionnaire], int]:
        query = select(Questionnaire).where(Questionnaire.deleted_at.is_(None))
        count_q = select(func.count(Questionnaire.id)).where(Questionnaire.deleted_at.is_(None))

        if client_id:
            query = query.where(Questionnaire.client_id == client_id)
            count_q = count_q.where(Questionnaire.client_id == client_id)
        if status_filter:
            query = query.where(Questionnaire.status == status_filter)
            count_q = count_q.where(Questionnaire.status == status_filter)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(Questionnaire.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    @staticmethod
    async def get_questionnaire(
        db: AsyncSession, questionnaire_id: uuid.UUID,
    ) -> Questionnaire:
        result = await db.execute(
            select(Questionnaire).where(
                Questionnaire.id == questionnaire_id,
                Questionnaire.deleted_at.is_(None),
            )
        )
        q = result.scalar_one_or_none()
        if not q:
            raise HTTPException(status_code=404, detail="Questionnaire not found")
        return q

    @staticmethod
    async def send_questionnaire(
        db: AsyncSession, questionnaire_id: uuid.UUID, current_user: CurrentUser,
    ) -> Questionnaire:
        q = await PortalService.get_questionnaire(db, questionnaire_id)
        if q.status != QuestionnaireStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Must be DRAFT to send")
        q.status = QuestionnaireStatus.SENT
        q.sent_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(q)
        return q

    @staticmethod
    async def submit_responses(
        db: AsyncSession, questionnaire_id: uuid.UUID,
        data: QuestionnaireSubmit,
        portal_user_id: uuid.UUID | None = None,
    ) -> Questionnaire:
        q = await PortalService.get_questionnaire(db, questionnaire_id)
        if q.status not in (QuestionnaireStatus.SENT, QuestionnaireStatus.IN_PROGRESS):
            raise HTTPException(status_code=400, detail="Questionnaire not available for responses")

        for resp in data.responses:
            response = QuestionnaireResponse(
                question_id=resp.question_id,
                response_text=resp.response_text,
                response_data=resp.response_data,
                responded_by=portal_user_id,
            )
            db.add(response)

        q.status = QuestionnaireStatus.SUBMITTED
        q.submitted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(q)
        return q

    # --- Signature Requests ---
    @staticmethod
    async def create_signature_request(
        db: AsyncSession, data: SignatureRequestCreate, current_user: CurrentUser,
    ) -> SignatureRequest:
        verify_role(current_user, "CPA_OWNER")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

        sig = SignatureRequest(
            client_id=data.client_id,
            document_id=data.document_id,
            engagement_id=data.engagement_id,
            signer_name=data.signer_name,
            signer_email=data.signer_email,
            signing_token=token,
            expires_at=expires_at,
        )
        db.add(sig)
        await db.commit()
        await db.refresh(sig)
        return sig

    @staticmethod
    async def list_signature_requests(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        status_filter: str | None = None,
    ) -> list[SignatureRequest]:
        query = select(SignatureRequest)
        if client_id:
            query = query.where(SignatureRequest.client_id == client_id)
        if status_filter:
            query = query.where(SignatureRequest.status == status_filter)
        result = await db.execute(query.order_by(SignatureRequest.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def sign_document(
        db: AsyncSession, signing_token: str,
        data: SignatureSubmit, ip_address: str | None = None,
    ) -> SignatureRequest:
        result = await db.execute(
            select(SignatureRequest).where(
                SignatureRequest.signing_token == signing_token,
            )
        )
        sig = result.scalar_one_or_none()
        if not sig:
            raise HTTPException(status_code=404, detail="Signature request not found")
        if sig.status != SignatureStatus.PENDING:
            raise HTTPException(status_code=400, detail="Already signed/declined/expired")
        if sig.expires_at and sig.expires_at < datetime.now(timezone.utc):
            sig.status = SignatureStatus.EXPIRED
            await db.commit()
            raise HTTPException(status_code=400, detail="Signature request has expired")

        sig.status = SignatureStatus.SIGNED
        sig.signature_data = data.signature_data
        sig.signed_at = datetime.now(timezone.utc)
        sig.ip_address = ip_address
        await db.commit()
        await db.refresh(sig)
        return sig
