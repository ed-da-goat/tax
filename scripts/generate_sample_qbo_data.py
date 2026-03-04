#!/usr/bin/env python3
"""
Generate Sample QBO Export Data
===============================

Generates realistic CSV files that match QuickBooks Online export format.
Used for testing the migration parser without real client data.

Usage:
    python scripts/generate_sample_qbo_data.py [--output-dir OUTPUT_DIR]

Output files:
    - chart_of_accounts_samplecpa_YYYY-MM-DD.csv
    - transaction_detail_samplecpa_YYYY-MM-DD.csv
    - customer_list_samplecpa_YYYY-MM-DD.csv
    - invoice_list_samplecpa_YYYY-MM-DD.csv
    - payroll_summary_samplecpa_YYYY-MM-DD.csv
    - payroll_detail_samplecpa_YYYY-MM-DD.csv
    - employee_details_samplecpa_YYYY-MM-DD.csv
    - vendor_list_samplecpa_YYYY-MM-DD.csv
    - bill_list_samplecpa_YYYY-MM-DD.csv

    Supplemental files (CPA-provided):
    - entity_type_mapping.csv
    - employee_client_mapping.csv
    - vendor_client_mapping.csv

Agent: QB Format Research Agent (Agent 05)
Date: 2026-03-04
"""

import argparse
import csv
import os
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


# ==============================================================================
# CONSTANTS
# ==============================================================================

COMPANY_NAME = "Sample CPA Firm"
EXPORT_DATE = datetime.now().strftime("%Y-%m-%d")

# Three sample clients with different entity types
CLIENTS = [
    {
        "name": "Peachtree Landscaping LLC",
        "entity_type": "PARTNERSHIP_LLC",
        "contact": "James Williams",
        "phone": "(770) 555-1234",
        "email": "info@peachtreelandscaping.com",
        "street": "456 Magnolia Blvd",
        "city": "Marietta",
        "state": "GA",
        "zip": "30060",
        "industry": "landscaping",
    },
    {
        "name": "Atlanta Tech Solutions Inc",
        "entity_type": "S_CORP",
        "contact": "Sarah Chen",
        "phone": "(404) 555-5678",
        "email": "sarah@atlantatechsolutions.com",
        "street": "1200 Peachtree St NE, Suite 400",
        "city": "Atlanta",
        "state": "GA",
        "zip": "30309",
        "industry": "technology",
    },
    {
        "name": "Savannah Sweets",
        "entity_type": "SOLE_PROP",
        "contact": "Maria Rodriguez",
        "phone": "(912) 555-9012",
        "email": "maria@savannahsweets.com",
        "street": "89 River St",
        "city": "Savannah",
        "state": "GA",
        "zip": "31401",
        "industry": "bakery",
    },
]

# Employees per client
EMPLOYEES = {
    "Peachtree Landscaping LLC": [
        {"name": "John Smith", "rate": "18.50", "type": "Hourly",
         "filing": "Married", "hire": "01/15/2020"},
        {"name": "Carlos Ramirez", "rate": "16.00", "type": "Hourly",
         "filing": "Single", "hire": "03/01/2021"},
        {"name": "David Park", "rate": "20.00", "type": "Hourly",
         "filing": "Single", "hire": "06/15/2022"},
        {"name": "Tyler Brown", "rate": "15.50", "type": "Hourly",
         "filing": "Single", "hire": "09/01/2023"},
    ],
    "Atlanta Tech Solutions Inc": [
        {"name": "Jennifer Liu", "rate": "85000.00", "type": "Salary",
         "filing": "Single", "hire": "02/01/2019"},
        {"name": "Michael Washington", "rate": "72000.00", "type": "Salary",
         "filing": "Married", "hire": "08/15/2020"},
        {"name": "Aisha Patel", "rate": "68000.00", "type": "Salary",
         "filing": "Single", "hire": "01/10/2022"},
        {"name": "Ryan O'Brien", "rate": "78000.00", "type": "Salary",
         "filing": "Married", "hire": "05/01/2021"},
        {"name": "Keisha Thompson", "rate": "62000.00", "type": "Salary",
         "filing": "Single", "hire": "11/01/2023"},
    ],
    "Savannah Sweets": [
        {"name": "Lisa Jackson", "rate": "14.00", "type": "Hourly",
         "filing": "Single", "hire": "04/01/2021"},
        {"name": "Robert Kim", "rate": "15.00", "type": "Hourly",
         "filing": "Married", "hire": "07/15/2022"},
    ],
}

# Vendors (shared across clients for realism)
VENDORS = [
    {"name": "Georgia Power", "company": "Georgia Power Company",
     "phone": "(800) 555-0100", "email": "billing@gapower.com",
     "street": "241 Ralph McGill Blvd", "city": "Atlanta", "state": "GA",
     "zip": "30308", "is_1099": "No", "terms": "Net 30",
     "clients": ["Peachtree Landscaping LLC", "Atlanta Tech Solutions Inc",
                  "Savannah Sweets"]},
    {"name": "Office Depot", "company": "Office Depot Inc",
     "phone": "(800) 555-0200", "email": "orders@officedepot.com",
     "street": "6600 N Military Trail", "city": "Boca Raton", "state": "FL",
     "zip": "33496", "is_1099": "No", "terms": "Net 30",
     "clients": ["Atlanta Tech Solutions Inc", "Savannah Sweets"]},
    {"name": "Davis Plumbing", "company": "Davis Plumbing Services",
     "phone": "(770) 555-2345", "email": "mike@davisplumbing.com",
     "street": "123 Elm St", "city": "Kennesaw", "state": "GA",
     "zip": "30144", "is_1099": "Yes", "terms": "Due on receipt",
     "clients": ["Peachtree Landscaping LLC"]},
    {"name": "SiteOne Landscape Supply", "company": "SiteOne Landscape Supply LLC",
     "phone": "(770) 555-3456", "email": "sales@siteone.com",
     "street": "300 Colonial Center Pkwy", "city": "Roswell", "state": "GA",
     "zip": "30076", "is_1099": "No", "terms": "Net 15",
     "clients": ["Peachtree Landscaping LLC"]},
    {"name": "Amazon Web Services", "company": "Amazon.com Inc",
     "phone": "(888) 555-4567", "email": "billing@aws.amazon.com",
     "street": "410 Terry Ave N", "city": "Seattle", "state": "WA",
     "zip": "98109", "is_1099": "No", "terms": "Net 30",
     "clients": ["Atlanta Tech Solutions Inc"]},
    {"name": "Sysco Foods", "company": "Sysco Corporation",
     "phone": "(912) 555-5678", "email": "orders@sysco.com",
     "street": "1390 Enclave Pkwy", "city": "Houston", "state": "TX",
     "zip": "77077", "is_1099": "No", "terms": "Net 15",
     "clients": ["Savannah Sweets"]},
    {"name": "Johnson Insurance Agency", "company": "Johnson Insurance LLC",
     "phone": "(404) 555-6789", "email": "tom@johnsoninsurance.com",
     "street": "3344 Peachtree Rd NE", "city": "Atlanta", "state": "GA",
     "zip": "30326", "is_1099": "Yes", "terms": "Due on receipt",
     "clients": ["Peachtree Landscaping LLC", "Atlanta Tech Solutions Inc",
                  "Savannah Sweets"]},
    {"name": "Atlanta Web Design", "company": "Atlanta Web Design Co",
     "phone": "(678) 555-7890", "email": "hello@atlwebdesign.com",
     "street": "100 Centennial Olympic Park Dr", "city": "Atlanta",
     "state": "GA", "zip": "30313", "is_1099": "Yes", "terms": "Net 30",
     "clients": ["Savannah Sweets"]},
    {"name": "Peach State Fuel", "company": "Peach State Fuel Co",
     "phone": "(770) 555-8901", "email": "accounts@peachstatefuel.com",
     "street": "456 Industrial Blvd", "city": "Norcross", "state": "GA",
     "zip": "30071", "is_1099": "No", "terms": "Net 15",
     "clients": ["Peachtree Landscaping LLC"]},
    {"name": "Comcast Business", "company": "Comcast Corporation",
     "phone": "(800) 555-9012", "email": "business@comcast.com",
     "street": "One Comcast Center", "city": "Philadelphia", "state": "PA",
     "zip": "19103", "is_1099": "No", "terms": "Net 30",
     "clients": ["Atlanta Tech Solutions Inc", "Savannah Sweets"]},
]

# Chart of Accounts (QBO-format types and detail types)
BASE_ACCOUNTS = [
    # Assets
    ("Checking", "Bank", "Checking", "1000"),
    ("Savings", "Bank", "Savings", "1010"),
    ("Accounts Receivable (A/R)", "Accounts Receivable (A/R)",
     "Accounts Receivable (A/R)", "1100"),
    ("Undeposited Funds", "Other Current Assets", "Undeposited Funds", "1200"),
    ("Prepaid Insurance", "Other Current Assets", "Prepaid Expenses", "1300"),
    # Fixed Assets
    ("Vehicles", "Fixed Assets", "Vehicles", "1500"),
    ("Equipment", "Fixed Assets", "Machinery & Equipment", "1510"),
    ("Accumulated Depreciation", "Fixed Assets", "Accumulated Depreciation", "1520"),
    # Liabilities
    ("Accounts Payable (A/P)", "Accounts Payable (A/P)",
     "Accounts Payable (A/P)", "2000"),
    ("Credit Card", "Credit Card", "Credit Card", "2100"),
    ("Payroll Liabilities", "Other Current Liabilities",
     "Payroll Tax Payable", "2200"),
    ("Sales Tax Payable", "Other Current Liabilities",
     "Sales Tax Payable", "2300"),
    # Equity
    ("Owner's Equity", "Equity", "Owner's Equity", "3000"),
    ("Retained Earnings", "Equity", "Retained Earnings", "3100"),
    ("Owner's Draw", "Equity", "Owner's Equity", "3200"),
    # Income
    ("Services Revenue", "Income", "Service/Fee Income", "4000"),
    ("Product Sales", "Income", "Sales of Product Income", "4100"),
    ("Interest Income", "Other Income", "Interest Earned", "5000"),
    # COGS
    ("Materials & Supplies", "Cost of Goods Sold",
     "Supplies & Materials - COGS", "5200"),
    ("Cost of Labor", "Cost of Goods Sold", "Cost of labor - COS", "5300"),
    # Expenses
    ("Advertising", "Expenses", "Advertising/Promotional", "6000"),
    ("Auto Expense", "Expenses", "Auto", "6100"),
    ("Bank Charges", "Expenses", "Bank Charges & Fees", "6200"),
    ("Insurance", "Expenses", "Insurance", "6300"),
    ("Office Supplies", "Expenses", "Office/General Administrative Expenses", "6400"),
    ("Payroll Expenses", "Expenses", "Payroll Expenses", "6500"),
    ("Rent", "Expenses", "Rent or Lease of Buildings", "6600"),
    ("Repairs & Maintenance", "Expenses", "Repair & Maintenance", "6700"),
    ("Utilities:Electric", "Expenses", "Utilities", "6800"),
    ("Utilities:Water", "Expenses", "Utilities", "6810"),
    ("Utilities:Internet", "Expenses", "Utilities", "6820"),
    ("Depreciation Expense", "Other Expenses", "Depreciation", "8000"),
    ("Ask My Accountant", "Expenses",
     "Other Miscellaneous Service Cost", "9999"),
]

# Industry-specific accounts
INDUSTRY_ACCOUNTS = {
    "landscaping": [
        ("Landscaping Revenue", "Income", "Service/Fee Income", "4010"),
        ("Mulch & Soil", "Cost of Goods Sold",
         "Supplies & Materials - COGS", "5210"),
        ("Equipment Rental", "Expenses", "Equipment Rental", "6710"),
        ("Fuel", "Expenses", "Auto", "6110"),
    ],
    "technology": [
        ("Consulting Revenue", "Income", "Service/Fee Income", "4010"),
        ("Software Revenue", "Income", "Sales of Product Income", "4110"),
        ("Cloud Hosting", "Expenses", "Other Miscellaneous Service Cost", "6900"),
        ("Software Subscriptions", "Expenses", "Dues & Subscriptions", "6910"),
    ],
    "bakery": [
        ("Bakery Sales", "Income", "Sales of Product Income", "4010"),
        ("Catering Revenue", "Income", "Service/Fee Income", "4020"),
        ("Ingredients", "Cost of Goods Sold",
         "Supplies & Materials - COGS", "5210"),
        ("Packaging", "Cost of Goods Sold",
         "Supplies & Materials - COGS", "5220"),
    ],
}

# Transaction types for realistic variety
TRANSACTION_TYPES = [
    "Invoice", "Payment", "Bill", "Bill Payment (Check)", "Check",
    "Deposit", "Journal Entry", "Credit Card Expense", "Expense",
    "Sales Receipt", "Transfer",
]

# Invoice customers (customers OF the client, not the CPA's clients)
INVOICE_CUSTOMERS = {
    "Peachtree Landscaping LLC": [
        "Cobb County HOA", "Roswell Garden Estates", "Marietta City Parks",
        "The Greens at Vinings", "Buckhead Residential Group",
        "Dunwoody Commons HOA", "Sandy Springs Town Center",
    ],
    "Atlanta Tech Solutions Inc": [
        "Piedmont Healthcare", "Georgia-Pacific Corp",
        "Delta Air Lines IT Dept", "Cox Enterprises",
        "NCR Corporation", "Southern Company",
        "Equifax Technology Services",
    ],
    "Savannah Sweets": [
        "The Olde Pink House Restaurant", "Savannah Visitor Center",
        "Moon River Brewing Co", "River Street Market",
        "The Grey Restaurant", "Forsyth Park Cafe",
    ],
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def money(val):
    """Format a Decimal as a currency string with commas."""
    d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parts = str(d).split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"

    negative = integer_part.startswith("-")
    if negative:
        integer_part = integer_part[1:]

    # Add commas
    result = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            result = "," + result
        result = digit + result

    formatted = f"{result}.{decimal_part}"
    return f"-{formatted}" if negative else formatted


def random_date(start_date, end_date):
    """Generate a random date between start_date and end_date."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)


def generate_dates(count, start_year=2025, end_year=2025):
    """Generate sorted random dates within a year range."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    dates = [random_date(start, end) for _ in range(count)]
    dates.sort()
    return dates


# ==============================================================================
# GENERATORS
# ==============================================================================

def generate_chart_of_accounts(output_dir):
    """Generate Chart of Accounts CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"chart_of_accounts_samplecpa_{EXPORT_DATE}.csv"
    )

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        # QBO report header rows
        f.write('"Account List"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write(f'"As of {datetime.now().strftime("%B %d, %Y")}"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Account", "Type", "Detail Type", "Description",
                         "Balance", "Currency", "Account #"])

        # Generate accounts for each client's industry plus base accounts
        all_accounts = []
        for acct in BASE_ACCOUNTS:
            balance = Decimal(str(random.randint(0, 50000))) + \
                Decimal(str(random.randint(0, 99))) / 100
            # Some accounts should have negative balances (AP, credit card)
            if acct[1] in ("Accounts Payable (A/P)", "Credit Card"):
                balance = -balance
            # Accumulated depreciation is negative
            if "Accumulated" in acct[0]:
                balance = -abs(balance)
            all_accounts.append(acct + ("", money(balance), "USD"))

        # Add industry-specific accounts from all industries
        for industry, accounts in INDUSTRY_ACCOUNTS.items():
            for acct in accounts:
                balance = Decimal(str(random.randint(0, 30000))) + \
                    Decimal(str(random.randint(0, 99))) / 100
                all_accounts.append(acct + ("", money(balance), "USD"))

        for acct in all_accounts:
            writer.writerow([acct[0], acct[1], acct[2], acct[3],
                             acct[5], acct[6], acct[4]])

    print(f"  Generated: {filepath}")
    return filepath


def generate_customer_list(output_dir):
    """Generate Customer Contact List CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"customer_list_samplecpa_{EXPORT_DATE}.csv"
    )

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Customer Contact List"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write(f'"As of {datetime.now().strftime("%B %d, %Y")}"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Customer", "Phone", "Email", "Full Name", "Company",
            "Billing Street", "Billing City", "Billing State",
            "Billing ZIP", "Billing Country", "Open Balance", "Notes",
            "Tax Resale No.", "Terms", "Created"
        ])

        for client in CLIENTS:
            open_balance = money(
                Decimal(str(random.randint(0, 15000))) +
                Decimal(str(random.randint(0, 99))) / 100
            )
            writer.writerow([
                client["name"], client["phone"], client["email"],
                client["contact"], client["name"],
                client["street"], client["city"], client["state"],
                client["zip"], "US", open_balance,
                f"Entity: {client['entity_type']}",
                "", "Net 30",
                f"01/{random.randint(1,28):02d}/2020"
            ])

            # Add a sub-customer for the first client (Peachtree)
            if client["name"] == "Peachtree Landscaping LLC":
                writer.writerow([
                    "Peachtree Landscaping LLC:Residential Division",
                    client["phone"], client["email"],
                    "Mike Johnson", client["name"],
                    client["street"], client["city"], client["state"],
                    client["zip"], "US", "0.00", "", "", "Net 30",
                    "06/15/2021"
                ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_transaction_detail(output_dir):
    """Generate Transaction Detail by Account CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"transaction_detail_samplecpa_{EXPORT_DATE}.csv"
    )

    random.seed(42)  # Reproducible data

    # Generate dates spanning 12 months
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Transaction Detail by Account"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write('"January 1 - December 31, 2025"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Date", "Transaction Type", "No.", "Name",
            "Memo/Description", "Split", "Amount", "Balance", "Account"
        ])

        txn_counter = 1000
        running_balances = {}

        # Generate transactions per client
        for client in CLIENTS:
            client_name = client["name"]
            industry = client["industry"]
            industry_accts = INDUSTRY_ACCOUNTS.get(industry, [])
            customers = INVOICE_CUSTOMERS.get(client_name, [])
            client_vendors = [v for v in VENDORS
                              if client_name in v.get("clients", [])]

            # Generate ~60 transactions per client (>50 as required)
            num_txns = random.randint(55, 70)
            dates = generate_dates(num_txns, 2025, 2025)

            for i, txn_date in enumerate(dates):
                date_str = txn_date.strftime("%m/%d/%Y")
                txn_counter += 1
                txn_num = str(txn_counter)

                # Randomly choose transaction type
                txn_type_choice = random.random()

                if txn_type_choice < 0.25 and customers:
                    # Invoice
                    customer = random.choice(customers)
                    amount = Decimal(str(random.randint(500, 8000))) + \
                        Decimal(str(random.randint(0, 99))) / 100
                    rev_account = industry_accts[0][0] if industry_accts \
                        else "Services Revenue"

                    # AR debit line
                    writer.writerow([
                        date_str, "Invoice", txn_num, customer,
                        f"Invoice for services - {txn_date.strftime('%B %Y')}",
                        rev_account, money(amount), "",
                        "Accounts Receivable (A/R)"
                    ])
                    # Revenue credit line
                    writer.writerow([
                        date_str, "Invoice", txn_num, customer,
                        f"Invoice for services - {txn_date.strftime('%B %Y')}",
                        "Accounts Receivable (A/R)", money(amount), "",
                        rev_account
                    ])

                elif txn_type_choice < 0.35 and customers:
                    # Payment received
                    customer = random.choice(customers)
                    amount = Decimal(str(random.randint(500, 8000))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    writer.writerow([
                        date_str, "Payment", txn_num, customer,
                        f"Payment received",
                        "Accounts Receivable (A/R)", money(amount), "",
                        "Undeposited Funds"
                    ])
                    writer.writerow([
                        date_str, "Payment", txn_num, customer,
                        f"Payment received",
                        "Undeposited Funds", money(-amount), "",
                        "Accounts Receivable (A/R)"
                    ])

                elif txn_type_choice < 0.50 and client_vendors:
                    # Bill
                    vendor = random.choice(client_vendors)
                    amount = Decimal(str(random.randint(50, 3000))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    # Choose an expense account
                    expense_accounts = [
                        "Utilities:Electric", "Office Supplies", "Insurance",
                        "Rent", "Repairs & Maintenance", "Auto Expense",
                    ]
                    if industry_accts and len(industry_accts) > 1:
                        expense_accounts.append(industry_accts[1][0])
                    expense_acct = random.choice(expense_accounts)

                    writer.writerow([
                        date_str, "Bill", txn_num, vendor["name"],
                        f"{vendor['name']} - {txn_date.strftime('%B')} service",
                        expense_acct, money(amount), "",
                        "Accounts Payable (A/P)"
                    ])
                    writer.writerow([
                        date_str, "Bill", txn_num, vendor["name"],
                        f"{vendor['name']} - {txn_date.strftime('%B')} service",
                        "Accounts Payable (A/P)", money(amount), "",
                        expense_acct
                    ])

                elif txn_type_choice < 0.60 and client_vendors:
                    # Bill Payment (Check)
                    vendor = random.choice(client_vendors)
                    amount = Decimal(str(random.randint(50, 3000))) + \
                        Decimal(str(random.randint(0, 99))) / 100
                    check_num = str(5000 + random.randint(1, 999))

                    writer.writerow([
                        date_str, "Bill Payment (Check)", check_num,
                        vendor["name"],
                        f"Payment to {vendor['name']}",
                        "Accounts Payable (A/P)", money(-amount), "",
                        "Checking"
                    ])
                    writer.writerow([
                        date_str, "Bill Payment (Check)", check_num,
                        vendor["name"],
                        f"Payment to {vendor['name']}",
                        "Checking", money(-amount), "",
                        "Accounts Payable (A/P)"
                    ])

                elif txn_type_choice < 0.70:
                    # Check (direct expense)
                    check_num = str(5000 + random.randint(1, 999))
                    expense_accounts = [
                        "Office Supplies", "Repairs & Maintenance",
                        "Advertising", "Bank Charges",
                    ]
                    expense_acct = random.choice(expense_accounts)
                    amount = Decimal(str(random.randint(25, 500))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    payee = random.choice(
                        [v["name"] for v in client_vendors]
                    ) if client_vendors else "Cash"

                    writer.writerow([
                        date_str, "Check", check_num, payee,
                        f"Direct payment - {expense_acct.lower()}",
                        expense_acct, money(-amount), "", "Checking"
                    ])
                    writer.writerow([
                        date_str, "Check", check_num, payee,
                        f"Direct payment - {expense_acct.lower()}",
                        "Checking", money(amount), "", expense_acct
                    ])

                elif txn_type_choice < 0.78:
                    # Deposit
                    amount = Decimal(str(random.randint(1000, 15000))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    writer.writerow([
                        date_str, "Deposit", txn_num, "",
                        "Bank deposit",
                        "Undeposited Funds", money(amount), "", "Checking"
                    ])
                    writer.writerow([
                        date_str, "Deposit", txn_num, "",
                        "Bank deposit",
                        "Checking", money(-amount), "",
                        "Undeposited Funds"
                    ])

                elif txn_type_choice < 0.85:
                    # Credit Card Expense
                    amount = Decimal(str(random.randint(15, 300))) + \
                        Decimal(str(random.randint(0, 99))) / 100
                    cc_expenses = [
                        "Office Supplies", "Advertising",
                        "Utilities:Internet",
                    ]
                    cc_acct = random.choice(cc_expenses)

                    writer.writerow([
                        date_str, "Credit Card Expense", txn_num,
                        random.choice(
                            [v["name"] for v in client_vendors]
                        ) if client_vendors else "Various",
                        f"Credit card purchase - {cc_acct.lower()}",
                        cc_acct, money(amount), "", "Credit Card"
                    ])
                    writer.writerow([
                        date_str, "Credit Card Expense", txn_num,
                        random.choice(
                            [v["name"] for v in client_vendors]
                        ) if client_vendors else "Various",
                        f"Credit card purchase - {cc_acct.lower()}",
                        "Credit Card", money(amount), "", cc_acct
                    ])

                elif txn_type_choice < 0.92:
                    # Journal Entry (month-end adjustments)
                    je_num = f"JE-{txn_counter}"
                    amount = Decimal(str(random.randint(100, 2500))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    je_types = [
                        ("Depreciation Expense", "Accumulated Depreciation",
                         "Monthly depreciation"),
                        ("Insurance", "Prepaid Insurance",
                         "Amortize prepaid insurance"),
                        ("Payroll Expenses", "Payroll Liabilities",
                         "Accrue payroll liabilities"),
                    ]
                    debit_acct, credit_acct, memo = random.choice(je_types)

                    writer.writerow([
                        date_str, "Journal Entry", je_num, client_name,
                        memo, credit_acct, money(amount), "",
                        debit_acct
                    ])
                    writer.writerow([
                        date_str, "Journal Entry", je_num, client_name,
                        memo, debit_acct, money(-amount), "",
                        credit_acct
                    ])

                else:
                    # Transfer between bank accounts
                    amount = Decimal(str(random.randint(500, 5000))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    writer.writerow([
                        date_str, "Transfer", txn_num, "",
                        "Transfer to savings",
                        "Savings", money(-amount), "", "Checking"
                    ])
                    writer.writerow([
                        date_str, "Transfer", txn_num, "",
                        "Transfer to savings",
                        "Checking", money(amount), "", "Savings"
                    ])

            # Add one voided transaction per client
            void_date = random_date(start_date, end_date).strftime("%m/%d/%Y")
            txn_counter += 1
            writer.writerow([
                void_date, "Invoice", str(txn_counter),
                customers[0] if customers else client_name,
                "Void: Original invoice voided",
                "Services Revenue", "0.00", "",
                "Accounts Receivable (A/R)"
            ])

            # Add a few transactions with blank Name (edge case)
            for _ in range(3):
                blank_date = random_date(
                    start_date, end_date).strftime("%m/%d/%Y")
                txn_counter += 1
                amount = Decimal(str(random.randint(10, 50))) + \
                    Decimal(str(random.randint(0, 99))) / 100
                writer.writerow([
                    blank_date, "Expense", str(txn_counter), "",
                    "Bank service charge",
                    "Checking", money(amount), "", "Bank Charges"
                ])
                writer.writerow([
                    blank_date, "Expense", str(txn_counter), "",
                    "Bank service charge",
                    "Bank Charges", money(-amount), "", "Checking"
                ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_invoice_list(output_dir):
    """Generate Invoice List CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"invoice_list_samplecpa_{EXPORT_DATE}.csv"
    )

    random.seed(43)  # Different seed for variety

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Invoice List"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write('"January 1 - December 31, 2025"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Invoice Date", "No.", "Customer", "Due Date", "Terms",
            "Memo/Description", "Amount", "Open Balance", "Status"
        ])

        inv_counter = 1000

        for client in CLIENTS:
            client_name = client["name"]
            customers = INVOICE_CUSTOMERS.get(client_name, [])

            # Generate 12-18 invoices per client (>10 as required)
            num_invoices = random.randint(12, 18)
            dates = generate_dates(num_invoices, 2025, 2025)

            for inv_date in dates:
                inv_counter += 1
                inv_date_str = inv_date.strftime("%m/%d/%Y")
                due_date = inv_date + timedelta(days=30)
                due_date_str = due_date.strftime("%m/%d/%Y")
                customer = random.choice(customers)
                amount = Decimal(str(random.randint(500, 12000))) + \
                    Decimal(str(random.randint(0, 99))) / 100

                # Determine status
                status_roll = random.random()
                if status_roll < 0.50:
                    status = "Paid"
                    open_balance = "0.00"
                elif status_roll < 0.75:
                    status = "Open"
                    open_balance = money(amount)
                elif status_roll < 0.90:
                    status = "Overdue"
                    open_balance = money(amount)
                else:
                    # Partially paid
                    status = "Open"
                    partial = amount * Decimal(str(
                        random.randint(30, 70))) / Decimal("100")
                    open_balance = money(amount - partial)

                memo = f"Services for {inv_date.strftime('%B %Y')}"

                writer.writerow([
                    inv_date_str, str(inv_counter), customer,
                    due_date_str, "Net 30", memo,
                    money(amount), open_balance, status
                ])

            # Add one voided invoice per client
            inv_counter += 1
            void_date = random_date(
                datetime(2025, 1, 1), datetime(2025, 12, 31)
            )
            writer.writerow([
                void_date.strftime("%m/%d/%Y"), str(inv_counter),
                customers[0] if customers else client_name,
                (void_date + timedelta(days=30)).strftime("%m/%d/%Y"),
                "Net 30", "Void: Duplicate invoice",
                "0.00", "0.00", "Voided"
            ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_employee_details(output_dir):
    """Generate Employee Details CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"employee_details_samplecpa_{EXPORT_DATE}.csv"
    )

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Employee Details"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write(f'"As of {datetime.now().strftime("%B %d, %Y")}"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Employee", "SSN (last 4)", "Hire Date", "Status",
            "Pay Rate", "Pay Type", "Pay Schedule",
            "Filing Status (Federal)"
        ])

        ssn_counter = 1000
        for client_name, emps in EMPLOYEES.items():
            for emp in emps:
                ssn_counter += random.randint(100, 999)
                ssn_last4 = f"xxxx-xx-{ssn_counter % 10000:04d}"

                pay_schedule = "Every other week" if emp["type"] == "Hourly" \
                    else "Twice a month"

                writer.writerow([
                    emp["name"], ssn_last4, emp["hire"], "Active",
                    money(Decimal(emp["rate"])), emp["type"],
                    pay_schedule, emp["filing"]
                ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_payroll_detail(output_dir):
    """Generate Payroll Detail CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"payroll_detail_samplecpa_{EXPORT_DATE}.csv"
    )

    random.seed(44)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Payroll Details"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write('"January 1 - December 31, 2025"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Employee", "Pay Period", "Pay Date", "Hours",
            "Gross Pay", "Federal Withholding",
            "Social Security Employee", "Medicare Employee",
            "GA Withholding", "Net Pay",
            "Social Security Employer", "Medicare Employer",
            "Federal Unemployment", "GA SUI", "Check No."
        ])

        check_counter = 4000

        # Generate bi-weekly pay periods for 2025
        pay_periods = []
        period_start = datetime(2025, 1, 1)
        while period_start < datetime(2025, 12, 31):
            period_end = period_start + timedelta(days=13)
            if period_end > datetime(2025, 12, 31):
                period_end = datetime(2025, 12, 31)
            pay_date = period_end + timedelta(days=5)
            pay_periods.append((period_start, period_end, pay_date))
            period_start = period_end + timedelta(days=1)

        for client_name, emps in EMPLOYEES.items():
            for emp in emps:
                for period_start, period_end, pay_date in pay_periods:
                    check_counter += 1

                    if emp["type"] == "Hourly":
                        hours = Decimal(str(
                            random.randint(60, 90))) + Decimal("0.5") * \
                            random.randint(0, 1)
                        gross = (hours * Decimal(emp["rate"])).quantize(
                            Decimal("0.01"))
                    else:
                        hours = Decimal("80.00")
                        # Bi-weekly salary = annual / 26
                        gross = (Decimal(emp["rate"]) / Decimal("26")).quantize(
                            Decimal("0.01"))

                    # Calculate taxes
                    # SOURCE: Approximate rates for sample data generation
                    # These are NOT production rates -- see payroll_tax_tables
                    fed_wh = (gross * Decimal("0.12")).quantize(
                        Decimal("0.01"))
                    ss_ee = (gross * Decimal("0.062")).quantize(
                        Decimal("0.01"))
                    med_ee = (gross * Decimal("0.0145")).quantize(
                        Decimal("0.01"))
                    ga_wh = (gross * Decimal("0.0525")).quantize(
                        Decimal("0.01"))
                    net = gross - fed_wh - ss_ee - med_ee - ga_wh

                    ss_er = ss_ee  # Employer matches
                    med_er = med_ee
                    futa = (gross * Decimal("0.006")).quantize(
                        Decimal("0.01"))
                    # SOURCE: Georgia DOR, new employer rate 2.7%
                    # on first $9,500 wages
                    ga_sui = (gross * Decimal("0.027")).quantize(
                        Decimal("0.01"))

                    period_str = (
                        f"{period_start.strftime('%m/%d/%Y')} to "
                        f"{period_end.strftime('%m/%d/%Y')}"
                    )

                    writer.writerow([
                        emp["name"], period_str,
                        pay_date.strftime("%m/%d/%Y"),
                        str(hours), money(gross), money(fed_wh),
                        money(ss_ee), money(med_ee), money(ga_wh),
                        money(net), money(ss_er), money(med_er),
                        money(futa), money(ga_sui),
                        f"DD-{check_counter}"
                    ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_payroll_summary(output_dir):
    """Generate Payroll Summary CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"payroll_summary_samplecpa_{EXPORT_DATE}.csv"
    )

    random.seed(44)  # Same seed as detail for consistency

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Payroll Summary"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write('"January 1 - December 31, 2025"\n')
        f.write("\n")

        # Payroll summary has a different header structure
        # Two-level headers
        f.write('"","","EMPLOYEE","","","","","EMPLOYER","","",""\n')

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Employee", "Gross Pay", "Federal Withholding",
            "Social Security Employee", "Medicare Employee",
            "GA Withholding", "Net Pay",
            "Social Security Employer", "Medicare Employer",
            "Federal Unemployment", "GA SUI"
        ])

        totals = {col: Decimal("0") for col in [
            "gross", "fed", "ss_ee", "med_ee", "ga_wh", "net",
            "ss_er", "med_er", "futa", "ga_sui"
        ]}

        for client_name, emps in EMPLOYEES.items():
            for emp in emps:
                if emp["type"] == "Hourly":
                    # Approximate annual (26 pay periods * ~75 hours avg)
                    annual_hours = 26 * 75
                    gross = (Decimal(str(annual_hours)) *
                             Decimal(emp["rate"])).quantize(Decimal("0.01"))
                else:
                    gross = Decimal(emp["rate"])

                fed_wh = (gross * Decimal("0.12")).quantize(Decimal("0.01"))
                ss_ee = (gross * Decimal("0.062")).quantize(Decimal("0.01"))
                med_ee = (gross * Decimal("0.0145")).quantize(Decimal("0.01"))
                ga_wh = (gross * Decimal("0.0525")).quantize(Decimal("0.01"))
                net = gross - fed_wh - ss_ee - med_ee - ga_wh
                ss_er = ss_ee
                med_er = med_ee
                futa = (gross * Decimal("0.006")).quantize(Decimal("0.01"))
                ga_sui = (gross * Decimal("0.027")).quantize(Decimal("0.01"))

                writer.writerow([
                    emp["name"], money(gross), money(fed_wh),
                    money(ss_ee), money(med_ee), money(ga_wh),
                    money(net), money(ss_er), money(med_er),
                    money(futa), money(ga_sui)
                ])

                totals["gross"] += gross
                totals["fed"] += fed_wh
                totals["ss_ee"] += ss_ee
                totals["med_ee"] += med_ee
                totals["ga_wh"] += ga_wh
                totals["net"] += net
                totals["ss_er"] += ss_er
                totals["med_er"] += med_er
                totals["futa"] += futa
                totals["ga_sui"] += ga_sui

        # Grand total row
        writer.writerow([
            "TOTAL",
            money(totals["gross"]), money(totals["fed"]),
            money(totals["ss_ee"]), money(totals["med_ee"]),
            money(totals["ga_wh"]), money(totals["net"]),
            money(totals["ss_er"]), money(totals["med_er"]),
            money(totals["futa"]), money(totals["ga_sui"])
        ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_vendor_list(output_dir):
    """Generate Vendor Contact List CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"vendor_list_samplecpa_{EXPORT_DATE}.csv"
    )

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Vendor Contact List"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write(f'"As of {datetime.now().strftime("%B %d, %Y")}"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Vendor", "Company", "Phone", "Email", "Street",
            "City", "State", "ZIP", "Country", "Tax ID",
            "1099 Tracking", "Terms", "Open Balance"
        ])

        for vendor in VENDORS:
            # Mask tax ID like QBO does
            tax_id = f"XX-XXXXX{random.randint(10, 99):02d}" \
                if vendor["is_1099"] == "Yes" else ""
            open_balance = money(
                Decimal(str(random.randint(0, 2000))) +
                Decimal(str(random.randint(0, 99))) / 100
            ) if random.random() < 0.3 else "0.00"

            writer.writerow([
                vendor["name"], vendor["company"], vendor["phone"],
                vendor["email"], vendor["street"], vendor["city"],
                vendor["state"], vendor["zip"], "US", tax_id,
                vendor["is_1099"], vendor["terms"], open_balance
            ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_bill_list(output_dir):
    """Generate Bill List CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"bill_list_samplecpa_{EXPORT_DATE}.csv"
    )

    random.seed(45)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Transaction List by Vendor"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write('"January 1 - December 31, 2025"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Date", "Transaction Type", "No.", "Vendor", "Due Date",
            "Terms", "Memo/Description", "Amount", "Open Balance",
            "Account"
        ])

        bill_counter = 0

        for client in CLIENTS:
            client_name = client["name"]
            client_vendors = [v for v in VENDORS
                              if client_name in v.get("clients", [])]

            for vendor in client_vendors:
                # Generate 2-5 bills per vendor per client
                num_bills = random.randint(2, 5)
                dates = generate_dates(num_bills, 2025, 2025)

                for bill_date in dates:
                    bill_counter += 1
                    bill_date_str = bill_date.strftime("%m/%d/%Y")
                    due_date = bill_date + timedelta(days=30)
                    due_date_str = due_date.strftime("%m/%d/%Y")

                    amount = Decimal(str(random.randint(50, 3000))) + \
                        Decimal(str(random.randint(0, 99))) / 100

                    # Status: 60% paid, 30% open, 10% overdue
                    status_roll = random.random()
                    if status_roll < 0.60:
                        open_balance = "0.00"
                    elif status_roll < 0.90:
                        open_balance = money(amount)
                    else:
                        open_balance = money(amount)

                    # Choose expense account
                    expense_accounts = [
                        "Utilities:Electric", "Office Supplies",
                        "Insurance", "Repairs & Maintenance",
                    ]
                    expense_acct = random.choice(expense_accounts)

                    bill_num = f"INV-{bill_date.strftime('%Y')}-{bill_counter:04d}"

                    writer.writerow([
                        bill_date_str, "Bill", bill_num, vendor["name"],
                        due_date_str, vendor["terms"],
                        f"{vendor['name']} - {bill_date.strftime('%B')} service",
                        money(amount), open_balance, expense_acct
                    ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_general_journal(output_dir):
    """Generate General Journal CSV in QBO export format."""
    filepath = os.path.join(
        output_dir,
        f"general_journal_samplecpa_{EXPORT_DATE}.csv"
    )

    random.seed(46)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        f.write('"Journal"\n')
        f.write(f'"{COMPANY_NAME}"\n')
        f.write('"January 1 - December 31, 2025"\n')
        f.write("\n")

        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Date", "Transaction Type", "No.", "Name",
            "Memo/Description", "Account", "Debit", "Credit"
        ])

        je_counter = 0

        for client in CLIENTS:
            # Generate 3-5 journal entries per client (month-end adjustments)
            for month in range(1, 13):
                if random.random() < 0.4:  # Not every month
                    continue

                je_counter += 1
                last_day = datetime(
                    2025, month,
                    28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31
                )
                date_str = last_day.strftime("%m/%d/%Y")
                je_num = f"JE-{je_counter:03d}"

                amount = Decimal(str(random.randint(200, 3000))) + \
                    Decimal(str(random.randint(0, 99))) / 100

                je_types = [
                    ("Depreciation Expense", "Accumulated Depreciation",
                     "Monthly depreciation"),
                    ("Insurance", "Prepaid Insurance",
                     "Amortize prepaid insurance"),
                    ("Payroll Expenses", "Payroll Liabilities",
                     "Accrue payroll liabilities"),
                ]
                debit_acct, credit_acct, memo = random.choice(je_types)

                writer.writerow([
                    date_str, "Journal Entry", je_num, client["name"],
                    f"{memo} - {last_day.strftime('%B %Y')}",
                    debit_acct, money(amount), ""
                ])
                writer.writerow([
                    date_str, "Journal Entry", je_num, client["name"],
                    f"{memo} - {last_day.strftime('%B %Y')}",
                    credit_acct, "", money(amount)
                ])

    print(f"  Generated: {filepath}")
    return filepath


def generate_supplemental_mappings(output_dir):
    """Generate CPA-provided supplemental mapping files."""

    # Entity type mapping
    filepath = os.path.join(output_dir, "entity_type_mapping.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_name", "entity_type"])
        for client in CLIENTS:
            writer.writerow([client["name"], client["entity_type"]])
    print(f"  Generated: {filepath}")

    # Employee-to-client mapping
    filepath = os.path.join(output_dir, "employee_client_mapping.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["employee_name", "client_name"])
        for client_name, emps in EMPLOYEES.items():
            for emp in emps:
                writer.writerow([emp["name"], client_name])
    print(f"  Generated: {filepath}")

    # Vendor-to-client mapping
    filepath = os.path.join(output_dir, "vendor_client_mapping.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["vendor_name", "client_name"])
        for vendor in VENDORS:
            for client_name in vendor.get("clients", []):
                writer.writerow([vendor["name"], client_name])
    print(f"  Generated: {filepath}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate sample QBO export CSV files for migration testing"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for CSV files "
             "(default: data/sample_qbo_exports/)"
    )
    args = parser.parse_args()

    # Determine output directory
    project_root = Path(__file__).parent.parent
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = str(project_root / "data" / "sample_qbo_exports")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating sample QBO export files in: {output_dir}")
    print(f"Export date: {EXPORT_DATE}")
    print(f"Clients: {len(CLIENTS)}")
    print(f"Total employees: {sum(len(e) for e in EMPLOYEES.values())}")
    print(f"Total vendors: {len(VENDORS)}")
    print()

    print("Generating QBO export files:")
    generate_chart_of_accounts(output_dir)
    generate_customer_list(output_dir)
    generate_transaction_detail(output_dir)
    generate_invoice_list(output_dir)
    generate_employee_details(output_dir)
    generate_payroll_detail(output_dir)
    generate_payroll_summary(output_dir)
    generate_vendor_list(output_dir)
    generate_bill_list(output_dir)
    generate_general_journal(output_dir)

    print()
    print("Generating supplemental mapping files:")
    generate_supplemental_mappings(output_dir)

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print()
    print("Files generated:")
    for f in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, f)
        size = os.path.getsize(fpath)
        print(f"  {f:55s} {size:>8,d} bytes")
    print()
    print("These files simulate QBO exports for 3 clients:")
    for client in CLIENTS:
        emp_count = len(EMPLOYEES.get(client["name"], []))
        vendor_count = len([
            v for v in VENDORS if client["name"] in v.get("clients", [])
        ])
        print(f"  - {client['name']} ({client['entity_type']}) "
              f"| {emp_count} employees | {vendor_count} vendors")
    print()
    print("Use these files to test the migration parser.")
    print("IMPORTANT: This is SAMPLE data. Do not use for production.")


if __name__ == "__main__":
    main()
