"""
Georgia income tax withholding engine (module P2).

Calculates Georgia state income tax withholding per pay period using
the Form G-4 filing status and allowances. Tax tables are parameterized
by tax year and loaded from the payroll_tax_tables database table.

Compliance (CLAUDE.md rule #3):
    Every rate constant must cite its Georgia DOR source document,
    tax year, and review date. See SOURCE comments throughout.

Compliance (CLAUDE.md rule #4):
    All calculations are scoped to a specific employee belonging to a client.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payroll_tax_table import PayrollTaxTable


# ---------------------------------------------------------------------------
# Constants — cited per CLAUDE.md rule #3
# ---------------------------------------------------------------------------

# SOURCE: Georgia DOR, Employer's Tax Guide 2024, Page 12
# REVIEW DATE: 2026-03-04
# Georgia personal allowance amount per exemption claimed on G-4
GA_PERSONAL_ALLOWANCE_2024 = Decimal("2700.00")

# SOURCE: Georgia DOR, Employer's Tax Guide 2025, HB 1015 flat tax transition
# REVIEW DATE: 2026-03-04
GA_PERSONAL_ALLOWANCE_2025 = Decimal("2700.00")

# SOURCE: Georgia DOR, Employer's Tax Guide 2026 (projected per HB 1015)
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2026 personal allowance with GA DOR publication
GA_PERSONAL_ALLOWANCE_2026 = Decimal("2700.00")

# Standard deductions by filing status and year
# SOURCE: Georgia DOR, Employer's Tax Guide 2024, Page 11
# REVIEW DATE: 2026-03-04
GA_STANDARD_DEDUCTIONS: dict[int, dict[str, Decimal]] = {
    2024: {
        "SINGLE": Decimal("5400.00"),
        "MARRIED": Decimal("7100.00"),
        "HEAD_OF_HOUSEHOLD": Decimal("5400.00"),
    },
    # SOURCE: Georgia DOR, Employer's Tax Guide 2025
    # REVIEW DATE: 2026-03-04
    2025: {
        "SINGLE": Decimal("5400.00"),
        "MARRIED": Decimal("7100.00"),
        "HEAD_OF_HOUSEHOLD": Decimal("5400.00"),
    },
    # SOURCE: Georgia DOR, Employer's Tax Guide 2026 (projected per HB 1015)
    # REVIEW DATE: 2026-03-04
    # COMPLIANCE REVIEW NEEDED: Verify 2026 standard deductions with GA DOR
    2026: {
        "SINGLE": Decimal("5400.00"),
        "MARRIED": Decimal("7100.00"),
        "HEAD_OF_HOUSEHOLD": Decimal("5400.00"),
    },
}

PERSONAL_ALLOWANCES: dict[int, Decimal] = {
    2024: GA_PERSONAL_ALLOWANCE_2024,
    2025: GA_PERSONAL_ALLOWANCE_2025,
    2026: GA_PERSONAL_ALLOWANCE_2026,
}

# Georgia graduated tax brackets (pre-flat-tax years)
# SOURCE: Georgia DOR, Employer's Tax Guide 2024, Page 13
# REVIEW DATE: 2026-03-04
GA_BRACKETS_2024_SINGLE: list[tuple[Decimal, Decimal, Decimal]] = [
    # (bracket_min, bracket_max, rate)
    (Decimal("0.00"), Decimal("750.00"), Decimal("0.01")),
    (Decimal("750.00"), Decimal("2250.00"), Decimal("0.02")),
    (Decimal("2250.00"), Decimal("3750.00"), Decimal("0.03")),
    (Decimal("3750.00"), Decimal("5250.00"), Decimal("0.04")),
    (Decimal("5250.00"), Decimal("7000.00"), Decimal("0.05")),
    (Decimal("7000.00"), Decimal("999999999.99"), Decimal("0.0549")),
]

GA_BRACKETS_2024_MARRIED: list[tuple[Decimal, Decimal, Decimal]] = [
    (Decimal("0.00"), Decimal("1000.00"), Decimal("0.01")),
    (Decimal("1000.00"), Decimal("3000.00"), Decimal("0.02")),
    (Decimal("3000.00"), Decimal("5000.00"), Decimal("0.03")),
    (Decimal("5000.00"), Decimal("7000.00"), Decimal("0.04")),
    (Decimal("7000.00"), Decimal("10000.00"), Decimal("0.05")),
    (Decimal("10000.00"), Decimal("999999999.99"), Decimal("0.0549")),
]

# SOURCE: Georgia DOR, HB 111 (retroactive), Tax Year 2025 — flat rate 5.19%
# REVIEW DATE: 2026-03-04
GA_FLAT_RATE_2025 = Decimal("0.0519")

# SOURCE: Georgia DOR, HB 111, Tax Year 2026 — flat rate 5.19%
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2026 flat rate with GA DOR publication
GA_FLAT_RATE_2026 = Decimal("0.0519")


# ---------------------------------------------------------------------------
# Hardcoded fallback brackets (used when DB tax tables are unavailable)
# ---------------------------------------------------------------------------
_FALLBACK_BRACKETS: dict[int, dict[str, list[tuple[Decimal, Decimal, Decimal]]]] = {
    2024: {
        "SINGLE": GA_BRACKETS_2024_SINGLE,
        "HEAD_OF_HOUSEHOLD": GA_BRACKETS_2024_SINGLE,
        "MARRIED": GA_BRACKETS_2024_MARRIED,
    },
}


@dataclass(frozen=True)
class GAWithholdingResult:
    """Result of a Georgia state income tax withholding calculation."""

    annual_gross: Decimal
    standard_deduction: Decimal
    personal_allowance_total: Decimal
    taxable_income: Decimal
    annual_tax: Decimal
    per_period_tax: Decimal
    tax_year: int
    filing_status: str
    pay_periods: int


class GeorgiaWithholdingCalculator:
    """
    Calculates Georgia state income tax withholding.

    Tax tables are loaded from the payroll_tax_tables DB table when a
    database session is available. Falls back to hardcoded brackets
    for unit testing or when DB is unavailable.

    The calculation follows the Georgia DOR percentage method:
    1. Annualize gross pay
    2. Subtract standard deduction for filing status
    3. Subtract personal allowance × number of allowances
    4. Apply graduated tax brackets (or flat rate for 2025+)
    5. Divide annual tax by number of pay periods
    """

    @staticmethod
    def _get_standard_deduction(tax_year: int, filing_status: str) -> Decimal:
        """Get the standard deduction for a given year and filing status."""
        year_deductions = GA_STANDARD_DEDUCTIONS.get(tax_year)
        if year_deductions is None:
            # Fall back to most recent known year
            latest = max(GA_STANDARD_DEDUCTIONS.keys())
            year_deductions = GA_STANDARD_DEDUCTIONS[latest]
        return year_deductions.get(filing_status, year_deductions["SINGLE"])

    @staticmethod
    def _get_personal_allowance(tax_year: int) -> Decimal:
        """Get the per-allowance amount for a given year."""
        if tax_year in PERSONAL_ALLOWANCES:
            return PERSONAL_ALLOWANCES[tax_year]
        return PERSONAL_ALLOWANCES[max(PERSONAL_ALLOWANCES.keys())]

    @staticmethod
    def _apply_brackets(
        taxable_income: Decimal,
        brackets: list[tuple[Decimal, Decimal, Decimal]],
    ) -> Decimal:
        """Apply graduated tax brackets to taxable income."""
        tax = Decimal("0.00")
        for bracket_min, bracket_max, rate in brackets:
            if taxable_income <= bracket_min:
                break
            taxable_in_bracket = min(taxable_income, bracket_max) - bracket_min
            tax += (taxable_in_bracket * rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )
        return tax

    @staticmethod
    def _apply_flat_rate(taxable_income: Decimal, rate: Decimal) -> Decimal:
        """Apply a flat tax rate to taxable income."""
        return (taxable_income * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _get_flat_rate(tax_year: int) -> Decimal | None:
        """Get the flat rate for years using the HB 1015 flat tax."""
        flat_rates = {
            2025: GA_FLAT_RATE_2025,
            2026: GA_FLAT_RATE_2026,
        }
        return flat_rates.get(tax_year)

    @staticmethod
    async def load_brackets_from_db(
        db: AsyncSession,
        tax_year: int,
        filing_status: str,
    ) -> list[tuple[Decimal, Decimal, Decimal]] | None:
        """
        Load tax brackets from the payroll_tax_tables database table.

        Returns None if no brackets found for this year/status combination.
        """
        stmt = (
            select(PayrollTaxTable)
            .where(
                PayrollTaxTable.tax_year == tax_year,
                PayrollTaxTable.tax_type == "GA_INCOME",
                PayrollTaxTable.filing_status == filing_status,
            )
            .order_by(PayrollTaxTable.bracket_min)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return None
        return [
            (row.bracket_min, row.bracket_max or Decimal("999999999.99"), row.rate)
            for row in rows
        ]

    @classmethod
    def calculate(
        cls,
        gross_pay_per_period: Decimal,
        filing_status: str,
        allowances: int,
        pay_periods: int,
        tax_year: int,
        brackets: list[tuple[Decimal, Decimal, Decimal]] | None = None,
    ) -> GAWithholdingResult:
        """
        Calculate Georgia state income tax withholding for one pay period.

        Parameters
        ----------
        gross_pay_per_period : Decimal
            Gross pay for this pay period.
        filing_status : str
            Employee's G-4 filing status (SINGLE, MARRIED, HEAD_OF_HOUSEHOLD).
        allowances : int
            Number of allowances claimed on Form G-4.
        pay_periods : int
            Number of pay periods per year (e.g. 26 for biweekly, 24 for semi-monthly).
        tax_year : int
            Tax year for rate lookup.
        brackets : list or None
            Pre-loaded brackets from DB. If None, uses hardcoded fallback.

        Returns
        -------
        GAWithholdingResult
            Detailed breakdown of the withholding calculation.
        """
        # Step 1: Annualize gross pay
        annual_gross = (gross_pay_per_period * pay_periods).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        # Step 2: Standard deduction
        standard_deduction = cls._get_standard_deduction(tax_year, filing_status)

        # Step 3: Personal allowances
        personal_allowance = cls._get_personal_allowance(tax_year)
        personal_allowance_total = (personal_allowance * allowances).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        # Step 4: Taxable income
        taxable_income = annual_gross - standard_deduction - personal_allowance_total
        if taxable_income < Decimal("0"):
            taxable_income = Decimal("0.00")

        # Step 5: Calculate annual tax
        flat_rate = cls._get_flat_rate(tax_year)
        if flat_rate is not None:
            annual_tax = cls._apply_flat_rate(taxable_income, flat_rate)
        elif brackets is not None:
            annual_tax = cls._apply_brackets(taxable_income, brackets)
        else:
            # Use hardcoded fallback brackets
            fallback = _FALLBACK_BRACKETS.get(tax_year, {})
            fb_brackets = fallback.get(
                filing_status,
                fallback.get("SINGLE", GA_BRACKETS_2024_SINGLE),
            )
            annual_tax = cls._apply_brackets(taxable_income, fb_brackets)

        # Step 6: Per-period withholding
        if pay_periods > 0:
            per_period_tax = (annual_tax / pay_periods).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )
        else:
            per_period_tax = Decimal("0.00")

        return GAWithholdingResult(
            annual_gross=annual_gross,
            standard_deduction=standard_deduction,
            personal_allowance_total=personal_allowance_total,
            taxable_income=taxable_income,
            annual_tax=annual_tax,
            per_period_tax=per_period_tax,
            tax_year=tax_year,
            filing_status=filing_status,
            pay_periods=pay_periods,
        )
