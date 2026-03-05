================================================================
FILE: AGENT_PROMPTS/01_MIGRATION_AGENT.md
(Run AFTER Research Agent. Run ONCE per QB export batch.)
================================================================

# MIGRATION AGENT — QuickBooks Online Data Import

[CONTEXT]
You are the Migration Agent. Your job is to safely import the
CPA firm's full QuickBooks Online history into the new system.
This is the highest-risk operation in the entire project.
A mistake here corrupts real client financial history.

Read CLAUDE.md and MIGRATION_SPEC.md in full before writing
any code.

[INSTRUCTION]

STEP 1: VALIDATE INPUT FILES
Before importing anything, run validation checks on every CSV:
- Required columns present for each file type
- No null values in client identifier fields
- Date formats parseable
- Debit/credit columns balance per transaction
- No duplicate transaction IDs
Print a VALIDATION REPORT. If any check fails, halt and
print which file and row failed. Do not proceed until clean.

STEP 2: DRY RUN
Execute the full migration in a transaction with ROLLBACK at end.
Print a DRY RUN REPORT showing:
- Number of clients that will be created
- Number of transactions per client
- Number of invoices per client
- Number of payroll records per client
- Any records that could not be mapped (flagged for CPA review)

Show this report to the CPA before proceeding.
Print: "Review the dry run report above. Type CONFIRM to proceed
or ABORT to stop."

STEP 3: LIVE IMPORT (only after CONFIRM)
Execute migration for real. Import in this order:
1. Clients
2. Chart of accounts per client
3. Opening balances
4. Transaction history (oldest first)
5. Invoice history
6. Payroll history

Wrap the entire import in a single database transaction.
If any step fails: ROLLBACK everything, print exact error,
print recovery instructions. Never leave partial data.

STEP 4: VERIFICATION
After import, run these checks:
- GL balance per client (debits must equal credits)
- Invoice count matches QB export row count
- Payroll record count matches QB export row count
- Spot-check 5 random transactions per client for accuracy
Print a MIGRATION VERIFICATION REPORT.

STEP 5: COMMIT
  git add -A
  git commit following CLAUDE.md schema
  git push origin main

[OUTPUT FORMAT]
- VALIDATION REPORT (printed to terminal)
- DRY RUN REPORT (printed to terminal, saved to
  /docs/migration/dry_run_[timestamp].txt)
- MIGRATION VERIFICATION REPORT (saved to
  /docs/migration/verification_[timestamp].txt)
- OPEN_ISSUES.md updated with any unmapped records

[ERROR HANDLING]
If client name collision detected (two clients with same name):
  Do not auto-resolve. Print both records, ask CPA to
  manually assign unique identifiers before proceeding.

If QB data is missing payroll tax withholding amounts:
  Import gross pay only. Flag all affected records in
  OPEN_ISSUES.md with [COMPLIANCE] label.
  Do not calculate retroactive withholding.

[STATUS: TODO — Depends on Phase 1 Foundation being built first]
