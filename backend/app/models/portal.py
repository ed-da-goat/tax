"""
SQLAlchemy ORM models for client portal (CP1-CP4).

Tables: portal_users, messages, message_attachments,
        questionnaires, questionnaire_questions, questionnaire_responses,
        signature_requests
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer,
    String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class QuestionnaireStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"


class QuestionType(str, enum.Enum):
    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATE"
    YES_NO = "YES_NO"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    FILE_UPLOAD = "FILE_UPLOAD"


class SignatureStatus(str, enum.Enum):
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class PortalUser(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "portal_users"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    magic_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    magic_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Message(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "messages"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'STAFF' or 'CLIENT'
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    sender_portal_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal_users.id"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", lazy="selectin"
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    message: Mapped["Message"] = relationship(back_populates="attachments")


class Questionnaire(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "questionnaires"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    questionnaire_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[QuestionnaireStatus] = mapped_column(
        Enum(QuestionnaireStatus, name="questionnaire_status", create_type=False),
        default=QuestionnaireStatus.DRAFT, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    questions: Mapped[list["QuestionnaireQuestion"]] = relationship(
        back_populates="questionnaire", cascade="all, delete-orphan", lazy="selectin"
    )


class QuestionnaireQuestion(Base, TimestampMixin):
    __tablename__ = "questionnaire_questions"

    questionnaire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", create_type=False),
        default=QuestionType.TEXT, nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    questionnaire: Mapped["Questionnaire"] = relationship(back_populates="questions")
    responses: Mapped[list["QuestionnaireResponse"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin"
    )


class QuestionnaireResponse(Base, TimestampMixin):
    __tablename__ = "questionnaire_responses"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questionnaire_questions.id", ondelete="CASCADE"), nullable=False
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    responded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal_users.id"), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    question: Mapped["QuestionnaireQuestion"] = relationship(back_populates="responses")


class SignatureRequest(Base, TimestampMixin):
    __tablename__ = "signature_requests"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=True
    )
    signer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    portal_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal_users.id"), nullable=True
    )
    status: Mapped[SignatureStatus] = mapped_column(
        Enum(SignatureStatus, name="signature_status", create_type=False),
        default=SignatureStatus.PENDING, nullable=False
    )
    signature_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signing_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
