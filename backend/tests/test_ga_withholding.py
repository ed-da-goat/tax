"""
Tests for Georgia Income Tax Withholding Engine (module P2).

Tests the G-4 withholding calculation with various filing statuses,
allowances, and tax years. Validates both graduated bracket system
(2024) and flat rate system (2025+).
"""

from decimal import Decimal

import pytest

from app.services.payroll.ga_withholding import (
    GA_FLAT_RATE_2025,
    GA_FLAT_RATE_2026,
    GeorgiaWithholdingCalculator,
    GAWithholdingResult,
)


class TestGeorgiaWithholding2024:
    """Test graduated bracket system for TY2024."""

    def test_single_no_allowances_basic(self):
        """Single filer, 0 allowances, $2000/biweekly."""
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        assert isinstance(result, GAWithholdingResult)
        assert result.annual_gross == Decimal("52000.00")
        assert result.standard_deduction == Decimal("5400.00")
        assert result.personal_allowance_total == Decimal("0.00")
        assert result.taxable_income == Decimal("46600.00")
        assert result.per_period_tax > Decimal("0")
        assert result.tax_year == 2024
        assert result.filing_status == "SINGLE"

    def test_single_with_allowances(self):
        """Single filer, 2 allowances — reduces taxable income."""
        result_0 = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        result_2 = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2000.00"),
            filing_status="SINGLE",
            allowances=2,
            pay_periods=26,
            tax_year=2024,
        )
        # More allowances = less tax
        assert result_2.per_period_tax < result_0.per_period_tax
        assert result_2.personal_allowance_total == Decimal("5400.00")  # 2700 * 2

    def test_married_filing_status(self):
        """Married filer gets higher standard deduction and wider brackets."""
        single = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        married = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="MARRIED",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        assert married.standard_deduction > single.standard_deduction
        assert married.per_period_tax < single.per_period_tax

    def test_head_of_household(self):
        """Head of household uses single brackets but single standard deduction."""
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2500.00"),
            filing_status="HEAD_OF_HOUSEHOLD",
            allowances=1,
            pay_periods=26,
            tax_year=2024,
        )
        assert result.filing_status == "HEAD_OF_HOUSEHOLD"
        assert result.per_period_tax > Decimal("0")

    def test_zero_income(self):
        """Zero gross pay = zero tax."""
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("0.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        assert result.per_period_tax == Decimal("0.00")
        assert result.taxable_income == Decimal("0.00")

    def test_very_low_income_below_deductions(self):
        """Income below standard deduction + allowances = zero tax."""
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("100.00"),
            filing_status="SINGLE",
            allowances=5,
            pay_periods=26,
            tax_year=2024,
        )
        # $2600 annual gross, std deduction $5400 + 5*$2700 = $18900
        assert result.taxable_income == Decimal("0.00")
        assert result.per_period_tax == Decimal("0.00")

    def test_bracket_calculation_accuracy(self):
        """Verify the graduated bracket math is correct."""
        # Single, 0 allowances, $1000/yr taxable after deductions
        # Should hit only the 1% bracket ($0-$750) and 2% bracket ($750-$1000)
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("246.15"),  # ~$6400/yr annual, $6400-$5400=$1000 taxable
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        # $246.15 * 26 = $6399.90, - $5400 std ded = $999.90
        # 1% on first $750 = $7.50
        # 2% on $249.90 = $5.00
        # Total ~$12.50/yr = ~$0.48/period
        assert result.annual_tax >= Decimal("12.00")
        assert result.annual_tax <= Decimal("13.00")


class TestGeorgiaWithholding2025FlatRate:
    """Test flat rate system for TY2025 (HB 1015 transition)."""

    def test_flat_rate_2025(self):
        """2025 uses flat rate of 5.39%."""
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2025,
        )
        # Taxable = $52000 - $5400 = $46600
        expected_annual = (Decimal("46600") * GA_FLAT_RATE_2025).quantize(Decimal("0.01"))
        assert result.annual_tax == expected_annual

    def test_flat_rate_2026(self):
        """2026 uses flat rate of 5.19%."""
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2026,
        )
        expected_annual = (Decimal("46600") * GA_FLAT_RATE_2026).quantize(Decimal("0.01"))
        assert result.annual_tax == expected_annual

    def test_flat_rate_lower_than_2024_brackets(self):
        """Flat rate should produce different results than brackets."""
        result_2024 = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
        )
        result_2025 = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2025,
        )
        # They should be different amounts (flat vs graduated)
        assert result_2024.annual_tax != result_2025.annual_tax


class TestGeorgiaWithholdingPayPeriods:
    """Test different pay period frequencies."""

    def test_weekly(self):
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("1000.00"),
            filing_status="SINGLE",
            allowances=1,
            pay_periods=52,
            tax_year=2024,
        )
        assert result.pay_periods == 52
        assert result.per_period_tax > Decimal("0")

    def test_monthly(self):
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("5000.00"),
            filing_status="MARRIED",
            allowances=3,
            pay_periods=12,
            tax_year=2024,
        )
        assert result.pay_periods == 12
        assert result.per_period_tax > Decimal("0")

    def test_semi_monthly(self):
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2500.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=24,
            tax_year=2024,
        )
        assert result.pay_periods == 24


class TestGeorgiaWithholdingCustomBrackets:
    """Test with custom brackets loaded from DB."""

    def test_custom_brackets_override(self):
        """Custom brackets from DB should override hardcoded ones."""
        custom_brackets = [
            (Decimal("0.00"), Decimal("50000.00"), Decimal("0.05")),
            (Decimal("50000.00"), Decimal("999999.99"), Decimal("0.06")),
        ]
        result = GeorgiaWithholdingCalculator.calculate(
            gross_pay_per_period=Decimal("2000.00"),
            filing_status="SINGLE",
            allowances=0,
            pay_periods=26,
            tax_year=2024,
            brackets=custom_brackets,
        )
        # With custom: taxable $46600, all at 5% = $2330
        assert result.annual_tax == Decimal("2330.00")
