"""
Pydantic schemas for Transaction Approval Workflow (module T4).

Request/response models for the approval queue, batch operations,
rejection workflow, and approval history.

Compliance (CLAUDE.md rule #5): ASSOCIATE enters DRAFT, only CPA_OWNER approves/rejects.
Compliance (CLAUDE.md rule #6): Defense in depth — role checks at function level.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema


class ApprovalActionType(str, enum.Enum):
    """Allowed actions in a batch approval request."""

    APPROVE = "approve"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Queue item schemas
# ---------------------------------------------------------------------------


class ApprovalQueueItem(BaseSchema):
    """Summary of a journal entry in the approval queue."""

    id: UUID
    client_id: UUID
    client_name: str
    entry_date: date
    description: str | None = None
    reference_number: str | None = None
    total_debits: Decimal
    total_credits: Decimal
    created_by: UUID
    created_at: datetime
    submitted_at: datetime | None = None


class ApprovalQueueFilters(BaseSchema):
    """Filters that were applied to the approval queue query."""

    client_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None


class ApprovalQueueResponse(BaseSchema):
    """Paginated approval queue response."""

    items: list[ApprovalQueueItem]
    total: int
    skip: int
    limit: int
    filters: ApprovalQueueFilters


# ---------------------------------------------------------------------------
# Approval action schemas
# ---------------------------------------------------------------------------


class ApprovalAction(BaseSchema):
    """A single approve/reject action in a batch request."""

    entry_id: UUID
    action: ApprovalActionType
    note: str | None = None


class BatchApprovalRequest(BaseSchema):
    """Request to process multiple approve/reject actions."""

    actions: list[ApprovalAction] = Field(..., min_length=1)


class BatchApprovalResultItem(BaseSchema):
    """Result of a single entry in a batch approval operation."""

    entry_id: UUID
    action: ApprovalActionType
    success: bool
    error: str | None = None


class BatchApprovalResponse(BaseSchema):
    """Response from a batch approval operation."""

    results: list[BatchApprovalResultItem]
    total_processed: int
    total_succeeded: int
    total_failed: int


# ---------------------------------------------------------------------------
# Rejection schema
# ---------------------------------------------------------------------------


class RejectionRequest(BaseSchema):
    """Request to reject a journal entry (requires a note explaining why)."""

    note: str = Field(..., min_length=1, max_length=2000)


class RejectionResponse(BaseSchema):
    """Response after rejecting a journal entry."""

    entry_id: UUID
    status: str
    rejection_note: str
    rejected_by: UUID
    rejected_at: datetime


# ---------------------------------------------------------------------------
# Approval history schemas
# ---------------------------------------------------------------------------


class ApprovalHistoryItem(BaseSchema):
    """A single status change event in the approval history."""

    action: str
    old_status: str | None = None
    new_status: str | None = None
    changed_by: UUID | None = None
    note: str | None = None
    timestamp: datetime


class ApprovalHistoryResponse(BaseSchema):
    """Full approval history for a journal entry."""

    entry_id: UUID
    history: list[ApprovalHistoryItem]
