"""
Tests for Georgia SUTA Calculator (module P3).

Tests wage base cap logic, custom employer rates, and edge cases.
"""

from decimal import Decimal

import pytest

from app.services.payroll.ga_suta import (
    GA_SUTA_NEW_EMPLOYER_RATE,
    GeorgiaSUTACalculator,
    SUTAResult,
)


class TestGeorgiaSUTA:

    def test_basic_calculation_default_rate(self):
        """Basic SUTA at default 2.7% rate."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("0.00"),
            tax_year=2024,
        )
        assert isinstance(result, SUTAResult)
        assert result.rate_used == GA_SUTA_NEW_EMPLOYER_RATE
        assert result.taxable_wages == Decimal("2000.00")
        assert result.suta_amount == Decimal("54.00")  # 2000 * 0.027
        assert result.capped is False

    def test_custom_experienced_employer_rate(self):
        """Per-client custom rate for experienced employers."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("0.00"),
            tax_year=2024,
            custom_rate=Decimal("0.015"),  # 1.5% experienced rate
        )
        assert result.rate_used == Decimal("0.015")
        assert result.suta_amount == Decimal("30.00")  # 2000 * 0.015

    def test_wage_base_not_reached(self):
        """Full pay is taxable when YTD wages are below the base."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("1500.00"),
            ytd_wages=Decimal("5000.00"),
            tax_year=2024,
        )
        assert result.taxable_wages == Decimal("1500.00")
        assert result.capped is False

    def test_wage_base_partially_reached(self):
        """Only the portion up to the wage base is taxable."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("8500.00"),  # $8500 YTD, base is $9500
            tax_year=2024,
        )
        # Only $1000 is taxable (9500 - 8500)
        assert result.taxable_wages == Decimal("1000.00")
        assert result.suta_amount == Decimal("27.00")  # 1000 * 0.027
        assert result.capped is True

    def test_wage_base_already_reached(self):
        """No SUTA when YTD wages already exceed the wage base."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("10000.00"),  # Already over $9500
            tax_year=2024,
        )
        assert result.taxable_wages == Decimal("0.00")
        assert result.suta_amount == Decimal("0.00")
        assert result.capped is True

    def test_wage_base_exact_cap(self):
        """Wages exactly at the wage base."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("500.00"),
            ytd_wages=Decimal("9000.00"),  # 9000 + 500 = 9500 exactly
            tax_year=2024,
        )
        assert result.taxable_wages == Decimal("500.00")
        assert result.suta_amount == Decimal("13.50")
        assert result.capped is False  # Not capped — exactly at the limit

    def test_zero_gross_pay(self):
        """Zero gross pay = zero SUTA."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("0.00"),
            ytd_wages=Decimal("5000.00"),
            tax_year=2024,
        )
        assert result.suta_amount == Decimal("0.00")

    def test_ytd_tracking(self):
        """YTD values are correctly tracked in result."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("3000.00"),
            ytd_wages=Decimal("6000.00"),
            tax_year=2024,
        )
        assert result.ytd_wages_before == Decimal("6000.00")
        assert result.ytd_wages_after == Decimal("9000.00")

    def test_different_tax_years(self):
        """Wage base lookup works for different years."""
        for year in (2024, 2025, 2026):
            result = GeorgiaSUTACalculator.calculate(
                gross_pay=Decimal("1000.00"),
                ytd_wages=Decimal("0.00"),
                tax_year=year,
            )
            assert result.wage_base == Decimal("9500.00")
            assert result.tax_year == year

    def test_very_high_custom_rate(self):
        """High custom rate for problematic employers."""
        result = GeorgiaSUTACalculator.calculate(
            gross_pay=Decimal("1000.00"),
            ytd_wages=Decimal("0.00"),
            tax_year=2024,
            custom_rate=Decimal("0.054"),  # 5.4% max rate
        )
        assert result.suta_amount == Decimal("54.00")
