"""
Pydantic schemas for AR/AP aging reports.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.schemas import BaseSchema


class AgingDetail(BaseSchema):
    """A single invoice or bill in the aging report."""

    id: UUID
    number: str | None = None
    counterparty: str  # customer_name for AR, vendor name for AP
    date_issued: date
    due_date: date
    total_amount: Decimal
    amount_paid: Decimal = Decimal("0.00")
    outstanding: Decimal = Decimal("0.00")
    days_past_due: int = 0
    bucket: str  # "Current", "1-30", "31-60", "61-90", "90+"


class AgingBucketSummary(BaseSchema):
    """Totals for a single aging bucket."""

    bucket: str
    total: Decimal = Decimal("0.00")
    count: int = 0


class ARAgingReport(BaseSchema):
    """Accounts Receivable aging report."""

    client_id: UUID
    as_of_date: date
    details: list[AgingDetail] = []
    buckets: list[AgingBucketSummary] = []
    total_outstanding: Decimal = Decimal("0.00")


class APAgingReport(BaseSchema):
    """Accounts Payable aging report."""

    client_id: UUID
    as_of_date: date
    details: list[AgingDetail] = []
    buckets: list[AgingBucketSummary] = []
    total_outstanding: Decimal = Decimal("0.00")
