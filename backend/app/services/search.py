"""
Global search service (D1).

Searches across clients, vendors, employees, invoices, and bills
by name/number/description.
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SearchService:

    @staticmethod
    async def search(db: AsyncSession, query: str, limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        """Search across multiple entity types. Returns categorized results."""
        if not query or len(query) < 2:
            return {"clients": [], "vendors": [], "employees": [], "invoices": [], "bills": []}

        like_pattern = f"%{query}%"
        results: dict[str, list[dict[str, Any]]] = {}

        # Clients
        r = await db.execute(text(
            "SELECT id, name, entity_type, email, phone "
            "FROM clients WHERE deleted_at IS NULL AND is_active = TRUE "
            "AND (name ILIKE :q OR email ILIKE :q OR phone ILIKE :q) "
            "ORDER BY name LIMIT :lim"
        ), {"q": like_pattern, "lim": limit})
        results["clients"] = [
            {"id": str(row.id), "name": row.name, "entity_type": row.entity_type,
             "email": row.email, "phone": row.phone, "type": "client"}
            for row in r.all()
        ]

        # Vendors
        r = await db.execute(text(
            "SELECT v.id, v.name, v.client_id, c.name as client_name "
            "FROM vendors v JOIN clients c ON c.id = v.client_id "
            "WHERE v.deleted_at IS NULL "
            "AND (v.name ILIKE :q) "
            "ORDER BY v.name LIMIT :lim"
        ), {"q": like_pattern, "lim": limit})
        results["vendors"] = [
            {"id": str(row.id), "name": row.name, "client_id": str(row.client_id),
             "client_name": row.client_name, "type": "vendor"}
            for row in r.all()
        ]

        # Employees
        r = await db.execute(text(
            "SELECT e.id, e.first_name, e.last_name, e.client_id, c.name as client_name "
            "FROM employees e JOIN clients c ON c.id = e.client_id "
            "WHERE e.deleted_at IS NULL AND e.is_active = TRUE "
            "AND (e.first_name ILIKE :q OR e.last_name ILIKE :q "
            "     OR CONCAT(e.first_name, ' ', e.last_name) ILIKE :q) "
            "ORDER BY e.last_name LIMIT :lim"
        ), {"q": like_pattern, "lim": limit})
        results["employees"] = [
            {"id": str(row.id), "name": f"{row.first_name} {row.last_name}",
             "client_id": str(row.client_id), "client_name": row.client_name, "type": "employee"}
            for row in r.all()
        ]

        # Invoices
        r = await db.execute(text(
            "SELECT i.id, i.invoice_number, i.customer_name, i.total_amount, "
            "       i.status, i.client_id, c.name as client_name "
            "FROM invoices i JOIN clients c ON c.id = i.client_id "
            "WHERE i.deleted_at IS NULL "
            "AND (i.invoice_number ILIKE :q OR i.customer_name ILIKE :q) "
            "ORDER BY i.invoice_date DESC LIMIT :lim"
        ), {"q": like_pattern, "lim": limit})
        results["invoices"] = [
            {"id": str(row.id), "name": f"#{row.invoice_number} — {row.customer_name}",
             "amount": float(row.total_amount), "status": row.status,
             "client_id": str(row.client_id), "client_name": row.client_name, "type": "invoice"}
            for row in r.all()
        ]

        # Bills
        r = await db.execute(text(
            "SELECT b.id, b.bill_number, v.name as vendor_name, b.total_amount, "
            "       b.status, b.client_id, c.name as client_name "
            "FROM bills b JOIN vendors v ON v.id = b.vendor_id "
            "JOIN clients c ON c.id = b.client_id "
            "WHERE b.deleted_at IS NULL "
            "AND (b.bill_number ILIKE :q OR v.name ILIKE :q) "
            "ORDER BY b.bill_date DESC LIMIT :lim"
        ), {"q": like_pattern, "lim": limit})
        results["bills"] = [
            {"id": str(row.id), "name": f"#{row.bill_number} — {row.vendor_name}",
             "amount": float(row.total_amount), "status": row.status,
             "client_id": str(row.client_id), "client_name": row.client_name, "type": "bill"}
            for row in r.all()
        ]

        return results
