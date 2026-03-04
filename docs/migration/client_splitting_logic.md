# Client Splitting Logic — QBO Single Account to Per-Client Ledgers

**Agent:** QB Format Research Agent (Agent 05)
**Date:** 2026-03-04
**Purpose:** Document the exact algorithm for splitting one QBO company file into isolated per-client ledgers in the target PostgreSQL database.

---

## 1. Problem Statement

QuickBooks Online stores all of a CPA firm's client data within a single company file. The target database requires strict client isolation -- every record must have a `client_id` foreign key, and queries must never leak data across clients.

This document specifies how to deterministically assign a `client_id` to every record imported from QBO.

---

## 2. Client Identification Fields in QBO

### 2.1 Primary Identification Field

The **Customer** field (or **Name** field in transaction exports) is the primary identifier for splitting data by client.

| QBO Export                  | Client Identifier Column | Column Header Text       |
|-----------------------------|--------------------------|--------------------------|
| Customer Contact List       | Customer                 | `Customer`               |
| Transaction Detail by Account | Name                  | `Name`                   |
| Invoice List                | Customer                 | `Customer`               |
| Payroll Summary/Detail      | (none -- see Section 4)  | —                        |
| Vendor Contact List         | (none -- see Section 5)  | —                        |
| Bills / AP                  | (none -- see Section 5)  | —                        |
| General Journal             | Name                     | `Name`                   |

### 2.2 Alternative Identification: Class Tracking

**[CPA_REVIEW_NEEDED]** If the CPA firm uses QBO Class Tracking to tag transactions by client, the `Class` column may be a more reliable client identifier than the `Name` field because:

- Classes are explicitly assigned (not inferred from counterparty name)
- A transaction's Name field may refer to a sub-vendor or employee, not the client
- Classes are maintained in a controlled list (less prone to typos)

**Decision needed from CPA:**
1. Is Class Tracking enabled in QBO?
2. If yes, do classes map 1:1 to clients?
3. Should Class override Name for client assignment?
4. Are there transactions with a Class but no Name, or vice versa?

If Class is the primary client identifier, replace all references to "Name" in this document with "Class".

---

## 3. Client Registry Construction Algorithm

### Step 1: Build the Master Client List

```
INPUT:  Customer Contact List CSV
OUTPUT: Client registry (dictionary: normalized_name -> client record)

ALGORITHM:
1. Read Customer Contact List CSV
2. For each row:
   a. Extract "Customer" column value
   b. Skip if this is a sub-customer (contains ":" delimiter) -- handled in Step 2
   c. Normalize the name (see Section 3.1)
   d. Create a client record:
      - original_name = raw Customer value
      - normalized_name = normalized value
      - client_id = new UUID
      - entity_type = lookup from entity_type_mapping.csv (FATAL if not found)
      - phone, email, address, city, state, zip = from corresponding columns
   e. Add to client registry, keyed by normalized_name
3. Check for duplicate normalized names -> FATAL error if any duplicates found
4. Return client registry
```

### Step 2: Handle Sub-Customers

```
INPUT:  Customer Contact List CSV rows containing ":" in Customer field
OUTPUT: Sub-customer to parent mapping

ALGORITHM:
1. For each sub-customer row (Customer field contains ":"):
   a. Split on ":" -> ["Parent Name", "Sub-customer Name"]
   b. Normalize "Parent Name"
   c. Look up parent in client registry
   d. If parent found: map sub-customer to parent's client_id
   e. If parent NOT found: FATAL error -- orphaned sub-customer
2. Return sub-customer mapping
```

**Example:**
```
"Peachtree Landscaping LLC"                -> client_id = UUID-001
"Peachtree Landscaping LLC:Atlanta Office" -> maps to client_id = UUID-001
"Peachtree Landscaping LLC:Marietta Office"-> maps to client_id = UUID-001
```

### 3.1 Name Normalization Function

```python
import re
import unicodedata

def normalize_client_name(name: str) -> str:
    """
    Normalize a client/customer name for matching purposes.

    Rules:
    1. Strip leading/trailing whitespace
    2. Convert to uppercase
    3. Normalize Unicode characters (e.g., accented chars -> ASCII)
    4. Collapse multiple whitespace to single space
    5. Remove common suffixes that cause false mismatches
    6. Remove punctuation except hyphens and ampersands
    """
    if not name:
        return ""

    # Step 1: Strip whitespace
    result = name.strip()

    # Step 2: Uppercase
    result = result.upper()

    # Step 3: Unicode normalization
    result = unicodedata.normalize('NFKD', result)
    result = result.encode('ASCII', 'ignore').decode('ASCII')

    # Step 4: Collapse whitespace
    result = re.sub(r'\s+', ' ', result)

    # Step 5: Standardize common business suffixes
    suffix_map = {
        r'\bL\.?L\.?C\.?\b': 'LLC',
        r'\bINC\.?\b': 'INC',
        r'\bCORP\.?\b': 'CORP',
        r'\bCO\.?\b': 'CO',
        r'\bLTD\.?\b': 'LTD',
        r'\bP\.?C\.?\b': 'PC',
        r'\bP\.?A\.?\b': 'PA',
        r'\bD/?B/?A\b': 'DBA',
    }
    for pattern, replacement in suffix_map.items():
        result = re.sub(pattern, replacement, result)

    # Step 6: Remove punctuation except hyphens and ampersands
    result = re.sub(r'[^\w\s\-&]', '', result)

    # Final whitespace cleanup
    result = re.sub(r'\s+', ' ', result).strip()

    return result
```

---

## 4. Transaction Splitting Algorithm

### Step 3: Assign Transactions to Clients

```
INPUT:  Transaction Detail by Account CSV
        Client registry (from Step 1)
        Sub-customer mapping (from Step 2)
OUTPUT: Transactions with client_id assignments
        Flagged records list

ALGORITHM:
For each transaction row:
1. Extract "Name" column value
2. If Name is blank or NULL:
   -> Flag as [UNASSIGNED], set client_id = NULL
   -> Add to flagged records list
   -> Continue to next row

3. Normalize the Name value

4. EXACT MATCH: Look up normalized name in client registry
   -> If found: assign client_id from registry
   -> Continue to next row

5. SUB-CUSTOMER MATCH: Check if Name matches a sub-customer
   -> If found: assign parent's client_id
   -> Continue to next row

6. FUZZY MATCH: Compute Levenshtein distance against all registry entries
   -> If exactly ONE match with distance <= 3 characters:
      -> Flag as [FUZZY_MATCH] with original and matched name
      -> Tentatively assign client_id (requires CPA confirmation)
   -> If MULTIPLE matches with distance <= 3:
      -> Flag as [AMBIGUOUS]
      -> Set client_id = NULL
   -> If NO matches within distance 3:
      -> Flag as [UNASSIGNED]
      -> Set client_id = NULL

7. Record the assignment decision in the migration audit log
```

### Step 4: Assign Invoices to Clients

```
INPUT:  Invoice List CSV
        Client registry (from Step 1)
OUTPUT: Invoices with client_id assignments

ALGORITHM:
For each invoice row:
1. Extract "Customer" column value
2. Follow same matching logic as Step 3 (exact -> sub-customer -> fuzzy)
3. SPECIAL CASE: If invoice Customer does not match any client but
   matches a vendor name, flag as [POSSIBLE_VENDOR_INVOICE] for CPA review
```

### Step 5: Assign Payroll Records to Clients

```
INPUT:  Payroll Summary/Detail CSV
        Employee-to-client mapping CSV (provided by CPA)
OUTPUT: Payroll records with client_id assignments

ALGORITHM:
For each payroll row:
1. Extract "Employee" column value
2. Look up employee in employee-to-client mapping:
   -> If found: assign client_id from mapping
   -> If NOT found: Flag as [UNMAPPED_EMPLOYEE], set client_id = NULL
3. Validate: all payroll items within the same payroll_run must have
   the same client_id (one payroll run per client)
```

### Step 6: Assign Vendors and Bills to Clients

```
INPUT:  Vendor Contact List CSV
        Vendor-to-client mapping CSV (provided by CPA)
        Bills CSV
OUTPUT: Vendors and bills with client_id assignments

ALGORITHM:
For vendors:
1. Read vendor-to-client mapping CSV
2. For each vendor:
   a. Look up in mapping
   b. If vendor serves multiple clients: create one vendor record per client
   c. If vendor is not in mapping: flag as [UNMAPPED_VENDOR]

For bills:
1. Extract "Vendor" column from bill row
2. Look up vendor -> get client_id from vendor record
3. If vendor has multiple client_ids:
   -> Check if bill's transaction appears in a client-specific account
   -> If still ambiguous: flag as [AMBIGUOUS_BILL]
```

---

## 5. Edge Cases

### 5.1 Transaction Assigned to No Client

**Scenario:** The "Name" field in the Transaction Detail is blank.

**Handling:**
- Flag as `[UNASSIGNED]`
- Set `client_id = NULL` temporarily
- Add to the CPA review queue
- These records will appear in the Migration Audit Report
- The CPA must manually assign each to a client before final import

**Common causes:**
- Bank fees and charges (no specific customer/vendor)
- Owner draws or capital contributions
- General overhead expenses
- Journal entries without a counterparty

**Recommendation:** Before export, CPA should review QBO transactions with blank Name fields and assign names where possible.

### 5.2 Transaction Assigned to Multiple Clients

**Scenario:** A single QBO transaction has line items affecting multiple clients (e.g., a combined deposit, a shared expense allocation).

**Handling:**
- If the "Split" column shows `-Split-`, examine each journal entry line individually
- Each line's "Name" field may differ, allowing per-line client assignment
- If the entire transaction has a single Name but should be split across clients:
  - Flag as `[MULTI_CLIENT]`
  - Do NOT auto-split -- the CPA must decide how to allocate
  - Provide the CPA with the transaction details for manual splitting

### 5.3 Client Name Variations

**Scenario:** The same client appears with different spellings across QBO records.

**Examples:**
```
"ABC Corp"           vs  "ABC Corporation"
"Smith & Sons"       vs  "Smith and Sons"
"J. Williams"        vs  "James Williams"
"Peachtree Landscape" vs  "Peachtree Landscaping LLC"
```

**Handling:**
1. Normalization (Section 3.1) handles many variations (suffix standardization, punctuation removal)
2. Fuzzy matching (Levenshtein distance <= 3) catches close typos
3. For remaining mismatches:
   - Generate a "potential duplicates" report showing all pairs with Levenshtein distance 4-8
   - CPA reviews and confirms or rejects each pair
   - Confirmed matches are added to a `name_aliases.csv` file:
     ```csv
     alias_name,canonical_name
     "ABC Corp","ABC Corporation"
     "J. Williams","James Williams"
     ```
   - The parser loads this alias file and applies it before matching

### 5.4 Sub-Customers in QBO

**Scenario:** QBO supports hierarchical customers (parent:child relationships).

**Handling:**
- All sub-customers roll up to their parent customer
- The parent customer's `client_id` is used for all sub-customer records
- The sub-customer name is preserved in the transaction's memo/description for audit trail
- Sub-customer names appearing in the Name column are matched to the parent:
  ```
  Name: "Peachtree Landscaping LLC:Atlanta Office"
  -> Split on ":"
  -> Match parent "Peachtree Landscaping LLC" to client registry
  -> Assign parent's client_id
  ```

### 5.5 Inter-Client Transfers

**Scenario:** A QBO transaction represents a transfer or allocation between two clients (e.g., shared rent split between two businesses).

**Handling:**
- Flag as `[INTER_CLIENT]`
- Do NOT auto-resolve
- Present both sides to the CPA:
  ```
  INTER-CLIENT TRANSFER DETECTED
  Transaction: JE-005, Date: 03/31/2025, Amount: $2,000.00
  Line 1: Debit  Rent Expense    Name: "Client A"  -> client_id: UUID-001
  Line 2: Credit Cash            Name: "Client B"  -> client_id: UUID-002

  ACTION REQUIRED: CPA must decide how to record this:
  Option A: Split into two separate journal entries (one per client)
  Option B: Record fully under one client with a note
  Option C: Skip and re-enter manually after migration
  ```

### 5.6 Vendor Transactions Without Client Association

**Scenario:** A bill or expense is paid to a vendor but the Name field in QBO shows the vendor name, not a client name.

**Handling:**
- The "Name" field in expense transactions typically shows the vendor, not the client
- Client association must be derived from:
  1. The vendor-to-client mapping CSV (preferred)
  2. The account the transaction posts to (if accounts are client-specific)
  3. The Class field (if Class Tracking is used for client identification)
- If none of these resolve to a client: flag as `[UNASSIGNED_EXPENSE]`

### 5.7 Opening Balance Equity Transactions

**Scenario:** QBO creates "Opening Balance Equity" transactions when accounts are first set up. These are system-generated bookkeeping entries.

**Handling:**
- Identify by Transaction Type = "Opening Balance" or Account = "Opening Balance Equity"
- These should be imported but reviewed carefully:
  - They establish starting balances
  - They may not have a meaningful "Name" field
  - Assign to the appropriate client based on which client's account is being initialized
- Flag as `[OPENING_BALANCE]` for CPA review

### 5.8 Payroll Transactions

**Scenario:** Payroll transactions in the Transaction Detail export have the employee name in the "Name" field, not the client name.

**Handling:**
- Payroll transactions are identified by Transaction Type = "Payroll" or Transaction Type containing "Tax Payment"
- The employee name in the "Name" field is used to look up the employee-to-client mapping
- If the employee is not in the mapping: flag as `[UNMAPPED_PAYROLL]`
- Payroll transactions should be imported as journal entries AND as payroll records (separate tables)

---

## 6. Pre-Export Data Cleaning Recommendations for CPA

Before exporting data from QBO, the CPA should complete these cleanup tasks to maximize automated matching:

### 6.1 Customer Name Standardization

```
1. Open QBO > Sales > Customers
2. Review all customer names for consistency
3. Fix common issues:
   - Merge duplicates (QBO supports customer merge)
   - Standardize suffixes (LLC, Inc., Corp.)
   - Remove test/dummy customers
   - Deactivate (not delete) customers who are no longer clients
4. Ensure every active client has a unique, unambiguous name
```

### 6.2 Transaction Name Cleanup

```
1. Run Reports > Transaction Detail by Account
2. Filter for transactions where Name is blank
3. For each blank-name transaction:
   - Edit the transaction in QBO
   - Assign the appropriate customer/vendor name
4. Note: This may require reviewing hundreds of transactions
   - Prioritize: Journal Entries, Transfers, and Deposits
   - Expense transactions will use vendor-to-client mapping instead
```

### 6.3 Class Tracking Review (if enabled)

```
1. Open QBO > Settings > Advanced > Categories
2. Confirm Classes are used for client identification (or not)
3. If yes:
   - Ensure every Class maps to exactly one client
   - Review unclassified transactions and assign classes
   - Provide the Class-to-Client mapping to the migration team
```

### 6.4 Sub-Customer Cleanup

```
1. Open QBO > Sales > Customers
2. Review sub-customer hierarchy
3. Confirm all sub-customers should roll up to their parent for migration
4. If any sub-customer should be a separate client:
   - Promote to top-level customer in QBO before export
   - Add to entity_type_mapping.csv
```

---

## 7. Post-Split Validation Rules

After the splitting algorithm runs, these checks must ALL pass before proceeding to import:

### 7.1 Completeness Checks

| Check ID | Rule                                                     | Severity |
|----------|----------------------------------------------------------|----------|
| S-001    | Every client in entity_type_mapping.csv exists in Customer List | FATAL |
| S-002    | Every Customer in Customer List has an entity_type_mapping entry | FATAL |
| S-003    | No client_id is NULL except flagged [UNASSIGNED] records  | FATAL    |
| S-004    | Every employee has exactly one client_id assignment       | FATAL    |
| S-005    | Every payroll record has a client_id                      | FATAL    |

### 7.2 Consistency Checks

| Check ID | Rule                                                     | Severity |
|----------|----------------------------------------------------------|----------|
| S-010    | All transactions for a given client reference only that client's chart of accounts | WARNING |
| S-011    | Invoice Customer matches client name (not a cross-client invoice) | FATAL |
| S-012    | No two clients share the same normalized name             | FATAL    |
| S-013    | Sub-customer assignments are consistent (same parent throughout) | FATAL |

### 7.3 Balance Checks

| Check ID | Rule                                                     | Severity |
|----------|----------------------------------------------------------|----------|
| S-020    | Per-client GL balances: total debits = total credits      | FATAL    |
| S-021    | Sum of per-client AR balances = total QBO AR balance      | WARNING  |
| S-022    | Sum of per-client revenue = total QBO revenue             | WARNING  |

---

## 8. Client Splitting Summary Report Template

After running the splitting algorithm, generate this report:

```
========================================
CLIENT SPLITTING SUMMARY REPORT
========================================
Date:              2026-03-04 14:30:00
Source:             QuickBooks Online Export
Clients in Registry: 35

ASSIGNMENT STATISTICS
---------------------
Total transactions processed:    12,456
  Exact match (assigned):         11,823 (94.9%)
  Sub-customer match:                234 ( 1.9%)
  Fuzzy match:                        67 ( 0.5%)
  Unassigned (no Name):              289 ( 2.3%)
  Ambiguous (multiple matches):       18 ( 0.1%)
  Multi-client:                       12 ( 0.1%)
  Inter-client:                        8 ( 0.1%)
  Opening balance:                     5 ( 0.0%)

Total invoices processed:         3,450
  Assigned:                        3,445 (99.9%)
  Unassigned:                          5 ( 0.1%)

Total payroll records processed:    890
  Assigned (via employee mapping):   885 (99.4%)
  Unmapped employee:                    5 ( 0.6%)

Total vendor records processed:     120
  Assigned (via vendor mapping):     115 (95.8%)
  Unmapped vendor:                      5 ( 4.2%)

FLAGGED RECORDS REQUIRING CPA REVIEW
-------------------------------------
[UNASSIGNED]:          289 records (see unassigned_records.csv)
[FUZZY_MATCH]:          67 records (see fuzzy_matches.csv)
[AMBIGUOUS]:            18 records (see ambiguous_records.csv)
[MULTI_CLIENT]:         12 records (see multi_client_records.csv)
[INTER_CLIENT]:          8 records (see inter_client_records.csv)
[UNMAPPED_EMPLOYEE]:     5 records (see unmapped_employees.csv)
[UNMAPPED_VENDOR]:       5 records (see unmapped_vendors.csv)

TOTAL REQUIRING REVIEW: 404 records

PER-CLIENT BREAKDOWN
---------------------
Client: Peachtree Landscaping LLC (PARTNERSHIP_LLC)
  Transactions:  2,345
  Invoices:        456
  Payroll records: 120
  Vendors:          18

Client: Atlanta Tech Solutions Inc (S_CORP)
  Transactions:  1,890
  Invoices:        312
  Payroll records:  96
  Vendors:          22

... [remaining clients] ...

VALIDATION RESULTS
------------------
S-001: PASS
S-002: PASS
S-003: PASS (289 flagged UNASSIGNED excluded)
S-004: PASS
S-005: FAIL -- 5 payroll records missing client_id
S-010: PASS
S-011: PASS
S-012: PASS
S-013: PASS
S-020: PASS
S-021: WARNING -- $234.56 variance
S-022: PASS
========================================
```

---

## 9. Output Files

The splitting algorithm produces these files for CPA review:

| File Name                    | Contents                                      |
|------------------------------|-----------------------------------------------|
| `splitting_summary.txt`      | Full summary report (template above)          |
| `client_registry.csv`        | All clients with assigned UUIDs               |
| `unassigned_records.csv`     | Transactions with no client assignment         |
| `fuzzy_matches.csv`          | Fuzzy match candidates for CPA confirmation    |
| `ambiguous_records.csv`      | Records matching multiple clients              |
| `multi_client_records.csv`   | Transactions spanning multiple clients         |
| `inter_client_records.csv`   | Transfers between clients                      |
| `unmapped_employees.csv`     | Employees not in employee-to-client mapping    |
| `unmapped_vendors.csv`       | Vendors not in vendor-to-client mapping        |
| `name_aliases_suggested.csv` | Suggested name aliases for CPA review          |
