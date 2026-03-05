"""Pydantic schemas for client portal (CP1-CP4)."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas import BaseSchema, RecordSchema


# --- Portal Users ---
class PortalUserCreate(BaseSchema):
    client_id: UUID
    contact_id: UUID | None = None
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)


class PortalUserResponse(RecordSchema):
    client_id: UUID
    contact_id: UUID | None = None
    email: str
    full_name: str
    is_active: bool
    last_login_at: datetime | None = None


class PortalUserList(BaseSchema):
    items: list[PortalUserResponse]
    total: int


class PortalLoginRequest(BaseSchema):
    email: EmailStr
    password: str


class PortalLoginResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    portal_user: PortalUserResponse


# --- Messages ---
class MessageCreate(BaseSchema):
    client_id: UUID
    subject: str | None = None
    body: str = Field(..., min_length=1)
    thread_id: UUID | None = None


class MessageResponse(RecordSchema):
    client_id: UUID
    thread_id: UUID | None = None
    subject: str | None = None
    body: str
    sender_type: str
    sender_user_id: UUID | None = None
    sender_portal_user_id: UUID | None = None
    is_read: bool
    read_at: datetime | None = None
    has_attachments: bool
    deleted_at: datetime | None = None


class MessageList(BaseSchema):
    items: list[MessageResponse]
    total: int


# --- Questionnaires ---
class QuestionnaireStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"


class QuestionTypeEnum(str, Enum):
    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATE"
    YES_NO = "YES_NO"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    FILE_UPLOAD = "FILE_UPLOAD"


class QuestionCreate(BaseSchema):
    question_text: str
    question_type: QuestionTypeEnum = QuestionTypeEnum.TEXT
    is_required: bool = False
    sort_order: int = 0
    options: dict | None = None
    section: str | None = None
    help_text: str | None = None


class QuestionnaireCreate(BaseSchema):
    client_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    questionnaire_type: str
    tax_year: int | None = None
    questions: list[QuestionCreate] = []


class QuestionResponseData(BaseSchema):
    question_id: UUID
    response_text: str | None = None
    response_data: dict | None = None


class QuestionnaireSubmit(BaseSchema):
    responses: list[QuestionResponseData]


class QuestionResponse(RecordSchema):
    questionnaire_id: UUID
    question_text: str
    question_type: QuestionTypeEnum
    is_required: bool
    sort_order: int
    options: dict | None = None
    section: str | None = None
    help_text: str | None = None


class ResponseResponse(RecordSchema):
    question_id: UUID
    response_text: str | None = None
    response_data: dict | None = None
    responded_by: UUID | None = None
    responded_at: datetime | None = None


class QuestionnaireResponse(RecordSchema):
    client_id: UUID
    title: str
    description: str | None = None
    questionnaire_type: str
    tax_year: int | None = None
    status: QuestionnaireStatusEnum
    sent_at: datetime | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    questions: list[QuestionResponse] = []
    deleted_at: datetime | None = None


class QuestionnaireList(BaseSchema):
    items: list[QuestionnaireResponse]
    total: int


# --- Signature Requests ---
class SignatureStatusEnum(str, Enum):
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class SignatureRequestCreate(BaseSchema):
    client_id: UUID
    document_id: UUID | None = None
    engagement_id: UUID | None = None
    signer_name: str = Field(..., min_length=1, max_length=255)
    signer_email: EmailStr
    expires_in_days: int = 30


class SignatureSubmit(BaseSchema):
    signature_data: str  # base64 encoded signature image


class SignatureRequestResponse(RecordSchema):
    client_id: UUID
    document_id: UUID | None = None
    engagement_id: UUID | None = None
    signer_name: str
    signer_email: str
    status: SignatureStatusEnum
    signed_at: datetime | None = None
    expires_at: datetime | None = None


class SignatureRequestList(BaseSchema):
    items: list[SignatureRequestResponse]
    total: int
