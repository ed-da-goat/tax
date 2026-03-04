"""
Client splitter for QuickBooks Online migration data.

Module M2 — Takes parsed QBO data (from QBOParser) and splits it into
per-client datasets. This module does NOT write to the database.

For single-company QBO files: all records belong to one client.
For multi-client CPA files: records are split by the Name/Customer
field in transactions, invoices, payroll, etc.

Client name matching is case-insensitive and whitespace-normalized.
"""

from dataclasses import dataclass, field

from .models import (
    ParsedAccount,
    ParsedCustomer,
    ParsedEmployee,
    ParsedInvoice,
    ParsedJournalEntry,
    ParsedPayrollRecord,
    ParsedTransaction,
    ParsedVendor,
)


@dataclass
class UnmatchedRecord:
    """A record that could not be assigned to any client."""

    record_type: str
    record: (
        ParsedTransaction
        | ParsedInvoice
        | ParsedVendor
        | ParsedEmployee
        | ParsedPayrollRecord
        | ParsedJournalEntry
    )
    reason: str


@dataclass
class ClientDataset:
    """All parsed QBO data belonging to a single client."""

    client_name: str
    entity_type: str | None = None
    accounts: list[ParsedAccount] = field(default_factory=list)
    transactions: list[ParsedTransaction] = field(default_factory=list)
    customers: list[ParsedCustomer] = field(default_factory=list)
    invoices: list[ParsedInvoice] = field(default_factory=list)
    vendors: list[ParsedVendor] = field(default_factory=list)
    employees: list[ParsedEmployee] = field(default_factory=list)
    payroll_records: list[ParsedPayrollRecord] = field(default_factory=list)
    journal_entries: list[ParsedJournalEntry] = field(default_factory=list)
    unmatched_records: list[UnmatchedRecord] = field(default_factory=list)


def _normalize_name(name: str | None) -> str:
    """Normalize a name for case-insensitive, whitespace-collapsed comparison."""
    if not name:
        return ""
    return " ".join(name.lower().split())


def _canonical_name(name: str | None, known_names: dict[str, str]) -> str | None:
    """
    Return the canonical (original-cased) client name for a given name,
    or None if no match is found.

    known_names maps normalized_name -> canonical_name.
    """
    if not name:
        return None
    normalized = _normalize_name(name)
    return known_names.get(normalized)


class ClientSplitter:
    """
    Splits parsed QBO data into per-client datasets.

    The primary split key is the customer/client name field from
    transactions and invoices. Vendors are assigned based on which
    client's transactions reference them. Employees are assigned
    based on payroll records. The chart of accounts is duplicated
    to every client.
    """

    def split_by_client(
        self,
        parsed_data: dict[str, list],
    ) -> dict[str, ClientDataset]:
        """
        Split all parsed QBO data into per-client datasets.

        Parameters
        ----------
        parsed_data : dict[str, list]
            Keys are record type names, values are lists of parsed model
            instances.  Expected keys (all optional):
              - "accounts"        : list[ParsedAccount]
              - "transactions"    : list[ParsedTransaction]
              - "customers"       : list[ParsedCustomer]
              - "invoices"        : list[ParsedInvoice]
              - "vendors"         : list[ParsedVendor]
              - "employees"       : list[ParsedEmployee]
              - "payroll_records" : list[ParsedPayrollRecord]
              - "journal_entries" : list[ParsedJournalEntry]

        Returns
        -------
        dict[str, ClientDataset]
            Mapping of canonical client name -> ClientDataset.
            An additional key "__unmatched__" is included if any records
            could not be assigned.
        """
        accounts: list[ParsedAccount] = parsed_data.get("accounts", [])
        transactions: list[ParsedTransaction] = parsed_data.get("transactions", [])
        customers: list[ParsedCustomer] = parsed_data.get("customers", [])
        invoices: list[ParsedInvoice] = parsed_data.get("invoices", [])
        vendors: list[ParsedVendor] = parsed_data.get("vendors", [])
        employees: list[ParsedEmployee] = parsed_data.get("employees", [])
        payroll_records: list[ParsedPayrollRecord] = parsed_data.get("payroll_records", [])
        journal_entries: list[ParsedJournalEntry] = parsed_data.get("journal_entries", [])

        # -----------------------------------------------------------------
        # Step 1: Discover client names from customers list and transaction
        #         names.  Build a normalized -> canonical name mapping.
        # -----------------------------------------------------------------
        canonical_names: dict[str, str] = {}  # normalized -> canonical

        # Customers are the primary source of client names
        for cust in customers:
            norm = _normalize_name(cust.name)
            if norm and norm not in canonical_names:
                canonical_names[norm] = cust.name.strip()

        # Also discover client names from transaction Name field
        for txn in transactions:
            if txn.name:
                norm = _normalize_name(txn.name)
                if norm and norm not in canonical_names:
                    canonical_names[norm] = txn.name.strip()

        # Also discover from invoice Customer field
        for inv in invoices:
            norm = _normalize_name(inv.customer)
            if norm and norm not in canonical_names:
                canonical_names[norm] = inv.customer.strip()

        # Also discover from journal entry Name field
        for je in journal_entries:
            if je.name:
                norm = _normalize_name(je.name)
                if norm and norm not in canonical_names:
                    canonical_names[norm] = je.name.strip()

        # -----------------------------------------------------------------
        # Step 2: Create ClientDataset for each discovered client
        # -----------------------------------------------------------------
        datasets: dict[str, ClientDataset] = {}
        for canonical in canonical_names.values():
            datasets[canonical] = ClientDataset(client_name=canonical)

        # If no clients discovered at all but we have data, treat as
        # single-client file: create one dataset named from the first
        # account or a default name.
        if not datasets and any([
            accounts, transactions, customers, invoices, vendors,
            employees, payroll_records, journal_entries,
        ]):
            default_name = "Default Client"
            datasets[default_name] = ClientDataset(client_name=default_name)
            canonical_names[_normalize_name(default_name)] = default_name

        # Collect unmatched records here
        unmatched: list[UnmatchedRecord] = []

        # -----------------------------------------------------------------
        # Step 3: Chart of accounts is SHARED — duplicate to each client
        # -----------------------------------------------------------------
        for dataset in datasets.values():
            dataset.accounts = list(accounts)

        # -----------------------------------------------------------------
        # Step 4: Assign customers to matching client datasets
        # -----------------------------------------------------------------
        for cust in customers:
            canonical = _canonical_name(cust.name, canonical_names)
            if canonical and canonical in datasets:
                datasets[canonical].customers.append(cust)

        # -----------------------------------------------------------------
        # Step 5: Assign transactions by Name field
        # -----------------------------------------------------------------
        # Track which vendors are referenced by which clients (for
        # vendor assignment later).
        vendor_to_clients: dict[str, set[str]] = {}  # normalized vendor -> set of canonical client names

        for txn in transactions:
            canonical = _canonical_name(txn.name, canonical_names)
            if canonical and canonical in datasets:
                datasets[canonical].transactions.append(txn)
                # If this is a bill/expense type, the Name might be a vendor
                # referenced by this client
                if txn.transaction_type and txn.transaction_type.lower() in (
                    "bill", "bill payment", "check", "expense",
                    "bill payment (check)", "bill payment (credit card)",
                ):
                    if txn.name:
                        vnorm = _normalize_name(txn.name)
                        vendor_to_clients.setdefault(vnorm, set()).add(canonical)
            elif txn.name is None or txn.name.strip() == "":
                unmatched.append(UnmatchedRecord(
                    record_type="transaction",
                    record=txn,
                    reason="Transaction has no client/customer name",
                ))
            else:
                # Name present but doesn't match any known client —
                # this could be a vendor name on the transaction. Still
                # track it but also mark as potentially client-less.
                # Try to match it later if it looks like a vendor reference.
                # For now, add to unmatched.
                unmatched.append(UnmatchedRecord(
                    record_type="transaction",
                    record=txn,
                    reason=f"Name '{txn.name}' does not match any known client",
                ))

        # -----------------------------------------------------------------
        # Step 6: Assign invoices by Customer field
        # -----------------------------------------------------------------
        for inv in invoices:
            canonical = _canonical_name(inv.customer, canonical_names)
            if canonical and canonical in datasets:
                datasets[canonical].invoices.append(inv)
            else:
                unmatched.append(UnmatchedRecord(
                    record_type="invoice",
                    record=inv,
                    reason=f"Customer '{inv.customer}' does not match any known client",
                ))

        # -----------------------------------------------------------------
        # Step 7: Assign vendors based on which client's transactions
        #         reference them (bill/expense transactions)
        # -----------------------------------------------------------------
        for vendor in vendors:
            vnorm = _normalize_name(vendor.name)
            client_names = vendor_to_clients.get(vnorm, set())
            if client_names:
                for client_name in client_names:
                    datasets[client_name].vendors.append(vendor)
            else:
                # Vendor not referenced in any client's bills/expenses.
                # Assign to all clients (they may need the vendor later)
                # or leave unmatched. Per spec, leave unmatched.
                unmatched.append(UnmatchedRecord(
                    record_type="vendor",
                    record=vendor,
                    reason=f"Vendor '{vendor.name}' not referenced in any client's transactions",
                ))

        # -----------------------------------------------------------------
        # Step 8: Assign employees based on payroll records
        # -----------------------------------------------------------------
        # First, build employee -> client mapping from payroll records
        # that reference a client via the employee name cross-referenced
        # with transaction names.
        # Since payroll records have employee name but not client name,
        # we assign employees to the client that has transactions where
        # the employee appears (e.g., payroll checks).
        employee_to_client: dict[str, str] = {}  # normalized employee name -> canonical client

        # Check if transactions reference employees (payroll check types)
        for txn in transactions:
            if txn.transaction_type and txn.transaction_type.lower() in (
                "payroll check", "paycheck", "payroll",
                "payroll liability check", "payroll tax payment",
            ):
                if txn.name:
                    enorm = _normalize_name(txn.name)
                    canonical = _canonical_name(txn.name, canonical_names)
                    # In a CPA multi-client file, payroll transactions may
                    # have employee names in the Name field — but those
                    # wouldn't be in canonical_names (which are client names).
                    # We need a different approach: look at the account or
                    # memo for a client reference, or match employees to
                    # the single client if only one exists.
                    if canonical and canonical in datasets:
                        employee_to_client[enorm] = canonical

        # If there is exactly one client, all employees belong to it.
        single_client = None
        if len(datasets) == 1:
            single_client = next(iter(datasets))

        for emp in employees:
            enorm = _normalize_name(emp.name)
            if enorm in employee_to_client:
                client_name = employee_to_client[enorm]
                datasets[client_name].employees.append(emp)
            elif single_client:
                datasets[single_client].employees.append(emp)
            else:
                unmatched.append(UnmatchedRecord(
                    record_type="employee",
                    record=emp,
                    reason=f"Employee '{emp.name}' cannot be mapped to a client",
                ))

        # -----------------------------------------------------------------
        # Step 9: Assign payroll records based on employee -> client mapping
        # -----------------------------------------------------------------
        for pr in payroll_records:
            enorm = _normalize_name(pr.employee)
            if enorm in employee_to_client:
                client_name = employee_to_client[enorm]
                datasets[client_name].payroll_records.append(pr)
            elif single_client:
                datasets[single_client].payroll_records.append(pr)
            else:
                unmatched.append(UnmatchedRecord(
                    record_type="payroll_record",
                    record=pr,
                    reason=f"Employee '{pr.employee}' on payroll record cannot be mapped to a client",
                ))

        # -----------------------------------------------------------------
        # Step 10: Assign journal entries by Name field
        # -----------------------------------------------------------------
        for je in journal_entries:
            canonical = _canonical_name(je.name, canonical_names)
            if canonical and canonical in datasets:
                datasets[canonical].journal_entries.append(je)
            elif je.name is None or je.name.strip() == "":
                unmatched.append(UnmatchedRecord(
                    record_type="journal_entry",
                    record=je,
                    reason="Journal entry has no name/client reference",
                ))
            else:
                unmatched.append(UnmatchedRecord(
                    record_type="journal_entry",
                    record=je,
                    reason=f"Name '{je.name}' does not match any known client",
                ))

        # -----------------------------------------------------------------
        # Step 11: If there are unmatched records, store them in a special
        #          dataset so the caller can review them.
        # -----------------------------------------------------------------
        if unmatched:
            unmatched_ds = datasets.get("__unmatched__")
            if not unmatched_ds:
                unmatched_ds = ClientDataset(client_name="__unmatched__")
                datasets["__unmatched__"] = unmatched_ds
            unmatched_ds.unmatched_records.extend(unmatched)

        return datasets
