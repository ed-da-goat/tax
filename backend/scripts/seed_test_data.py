"""
Seed script for end-to-end testing.

Populates the database with realistic test data covering all 4 entity types,
all workflow statuses, and all modules (AP, AR, GL, Bank Recon, Payroll, Docs).

Usage:
    cd backend && python -m scripts.seed_test_data          # seed
    cd backend && python -m scripts.seed_test_data --reset   # wipe and re-seed
"""

import argparse
import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, engine
from app.models import (
    User, Client, EntityType,
    ChartOfAccounts,
    JournalEntry, JournalEntryLine, JournalEntryStatus,
    Vendor, Bill, BillLine, BillPayment, BillStatus,
    Invoice, InvoiceLine, InvoicePayment, InvoiceStatus,
    BankAccount, BankTransaction, Reconciliation,
    Document, Employee,
    PayrollRun, PayrollItem, PayrollRunStatus,
    PayrollTaxTable,
    # Phase 9-12 models
    TimeEntry, TimeEntryStatus, StaffRate,
    Workflow, WorkflowStatus, WorkflowStage, WorkflowTask,
    TaskStatusEnum, TaskPriority, RecurrenceType,
    DueDate,
    Contact,
    Engagement, EngagementStatus,
    ServiceInvoice, ServiceInvoiceLine, ServiceInvoiceStatus, PaymentMethod,
    PortalUser, Message, Questionnaire, QuestionnaireStatus,
    QuestionnaireQuestion, QuestionType,
    SignatureRequest, SignatureStatus,
    FixedAsset, DepreciationMethod, AssetStatus, DepreciationEntry,
    Budget, BudgetLine,
)
from app.services.auth import hash_password
from app.services.chart_of_accounts import (
    ChartOfAccountsService,
    TEMPLATE_CLIENT_ID,
)

# ---------------------------------------------------------------------------
# Fixed UUIDs for deterministic references
# ---------------------------------------------------------------------------
USER_CPA_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
USER_ASSOC_ID = uuid.UUID("10000000-0000-0000-0000-000000000002")

CLIENT_SOLE_PROP_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
CLIENT_S_CORP_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
CLIENT_C_CORP_ID = uuid.UUID("20000000-0000-0000-0000-000000000003")
CLIENT_PARTNERSHIP_ID = uuid.UUID("20000000-0000-0000-0000-000000000004")

# Date constants — TY2025 data
TODAY = date(2025, 12, 31)
JAN1 = date(2025, 1, 1)
Q1_END = date(2025, 3, 31)
Q2_END = date(2025, 6, 30)
Q3_END = date(2025, 9, 30)
Q4_END = date(2025, 12, 31)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def d(amount: str) -> Decimal:
    """Shorthand for Decimal."""
    return Decimal(amount)


def make_date(month: int, day: int, year: int = 2025) -> date:
    return date(year, month, day)


# ---------------------------------------------------------------------------
# RESET — wipe all non-template data
# ---------------------------------------------------------------------------
async def reset_database(session: AsyncSession) -> None:
    """Truncate all data tables (except template CoA) using replica mode to bypass triggers."""
    print("  Resetting database...")

    # Bypass hard-delete prevention triggers
    await session.execute(text("SET session_replication_role = 'replica'"))

    # Order matters — child tables first to respect FK constraints
    tables_to_truncate = [
        "audit_log",
        "permission_log",
        # Practice management tables (Phase 9-12)
        "questionnaire_responses",
        "questionnaire_questions",
        "questionnaires",
        "message_attachments",
        "messages",
        "signature_requests",
        "portal_users",
        "service_invoice_payments",
        "service_invoice_lines",
        "service_invoices",
        "task_comments",
        "workflow_tasks",
        "workflows",
        "workflow_stages",
        "reminders",
        "due_dates",
        "depreciation_entries",
        "fixed_assets",
        "budget_lines",
        "budgets",
        "time_entries",
        "timer_sessions",
        "staff_rates",
        "contacts",
        "engagements",
        "service_types",
        # Core tables
        "payroll_items",
        "payroll_runs",
        "documents",
        "bank_transactions",
        "reconciliations",
        "bank_accounts",
        "journal_entry_lines",
        "journal_entries",
        "invoice_payments",
        "invoice_lines",
        "invoices",
        "bill_payments",
        "bill_lines",
        "bills",
        "vendors",
        "employees",
        "payroll_tax_tables",
    ]
    for tbl in tables_to_truncate:
        await session.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))

    # Delete non-template chart_of_accounts and clients
    await session.execute(text(
        "DELETE FROM chart_of_accounts WHERE client_id != :tid"
    ), {"tid": str(TEMPLATE_CLIENT_ID)})
    await session.execute(text(
        "DELETE FROM clients WHERE id != :tid"
    ), {"tid": str(TEMPLATE_CLIENT_ID)})
    await session.execute(text("DELETE FROM users"))

    # Restore trigger enforcement
    await session.execute(text("SET session_replication_role = 'origin'"))
    await session.commit()
    print("  Database reset complete.")


# ---------------------------------------------------------------------------
# CHECK if already seeded
# ---------------------------------------------------------------------------
async def is_already_seeded(session: AsyncSession) -> bool:
    result = await session.execute(
        select(User).where(User.id == USER_CPA_ID)
    )
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# SEED USERS
# ---------------------------------------------------------------------------
async def seed_users(session: AsyncSession) -> None:
    print("  Creating users...")
    session.add(User(
        id=USER_CPA_ID,
        email="edward@755mortgage.com",
        password_hash=hash_password("admin123"),
        full_name="Edward Ahrens",
        role="CPA_OWNER",
        is_active=True,
    ))
    session.add(User(
        id=USER_ASSOC_ID,
        email="sarah@755mortgage.com",
        password_hash=hash_password("associate123"),
        full_name="Sarah Johnson",
        role="ASSOCIATE",
        is_active=True,
    ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED CLIENTS
# ---------------------------------------------------------------------------
CLIENTS_DATA = [
    {
        "id": CLIENT_SOLE_PROP_ID,
        "name": "Peachtree Landscaping LLC",
        "entity_type": EntityType.SOLE_PROP,
        "address": "456 Magnolia Dr",
        "city": "Marietta",
        "state": "GA",
        "zip": "30060",
        "phone": "770-555-1234",
        "email": "mike@peachtreelandscaping.com",
    },
    {
        "id": CLIENT_S_CORP_ID,
        "name": "Atlanta Tech Solutions Inc",
        "entity_type": EntityType.S_CORP,
        "address": "100 Peachtree St NE, Suite 400",
        "city": "Atlanta",
        "state": "GA",
        "zip": "30303",
        "phone": "404-555-2345",
        "email": "info@atlantatechsolutions.com",
    },
    {
        "id": CLIENT_C_CORP_ID,
        "name": "Southern Manufacturing Corp",
        "entity_type": EntityType.C_CORP,
        "address": "789 Industrial Blvd",
        "city": "Savannah",
        "state": "GA",
        "zip": "31401",
        "phone": "912-555-3456",
        "email": "accounting@southernmfg.com",
    },
    {
        "id": CLIENT_PARTNERSHIP_ID,
        "name": "Buckhead Partners Group",
        "entity_type": EntityType.PARTNERSHIP_LLC,
        "address": "3500 Lenox Rd NE, Suite 200",
        "city": "Atlanta",
        "state": "GA",
        "zip": "30326",
        "phone": "404-555-4567",
        "email": "partners@buckheadpartners.com",
    },
]


async def seed_clients(session: AsyncSession) -> None:
    print("  Creating clients...")
    for data in CLIENTS_DATA:
        session.add(Client(**data, is_active=True))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED CHART OF ACCOUNTS (clone from template)
# ---------------------------------------------------------------------------
async def seed_chart_of_accounts(session: AsyncSession) -> dict[uuid.UUID, dict[str, uuid.UUID]]:
    """Clone template CoA for each client. Returns {client_id: {acct_number: acct_id}}."""
    print("  Cloning chart of accounts...")
    acct_map: dict[uuid.UUID, dict[str, uuid.UUID]] = {}
    for client_data in CLIENTS_DATA:
        cid = client_data["id"]
        cloned = await ChartOfAccountsService.clone_template_accounts(session, cid)
        acct_map[cid] = {a.account_number: a.id for a in cloned}
    await session.flush()
    return acct_map


# ---------------------------------------------------------------------------
# Helper: look up account ID by number
# ---------------------------------------------------------------------------
def acct(acct_map: dict[str, uuid.UUID], number: str) -> uuid.UUID:
    """Get account UUID by account number. Raises KeyError with helpful message."""
    if number not in acct_map:
        raise KeyError(f"Account {number} not found. Available: {sorted(acct_map.keys())[:10]}...")
    return acct_map[number]


# ---------------------------------------------------------------------------
# SEED VENDORS
# ---------------------------------------------------------------------------
async def seed_vendors(
    session: AsyncSession,
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Create vendors per client. Returns {client_id: [vendor_ids]}."""
    print("  Creating vendors...")
    vendor_map: dict[uuid.UUID, list[uuid.UUID]] = {}

    vendors_by_client = {
        CLIENT_SOLE_PROP_ID: [
            ("Home Depot Pro", "123 Commerce Blvd", "Atlanta", "GA", "30301"),
            ("SiteOne Landscape Supply", "456 Garden Way", "Roswell", "GA", "30075"),
            ("Georgia Power", "241 Ralph McGill Blvd", "Atlanta", "GA", "30308"),
            ("State Farm Insurance", "100 State Farm Pkwy", "Bloomington", "GA", "30601"),
        ],
        CLIENT_S_CORP_ID: [
            ("Amazon Web Services", "410 Terry Ave N", "Seattle", "WA", "98109"),
            ("WeWork Atlanta", "1372 Peachtree St", "Atlanta", "GA", "30309"),
            ("Blue Cross Blue Shield GA", "3350 Peachtree Rd", "Atlanta", "GA", "30326"),
            ("CDW Corporation", "200 N Milwaukee Ave", "Vernon Hills", "IL", "60061"),
            ("ADP Payroll Services", "1 ADP Blvd", "Roseland", "NJ", "07068"),
        ],
        CLIENT_C_CORP_ID: [
            ("Grainger Industrial", "100 Grainger Pkwy", "Lake Forest", "IL", "60045"),
            ("Georgia Natural Gas", "600 Boulevard SE", "Atlanta", "GA", "30312"),
            ("Hartford Insurance", "One Hartford Plaza", "Hartford", "CT", "06155"),
            ("Caterpillar Inc", "510 Lake Cook Rd", "Deerfield", "IL", "60015"),
            ("Fastenal Company", "2001 Theurer Blvd", "Winona", "MN", "55987"),
            ("Sysco Georgia", "1390 Enclave Pkwy", "Houston", "TX", "77077"),
        ],
        CLIENT_PARTNERSHIP_ID: [
            ("Regus Office Space", "3340 Peachtree Rd NE", "Atlanta", "GA", "30326"),
            ("Lexis Nexis", "1000 Alderman Dr", "Alpharetta", "GA", "30005"),
            ("Verizon Business", "One Verizon Way", "Basking Ridge", "NJ", "07920"),
            ("FedEx Office", "942 S Shady Grove Rd", "Memphis", "TN", "38120"),
        ],
    }

    for client_id, vendors in vendors_by_client.items():
        ids = []
        for name, addr, city, state, zipcode in vendors:
            vid = uuid.uuid4()
            session.add(Vendor(
                id=vid,
                client_id=client_id,
                name=name,
                address=addr,
                city=city,
                state=state,
                zip=zipcode,
            ))
            ids.append(vid)
        vendor_map[client_id] = ids

    await session.flush()
    return vendor_map


# ---------------------------------------------------------------------------
# SEED BILLS (AP)
# ---------------------------------------------------------------------------
async def seed_bills(
    session: AsyncSession,
    acct_maps: dict[uuid.UUID, dict[str, uuid.UUID]],
    vendor_map: dict[uuid.UUID, list[uuid.UUID]],
) -> None:
    """Create bills with lines and payments for each client."""
    print("  Creating bills...")

    # Bills per client: (vendor_idx, bill_number, bill_date, due_date, status, expense_acct, amount, desc, payment?)
    bills_spec = {
        CLIENT_SOLE_PROP_ID: [
            (0, "HD-1001", (1, 15), (2, 15), "PAID", "6200", "2450.00", "Landscaping supplies - Q1", True),
            (0, "HD-1042", (3, 10), (4, 10), "PAID", "6200", "1875.50", "Spring equipment", True),
            (1, "SO-5521", (2, 1), (3, 1), "PAID", "6200", "3200.00", "Bulk mulch and soil", True),
            (2, "GP-2025-01", (1, 5), (2, 5), "PAID", "6110", "485.00", "Electric - January", True),
            (2, "GP-2025-06", (6, 5), (7, 5), "APPROVED", "6110", "612.00", "Electric - June", False),
            (3, "SF-INS-25", (1, 1), (1, 31), "PAID", "6300", "4800.00", "Annual liability insurance", True),
            (0, "HD-1098", (7, 20), (8, 20), "PENDING_APPROVAL", "6200", "1650.00", "Summer supplies", False),
            (1, "SO-5600", (8, 1), (9, 1), "DRAFT", "6200", "2100.00", "Fall inventory", False),
        ],
        CLIENT_S_CORP_ID: [
            (0, "AWS-2025-01", (1, 1), (1, 31), "PAID", "6810", "2850.00", "AWS hosting - Jan", True),
            (0, "AWS-2025-02", (2, 1), (2, 28), "PAID", "6810", "3100.00", "AWS hosting - Feb", True),
            (0, "AWS-2025-06", (6, 1), (6, 30), "PAID", "6810", "3450.00", "AWS hosting - Jun", True),
            (1, "WW-Q1", (1, 1), (1, 31), "PAID", "6100", "7500.00", "Office rent Q1", True),
            (1, "WW-Q2", (4, 1), (4, 30), "PAID", "6100", "7500.00", "Office rent Q2", True),
            (2, "BCBS-2025", (1, 15), (2, 15), "PAID", "6050", "18000.00", "Health insurance - annual", True),
            (3, "CDW-4421", (3, 15), (4, 15), "PAID", "6810", "12500.00", "Laptops x5", True),
            (4, "ADP-Q3", (7, 1), (7, 31), "APPROVED", "6520", "1200.00", "Payroll processing Q3", False),
            (0, "AWS-2025-09", (9, 1), (9, 30), "PENDING_APPROVAL", "6810", "3600.00", "AWS hosting - Sep", False),
            (3, "CDW-4500", (10, 1), (11, 1), "DRAFT", "6810", "8500.00", "Server equipment", False),
        ],
        CLIENT_C_CORP_ID: [
            (0, "GR-10001", (1, 10), (2, 10), "PAID", "6200", "15600.00", "Industrial supplies Q1", True),
            (0, "GR-10045", (4, 10), (5, 10), "PAID", "6200", "18200.00", "Industrial supplies Q2", True),
            (1, "GNG-2025-03", (3, 5), (4, 5), "PAID", "6110", "3200.00", "Natural gas - March", True),
            (2, "HI-MFG-25", (1, 1), (1, 31), "PAID", "6300", "24000.00", "Mfg liability insurance", True),
            (3, "CAT-SVC-25", (2, 15), (3, 15), "PAID", "9000", "8500.00", "Equipment maintenance", True),
            (4, "FAST-2211", (5, 1), (6, 1), "PAID", "6200", "4300.00", "Fasteners and hardware", True),
            (5, "SYS-GA-Q2", (4, 1), (5, 1), "APPROVED", "6200", "6800.00", "Cafeteria supplies Q2", False),
            (0, "GR-10089", (7, 10), (8, 10), "PENDING_APPROVAL", "6200", "12400.00", "Industrial supplies Q3", False),
            (1, "GNG-2025-08", (8, 5), (9, 5), "PENDING_APPROVAL", "6110", "2800.00", "Natural gas - August", False),
            (4, "FAST-2300", (9, 15), (10, 15), "DRAFT", "6200", "5100.00", "Q4 fasteners order", False),
        ],
        CLIENT_PARTNERSHIP_ID: [
            (0, "REG-Q1", (1, 1), (1, 31), "PAID", "6100", "9000.00", "Office space Q1", True),
            (0, "REG-Q2", (4, 1), (4, 30), "PAID", "6100", "9000.00", "Office space Q2", True),
            (1, "LN-2025", (1, 15), (2, 15), "PAID", "6500", "6500.00", "Legal research annual", True),
            (2, "VZ-Q1", (1, 1), (1, 31), "PAID", "6120", "1800.00", "Telecom Q1", True),
            (2, "VZ-Q2", (4, 1), (4, 30), "PAID", "6120", "1950.00", "Telecom Q2", True),
            (3, "FDX-2025-04", (4, 15), (5, 15), "PAID", "6200", "850.00", "Shipping & printing", True),
            (1, "LN-Q3", (7, 1), (7, 31), "APPROVED", "6500", "1800.00", "Legal research Q3", False),
            (0, "REG-Q3", (7, 1), (7, 31), "PENDING_APPROVAL", "6100", "9000.00", "Office space Q3", False),
            (2, "VZ-Q3", (7, 1), (7, 31), "DRAFT", "6120", "2100.00", "Telecom Q3", False),
        ],
    }

    for client_id, bills in bills_spec.items():
        am = acct_maps[client_id]
        vendors = vendor_map[client_id]
        for vendor_idx, bill_num, bd, dd, status, exp_acct, amt, desc, has_payment in bills:
            bill_id = uuid.uuid4()
            amount = d(amt)
            session.add(Bill(
                id=bill_id,
                client_id=client_id,
                vendor_id=vendors[vendor_idx],
                bill_number=bill_num,
                bill_date=make_date(*bd),
                due_date=make_date(*dd),
                total_amount=amount,
                status=status,
            ))
            # Bill line
            session.add(BillLine(
                bill_id=bill_id,
                account_id=acct(am, exp_acct),
                description=desc,
                amount=amount,
            ))
            # Payment if paid
            if has_payment:
                session.add(BillPayment(
                    bill_id=bill_id,
                    payment_date=make_date(*dd),
                    amount=amount,
                    payment_method="ACH",
                    reference_number=f"PMT-{bill_num}",
                ))

    await session.flush()


# ---------------------------------------------------------------------------
# SEED INVOICES (AR)
# ---------------------------------------------------------------------------
async def seed_invoices(
    session: AsyncSession,
    acct_maps: dict[uuid.UUID, dict[str, uuid.UUID]],
) -> None:
    """Create invoices with lines and payments for each client."""
    print("  Creating invoices...")

    # (customer, inv_number, inv_date, due_date, status, rev_acct, qty, unit_price, desc, has_payment?)
    invoices_spec = {
        CLIENT_SOLE_PROP_ID: [
            ("Johnson Residence", "INV-1001", (1, 15), (2, 15), "PAID", "4000", "1", "4500.00", "Full landscape renovation", True),
            ("Smith Property Mgmt", "INV-1002", (2, 1), (3, 1), "PAID", "4000", "1", "2800.00", "Monthly maintenance - Feb", True),
            ("Smith Property Mgmt", "INV-1003", (3, 1), (4, 1), "PAID", "4000", "1", "2800.00", "Monthly maintenance - Mar", True),
            ("Williams Estate", "INV-1004", (3, 20), (4, 20), "PAID", "4000", "1", "8500.00", "Tree removal + stump grind", True),
            ("Peachtree HOA", "INV-1005", (4, 1), (5, 1), "PAID", "4000", "12", "1200.00", "HOA common area maint - Q2", True),
            ("Davis Commercial", "INV-1006", (5, 15), (6, 15), "PAID", "4000", "1", "6200.00", "Commercial property cleanup", True),
            ("Chen Residence", "INV-1007", (6, 1), (7, 1), "SENT", "4000", "1", "3400.00", "Irrigation installation", False),
            ("Smith Property Mgmt", "INV-1008", (7, 1), (8, 1), "OVERDUE", "4000", "1", "2800.00", "Monthly maintenance - Jul", False),
            ("Brown Residence", "INV-1009", (8, 15), (9, 15), "PENDING_APPROVAL", "4000", "1", "1950.00", "Lawn renovation", False),
            ("Peachtree HOA", "INV-1010", (9, 1), (10, 1), "DRAFT", "4000", "1", "14400.00", "HOA Q3 maintenance", False),
        ],
        CLIENT_S_CORP_ID: [
            ("Coca-Cola Enterprises", "ATS-2001", (1, 1), (1, 31), "PAID", "4000", "160", "150.00", "Dev hours - Jan", True),
            ("Delta Air Lines", "ATS-2002", (1, 15), (2, 15), "PAID", "4000", "200", "175.00", "Cloud migration", True),
            ("NCR Corporation", "ATS-2003", (2, 1), (3, 1), "PAID", "4000", "120", "150.00", "IT consulting - Feb", True),
            ("Home Depot HQ", "ATS-2004", (3, 1), (4, 1), "PAID", "4000", "180", "165.00", "App development Q1", True),
            ("Georgia-Pacific", "ATS-2005", (4, 1), (5, 1), "PAID", "4000", "140", "150.00", "System integration", True),
            ("Equifax Inc", "ATS-2006", (5, 1), (6, 1), "PAID", "4000", "200", "175.00", "Security audit", True),
            ("SunTrust Bank", "ATS-2007", (6, 1), (7, 1), "SENT", "4000", "160", "165.00", "Banking platform dev", False),
            ("Coca-Cola Enterprises", "ATS-2008", (7, 1), (8, 1), "OVERDUE", "4000", "180", "150.00", "Dev hours - Jul", False),
            ("Delta Air Lines", "ATS-2009", (8, 1), (9, 1), "PENDING_APPROVAL", "4000", "140", "175.00", "Consulting - Aug", False),
            ("NCR Corporation", "ATS-2010", (9, 1), (10, 1), "DRAFT", "4000", "100", "150.00", "IT support Q3", False),
        ],
        CLIENT_C_CORP_ID: [
            ("Ford Motor Company", "SMC-3001", (1, 10), (2, 10), "PAID", "4010", "500", "85.00", "Auto parts - Jan", True),
            ("General Electric", "SMC-3002", (2, 1), (3, 1), "PAID", "4010", "300", "120.00", "Electrical components", True),
            ("Boeing Company", "SMC-3003", (2, 15), (3, 15), "PAID", "4010", "200", "195.00", "Precision parts", True),
            ("Lockheed Martin", "SMC-3004", (3, 1), (4, 1), "PAID", "4010", "150", "250.00", "Defense components", True),
            ("Caterpillar Inc", "SMC-3005", (4, 1), (5, 1), "PAID", "4010", "400", "95.00", "Heavy equipment parts", True),
            ("John Deere", "SMC-3006", (5, 1), (6, 1), "PAID", "4010", "350", "88.00", "Agricultural parts", True),
            ("3M Company", "SMC-3007", (6, 1), (7, 1), "SENT", "4010", "250", "110.00", "Industrial supplies", False),
            ("Ford Motor Company", "SMC-3008", (7, 1), (8, 1), "OVERDUE", "4010", "600", "85.00", "Auto parts - Jul", False),
            ("General Electric", "SMC-3009", (8, 1), (9, 1), "PENDING_APPROVAL", "4010", "280", "120.00", "Components - Aug", False),
            ("Boeing Company", "SMC-3010", (9, 1), (10, 1), "DRAFT", "4010", "180", "195.00", "Q3 precision parts", False),
        ],
        CLIENT_PARTNERSHIP_ID: [
            ("Turner Broadcasting", "BPG-4001", (1, 1), (1, 31), "PAID", "4000", "80", "250.00", "Advisory services - Jan", True),
            ("Chick-fil-A Inc", "BPG-4002", (2, 1), (3, 1), "PAID", "4000", "60", "275.00", "Tax planning Q1", True),
            ("Arby's Restaurant Grp", "BPG-4003", (3, 1), (4, 1), "PAID", "4000", "40", "250.00", "Business consulting", True),
            ("Intercontinental Exchange", "BPG-4004", (4, 1), (5, 1), "PAID", "4000", "100", "300.00", "Financial advisory Q2", True),
            ("Genuine Parts Company", "BPG-4005", (5, 1), (6, 1), "PAID", "4000", "50", "275.00", "Tax compliance", True),
            ("Aflac Inc", "BPG-4006", (6, 1), (7, 1), "SENT", "4000", "70", "250.00", "Insurance advisory", False),
            ("Carter's Inc", "BPG-4007", (7, 1), (8, 1), "OVERDUE", "4000", "45", "275.00", "Business advisory - Jul", False),
            ("UPS Supply Chain", "BPG-4008", (8, 1), (9, 1), "PENDING_APPROVAL", "4000", "90", "250.00", "Logistics consulting", False),
            ("Turner Broadcasting", "BPG-4009", (9, 1), (10, 1), "DRAFT", "4000", "60", "250.00", "Advisory Q3", False),
        ],
    }

    for client_id, invoices in invoices_spec.items():
        am = acct_maps[client_id]
        for cust, inv_num, id_, dd, status, rev_acct, qty, up, desc, has_pmt in invoices:
            inv_id = uuid.uuid4()
            quantity = d(qty)
            unit_price = d(up)
            line_amount = quantity * unit_price
            session.add(Invoice(
                id=inv_id,
                client_id=client_id,
                customer_name=cust,
                invoice_number=inv_num,
                invoice_date=make_date(*id_),
                due_date=make_date(*dd),
                total_amount=line_amount,
                status=status,
            ))
            session.add(InvoiceLine(
                invoice_id=inv_id,
                account_id=acct(am, rev_acct),
                description=desc,
                quantity=quantity,
                unit_price=unit_price,
                amount=line_amount,
            ))
            if has_pmt:
                session.add(InvoicePayment(
                    invoice_id=inv_id,
                    payment_date=make_date(*dd),
                    amount=line_amount,
                    payment_method="Wire",
                    reference_number=f"RCV-{inv_num}",
                ))

    await session.flush()


# ---------------------------------------------------------------------------
# SEED JOURNAL ENTRIES (GL)
# ---------------------------------------------------------------------------
async def seed_journal_entries(
    session: AsyncSession,
    acct_maps: dict[uuid.UUID, dict[str, uuid.UUID]],
) -> None:
    """Create journal entries with balanced debit/credit lines.

    Strategy: Insert as DRAFT, add lines, then UPDATE to POSTED.
    The DB trigger validates balance on status change to POSTED.
    """
    print("  Creating journal entries...")

    # Per client: list of (entry_date, description, ref, status, lines)
    # lines: [(acct_number, debit, credit)]
    je_spec = {
        CLIENT_SOLE_PROP_ID: [
            # Revenue recognition
            ((1, 15), "Landscape renovation revenue", "JE-001", "POSTED", [
                ("1100", "4500.00", "0.00"),   # DR Accounts Receivable
                ("4000", "0.00", "4500.00"),    # CR Service Revenue
            ]),
            ((2, 1), "Monthly maintenance revenue - Feb", "JE-002", "POSTED", [
                ("1100", "2800.00", "0.00"),
                ("4000", "0.00", "2800.00"),
            ]),
            ((3, 1), "Monthly maintenance revenue - Mar", "JE-003", "POSTED", [
                ("1100", "2800.00", "0.00"),
                ("4000", "0.00", "2800.00"),
            ]),
            ((3, 20), "Tree removal revenue", "JE-004", "POSTED", [
                ("1100", "8500.00", "0.00"),
                ("4000", "0.00", "8500.00"),
            ]),
            ((4, 1), "HOA maintenance revenue Q2", "JE-005", "POSTED", [
                ("1100", "14400.00", "0.00"),
                ("4000", "0.00", "14400.00"),
            ]),
            ((5, 15), "Commercial cleanup revenue", "JE-006", "POSTED", [
                ("1100", "6200.00", "0.00"),
                ("4000", "0.00", "6200.00"),
            ]),
            # Cash collections
            ((2, 15), "Collected AR - Johnson", "JE-007", "POSTED", [
                ("1000", "4500.00", "0.00"),    # DR Cash
                ("1100", "0.00", "4500.00"),     # CR AR
            ]),
            ((3, 5), "Collected AR - Smith Feb", "JE-008", "POSTED", [
                ("1000", "2800.00", "0.00"),
                ("1100", "0.00", "2800.00"),
            ]),
            # Expense recognition
            ((1, 15), "Supplies purchase - Home Depot", "JE-009", "POSTED", [
                ("6200", "2450.00", "0.00"),    # DR Supplies
                ("2000", "0.00", "2450.00"),     # CR AP
            ]),
            ((1, 5), "Electric bill Jan", "JE-010", "POSTED", [
                ("6110", "485.00", "0.00"),      # DR Utilities
                ("2000", "0.00", "485.00"),
            ]),
            ((1, 1), "Insurance annual premium", "JE-011", "POSTED", [
                ("6300", "4800.00", "0.00"),     # DR Insurance
                ("1000", "0.00", "4800.00"),     # CR Cash
            ]),
            # Payroll entries
            ((1, 31), "Payroll Jan - gross wages", "JE-012", "POSTED", [
                ("6000", "8500.00", "0.00"),     # DR Salaries
                ("2300", "0.00", "1050.00"),     # CR Federal tax payable
                ("2310", "0.00", "425.00"),      # CR State tax payable
                ("2320", "0.00", "527.00"),      # CR FICA payable
                ("2360", "0.00", "123.25"),      # CR Medicare payable
                ("1000", "0.00", "6374.75"),     # CR Cash (net pay)
            ]),
            ((2, 28), "Payroll Feb - gross wages", "JE-013", "POSTED", [
                ("6000", "8500.00", "0.00"),
                ("2300", "0.00", "1050.00"),
                ("2310", "0.00", "425.00"),
                ("2320", "0.00", "527.00"),
                ("2360", "0.00", "123.25"),
                ("1000", "0.00", "6374.75"),
            ]),
            # Owner's draw
            ((3, 15), "Owner's draw - March", "JE-014", "POSTED", [
                ("3010", "5000.00", "0.00"),     # DR Owner's Draw
                ("1000", "0.00", "5000.00"),
            ]),
            # Sales tax collected
            ((3, 31), "Sales tax Q1 - collected", "JE-015", "POSTED", [
                ("1000", "1200.00", "0.00"),     # DR Cash
                ("2400", "0.00", "1200.00"),     # CR Sales tax payable
            ]),
            # Depreciation
            ((6, 30), "Depreciation - equipment H1", "JE-016", "POSTED", [
                ("6600", "2500.00", "0.00"),     # DR Depreciation
                ("1550", "0.00", "2500.00"),     # CR Accum depreciation
            ]),
            # Pending / Draft entries
            ((8, 15), "Summer supplies estimate", "JE-017", "PENDING_APPROVAL", [
                ("6200", "1650.00", "0.00"),
                ("2000", "0.00", "1650.00"),
            ]),
            ((9, 1), "Q3 revenue accrual", "JE-018", "DRAFT", [
                ("1100", "15000.00", "0.00"),
                ("4000", "0.00", "15000.00"),
            ]),
            # Additional revenue to hit ~180K
            ((6, 1), "Monthly maintenance revenue - Jun", "JE-019", "POSTED", [
                ("1100", "2800.00", "0.00"),
                ("4000", "0.00", "2800.00"),
            ]),
            ((4, 15), "Residential landscaping batch", "JE-020", "POSTED", [
                ("1100", "12000.00", "0.00"),
                ("4000", "0.00", "12000.00"),
            ]),
            # More expenses to hit ~140K
            ((3, 10), "Bulk supplies purchase", "JE-021", "POSTED", [
                ("6200", "3200.00", "0.00"),
                ("2000", "0.00", "3200.00"),
            ]),
            ((4, 1), "Vehicle fuel Q1", "JE-022", "POSTED", [
                ("6720", "1800.00", "0.00"),     # DR Auto expense
                ("1000", "0.00", "1800.00"),
            ]),
            ((5, 1), "Equipment repair", "JE-023", "POSTED", [
                ("9000", "2200.00", "0.00"),     # DR Miscellaneous (repairs)
                ("1000", "0.00", "2200.00"),
            ]),
            ((6, 15), "Advertising - Nextdoor ads", "JE-024", "POSTED", [
                ("6400", "1500.00", "0.00"),     # DR Advertising
                ("1000", "0.00", "1500.00"),
            ]),
        ],
        CLIENT_S_CORP_ID: [
            # Revenue - tech consulting
            ((1, 1), "Coca-Cola dev hours - Jan", "JE-101", "POSTED", [
                ("1100", "24000.00", "0.00"),
                ("4000", "0.00", "24000.00"),
            ]),
            ((1, 15), "Delta cloud migration", "JE-102", "POSTED", [
                ("1100", "35000.00", "0.00"),
                ("4000", "0.00", "35000.00"),
            ]),
            ((2, 1), "NCR consulting - Feb", "JE-103", "POSTED", [
                ("1100", "18000.00", "0.00"),
                ("4000", "0.00", "18000.00"),
            ]),
            ((3, 1), "Home Depot app dev Q1", "JE-104", "POSTED", [
                ("1100", "29700.00", "0.00"),
                ("4000", "0.00", "29700.00"),
            ]),
            ((4, 1), "GA-Pacific integration", "JE-105", "POSTED", [
                ("1100", "21000.00", "0.00"),
                ("4000", "0.00", "21000.00"),
            ]),
            ((5, 1), "Equifax security audit", "JE-106", "POSTED", [
                ("1100", "35000.00", "0.00"),
                ("4000", "0.00", "35000.00"),
            ]),
            # Cash collections
            ((2, 1), "Collected AR - Coca-Cola Jan", "JE-107", "POSTED", [
                ("1000", "24000.00", "0.00"),
                ("1100", "0.00", "24000.00"),
            ]),
            ((2, 20), "Collected AR - Delta", "JE-108", "POSTED", [
                ("1000", "35000.00", "0.00"),
                ("1100", "0.00", "35000.00"),
            ]),
            # Expenses
            ((1, 1), "AWS hosting - Jan", "JE-109", "POSTED", [
                ("6810", "2850.00", "0.00"),
                ("2000", "0.00", "2850.00"),
            ]),
            ((1, 1), "Office rent Q1", "JE-110", "POSTED", [
                ("6100", "7500.00", "0.00"),
                ("2000", "0.00", "7500.00"),
            ]),
            ((1, 15), "Health insurance annual", "JE-111", "POSTED", [
                ("6050", "18000.00", "0.00"),
                ("1000", "0.00", "18000.00"),
            ]),
            # Payroll
            ((1, 31), "Payroll Jan", "JE-112", "POSTED", [
                ("6000", "22000.00", "0.00"),
                ("2300", "0.00", "2750.00"),
                ("2310", "0.00", "1100.00"),
                ("2320", "0.00", "1364.00"),
                ("2360", "0.00", "319.00"),
                ("1000", "0.00", "16467.00"),
            ]),
            ((2, 28), "Payroll Feb", "JE-113", "POSTED", [
                ("6000", "22000.00", "0.00"),
                ("2300", "0.00", "2750.00"),
                ("2310", "0.00", "1100.00"),
                ("2320", "0.00", "1364.00"),
                ("2360", "0.00", "319.00"),
                ("1000", "0.00", "16467.00"),
            ]),
            # Equipment purchase
            ((3, 15), "Laptops purchase", "JE-114", "POSTED", [
                ("6810", "12500.00", "0.00"),
                ("2000", "0.00", "12500.00"),
            ]),
            # Depreciation
            ((6, 30), "Depreciation - equipment H1", "JE-115", "POSTED", [
                ("6600", "4200.00", "0.00"),
                ("1550", "0.00", "4200.00"),
            ]),
            # Shareholder distribution
            ((6, 15), "Shareholder distribution Q2", "JE-116", "POSTED", [
                ("3400", "15000.00", "0.00"),
                ("1000", "0.00", "15000.00"),
            ]),
            # More revenue to hit ~350K
            ((6, 15), "SunTrust platform dev", "JE-117", "POSTED", [
                ("1100", "26400.00", "0.00"),
                ("4000", "0.00", "26400.00"),
            ]),
            ((5, 15), "Additional consulting revenue", "JE-118", "POSTED", [
                ("1100", "45000.00", "0.00"),
                ("4000", "0.00", "45000.00"),
            ]),
            # More expenses
            ((4, 1), "Office rent Q2", "JE-119", "POSTED", [
                ("6100", "7500.00", "0.00"),
                ("2000", "0.00", "7500.00"),
            ]),
            ((4, 15), "Software licenses Q2", "JE-120", "POSTED", [
                ("6800", "4500.00", "0.00"),
                ("1000", "0.00", "4500.00"),
            ]),
            # Pending
            ((8, 1), "AWS Sep - pending approval", "JE-121", "PENDING_APPROVAL", [
                ("6400", "3600.00", "0.00"),
                ("2000", "0.00", "3600.00"),
            ]),
            ((9, 1), "Q3 revenue accrual", "JE-122", "DRAFT", [
                ("1100", "50000.00", "0.00"),
                ("4000", "0.00", "50000.00"),
            ]),
        ],
        CLIENT_C_CORP_ID: [
            # Revenue - manufacturing sales
            ((1, 10), "Ford auto parts - Jan", "JE-201", "POSTED", [
                ("1100", "42500.00", "0.00"),
                ("4010", "0.00", "42500.00"),
            ]),
            ((2, 1), "GE electrical components", "JE-202", "POSTED", [
                ("1100", "36000.00", "0.00"),
                ("4010", "0.00", "36000.00"),
            ]),
            ((2, 15), "Boeing precision parts", "JE-203", "POSTED", [
                ("1100", "39000.00", "0.00"),
                ("4010", "0.00", "39000.00"),
            ]),
            ((3, 1), "Lockheed defense components", "JE-204", "POSTED", [
                ("1100", "37500.00", "0.00"),
                ("4010", "0.00", "37500.00"),
            ]),
            ((4, 1), "Caterpillar equipment parts", "JE-205", "POSTED", [
                ("1100", "38000.00", "0.00"),
                ("4010", "0.00", "38000.00"),
            ]),
            ((5, 1), "John Deere agricultural", "JE-206", "POSTED", [
                ("1100", "30800.00", "0.00"),
                ("4010", "0.00", "30800.00"),
            ]),
            # Cash collections
            ((2, 10), "Collected AR - Ford Jan", "JE-207", "POSTED", [
                ("1000", "42500.00", "0.00"),
                ("1100", "0.00", "42500.00"),
            ]),
            ((3, 5), "Collected AR - GE", "JE-208", "POSTED", [
                ("1000", "36000.00", "0.00"),
                ("1100", "0.00", "36000.00"),
            ]),
            # COGS
            ((1, 31), "Cost of goods sold - Jan", "JE-209", "POSTED", [
                ("5000", "28000.00", "0.00"),    # DR COGS
                ("1300", "0.00", "28000.00"),     # CR Inventory
            ]),
            ((2, 28), "Cost of goods sold - Feb", "JE-210", "POSTED", [
                ("5000", "32000.00", "0.00"),
                ("1300", "0.00", "32000.00"),
            ]),
            ((3, 31), "Cost of goods sold - Mar", "JE-211", "POSTED", [
                ("5000", "30000.00", "0.00"),
                ("1300", "0.00", "30000.00"),
            ]),
            # Expenses
            ((1, 10), "Industrial supplies Q1", "JE-212", "POSTED", [
                ("6200", "15600.00", "0.00"),
                ("2000", "0.00", "15600.00"),
            ]),
            ((3, 5), "Natural gas - March", "JE-213", "POSTED", [
                ("6110", "3200.00", "0.00"),
                ("2000", "0.00", "3200.00"),
            ]),
            ((1, 1), "Mfg insurance annual", "JE-214", "POSTED", [
                ("6300", "24000.00", "0.00"),
                ("1000", "0.00", "24000.00"),
            ]),
            # Payroll
            ((1, 31), "Payroll Jan", "JE-215", "POSTED", [
                ("6000", "35000.00", "0.00"),
                ("2300", "0.00", "4375.00"),
                ("2310", "0.00", "1750.00"),
                ("2320", "0.00", "2170.00"),
                ("2360", "0.00", "507.50"),
                ("1000", "0.00", "26197.50"),
            ]),
            ((2, 28), "Payroll Feb", "JE-216", "POSTED", [
                ("6000", "35000.00", "0.00"),
                ("2300", "0.00", "4375.00"),
                ("2310", "0.00", "1750.00"),
                ("2320", "0.00", "2170.00"),
                ("2360", "0.00", "507.50"),
                ("1000", "0.00", "26197.50"),
            ]),
            # Depreciation
            ((6, 30), "Depreciation - machinery H1", "JE-217", "POSTED", [
                ("6600", "15000.00", "0.00"),
                ("1550", "0.00", "15000.00"),
            ]),
            # More revenue
            ((6, 1), "3M industrial supplies", "JE-218", "POSTED", [
                ("1100", "27500.00", "0.00"),
                ("4010", "0.00", "27500.00"),
            ]),
            ((6, 15), "Additional mfg sales Q2", "JE-219", "POSTED", [
                ("1100", "48000.00", "0.00"),
                ("4010", "0.00", "48000.00"),
            ]),
            # More COGS
            ((4, 30), "COGS - Apr", "JE-220", "POSTED", [
                ("5000", "25000.00", "0.00"),
                ("1300", "0.00", "25000.00"),
            ]),
            ((5, 31), "COGS - May", "JE-221", "POSTED", [
                ("5000", "22000.00", "0.00"),
                ("1300", "0.00", "22000.00"),
            ]),
            # Sales tax
            ((3, 31), "Sales tax Q1 collected", "JE-222", "POSTED", [
                ("1000", "4500.00", "0.00"),
                ("2400", "0.00", "4500.00"),
            ]),
            # Retained earnings
            ((1, 1), "Opening retained earnings", "JE-223", "POSTED", [
                ("1000", "50000.00", "0.00"),
                ("3200", "0.00", "50000.00"),
            ]),
            # Pending / Draft
            ((8, 10), "Industrial supplies Q3 - pending", "JE-224", "PENDING_APPROVAL", [
                ("6200", "12400.00", "0.00"),
                ("2000", "0.00", "12400.00"),
            ]),
            ((9, 1), "Q3 revenue accrual", "JE-225", "DRAFT", [
                ("1100", "55000.00", "0.00"),
                ("4010", "0.00", "55000.00"),
            ]),
        ],
        CLIENT_PARTNERSHIP_ID: [
            # Revenue - advisory/consulting
            ((1, 1), "Turner advisory - Jan", "JE-301", "POSTED", [
                ("1100", "20000.00", "0.00"),
                ("4000", "0.00", "20000.00"),
            ]),
            ((2, 1), "Chick-fil-A tax planning", "JE-302", "POSTED", [
                ("1100", "16500.00", "0.00"),
                ("4000", "0.00", "16500.00"),
            ]),
            ((3, 1), "Arby's consulting", "JE-303", "POSTED", [
                ("1100", "10000.00", "0.00"),
                ("4000", "0.00", "10000.00"),
            ]),
            ((4, 1), "ICE financial advisory Q2", "JE-304", "POSTED", [
                ("1100", "30000.00", "0.00"),
                ("4000", "0.00", "30000.00"),
            ]),
            ((5, 1), "Genuine Parts compliance", "JE-305", "POSTED", [
                ("1100", "13750.00", "0.00"),
                ("4000", "0.00", "13750.00"),
            ]),
            # Cash collections
            ((2, 1), "Collected AR - Turner Jan", "JE-306", "POSTED", [
                ("1000", "20000.00", "0.00"),
                ("1100", "0.00", "20000.00"),
            ]),
            ((3, 5), "Collected AR - Chick-fil-A", "JE-307", "POSTED", [
                ("1000", "16500.00", "0.00"),
                ("1100", "0.00", "16500.00"),
            ]),
            # Expenses
            ((1, 1), "Office space Q1", "JE-308", "POSTED", [
                ("6100", "9000.00", "0.00"),
                ("2000", "0.00", "9000.00"),
            ]),
            ((4, 1), "Office space Q2", "JE-309", "POSTED", [
                ("6100", "9000.00", "0.00"),
                ("2000", "0.00", "9000.00"),
            ]),
            ((1, 15), "Legal research annual", "JE-310", "POSTED", [
                ("6500", "6500.00", "0.00"),
                ("2000", "0.00", "6500.00"),
            ]),
            ((1, 1), "Telecom Q1", "JE-311", "POSTED", [
                ("6120", "1800.00", "0.00"),
                ("2000", "0.00", "1800.00"),
            ]),
            # Payroll
            ((1, 31), "Payroll Jan", "JE-312", "POSTED", [
                ("6000", "16000.00", "0.00"),
                ("2300", "0.00", "2000.00"),
                ("2310", "0.00", "800.00"),
                ("2320", "0.00", "992.00"),
                ("2360", "0.00", "232.00"),
                ("1000", "0.00", "11976.00"),
            ]),
            ((2, 28), "Payroll Feb", "JE-313", "POSTED", [
                ("6000", "16000.00", "0.00"),
                ("2300", "0.00", "2000.00"),
                ("2310", "0.00", "800.00"),
                ("2320", "0.00", "992.00"),
                ("2360", "0.00", "232.00"),
                ("1000", "0.00", "11976.00"),
            ]),
            # Partner draws
            ((3, 15), "Partner draw - Partner A", "JE-314", "POSTED", [
                ("3310", "8000.00", "0.00"),
                ("1000", "0.00", "8000.00"),
            ]),
            ((3, 15), "Partner draw - Partner B", "JE-315", "POSTED", [
                ("3310", "8000.00", "0.00"),
                ("1000", "0.00", "8000.00"),
            ]),
            # Member capital
            ((1, 1), "Opening member capital", "JE-316", "POSTED", [
                ("1000", "40000.00", "0.00"),
                ("3300", "0.00", "40000.00"),
            ]),
            # Depreciation
            ((6, 30), "Depreciation - office equip H1", "JE-317", "POSTED", [
                ("6600", "1800.00", "0.00"),
                ("1550", "0.00", "1800.00"),
            ]),
            # More revenue
            ((6, 1), "Aflac insurance advisory", "JE-318", "POSTED", [
                ("1100", "17500.00", "0.00"),
                ("4000", "0.00", "17500.00"),
            ]),
            ((5, 15), "Additional advisory revenue Q2", "JE-319", "POSTED", [
                ("1100", "22000.00", "0.00"),
                ("4000", "0.00", "22000.00"),
            ]),
            # More expenses
            ((4, 1), "Telecom Q2", "JE-320", "POSTED", [
                ("6120", "1950.00", "0.00"),
                ("2000", "0.00", "1950.00"),
            ]),
            ((4, 15), "Shipping & printing", "JE-321", "POSTED", [
                ("6200", "850.00", "0.00"),
                ("2000", "0.00", "850.00"),
            ]),
            ((5, 1), "Professional development", "JE-322", "POSTED", [
                ("6020", "3200.00", "0.00"),
                ("1000", "0.00", "3200.00"),
            ]),
            # Pending / Draft
            ((8, 1), "Office space Q3 - pending", "JE-323", "PENDING_APPROVAL", [
                ("6100", "9000.00", "0.00"),
                ("2000", "0.00", "9000.00"),
            ]),
            ((9, 1), "Q3 revenue accrual", "JE-324", "DRAFT", [
                ("1100", "25000.00", "0.00"),
                ("4000", "0.00", "25000.00"),
            ]),
        ],
    }

    for client_id, entries in je_spec.items():
        am = acct_maps[client_id]
        for dt, desc, ref, status, lines in entries:
            je_id = uuid.uuid4()

            # Insert as DRAFT first (trigger only fires when changing to POSTED)
            je = JournalEntry(
                id=je_id,
                client_id=client_id,
                entry_date=make_date(*dt),
                description=desc,
                reference_number=ref,
                status=JournalEntryStatus.DRAFT,
                created_by=USER_CPA_ID,
                approved_by=USER_CPA_ID if status == "POSTED" else None,
            )
            session.add(je)
            await session.flush()

            # Add lines
            for acct_num, debit_amt, credit_amt in lines:
                session.add(JournalEntryLine(
                    journal_entry_id=je_id,
                    account_id=acct(am, acct_num),
                    debit=d(debit_amt),
                    credit=d(credit_amt),
                ))
            await session.flush()

            # Now update status (trigger validates balance for POSTED)
            if status != "DRAFT":
                je.status = JournalEntryStatus(status)
                await session.flush()

    await session.flush()


# ---------------------------------------------------------------------------
# SEED BANK ACCOUNTS & TRANSACTIONS
# ---------------------------------------------------------------------------
async def seed_bank_data(
    session: AsyncSession,
    acct_maps: dict[uuid.UUID, dict[str, uuid.UUID]],
) -> None:
    """Create bank accounts, transactions, and reconciliation sessions."""
    print("  Creating bank accounts and transactions...")

    bank_data = {
        CLIENT_SOLE_PROP_ID: [
            ("Peachtree Business Checking", "Wells Fargo", "1000"),
        ],
        CLIENT_S_CORP_ID: [
            ("ATS Operating Account", "Bank of America", "1000"),
            ("ATS Payroll Account", "Bank of America", "1010"),
        ],
        CLIENT_C_CORP_ID: [
            ("SMC Main Operating", "SunTrust", "1000"),
            ("SMC Payroll Account", "SunTrust", "1010"),
        ],
        CLIENT_PARTNERSHIP_ID: [
            ("BPG Business Account", "Truist Bank", "1000"),
        ],
    }

    for client_id, accounts in bank_data.items():
        am = acct_maps[client_id]
        for acct_name, institution, gl_acct_num in accounts:
            ba_id = uuid.uuid4()
            session.add(BankAccount(
                id=ba_id,
                client_id=client_id,
                account_name=acct_name,
                institution_name=institution,
                account_id=acct(am, gl_acct_num),
            ))
            await session.flush()

            # Bank transactions — mix of reconciled and unreconciled
            txns = _generate_bank_transactions(ba_id, acct_name)
            for txn in txns:
                session.add(txn)
            await session.flush()

            # Reconciliation sessions
            session.add(Reconciliation(
                bank_account_id=ba_id,
                statement_date=make_date(3, 31),
                statement_balance=d("25000.00"),
                reconciled_balance=d("25000.00"),
                status="COMPLETED",
                completed_at=datetime(2025, 4, 5, tzinfo=timezone.utc),
                completed_by=USER_CPA_ID,
            ))
            session.add(Reconciliation(
                bank_account_id=ba_id,
                statement_date=make_date(6, 30),
                statement_balance=d("32000.00"),
                status="IN_PROGRESS",
            ))

    await session.flush()


def _generate_bank_transactions(ba_id: uuid.UUID, acct_name: str) -> list[BankTransaction]:
    """Generate realistic bank transactions for a bank account."""
    txns = []
    now_utc = datetime.now(timezone.utc)

    # Deposits (CREDIT type in bank terms)
    deposits = [
        (make_date(1, 15), "Client Payment - Wire", "15000.00"),
        (make_date(1, 31), "Client Payment - ACH", "8500.00"),
        (make_date(2, 15), "Client Payment - Check", "12000.00"),
        (make_date(2, 28), "Client Payment - Wire", "22000.00"),
        (make_date(3, 15), "Client Payment - ACH", "9500.00"),
        (make_date(3, 31), "Client Payment - Wire", "18000.00"),
        (make_date(4, 15), "Client Payment - Check", "14000.00"),
        (make_date(5, 1), "Client Payment - Wire", "25000.00"),
        (make_date(5, 15), "Client Payment - ACH", "11000.00"),
        (make_date(6, 1), "Client Payment - Wire", "16000.00"),
    ]
    # Withdrawals (DEBIT type in bank terms)
    debits = [
        (make_date(1, 5), "Electric Payment - Auto", "485.00"),
        (make_date(1, 10), "Vendor Payment - ACH", "2450.00"),
        (make_date(1, 31), "Payroll - ADP", "6374.75"),
        (make_date(2, 5), "Insurance Premium", "400.00"),
        (make_date(2, 15), "Vendor Payment - Check", "3200.00"),
        (make_date(2, 28), "Payroll - ADP", "6374.75"),
        (make_date(3, 5), "Utilities Payment", "612.00"),
        (make_date(3, 15), "Owner Distribution", "5000.00"),
        (make_date(3, 31), "Quarterly Taxes", "3500.00"),
        (make_date(4, 1), "Rent Payment", "2500.00"),
        (make_date(4, 15), "Vendor Payment - ACH", "1800.00"),
        (make_date(5, 1), "Payroll - ADP", "6374.75"),
        (make_date(6, 15), "Equipment Purchase", "4500.00"),
        (make_date(7, 1), "Vendor Payment - ACH", "3200.00"),
        (make_date(7, 15), "Unmatched debit - needs review", "1250.00"),
    ]

    # Reconciled through Q1 (March 31)
    for dt, desc, amt in deposits:
        is_q1 = dt <= make_date(3, 31)
        txns.append(BankTransaction(
            bank_account_id=ba_id,
            transaction_date=dt,
            description=desc,
            amount=d(amt),
            transaction_type="CREDIT",
            is_reconciled=is_q1,
            reconciled_at=now_utc if is_q1 else None,
        ))

    for dt, desc, amt in debits:
        is_q1 = dt <= make_date(3, 31)
        txns.append(BankTransaction(
            bank_account_id=ba_id,
            transaction_date=dt,
            description=desc,
            amount=d(amt),
            transaction_type="DEBIT",
            is_reconciled=is_q1,
            reconciled_at=now_utc if is_q1 else None,
        ))

    return txns


# ---------------------------------------------------------------------------
# SEED EMPLOYEES
# ---------------------------------------------------------------------------
async def seed_employees(
    session: AsyncSession,
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Create employees per client. Returns {client_id: [employee_ids]}."""
    print("  Creating employees...")
    emp_map: dict[uuid.UUID, list[uuid.UUID]] = {}

    employees_spec = {
        CLIENT_SOLE_PROP_ID: [
            ("Marcus", "Williams", "SINGLE", 0, "22.00", "HOURLY", (2024, 3, 15)),
            ("Jasmine", "Carter", "MARRIED", 2, "25.00", "HOURLY", (2023, 6, 1)),
            ("David", "Nguyen", "SINGLE", 1, "20.00", "HOURLY", (2025, 1, 15)),
        ],
        CLIENT_S_CORP_ID: [
            ("Michael", "Chen", "MARRIED", 3, "95000.00", "SALARY", (2022, 1, 1)),
            ("Jessica", "Rodriguez", "SINGLE", 1, "85000.00", "SALARY", (2023, 3, 15)),
            ("Brandon", "Taylor", "SINGLE", 0, "78000.00", "SALARY", (2023, 9, 1)),
            ("Amanda", "Lee", "MARRIED", 2, "72000.00", "SALARY", (2024, 2, 1)),
            ("Tyler", "Jackson", "HEAD_OF_HOUSEHOLD", 1, "65000.00", "SALARY", (2024, 8, 15)),
        ],
        CLIENT_C_CORP_ID: [
            ("Robert", "Thompson", "MARRIED", 4, "68000.00", "SALARY", (2020, 5, 1)),
            ("Maria", "Garcia", "SINGLE", 0, "55000.00", "SALARY", (2021, 8, 15)),
            ("James", "Wilson", "MARRIED", 2, "62000.00", "SALARY", (2022, 1, 1)),
            ("Patricia", "Anderson", "SINGLE", 1, "48000.00", "SALARY", (2023, 4, 1)),
            ("Kevin", "Brown", "HEAD_OF_HOUSEHOLD", 2, "58000.00", "SALARY", (2023, 7, 15)),
        ],
        CLIENT_PARTNERSHIP_ID: [
            ("Rachel", "Kim", "SINGLE", 0, "75000.00", "SALARY", (2023, 1, 15)),
            ("Daniel", "Martinez", "MARRIED", 2, "82000.00", "SALARY", (2022, 6, 1)),
            ("Stephanie", "Davis", "SINGLE", 1, "45.00", "HOURLY", (2024, 3, 1)),
        ],
    }

    for client_id, employees in employees_spec.items():
        ids = []
        for first, last, filing, allow, rate, pay_type, hire_dt in employees:
            eid = uuid.uuid4()
            session.add(Employee(
                id=eid,
                client_id=client_id,
                first_name=first,
                last_name=last,
                filing_status=filing,
                allowances=allow,
                pay_rate=d(rate),
                pay_type=pay_type,
                hire_date=date(*hire_dt),
                is_active=True,
            ))
            ids.append(eid)
        emp_map[client_id] = ids

    await session.flush()
    return emp_map


# ---------------------------------------------------------------------------
# SEED PAYROLL RUNS
# ---------------------------------------------------------------------------
async def seed_payroll(
    session: AsyncSession,
    emp_map: dict[uuid.UUID, list[uuid.UUID]],
) -> None:
    """Create payroll runs with items per client."""
    print("  Creating payroll runs...")

    # Payroll runs: (period_start, period_end, pay_date, status)
    runs_spec = {
        CLIENT_SOLE_PROP_ID: [
            ((1, 1), (1, 15), (1, 20), "FINALIZED"),
            ((1, 16), (1, 31), (2, 5), "FINALIZED"),
            ((2, 1), (2, 15), (2, 20), "FINALIZED"),
            ((2, 16), (2, 28), (3, 5), "FINALIZED"),
            ((3, 1), (3, 15), (3, 20), "PENDING_APPROVAL"),
            ((3, 16), (3, 31), (4, 5), "DRAFT"),
        ],
        CLIENT_S_CORP_ID: [
            ((1, 1), (1, 31), (2, 5), "FINALIZED"),
            ((2, 1), (2, 28), (3, 5), "FINALIZED"),
            ((3, 1), (3, 31), (4, 5), "FINALIZED"),
            ((4, 1), (4, 30), (5, 5), "FINALIZED"),
            ((5, 1), (5, 31), (6, 5), "PENDING_APPROVAL"),
            ((6, 1), (6, 30), (7, 5), "DRAFT"),
        ],
        CLIENT_C_CORP_ID: [
            ((1, 1), (1, 31), (2, 5), "FINALIZED"),
            ((2, 1), (2, 28), (3, 5), "FINALIZED"),
            ((3, 1), (3, 31), (4, 5), "FINALIZED"),
            ((4, 1), (4, 30), (5, 5), "FINALIZED"),
            ((5, 1), (5, 31), (6, 5), "PENDING_APPROVAL"),
            ((6, 1), (6, 30), (7, 5), "DRAFT"),
        ],
        CLIENT_PARTNERSHIP_ID: [
            ((1, 1), (1, 31), (2, 5), "FINALIZED"),
            ((2, 1), (2, 28), (3, 5), "FINALIZED"),
            ((3, 1), (3, 31), (4, 5), "FINALIZED"),
            ((4, 1), (4, 30), (5, 5), "PENDING_APPROVAL"),
            ((5, 1), (5, 31), (6, 5), "DRAFT"),
        ],
    }

    now_utc = datetime.now(timezone.utc)

    for client_id, runs in runs_spec.items():
        employees = emp_map[client_id]
        for ps, pe, pd, status in runs:
            run_id = uuid.uuid4()
            session.add(PayrollRun(
                id=run_id,
                client_id=client_id,
                pay_period_start=make_date(*ps),
                pay_period_end=make_date(*pe),
                pay_date=make_date(*pd),
                status=status,
                finalized_by=USER_CPA_ID if status == "FINALIZED" else None,
                finalized_at=now_utc if status == "FINALIZED" else None,
            ))
            await session.flush()

            # Create payroll items for each employee
            for emp_id in employees:
                # Look up employee to determine gross pay
                emp_result = await session.execute(
                    select(Employee).where(Employee.id == emp_id)
                )
                emp = emp_result.scalar_one()

                if emp.pay_type == "HOURLY":
                    # Biweekly: 80 hours, Monthly: 173 hours
                    period_days = (make_date(*pe) - make_date(*ps)).days + 1
                    hours = 80 if period_days <= 16 else 173
                    gross = emp.pay_rate * hours
                else:
                    # Salaried: divide annual by pay periods
                    period_days = (make_date(*pe) - make_date(*ps)).days + 1
                    if period_days <= 16:
                        gross = emp.pay_rate / 24  # Semi-monthly
                    else:
                        gross = emp.pay_rate / 12  # Monthly

                gross = round(gross, 2)
                # Calculate approximate withholdings
                fed_wh = round(gross * Decimal("0.12"), 2)
                state_wh = round(gross * Decimal("0.05"), 2)
                ss = round(gross * Decimal("0.062"), 2)
                med = round(gross * Decimal("0.0145"), 2)
                suta = round(gross * Decimal("0.027"), 2) if gross < Decimal("9500") else Decimal("0.00")
                futa = round(gross * Decimal("0.006"), 2) if gross < Decimal("7000") else Decimal("0.00")
                net = gross - fed_wh - state_wh - ss - med

                session.add(PayrollItem(
                    payroll_run_id=run_id,
                    employee_id=emp_id,
                    gross_pay=gross,
                    federal_withholding=fed_wh,
                    state_withholding=state_wh,
                    social_security=ss,
                    medicare=med,
                    ga_suta=suta,
                    futa=futa,
                    net_pay=net,
                ))

    await session.flush()


# ---------------------------------------------------------------------------
# SEED DOCUMENTS (metadata only)
# ---------------------------------------------------------------------------
async def seed_documents(session: AsyncSession) -> None:
    """Create document metadata records (no actual files — just DB entries)."""
    print("  Creating document metadata...")

    docs_spec = [
        (CLIENT_SOLE_PROP_ID, "W-9_Peachtree_Landscaping.pdf", "application/pdf", 125000, "W-9 form for Peachtree Landscaping", ["tax", "w-9"]),
        (CLIENT_SOLE_PROP_ID, "Insurance_Certificate_2025.pdf", "application/pdf", 340000, "Liability insurance certificate", ["insurance", "certificate"]),
        (CLIENT_SOLE_PROP_ID, "Q1_Bank_Statement.pdf", "application/pdf", 280000, "Wells Fargo Q1 2025 statement", ["bank", "statement", "q1"]),
        (CLIENT_S_CORP_ID, "Articles_of_Incorporation.pdf", "application/pdf", 450000, "Georgia Articles of Incorporation", ["legal", "incorporation"]),
        (CLIENT_S_CORP_ID, "AWS_Invoice_Jan2025.pdf", "application/pdf", 95000, "AWS hosting invoice January 2025", ["invoice", "aws"]),
        (CLIENT_S_CORP_ID, "Employee_Handbook_2025.pdf", "application/pdf", 1200000, "Company employee handbook", ["hr", "handbook"]),
        (CLIENT_S_CORP_ID, "Office_Lease_Agreement.pdf", "application/pdf", 520000, "WeWork lease agreement 2025", ["lease", "office"]),
        (CLIENT_C_CORP_ID, "Manufacturing_License.pdf", "application/pdf", 380000, "Georgia manufacturing license", ["license", "manufacturing"]),
        (CLIENT_C_CORP_ID, "Environmental_Compliance.pdf", "application/pdf", 620000, "EPA compliance certificate", ["compliance", "environmental"]),
        (CLIENT_C_CORP_ID, "Equipment_Invoice_CAT.pdf", "application/pdf", 180000, "Caterpillar maintenance invoice", ["invoice", "equipment"]),
        (CLIENT_C_CORP_ID, "Q1_Financial_Statement.pdf", "application/pdf", 290000, "Q1 2025 compiled financials", ["financial", "statement", "q1"]),
        (CLIENT_PARTNERSHIP_ID, "Partnership_Agreement.pdf", "application/pdf", 890000, "Operating agreement - Buckhead Partners", ["legal", "partnership"]),
        (CLIENT_PARTNERSHIP_ID, "Professional_License.pdf", "application/pdf", 210000, "Georgia professional license", ["license", "professional"]),
        (CLIENT_PARTNERSHIP_ID, "Office_Lease_Regus.pdf", "application/pdf", 430000, "Regus office space agreement", ["lease", "office"]),
    ]

    for client_id, fname, ftype, fsize, desc, tags in docs_spec:
        session.add(Document(
            client_id=client_id,
            file_name=fname,
            file_path=f"/data/documents/{client_id}/{fname}",
            file_type=ftype,
            file_size_bytes=fsize,
            description=desc,
            tags=tags,
            uploaded_by=USER_CPA_ID,
        ))

    await session.flush()


# ---------------------------------------------------------------------------
# SEED PAYROLL TAX TABLES (TY2025)
# ---------------------------------------------------------------------------
async def seed_tax_tables(session: AsyncSession) -> None:
    """Seed payroll tax tables for TY2025."""
    print("  Creating payroll tax tables...")

    review = date(2025, 1, 15)

    # SOURCE: Georgia DOR Tax Withholding Tables, Tax Year 2025
    # REVIEW DATE: 2025-01-15
    ga_single = [
        (d("0.00"), d("750.00"), d("0.010000"), d("0.00")),
        (d("750.00"), d("2250.00"), d("0.020000"), d("7.50")),
        (d("2250.00"), d("3750.00"), d("0.030000"), d("37.50")),
        (d("3750.00"), d("5250.00"), d("0.040000"), d("82.50")),
        (d("5250.00"), d("7000.00"), d("0.050000"), d("142.50")),
        (d("7000.00"), None, d("0.055000"), d("230.00")),
    ]
    ga_married = [
        (d("0.00"), d("1000.00"), d("0.010000"), d("0.00")),
        (d("1000.00"), d("3000.00"), d("0.020000"), d("10.00")),
        (d("3000.00"), d("5000.00"), d("0.030000"), d("50.00")),
        (d("5000.00"), d("7000.00"), d("0.040000"), d("110.00")),
        (d("7000.00"), d("10000.00"), d("0.050000"), d("190.00")),
        (d("10000.00"), None, d("0.055000"), d("340.00")),
    ]

    for bmin, bmax, rate, flat in ga_single:
        session.add(PayrollTaxTable(
            tax_year=2025,
            tax_type="GA_INCOME",
            filing_status="SINGLE",
            bracket_min=bmin,
            bracket_max=bmax,
            rate=rate,
            flat_amount=flat,
            source_document="Georgia DOR Tax Withholding Tables, Tax Year 2025",
            review_date=review,
        ))

    for bmin, bmax, rate, flat in ga_married:
        session.add(PayrollTaxTable(
            tax_year=2025,
            tax_type="GA_INCOME",
            filing_status="MARRIED",
            bracket_min=bmin,
            bracket_max=bmax,
            rate=rate,
            flat_amount=flat,
            source_document="Georgia DOR Tax Withholding Tables, Tax Year 2025",
            review_date=review,
        ))

    # SOURCE: IRS Publication 15-T, Tax Year 2025
    # REVIEW DATE: 2025-01-15
    fed_single = [
        (d("0.00"), d("11925.00"), d("0.100000"), d("0.00")),
        (d("11925.00"), d("48475.00"), d("0.120000"), d("1192.50")),
        (d("48475.00"), d("103350.00"), d("0.220000"), d("5578.50")),
        (d("103350.00"), d("197300.00"), d("0.240000"), d("17651.00")),
        (d("197300.00"), d("250525.00"), d("0.320000"), d("40199.00")),
        (d("250525.00"), d("626350.00"), d("0.350000"), d("57231.00")),
        (d("626350.00"), None, d("0.370000"), d("188769.75")),
    ]

    for bmin, bmax, rate, flat in fed_single:
        session.add(PayrollTaxTable(
            tax_year=2025,
            tax_type="FEDERAL_INCOME",
            filing_status="SINGLE",
            bracket_min=bmin,
            bracket_max=bmax,
            rate=rate,
            flat_amount=flat,
            source_document="IRS Publication 15-T, Tax Year 2025",
            review_date=review,
        ))

    # FICA rates
    # SOURCE: IRS Publication 15, Tax Year 2025
    session.add(PayrollTaxTable(
        tax_year=2025, tax_type="SOCIAL_SECURITY", filing_status=None,
        bracket_min=d("0.00"), bracket_max=d("176100.00"),
        rate=d("0.062000"), flat_amount=d("0.00"),
        source_document="IRS Publication 15, Tax Year 2025",
        review_date=review,
    ))
    session.add(PayrollTaxTable(
        tax_year=2025, tax_type="MEDICARE", filing_status=None,
        bracket_min=d("0.00"), bracket_max=None,
        rate=d("0.014500"), flat_amount=d("0.00"),
        source_document="IRS Publication 15, Tax Year 2025",
        review_date=review,
    ))
    session.add(PayrollTaxTable(
        tax_year=2025, tax_type="MEDICARE_ADDITIONAL", filing_status=None,
        bracket_min=d("200000.00"), bracket_max=None,
        rate=d("0.009000"), flat_amount=d("0.00"),
        source_document="IRS Publication 15, Tax Year 2025",
        review_date=review,
    ))

    # FUTA
    # SOURCE: IRS Publication 15, Tax Year 2025
    session.add(PayrollTaxTable(
        tax_year=2025, tax_type="FUTA", filing_status=None,
        bracket_min=d("0.00"), bracket_max=d("7000.00"),
        rate=d("0.006000"), flat_amount=d("0.00"),
        source_document="IRS Publication 15, Tax Year 2025 (net after credit)",
        review_date=review,
    ))

    # GA SUTA
    # SOURCE: Georgia DOL, New Employer Rate, Tax Year 2025
    session.add(PayrollTaxTable(
        tax_year=2025, tax_type="GA_SUTA", filing_status=None,
        bracket_min=d("0.00"), bracket_max=d("9500.00"),
        rate=d("0.027000"), flat_amount=d("0.00"),
        source_document="Georgia DOL, New Employer Rate 2.7%, Wage Base $9,500, Tax Year 2025",
        review_date=review,
    ))

    await session.flush()


# ---------------------------------------------------------------------------
# SEED STAFF RATES
# ---------------------------------------------------------------------------
async def seed_staff_rates(session: AsyncSession) -> None:
    """Create staff billing rates for CPA and associate users."""
    print("  Creating staff rates...")
    session.add(StaffRate(
        user_id=USER_CPA_ID, rate_name="Standard", hourly_rate=d("250.00"),
        effective_date=date(2025, 1, 1),
    ))
    session.add(StaffRate(
        user_id=USER_CPA_ID, rate_name="Advisory", hourly_rate=d("300.00"),
        effective_date=date(2025, 1, 1),
    ))
    session.add(StaffRate(
        user_id=USER_ASSOC_ID, rate_name="Standard", hourly_rate=d("150.00"),
        effective_date=date(2025, 1, 1),
    ))
    session.add(StaffRate(
        user_id=USER_ASSOC_ID, rate_name="Bookkeeping", hourly_rate=d("125.00"),
        effective_date=date(2025, 1, 1),
    ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED TIME ENTRIES
# ---------------------------------------------------------------------------
async def seed_time_entries(session: AsyncSession) -> None:
    """Create time entries for both staff across clients."""
    print("  Creating time entries...")
    entries_spec = [
        # (client_id, user_id, date, minutes, desc, billable, service_type, rate, status)
        (CLIENT_SOLE_PROP_ID, USER_CPA_ID, (1, 10), 120, "Q4 2024 tax prep review", True, "Tax Preparation", "250.00", "BILLED"),
        (CLIENT_SOLE_PROP_ID, USER_ASSOC_ID, (1, 12), 90, "Bookkeeping cleanup - Dec", True, "Bookkeeping", "125.00", "BILLED"),
        (CLIENT_SOLE_PROP_ID, USER_ASSOC_ID, (2, 5), 60, "Bank rec - January", True, "Bookkeeping", "125.00", "APPROVED"),
        (CLIENT_SOLE_PROP_ID, USER_CPA_ID, (2, 15), 45, "Payroll review Q1", True, "Payroll Processing", "250.00", "APPROVED"),
        (CLIENT_SOLE_PROP_ID, USER_ASSOC_ID, (3, 1), 75, "Monthly bookkeeping - Feb", True, "Bookkeeping", "125.00", "SUBMITTED"),
        (CLIENT_SOLE_PROP_ID, USER_ASSOC_ID, (3, 20), 30, "Document filing", False, "Bookkeeping", "125.00", "DRAFT"),
        (CLIENT_S_CORP_ID, USER_CPA_ID, (1, 5), 180, "S-Corp tax planning 2025", True, "Tax Preparation", "250.00", "BILLED"),
        (CLIENT_S_CORP_ID, USER_CPA_ID, (1, 20), 240, "Annual financial review", True, "Advisory", "300.00", "BILLED"),
        (CLIENT_S_CORP_ID, USER_ASSOC_ID, (2, 3), 120, "Monthly bookkeeping - Jan", True, "Bookkeeping", "125.00", "APPROVED"),
        (CLIENT_S_CORP_ID, USER_ASSOC_ID, (2, 15), 90, "Payroll processing Feb", True, "Payroll Processing", "150.00", "APPROVED"),
        (CLIENT_S_CORP_ID, USER_CPA_ID, (3, 1), 60, "Quarterly tax estimate", True, "Tax Preparation", "250.00", "SUBMITTED"),
        (CLIENT_S_CORP_ID, USER_ASSOC_ID, (3, 15), 45, "AP entry & reconciliation", True, "Bookkeeping", "125.00", "DRAFT"),
        (CLIENT_C_CORP_ID, USER_CPA_ID, (1, 8), 300, "C-Corp annual return prep", True, "Tax Preparation", "250.00", "BILLED"),
        (CLIENT_C_CORP_ID, USER_ASSOC_ID, (1, 15), 180, "Fixed asset schedule update", True, "Bookkeeping", "125.00", "BILLED"),
        (CLIENT_C_CORP_ID, USER_CPA_ID, (2, 1), 120, "Sales tax review Q4", True, "Tax Preparation", "250.00", "APPROVED"),
        (CLIENT_C_CORP_ID, USER_ASSOC_ID, (2, 20), 150, "Monthly bookkeeping - Jan", True, "Bookkeeping", "125.00", "APPROVED"),
        (CLIENT_C_CORP_ID, USER_ASSOC_ID, (3, 5), 90, "Payroll processing", True, "Payroll Processing", "150.00", "SUBMITTED"),
        (CLIENT_C_CORP_ID, USER_ASSOC_ID, (3, 25), 60, "Bank rec - February", True, "Bookkeeping", "125.00", "DRAFT"),
        (CLIENT_PARTNERSHIP_ID, USER_CPA_ID, (1, 3), 240, "Partnership return prep TY2024", True, "Tax Preparation", "250.00", "BILLED"),
        (CLIENT_PARTNERSHIP_ID, USER_CPA_ID, (1, 25), 90, "Partner K-1 review", True, "Tax Preparation", "250.00", "BILLED"),
        (CLIENT_PARTNERSHIP_ID, USER_ASSOC_ID, (2, 10), 120, "Monthly bookkeeping - Jan", True, "Bookkeeping", "125.00", "APPROVED"),
        (CLIENT_PARTNERSHIP_ID, USER_ASSOC_ID, (3, 1), 60, "Quarterly estimate calc", True, "Tax Preparation", "150.00", "SUBMITTED"),
        (CLIENT_PARTNERSHIP_ID, USER_ASSOC_ID, (3, 10), 45, "Document scanning & filing", False, "Bookkeeping", "125.00", "DRAFT"),
    ]
    for cid, uid, dt, mins, desc, bill, svc, rate, status in entries_spec:
        hourly = d(rate)
        amount = round(hourly * Decimal(mins) / Decimal(60), 2)
        session.add(TimeEntry(
            client_id=cid, user_id=uid, date=make_date(*dt),
            duration_minutes=mins, description=desc, is_billable=bill,
            service_type=svc, hourly_rate=hourly, amount=amount,
            status=TimeEntryStatus(status),
        ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED CONTACTS
# ---------------------------------------------------------------------------
async def seed_contacts(session: AsyncSession) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Create contacts per client. Returns {client_id: [contact_ids]}."""
    print("  Creating contacts...")
    contact_map: dict[uuid.UUID, list[uuid.UUID]] = {}
    contacts_spec = {
        CLIENT_SOLE_PROP_ID: [
            ("Mike", "Patterson", "mike@peachtreelandscaping.com", "770-555-1234", "Owner", True),
            ("Lisa", "Patterson", "lisa@peachtreelandscaping.com", "770-555-1235", "Office Manager", False),
        ],
        CLIENT_S_CORP_ID: [
            ("James", "Kim", "james@atlantatechsolutions.com", "404-555-2345", "CEO", True),
            ("Priya", "Patel", "priya@atlantatechsolutions.com", "404-555-2346", "CFO", False),
            ("Tom", "Morgan", "tom@atlantatechsolutions.com", "404-555-2347", "Controller", False),
        ],
        CLIENT_C_CORP_ID: [
            ("Robert", "Davis", "rdavis@southernmfg.com", "912-555-3456", "President", True),
            ("Karen", "Whitfield", "kwhitfield@southernmfg.com", "912-555-3457", "VP Finance", False),
            ("Steve", "Robinson", "srobinson@southernmfg.com", "912-555-3458", "Plant Manager", False),
        ],
        CLIENT_PARTNERSHIP_ID: [
            ("David", "Harrison", "dharrison@buckheadpartners.com", "404-555-4567", "Managing Partner", True),
            ("Michelle", "Okafor", "mokafor@buckheadpartners.com", "404-555-4568", "Partner", False),
        ],
    }
    for client_id, contacts in contacts_spec.items():
        ids = []
        for first, last, email, phone, title, primary in contacts:
            cid = uuid.uuid4()
            session.add(Contact(
                id=cid, client_id=client_id, first_name=first, last_name=last,
                email=email, phone=phone, title=title, is_primary=primary,
                tags=["client-contact"], custom_fields={},
            ))
            ids.append(cid)
        contact_map[client_id] = ids
    await session.flush()
    return contact_map


# ---------------------------------------------------------------------------
# SEED ENGAGEMENTS
# ---------------------------------------------------------------------------
async def seed_engagements(session: AsyncSession) -> None:
    """Create engagement letters per client."""
    print("  Creating engagements...")
    engagements_spec = [
        (CLIENT_SOLE_PROP_ID, "TY2025 Tax Preparation", "Tax Return", "FIXED", "1500.00", None, None, (1, 1), (4, 15), 2025, "SIGNED"),
        (CLIENT_SOLE_PROP_ID, "Monthly Bookkeeping 2025", "Bookkeeping", "FIXED", "500.00", None, None, (1, 1), (12, 31), 2025, "SIGNED"),
        (CLIENT_S_CORP_ID, "TY2025 S-Corp Return", "Tax Return", "FIXED", "3500.00", None, None, (1, 1), (3, 15), 2025, "SIGNED"),
        (CLIENT_S_CORP_ID, "Advisory Services 2025", "Advisory", "HOURLY", None, "300.00", "40", (1, 1), (12, 31), 2025, "SIGNED"),
        (CLIENT_S_CORP_ID, "Payroll Services 2025", "Payroll", "FIXED", "3600.00", None, None, (1, 1), (12, 31), 2025, "SENT"),
        (CLIENT_C_CORP_ID, "TY2025 C-Corp Return", "Tax Return", "FIXED", "5000.00", None, None, (1, 1), (4, 15), 2025, "SIGNED"),
        (CLIENT_C_CORP_ID, "Monthly Bookkeeping 2025", "Bookkeeping", "FIXED", "1200.00", None, None, (1, 1), (12, 31), 2025, "SIGNED"),
        (CLIENT_C_CORP_ID, "Sales Tax Compliance", "Tax Compliance", "FIXED", "2400.00", None, None, (1, 1), (12, 31), 2025, "DRAFT"),
        (CLIENT_PARTNERSHIP_ID, "TY2025 Partnership Return", "Tax Return", "FIXED", "4000.00", None, None, (1, 1), (3, 15), 2025, "SIGNED"),
        (CLIENT_PARTNERSHIP_ID, "Business Advisory Q1", "Advisory", "HOURLY", None, "275.00", "30", (1, 1), (3, 31), 2025, "SIGNED"),
    ]
    now_utc = datetime.now(timezone.utc)
    for cid, title, etype, fee_type, fixed, hourly, hours, sd, ed, ty, status in engagements_spec:
        session.add(Engagement(
            client_id=cid, title=title, engagement_type=etype,
            fee_type=fee_type,
            fixed_fee=d(fixed) if fixed else None,
            hourly_rate=d(hourly) if hourly else None,
            estimated_hours=d(hours) if hours else None,
            start_date=make_date(*sd), end_date=make_date(*ed),
            tax_year=ty, status=EngagementStatus(status),
            signed_at=now_utc if status == "SIGNED" else None,
            signed_by=title.split()[0] if status == "SIGNED" else None,
            sent_at=now_utc if status in ("SENT", "SIGNED") else None,
        ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED WORKFLOWS & STAGES & TASKS
# ---------------------------------------------------------------------------
async def seed_workflow_stages(session: AsyncSession) -> None:
    """Create standard workflow stage definitions."""
    print("  Creating workflow stages...")
    stages = {
        "Tax Prep": [
            ("Engagement", 1, "#6B7280", False),
            ("Document Collection", 2, "#3B82F6", False),
            ("Data Entry", 3, "#F59E0B", False),
            ("Review", 4, "#8B5CF6", False),
            ("Filing", 5, "#10B981", False),
            ("Complete", 6, "#059669", True),
        ],
        "Bookkeeping": [
            ("Data Collection", 1, "#6B7280", False),
            ("Transaction Entry", 2, "#3B82F6", False),
            ("Reconciliation", 3, "#F59E0B", False),
            ("Review", 4, "#8B5CF6", False),
            ("Delivered", 5, "#10B981", True),
        ],
        "Payroll": [
            ("Time Collection", 1, "#6B7280", False),
            ("Processing", 2, "#3B82F6", False),
            ("Review", 3, "#F59E0B", False),
            ("Approved", 4, "#10B981", True),
        ],
        "Onboarding": [
            ("Initial Contact", 1, "#6B7280", False),
            ("Engagement Letter", 2, "#3B82F6", False),
            ("Document Gathering", 3, "#F59E0B", False),
            ("System Setup", 4, "#8B5CF6", False),
            ("Complete", 5, "#10B981", True),
        ],
        "Advisory": [
            ("Planning", 1, "#6B7280", False),
            ("Analysis", 2, "#3B82F6", False),
            ("Recommendation", 3, "#F59E0B", False),
            ("Implementation", 4, "#8B5CF6", False),
            ("Follow-Up", 5, "#10B981", True),
        ],
    }
    for wtype, stage_list in stages.items():
        for sname, order, color, is_completion in stage_list:
            session.add(WorkflowStage(
                workflow_type=wtype, stage_name=sname,
                stage_order=order, color=color,
                is_completion_stage=is_completion,
            ))
    await session.flush()


async def seed_workflows(session: AsyncSession) -> None:
    """Create workflows with tasks across clients."""
    print("  Creating workflows and tasks...")
    workflows_spec = [
        # (client_id, name, type, status, stage, due, assigned, tasks)
        (CLIENT_SOLE_PROP_ID, "TY2025 Individual Return", "Tax Prep", "ACTIVE", "Document Collection", (3, 15),
         USER_CPA_ID, [
            ("Send engagement letter", "COMPLETED", "HIGH", (1, 5)),
            ("Collect W-2s and 1099s", "COMPLETED", "HIGH", (1, 31)),
            ("Gather expense records", "IN_PROGRESS", "MEDIUM", (2, 15)),
            ("Enter Schedule C data", "NOT_STARTED", "MEDIUM", (2, 28)),
            ("CPA review & sign", "NOT_STARTED", "HIGH", (3, 10)),
            ("E-file return", "NOT_STARTED", "URGENT", (3, 15)),
        ]),
        (CLIENT_SOLE_PROP_ID, "Monthly Bookkeeping - March", "Bookkeeping", "ACTIVE", "Transaction Entry", (3, 31),
         USER_ASSOC_ID, [
            ("Download bank statements", "COMPLETED", "MEDIUM", (3, 5)),
            ("Enter transactions", "IN_PROGRESS", "MEDIUM", (3, 15)),
            ("Reconcile accounts", "NOT_STARTED", "HIGH", (3, 25)),
            ("Review & deliver", "NOT_STARTED", "MEDIUM", (3, 31)),
        ]),
        (CLIENT_S_CORP_ID, "TY2025 S-Corp Return", "Tax Prep", "ACTIVE", "Data Entry", (3, 15),
         USER_CPA_ID, [
            ("Engagement letter signed", "COMPLETED", "HIGH", (1, 10)),
            ("Collect corporate docs", "COMPLETED", "HIGH", (1, 31)),
            ("Enter income/expense data", "IN_PROGRESS", "MEDIUM", (2, 15)),
            ("K-1 allocations", "NOT_STARTED", "HIGH", (2, 28)),
            ("CPA review", "NOT_STARTED", "HIGH", (3, 5)),
            ("E-file 1120-S", "NOT_STARTED", "URGENT", (3, 15)),
        ]),
        (CLIENT_S_CORP_ID, "Q1 Payroll Processing", "Payroll", "COMPLETED", "Approved", (3, 31),
         USER_ASSOC_ID, [
            ("Collect timesheets", "COMPLETED", "MEDIUM", (3, 25)),
            ("Process payroll", "COMPLETED", "HIGH", (3, 28)),
            ("CPA review & approve", "COMPLETED", "HIGH", (3, 30)),
        ]),
        (CLIENT_C_CORP_ID, "TY2025 C-Corp Return", "Tax Prep", "ACTIVE", "Review", (4, 15),
         USER_CPA_ID, [
            ("Engagement signed", "COMPLETED", "HIGH", (1, 10)),
            ("Collect corporate docs", "COMPLETED", "HIGH", (2, 1)),
            ("Enter all data", "COMPLETED", "MEDIUM", (2, 28)),
            ("State apportionment calc", "COMPLETED", "HIGH", (3, 10)),
            ("CPA final review", "IN_PROGRESS", "URGENT", (3, 31)),
            ("E-file 1120", "NOT_STARTED", "URGENT", (4, 15)),
        ]),
        (CLIENT_C_CORP_ID, "Sales Tax Q1", "Tax Prep", "ACTIVE", "Filing", (4, 30),
         USER_ASSOC_ID, [
            ("Pull sales reports", "COMPLETED", "MEDIUM", (4, 5)),
            ("Calculate ST-3", "COMPLETED", "HIGH", (4, 15)),
            ("CPA review", "COMPLETED", "HIGH", (4, 20)),
            ("File ST-3", "IN_PROGRESS", "URGENT", (4, 30)),
        ]),
        (CLIENT_PARTNERSHIP_ID, "TY2025 Partnership Return", "Tax Prep", "ACTIVE", "Document Collection", (3, 15),
         USER_CPA_ID, [
            ("Engagement letter", "COMPLETED", "HIGH", (1, 5)),
            ("Collect partner docs", "IN_PROGRESS", "HIGH", (2, 1)),
            ("Enter partnership data", "NOT_STARTED", "MEDIUM", (2, 20)),
            ("Partner allocations", "NOT_STARTED", "HIGH", (3, 1)),
            ("CPA review & K-1s", "NOT_STARTED", "HIGH", (3, 10)),
            ("E-file 1065", "NOT_STARTED", "URGENT", (3, 15)),
        ]),
        (CLIENT_PARTNERSHIP_ID, "New Client Onboarding", "Onboarding", "COMPLETED", "Complete", (1, 31),
         USER_ASSOC_ID, [
            ("Initial meeting", "COMPLETED", "HIGH", (1, 3)),
            ("Send engagement letter", "COMPLETED", "MEDIUM", (1, 5)),
            ("Collect prior returns", "COMPLETED", "MEDIUM", (1, 15)),
            ("Set up in system", "COMPLETED", "MEDIUM", (1, 25)),
        ]),
    ]
    now_utc = datetime.now(timezone.utc)
    for cid, name, wtype, status, stage, due, assigned, tasks in workflows_spec:
        wf_id = uuid.uuid4()
        session.add(Workflow(
            id=wf_id, client_id=cid, name=name, workflow_type=wtype,
            status=WorkflowStatus(status), current_stage=stage,
            due_date=make_date(*due), assigned_to=assigned,
            start_date=make_date(1, 1),
            completed_at=now_utc if status == "COMPLETED" else None,
            tax_year=2025,
        ))
        await session.flush()
        for i, (title, tstatus, priority, tdue) in enumerate(tasks):
            session.add(WorkflowTask(
                workflow_id=wf_id, title=title,
                status=TaskStatusEnum(tstatus),
                priority=TaskPriority(priority),
                due_date=make_date(*tdue),
                assigned_to=assigned, sort_order=i,
                completed_at=now_utc if tstatus == "COMPLETED" else None,
            ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED DUE DATES
# ---------------------------------------------------------------------------
async def seed_due_dates(session: AsyncSession) -> None:
    """Create tax filing due dates for all clients."""
    print("  Creating due dates...")
    due_dates_spec = [
        # (client_id, title, due_date, form_type, filing_type, completed)
        (CLIENT_SOLE_PROP_ID, "GA Form G-7 Q4 2024", (1, 31), "G-7", "State Payroll", True),
        (CLIENT_SOLE_PROP_ID, "Federal Schedule C TY2024", (4, 15), "1040-C", "Federal Income", False),
        (CLIENT_SOLE_PROP_ID, "GA Form 500 TY2024", (4, 15), "500", "State Income", False),
        (CLIENT_SOLE_PROP_ID, "GA Form G-7 Q1 2025", (4, 30), "G-7", "State Payroll", False),
        (CLIENT_SOLE_PROP_ID, "GA Form ST-3 Q1", (4, 20), "ST-3", "Sales Tax", False),
        (CLIENT_S_CORP_ID, "Federal 1120-S TY2024", (3, 15), "1120-S", "Federal Income", False),
        (CLIENT_S_CORP_ID, "GA Form 600-S TY2024", (3, 15), "600-S", "State Income", False),
        (CLIENT_S_CORP_ID, "GA Form G-7 Q4 2024", (1, 31), "G-7", "State Payroll", True),
        (CLIENT_S_CORP_ID, "GA Form G-7 Q1 2025", (4, 30), "G-7", "State Payroll", False),
        (CLIENT_S_CORP_ID, "W-2s TY2024", (1, 31), "W-2", "Federal Payroll", True),
        (CLIENT_C_CORP_ID, "Federal 1120 TY2024", (4, 15), "1120", "Federal Income", False),
        (CLIENT_C_CORP_ID, "GA Form 600 TY2024", (4, 15), "600", "State Income", False),
        (CLIENT_C_CORP_ID, "GA Form G-7 Q4 2024", (1, 31), "G-7", "State Payroll", True),
        (CLIENT_C_CORP_ID, "GA Form G-7 Q1 2025", (4, 30), "G-7", "State Payroll", False),
        (CLIENT_C_CORP_ID, "GA Form ST-3 Q1", (4, 20), "ST-3", "Sales Tax", False),
        (CLIENT_C_CORP_ID, "W-2s TY2024", (1, 31), "W-2", "Federal Payroll", True),
        (CLIENT_PARTNERSHIP_ID, "Federal 1065 TY2024", (3, 15), "1065", "Federal Income", False),
        (CLIENT_PARTNERSHIP_ID, "GA Form 700 TY2024", (3, 15), "700", "State Income", False),
        (CLIENT_PARTNERSHIP_ID, "GA Form G-7 Q4 2024", (1, 31), "G-7", "State Payroll", True),
        (CLIENT_PARTNERSHIP_ID, "GA Form G-7 Q1 2025", (4, 30), "G-7", "State Payroll", False),
    ]
    now_utc = datetime.now(timezone.utc)
    for cid, title, dd, form, filing, completed in due_dates_spec:
        session.add(DueDate(
            client_id=cid, title=title, due_date=make_date(*dd),
            form_type=form, filing_type=filing, tax_year=2025,
            is_completed=completed,
            completed_at=now_utc if completed else None,
            completed_by=USER_CPA_ID if completed else None,
            remind_days_before=7,
        ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED SERVICE INVOICES (firm-to-client billing)
# ---------------------------------------------------------------------------
async def seed_service_invoices(session: AsyncSession) -> None:
    """Create service invoices from CPA firm to clients."""
    print("  Creating service invoices...")
    invoices_spec = [
        (CLIENT_SOLE_PROP_ID, "SI-2025-001", (1, 15), (2, 15), "PAID", [
            ("Tax preparation - TY2024 Schedule C", "1", "1500.00", "Tax Preparation"),
        ]),
        (CLIENT_SOLE_PROP_ID, "SI-2025-002", (2, 1), (3, 1), "PAID", [
            ("Monthly bookkeeping - January", "1", "500.00", "Bookkeeping"),
        ]),
        (CLIENT_SOLE_PROP_ID, "SI-2025-003", (3, 1), (4, 1), "SENT", [
            ("Monthly bookkeeping - February", "1", "500.00", "Bookkeeping"),
            ("Payroll processing - February", "1", "150.00", "Payroll Processing"),
        ]),
        (CLIENT_S_CORP_ID, "SI-2025-004", (1, 15), (2, 15), "PAID", [
            ("S-Corp annual tax planning", "4", "300.00", "Advisory"),
        ]),
        (CLIENT_S_CORP_ID, "SI-2025-005", (2, 1), (3, 1), "PAID", [
            ("Monthly bookkeeping - January", "1", "800.00", "Bookkeeping"),
            ("Payroll processing - January", "1", "300.00", "Payroll Processing"),
        ]),
        (CLIENT_S_CORP_ID, "SI-2025-006", (3, 1), (4, 1), "SENT", [
            ("Monthly bookkeeping - February", "1", "800.00", "Bookkeeping"),
            ("Payroll processing - February", "1", "300.00", "Payroll Processing"),
            ("Quarterly estimate prep", "1", "250.00", "Tax Preparation"),
        ]),
        (CLIENT_S_CORP_ID, "SI-2025-007", (4, 1), (5, 1), "DRAFT", [
            ("Monthly bookkeeping - March", "1", "800.00", "Bookkeeping"),
        ]),
        (CLIENT_C_CORP_ID, "SI-2025-008", (1, 15), (2, 15), "PAID", [
            ("C-Corp annual return prep", "5", "250.00", "Tax Preparation"),
            ("Fixed asset schedule update", "3", "125.00", "Bookkeeping"),
        ]),
        (CLIENT_C_CORP_ID, "SI-2025-009", (2, 1), (3, 1), "PAID", [
            ("Monthly bookkeeping - January", "1", "1200.00", "Bookkeeping"),
            ("Sales tax compliance - Q4", "2", "250.00", "Tax Preparation"),
        ]),
        (CLIENT_C_CORP_ID, "SI-2025-010", (3, 1), (4, 1), "OVERDUE", [
            ("Monthly bookkeeping - February", "1", "1200.00", "Bookkeeping"),
            ("Payroll processing - February", "1", "350.00", "Payroll Processing"),
        ]),
        (CLIENT_PARTNERSHIP_ID, "SI-2025-011", (1, 15), (2, 15), "PAID", [
            ("Partnership return prep TY2024", "4", "250.00", "Tax Preparation"),
            ("Partner K-1 preparation", "1.5", "250.00", "Tax Preparation"),
        ]),
        (CLIENT_PARTNERSHIP_ID, "SI-2025-012", (2, 1), (3, 1), "PAID", [
            ("Monthly bookkeeping - January", "1", "600.00", "Bookkeeping"),
        ]),
        (CLIENT_PARTNERSHIP_ID, "SI-2025-013", (3, 1), (4, 1), "SENT", [
            ("Monthly bookkeeping - February", "1", "600.00", "Bookkeeping"),
            ("Quarterly estimate prep", "1", "200.00", "Tax Preparation"),
        ]),
    ]
    for cid, inv_num, inv_dt, due_dt, status, lines in invoices_spec:
        inv_id = uuid.uuid4()
        subtotal = sum(d(qty) * d(price) for _, qty, price, _ in lines)
        paid = subtotal if status == "PAID" else Decimal("0")
        session.add(ServiceInvoice(
            id=inv_id, client_id=cid, invoice_number=inv_num,
            invoice_date=make_date(*inv_dt), due_date=make_date(*due_dt),
            subtotal=subtotal, total_amount=subtotal,
            amount_paid=paid, balance_due=subtotal - paid,
            status=ServiceInvoiceStatus(status),
        ))
        for desc, qty, price, svc in lines:
            amt = d(qty) * d(price)
            session.add(ServiceInvoiceLine(
                invoice_id=inv_id, description=desc,
                quantity=d(qty), unit_price=d(price), amount=amt,
                service_type=svc,
            ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED PORTAL USERS & MESSAGES
# ---------------------------------------------------------------------------
async def seed_portal_data(
    session: AsyncSession,
    contact_map: dict[uuid.UUID, list[uuid.UUID]],
) -> None:
    """Create portal users and messages."""
    print("  Creating portal users and messages...")

    portal_users_spec = [
        (CLIENT_SOLE_PROP_ID, 0, "mike@peachtreelandscaping.com", "Mike Patterson"),
        (CLIENT_S_CORP_ID, 0, "james@atlantatechsolutions.com", "James Kim"),
        (CLIENT_C_CORP_ID, 0, "rdavis@southernmfg.com", "Robert Davis"),
        (CLIENT_PARTNERSHIP_ID, 0, "dharrison@buckheadpartners.com", "David Harrison"),
    ]
    portal_ids: dict[uuid.UUID, uuid.UUID] = {}
    for cid, cidx, email, name in portal_users_spec:
        pu_id = uuid.uuid4()
        session.add(PortalUser(
            id=pu_id, client_id=cid,
            contact_id=contact_map[cid][cidx] if cid in contact_map else None,
            email=email, password_hash=hash_password("portal123"),
            full_name=name, is_active=True,
        ))
        portal_ids[cid] = pu_id
    await session.flush()

    # Messages — threaded conversations
    now_utc = datetime.now(timezone.utc)
    messages_spec = [
        (CLIENT_SOLE_PROP_ID, "Tax Documents for 2024", [
            ("STAFF", USER_CPA_ID, None, "Hi Mike, please upload your W-2s and 1099s for TY2024 when you have them. Thanks!"),
            ("CLIENT", None, None, "Hi Edward, I have the W-2s ready. Will upload shortly. Still waiting on 1099 from the bank."),
            ("STAFF", USER_CPA_ID, None, "Sounds good. Let me know when you have the bank 1099. We need it for the Schedule B."),
        ]),
        (CLIENT_SOLE_PROP_ID, "Quarterly Estimates", [
            ("STAFF", USER_ASSOC_ID, None, "Mike, your Q1 estimated tax payment is due April 15. Amount: $2,500 federal, $800 state."),
        ]),
        (CLIENT_S_CORP_ID, "S-Corp Payroll Schedule", [
            ("STAFF", USER_CPA_ID, None, "James, we need to finalize the 2025 payroll schedule. Are you staying with semi-monthly?"),
            ("CLIENT", None, None, "Yes, semi-monthly works for us. Same dates as last year please."),
            ("STAFF", USER_CPA_ID, None, "Perfect. I'll set up the payroll calendar and send it over for your records."),
            ("CLIENT", None, None, "Thanks Edward. Also, we hired two new employees in January. I'll send their W-4s."),
            ("STAFF", USER_ASSOC_ID, None, "Got the W-4s. I've added both employees to the system. They'll be included in the next payroll run."),
        ]),
        (CLIENT_C_CORP_ID, "Annual Return Status", [
            ("STAFF", USER_CPA_ID, None, "Robert, your C-Corp return is in review. We should have it ready for your signature by March 31."),
            ("CLIENT", None, None, "Great, thanks for the update. Any issues I should be aware of?"),
            ("STAFF", USER_CPA_ID, None, "Nothing significant. Depreciation on the new equipment reduces your tax liability nicely. I'll include a summary with the return."),
        ]),
        (CLIENT_PARTNERSHIP_ID, "Partner K-1 Distribution", [
            ("STAFF", USER_CPA_ID, None, "David, the K-1s for TY2024 are being prepared. Each partner should receive theirs by March 10."),
            ("CLIENT", None, None, "Thanks Edward. Michelle is asking about the allocation percentages — are we still at 60/40?"),
            ("STAFF", USER_CPA_ID, None, "Yes, per the operating agreement it's 60/40. No changes unless you amend the agreement."),
        ]),
    ]
    for cid, subject, thread_msgs in messages_spec:
        thread_id = uuid.uuid4()
        for sender_type, user_id, portal_user_id, body in thread_msgs:
            session.add(Message(
                client_id=cid, thread_id=thread_id, subject=subject, body=body,
                sender_type=sender_type,
                sender_user_id=user_id if sender_type == "STAFF" else None,
                sender_portal_user_id=portal_ids.get(cid) if sender_type == "CLIENT" else None,
                is_read=True, read_at=now_utc,
            ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED FIXED ASSETS
# ---------------------------------------------------------------------------
async def seed_fixed_assets(
    session: AsyncSession,
    acct_maps: dict[uuid.UUID, dict[str, uuid.UUID]],
) -> None:
    """Create fixed assets with depreciation entries."""
    print("  Creating fixed assets...")
    assets_spec = [
        (CLIENT_SOLE_PROP_ID, "Ford F-150 Work Truck", "FA-001", "Vehicles", (2023, 6, 1), "45000.00", "MACRS_GDS", 5, "5000.00", "5-year", "15000.00", "30000.00", "1500", "6600", "1550"),
        (CLIENT_SOLE_PROP_ID, "Zero-Turn Mower", "FA-002", "Equipment", (2024, 3, 15), "12000.00", "MACRS_GDS", 7, "500.00", "7-year", "2571.43", "9428.57", "1500", "6600", "1550"),
        (CLIENT_SOLE_PROP_ID, "Trailer 20ft", "FA-003", "Equipment", (2024, 8, 1), "8500.00", "STRAIGHT_LINE", 10, "500.00", None, "425.00", "8075.00", "1500", "6600", "1550"),
        (CLIENT_S_CORP_ID, "Office Furniture", "FA-004", "Furniture", (2022, 1, 1), "25000.00", "MACRS_GDS", 7, "0.00", "7-year", "10714.28", "14285.72", "1500", "6600", "1550"),
        (CLIENT_S_CORP_ID, "Server Equipment", "FA-005", "Equipment", (2023, 9, 1), "35000.00", "MACRS_GDS", 5, "0.00", "5-year", "14000.00", "21000.00", "1500", "6600", "1550"),
        (CLIENT_S_CORP_ID, "Laptops (5)", "FA-006", "Equipment", (2025, 3, 15), "12500.00", "SECTION_179", 5, "0.00", "5-year", "0.00", "12500.00", "1500", "6600", "1550"),
        (CLIENT_C_CORP_ID, "CNC Machine", "FA-007", "Machinery", (2021, 3, 1), "180000.00", "MACRS_GDS", 7, "10000.00", "7-year", "97142.80", "82857.20", "1500", "6600", "1550"),
        (CLIENT_C_CORP_ID, "Forklift", "FA-008", "Equipment", (2022, 7, 1), "45000.00", "MACRS_GDS", 5, "5000.00", "5-year", "24000.00", "21000.00", "1500", "6600", "1550"),
        (CLIENT_C_CORP_ID, "Warehouse HVAC", "FA-009", "Building Improvement", (2023, 11, 1), "65000.00", "STRAIGHT_LINE", 15, "0.00", None, "5416.67", "59583.33", "1500", "6600", "1550"),
        (CLIENT_C_CORP_ID, "Delivery Truck", "FA-010", "Vehicles", (2024, 2, 1), "55000.00", "MACRS_GDS", 5, "8000.00", "5-year", "9400.00", "45600.00", "1500", "6600", "1550"),
        (CLIENT_PARTNERSHIP_ID, "Office Buildout", "FA-011", "Leasehold Improvement", (2023, 1, 15), "35000.00", "STRAIGHT_LINE", 10, "0.00", None, "7000.00", "28000.00", "1500", "6600", "1550"),
        (CLIENT_PARTNERSHIP_ID, "Conference Table & Chairs", "FA-012", "Furniture", (2023, 2, 1), "8500.00", "MACRS_GDS", 7, "0.00", "7-year", "2428.57", "6071.43", "1500", "6600", "1550"),
    ]
    for cid, name, num, cat, acq_dt, cost, method, life, salvage, macrs, accum, bv, asset_acct, depr_exp, accum_acct in assets_spec:
        am = acct_maps[cid]
        session.add(FixedAsset(
            client_id=cid, asset_name=name, asset_number=num, category=cat,
            acquisition_date=date(*acq_dt), acquisition_cost=d(cost),
            depreciation_method=DepreciationMethod(method),
            useful_life_years=life, salvage_value=d(salvage),
            macrs_class=macrs,
            accumulated_depreciation=d(accum), book_value=d(bv),
            status=AssetStatus.ACTIVE,
            asset_account_id=acct(am, asset_acct),
            depreciation_expense_account_id=acct(am, depr_exp),
            accumulated_depreciation_account_id=acct(am, accum_acct),
        ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED BUDGETS
# ---------------------------------------------------------------------------
async def seed_budgets(
    session: AsyncSession,
    acct_maps: dict[uuid.UUID, dict[str, uuid.UUID]],
) -> None:
    """Create budgets with monthly line items."""
    print("  Creating budgets...")
    budgets_spec = [
        (CLIENT_SOLE_PROP_ID, "FY2025 Operating Budget", 2025, [
            ("4000", [15000, 15000, 18000, 20000, 22000, 25000, 25000, 22000, 18000, 15000, 12000, 10000]),
            ("6000", [8500, 8500, 8500, 8500, 8500, 8500, 8500, 8500, 8500, 8500, 8500, 8500]),
            ("6100", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
            ("6110", [500, 500, 500, 500, 600, 700, 750, 700, 600, 500, 500, 500]),
            ("6200", [2000, 2000, 3000, 3500, 4000, 4000, 4000, 3500, 3000, 2000, 1500, 1000]),
            ("6300", [400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400]),
        ]),
        (CLIENT_S_CORP_ID, "FY2025 Operating Budget", 2025, [
            ("4000", [30000, 30000, 35000, 35000, 40000, 40000, 35000, 35000, 30000, 30000, 25000, 20000]),
            ("6000", [22000, 22000, 22000, 22000, 22000, 22000, 22000, 22000, 22000, 22000, 22000, 22000]),
            ("6100", [2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500]),
            ("6810", [3000, 3000, 3000, 3200, 3200, 3500, 3500, 3500, 3500, 3200, 3200, 3000]),
        ]),
        (CLIENT_C_CORP_ID, "FY2025 Operating Budget", 2025, [
            ("4010", [40000, 40000, 45000, 45000, 50000, 50000, 45000, 45000, 40000, 40000, 35000, 35000]),
            ("5000", [25000, 25000, 28000, 28000, 30000, 30000, 28000, 28000, 25000, 25000, 22000, 22000]),
            ("6000", [35000, 35000, 35000, 35000, 35000, 35000, 35000, 35000, 35000, 35000, 35000, 35000]),
            ("6200", [5000, 5000, 6000, 6000, 7000, 7000, 6000, 6000, 5000, 5000, 4000, 4000]),
        ]),
    ]
    for cid, name, fy, lines in budgets_spec:
        am = acct_maps[cid]
        budget_id = uuid.uuid4()
        session.add(Budget(
            id=budget_id, client_id=cid, name=name, fiscal_year=fy,
            is_active=True,
        ))
        await session.flush()
        for acct_num, months in lines:
            annual = sum(months)
            session.add(BudgetLine(
                budget_id=budget_id, account_id=acct(am, acct_num),
                month_1=d(str(months[0])), month_2=d(str(months[1])),
                month_3=d(str(months[2])), month_4=d(str(months[3])),
                month_5=d(str(months[4])), month_6=d(str(months[5])),
                month_7=d(str(months[6])), month_8=d(str(months[7])),
                month_9=d(str(months[8])), month_10=d(str(months[9])),
                month_11=d(str(months[10])), month_12=d(str(months[11])),
                annual_total=d(str(annual)),
            ))
    await session.flush()


# ---------------------------------------------------------------------------
# SEED SERVICE TYPES
# ---------------------------------------------------------------------------
async def seed_service_types(session: AsyncSession) -> None:
    """Create service type definitions."""
    print("  Creating service types...")
    types = [
        ("Tax Preparation", "Individual and business tax return preparation", "250.00"),
        ("Bookkeeping", "Monthly transaction recording and reconciliation", "125.00"),
        ("Payroll Processing", "Payroll calculation, filing, and compliance", "150.00"),
        ("Advisory", "Business and tax advisory services", "300.00"),
        ("Audit & Assurance", "Financial statement audit and review", "275.00"),
    ]
    for name, desc, rate in types:
        await session.execute(text(
            "INSERT INTO service_types (name, description, default_hourly_rate) "
            "VALUES (:name, :desc, :rate) ON CONFLICT (name) DO NOTHING"
        ), {"name": name, "desc": desc, "rate": rate})
    await session.flush()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def seed() -> None:
    """Run the full seed process."""
    async with async_session_factory() as session:
        async with session.begin():
            if await is_already_seeded(session):
                print("Database already seeded (CPA user found). Use --reset to re-seed.")
                return

    async with async_session_factory() as session:
        async with session.begin():
            await seed_users(session)
            await seed_clients(session)
            acct_maps = await seed_chart_of_accounts(session)
            vendor_map = await seed_vendors(session)
            await seed_bills(session, acct_maps, vendor_map)
            await seed_invoices(session, acct_maps)
            await seed_journal_entries(session, acct_maps)
            await seed_bank_data(session, acct_maps)
            emp_map = await seed_employees(session)
            await seed_payroll(session, emp_map)
            await seed_documents(session)
            await seed_tax_tables(session)
            # Phase 9-12: Practice management
            await seed_staff_rates(session)
            await seed_time_entries(session)
            contact_map = await seed_contacts(session)
            await seed_engagements(session)
            await seed_workflow_stages(session)
            await seed_workflows(session)
            await seed_due_dates(session)
            await seed_service_invoices(session)
            await seed_portal_data(session, contact_map)
            await seed_fixed_assets(session, acct_maps)
            await seed_budgets(session, acct_maps)
            await seed_service_types(session)

    print("\nSeed complete! Summary:")
    print("  Users: 2 (CPA_OWNER + ASSOCIATE)")
    print("  Clients: 4 (SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC)")
    print("  CoA: 87 accounts per client (348 total)")
    print("  Vendors: 19 total across all clients")
    print("  Bills: 37 total (PAID, APPROVED, PENDING, DRAFT)")
    print("  Invoices: 39 total (PAID, SENT, OVERDUE, PENDING, DRAFT)")
    print("  Journal Entries: ~90 total (POSTED, PENDING, DRAFT)")
    print("  Bank Accounts: 6 with ~150 transactions")
    print("  Employees: 16 total across all clients")
    print("  Payroll Runs: 23 with items per employee")
    print("  Documents: 14 metadata records")
    print("  Tax Tables: ~30 rows (TY2025)")
    print("  Staff Rates: 4 (2 per user)")
    print("  Time Entries: 23 across all clients")
    print("  Contacts: 10 across all clients")
    print("  Engagements: 10 across all clients")
    print("  Workflow Stages: 25 (5 types)")
    print("  Workflows: 8 with ~40 tasks")
    print("  Due Dates: 20 tax filing deadlines")
    print("  Service Invoices: 13 (firm billing)")
    print("  Portal Users: 4 (one per client)")
    print("  Messages: ~15 threaded messages")
    print("  Fixed Assets: 12 with depreciation")
    print("  Budgets: 3 with monthly lines")
    print("  Service Types: 5")
    print("\nLogin:")
    print("  CPA_OWNER: edward@755mortgage.com / admin123")
    print("  ASSOCIATE: sarah@755mortgage.com / associate123")


async def reset_and_seed() -> None:
    """Reset the database and re-seed."""
    async with async_session_factory() as session:
        async with session.begin():
            await reset_database(session)
    await seed()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed test data into ga_cpa database")
    parser.add_argument("--reset", action="store_true", help="Wipe all data and re-seed")
    args = parser.parse_args()

    print("Georgia CPA Accounting System — Test Data Seeder")
    print("=" * 50)

    if args.reset:
        print("Mode: RESET + SEED")
        asyncio.run(reset_and_seed())
    else:
        print("Mode: SEED (use --reset to wipe first)")
        asyncio.run(seed())


if __name__ == "__main__":
    main()
