"""
Router registry.

All API routers are registered here and mounted onto the FastAPI app.
Builder agents add their routers to this module as they complete each module.

Usage in main.py:
    from app.routers import register_routers
    register_routers(app)
"""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """
    Mount all API routers onto the FastAPI application.

    Builder agents: when you create a new router, import it here and
    add an `app.include_router(...)` call with the appropriate prefix
    and tags.

    Example:
        from app.routers.clients import router as clients_router
        app.include_router(clients_router, prefix="/api/v1/clients", tags=["clients"])
    """
    # --- Phase 1 routers (Foundation) ---
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

    from app.routers.clients import router as clients_router
    app.include_router(clients_router, prefix="/api/v1/clients", tags=["clients"])

    from app.routers.chart_of_accounts import router as coa_router
    app.include_router(coa_router, prefix="/api/v1", tags=["chart-of-accounts"])

    from app.routers.journal_entries import router as je_router
    app.include_router(je_router, prefix="/api/v1", tags=["journal-entries"])

    # --- Phase 2 routers (Transactions) ---
    from app.routers.approvals import router as approvals_router
    app.include_router(approvals_router, prefix="/api/v1", tags=["approvals"])

    from app.routers.vendors import router as vendors_router
    app.include_router(
        vendors_router,
        prefix="/api/v1/clients/{client_id}/vendors",
        tags=["vendors"],
    )

    from app.routers.bills import router as bills_router
    app.include_router(
        bills_router,
        prefix="/api/v1/clients/{client_id}/bills",
        tags=["bills"],
    )

    from app.routers.check_sequence import router as check_seq_router
    app.include_router(
        check_seq_router,
        prefix="/api/v1/clients/{client_id}/check-sequence",
        tags=["check-sequence"],
    )

    from app.routers.invoices import router as invoices_router
    app.include_router(
        invoices_router,
        prefix="/api/v1/clients/{client_id}/invoices",
        tags=["invoices"],
    )

    # --- Phase 2 routers (Bank Reconciliation) ---
    from app.routers.bank_reconciliation import router as bank_recon_router
    app.include_router(
        bank_recon_router,
        prefix="/api/v1/clients/{client_id}/bank-accounts",
        tags=["bank-reconciliation"],
    )

    # --- Phase 3 routers (Document Management) ---
    from app.routers.documents import router as documents_router
    app.include_router(
        documents_router,
        prefix="/api/v1/clients/{client_id}/documents",
        tags=["documents"],
    )

    # --- Phase 4 routers (Payroll — Employee Records) ---
    from app.routers.employees import router as employees_router
    app.include_router(
        employees_router,
        prefix="/api/v1/clients/{client_id}/employees",
        tags=["employees"],
    )

    # --- Phase 4 routers (Payroll — Runs + Approval) ---
    from app.routers.payroll import router as payroll_router
    app.include_router(
        payroll_router,
        prefix="/api/v1/clients/{client_id}/payroll",
        tags=["payroll"],
    )

    # --- Phase 5 routers (Tax Exports) ---
    from app.routers.tax_exports import router as tax_router
    app.include_router(tax_router, prefix="/api/v1/tax", tags=["tax-exports"])

    # --- Phase 6 routers (Reporting) ---
    from app.routers.reports import router as reports_router
    app.include_router(reports_router, prefix="/api/v1/reports", tags=["reports"])

    # --- Phase 7 routers (Operations) ---
    from app.routers.audit_log import router as audit_log_router
    app.include_router(audit_log_router, prefix="/api/v1/audit-log", tags=["audit-log"])

    from app.routers.operations import router as operations_router
    app.include_router(operations_router, prefix="/api/v1/operations", tags=["operations"])

    # --- Phase 8A routers (Direct Deposit / NACHA) ---
    from app.routers.direct_deposit import router as dd_router
    app.include_router(
        dd_router,
        prefix="/api/v1/clients/{client_id}",
        tags=["direct-deposit"],
    )

    # --- Phase 8B routers (Tax E-Filing) ---
    from app.routers.tax_filing import router as tax_filing_router
    app.include_router(
        tax_filing_router,
        prefix="/api/v1/clients/{client_id}/tax-filings",
        tags=["tax-filing"],
    )

    # --- Phase 9 routers (Time Tracking & Billing) ---
    from app.routers.time_tracking import router as time_tracking_router
    app.include_router(
        time_tracking_router,
        prefix="/api/v1",
        tags=["time-tracking"],
    )

    from app.routers.service_billing import router as service_billing_router
    app.include_router(
        service_billing_router,
        prefix="/api/v1/service-invoices",
        tags=["service-billing"],
    )

    from app.routers.engagements import router as engagements_router
    app.include_router(
        engagements_router,
        prefix="/api/v1/engagements",
        tags=["engagements"],
    )

    from app.routers.contacts import router as contacts_router
    app.include_router(
        contacts_router,
        prefix="/api/v1/contacts",
        tags=["contacts"],
    )

    # --- Phase 10 routers (Workflow Engine) ---
    from app.routers.workflows import router as workflows_router
    app.include_router(
        workflows_router,
        prefix="/api/v1",
        tags=["workflows"],
    )

    # --- Phase 11 routers (Client Portal) ---
    from app.routers.portal import router as portal_router
    app.include_router(
        portal_router,
        prefix="/api/v1",
        tags=["portal"],
    )

    # --- Phase 12 routers (Analytics & Advanced) ---
    from app.routers.firm_analytics import router as analytics_router
    app.include_router(
        analytics_router,
        prefix="/api/v1/analytics",
        tags=["analytics"],
    )

    from app.routers.fixed_assets import router as fixed_assets_router
    app.include_router(
        fixed_assets_router,
        prefix="/api/v1/clients/{client_id}/fixed-assets",
        tags=["fixed-assets"],
    )

    from app.routers.budgets import router as budgets_router
    app.include_router(
        budgets_router,
        prefix="/api/v1/clients/{client_id}/budgets",
        tags=["budgets"],
    )
