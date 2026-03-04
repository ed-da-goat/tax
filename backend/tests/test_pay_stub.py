"""
Tests for Pay Stub PDF Generator (module P5).

Tests HTML generation (without requiring WeasyPrint system libraries).
WeasyPrint PDF generation is tested separately since it requires pango.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.payroll.pay_stub import (
    PayStubData,
    _build_html,
    _format_currency,
    _format_date,
)


class TestPayStubFormatting:

    def test_format_currency(self):
        assert _format_currency(Decimal("1234.56")) == "$1,234.56"
        assert _format_currency(Decimal("0.00")) == "$0.00"
        assert _format_currency(Decimal("1000000.00")) == "$1,000,000.00"
        assert _format_currency(None) == "-"

    def test_format_date(self):
        assert _format_date(date(2024, 6, 15)) == "06/15/2024"
        assert _format_date(date(2024, 12, 31)) == "12/31/2024"


class TestPayStubHTMLGeneration:

    def _default_data(self) -> PayStubData:
        return PayStubData(
            company_name="Test CPA Firm",
            company_address="123 Main St, Atlanta, GA 30301",
            employee_name="John Smith",
            employee_id_display="abc12345",
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            hours_worked=Decimal("80"),
            pay_rate=Decimal("25.00"),
            pay_type="HOURLY",
            gross_pay=Decimal("2000.00"),
            federal_withholding=Decimal("250.00"),
            state_withholding=Decimal("100.00"),
            social_security=Decimal("124.00"),
            medicare=Decimal("29.00"),
            employer_ss=Decimal("124.00"),
            employer_medicare=Decimal("29.00"),
            ga_suta=Decimal("54.00"),
            futa=Decimal("12.00"),
            net_pay=Decimal("1497.00"),
        )

    def test_html_contains_company_name(self):
        data = self._default_data()
        html = _build_html(data)
        assert "Test CPA Firm" in html

    def test_html_contains_employee_name(self):
        data = self._default_data()
        html = _build_html(data)
        assert "John Smith" in html

    def test_html_contains_pay_date(self):
        data = self._default_data()
        html = _build_html(data)
        assert "06/20/2024" in html

    def test_html_contains_gross_pay(self):
        data = self._default_data()
        html = _build_html(data)
        assert "$2,000.00" in html

    def test_html_contains_net_pay(self):
        data = self._default_data()
        html = _build_html(data)
        assert "$1,497.00" in html

    def test_html_contains_deductions(self):
        data = self._default_data()
        html = _build_html(data)
        assert "$250.00" in html  # Federal
        assert "$100.00" in html  # State
        assert "$124.00" in html  # SS
        assert "$29.00" in html   # Medicare

    def test_html_contains_employer_taxes(self):
        data = self._default_data()
        html = _build_html(data)
        assert "$54.00" in html   # GA SUTA
        assert "$12.00" in html   # FUTA

    def test_html_salary_employee(self):
        data = PayStubData(
            company_name="Test Firm",
            employee_name="Jane Doe",
            pay_type="SALARY",
            pay_rate=Decimal("75000.00"),
            gross_pay=Decimal("2884.62"),
            net_pay=Decimal("2000.00"),
        )
        html = _build_html(data)
        assert "Salary" in html
        assert "$75,000.00/yr" in html

    def test_html_with_ytd_totals(self):
        data = PayStubData(
            company_name="Test Firm",
            employee_name="John Smith",
            gross_pay=Decimal("2000.00"),
            net_pay=Decimal("1500.00"),
            ytd_gross=Decimal("26000.00"),
            ytd_federal_withholding=Decimal("3250.00"),
            ytd_state_withholding=Decimal("1300.00"),
            ytd_social_security=Decimal("1612.00"),
            ytd_medicare=Decimal("377.00"),
            ytd_net_pay=Decimal("19461.00"),
        )
        html = _build_html(data)
        assert "Year-to-Date" in html
        assert "$26,000.00" in html

    def test_html_without_ytd(self):
        data = PayStubData(
            company_name="Test Firm",
            employee_name="John Smith",
            gross_pay=Decimal("2000.00"),
            net_pay=Decimal("1500.00"),
        )
        html = _build_html(data)
        assert "Year-to-Date" not in html

    def test_html_valid_structure(self):
        data = self._default_data()
        html = _build_html(data)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "<table>" in html

    def test_html_no_company_address(self):
        data = PayStubData(
            company_name="Test Firm",
            employee_name="John Smith",
            gross_pay=Decimal("1000.00"),
            net_pay=Decimal("800.00"),
        )
        html = _build_html(data)
        assert "Test Firm" in html
