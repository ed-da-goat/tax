"""
Pydantic models for parsed QuickBooks Online CSV data.

These models represent the structured output of QBOParser. They do NOT
map directly to database tables — the migration agent (M2-M7) handles
that transformation. These models capture what the CSV contains, with
light normalization (trimming, currency parsing) applied.
"""

import datetime as _dt
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ParsedAccount(BaseModel):
    """One row from the QBO Chart of Accounts export."""

    name: str = Field(..., description="Account name, colon-delimited for sub-accounts")
    type: str = Field(..., description="QBO account type (e.g. 'Bank', 'Expenses')")
    detail_type: str = Field(..., description="QBO sub-classification")
    description: Optional[str] = Field(None, description="User-entered description")
    balance: Optional[Decimal] = Field(None, description="Current balance at export time")
    currency: Optional[str] = Field(None, description="Currency code, e.g. 'USD'")
    account_number: Optional[str] = Field(None, description="User-assigned account number")


class ParsedTransaction(BaseModel):
    """One row from the QBO Transaction Detail by Account export."""

    date: _dt.date = Field(..., description="Transaction date")
    transaction_type: str = Field(..., description="QBO transaction type")
    num: Optional[str] = Field(None, description="Transaction/check number")
    name: Optional[str] = Field(None, description="Customer, vendor, or employee name")
    memo: Optional[str] = Field(None, description="Free-text memo")
    account: str = Field(..., description="Account this line posts to")
    split: Optional[str] = Field(None, description="Contra account(s)")
    amount: Decimal = Field(..., description="Signed amount (sign depends on account type)")
    balance: Optional[Decimal] = Field(None, description="Running balance in the account")


class ParsedCustomer(BaseModel):
    """One row from the QBO Customer Contact List export."""

    name: str = Field(..., description="Customer display name")
    company: Optional[str] = Field(None, description="Company name")
    email: Optional[str] = Field(None, description="Primary email")
    phone: Optional[str] = Field(None, description="Primary phone")
    billing_street: Optional[str] = Field(None, description="Billing street address")
    billing_city: Optional[str] = Field(None, description="Billing city")
    billing_state: Optional[str] = Field(None, description="Billing state")
    billing_zip: Optional[str] = Field(None, description="Billing ZIP")
    open_balance: Optional[Decimal] = Field(None, description="Outstanding balance")


class ParsedInvoice(BaseModel):
    """One row from the QBO Invoice List export."""

    invoice_date: _dt.date = Field(..., description="Date the invoice was created")
    invoice_no: str = Field(..., description="Invoice number")
    customer: str = Field(..., description="Customer display name")
    due_date: _dt.date = Field(..., description="Payment due date")
    amount: Decimal = Field(..., description="Total invoice amount")
    open_balance: Optional[Decimal] = Field(None, description="Remaining unpaid amount")
    status: Optional[str] = Field(None, description="QBO status: Paid, Open, Overdue, Voided")


class ParsedVendor(BaseModel):
    """One row from the QBO Vendor Contact List export."""

    name: str = Field(..., description="Vendor display name")
    company: Optional[str] = Field(None, description="Company name")
    email: Optional[str] = Field(None, description="Primary email")
    phone: Optional[str] = Field(None, description="Primary phone")
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    zip: Optional[str] = Field(None, description="ZIP code")


class ParsedEmployee(BaseModel):
    """One row from the QBO Employee Details export."""

    name: str = Field(..., description="Employee display name")
    ssn_last4: Optional[str] = Field(None, description="Last 4 digits of SSN")
    hire_date: Optional[_dt.date] = Field(None, description="Date of hire")
    status: Optional[str] = Field(None, description="Active or Terminated")
    pay_type: Optional[str] = Field(None, description="Hourly or Salary")
    pay_rate: Optional[Decimal] = Field(None, description="Current pay rate")
    filing_status: Optional[str] = Field(None, description="Federal W-4 filing status")


class ParsedPayrollRecord(BaseModel):
    """One row from the QBO Payroll Summary export."""

    employee: str = Field(..., description="Employee display name")
    gross_pay: Decimal = Field(..., description="Total gross compensation")
    federal_withholding: Optional[Decimal] = Field(None, description="Federal income tax withheld")
    state_withholding: Optional[Decimal] = Field(None, description="GA state income tax withheld")
    social_security: Optional[Decimal] = Field(None, description="Employee SS withholding")
    medicare: Optional[Decimal] = Field(None, description="Employee Medicare withholding")
    net_pay: Optional[Decimal] = Field(None, description="Net pay after deductions")
    ga_suta: Optional[Decimal] = Field(None, description="GA State Unemployment Insurance")
    futa: Optional[Decimal] = Field(None, description="Federal Unemployment Tax")


class ParsedJournalEntry(BaseModel):
    """One row from the QBO General Journal export."""

    date: _dt.date = Field(..., description="Entry date")
    entry_no: Optional[str] = Field(None, description="Journal entry number")
    account: str = Field(..., description="Account name")
    debit: Optional[Decimal] = Field(None, description="Debit amount")
    credit: Optional[Decimal] = Field(None, description="Credit amount")
    name: Optional[str] = Field(None, description="Name (customer/vendor/employee)")
    memo: Optional[str] = Field(None, description="Memo/description")
