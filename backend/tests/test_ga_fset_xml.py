"""
Tests for Georgia FSET G-7 XML generation (Phase 8B).

Validates that generated XML has correct structure and values
per Georgia DOR file format specification.
"""

import xml.etree.ElementTree as ET
from decimal import Decimal

import pytest

from app.services.tax_filing.ga_fset_client import G7QuarterData, GAFSETClient, GAFSETConfig


@pytest.fixture
def fset_client():
    return GAFSETClient(GAFSETConfig(is_test=True))


@pytest.fixture
def sample_g7_data():
    return G7QuarterData(
        employer_name="ACME CORP LLC",
        employer_ein="123456789",
        ga_withholding_account_number="GA1234567",
        tax_year=2026,
        quarter=1,
        month1_withholding=Decimal("1250.00"),
        month2_withholding=Decimal("1100.00"),
        month3_withholding=Decimal("1350.00"),
        total_wages_paid=Decimal("45000.00"),
        num_employees_month1=5,
        num_employees_month2=5,
        num_employees_month3=6,
    )


class TestG7XMLGeneration:
    def test_valid_xml(self, fset_client, sample_g7_data):
        """Generated XML should be parseable."""
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)
        assert root.tag == "ReturnState"

    def test_schema_version(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)
        assert root.get("stateSchemaVersion") == "GAWithholding2018.1"

    def test_header_fields(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)

        header = root.find("ReturnHeaderState")
        assert header.find("Jurisdiction").text == "GA"
        assert header.find("ReturnType").text == "G-7"
        assert header.find("TaxYear").text == "2026"
        assert header.find("TaxPeriodBeginDate").text == "2026-01-01"
        assert header.find("TaxPeriodEndDate").text == "2026-03-31"

    def test_filer_info(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)

        filer = root.find("ReturnHeaderState/Filer")
        assert filer.find("EIN").text == "123456789"
        assert filer.find("BusinessName").text == "ACME CORP LLC"
        assert filer.find("GAWithholdingAccountNumber").text == "GA1234567"

    def test_monthly_amounts(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)

        g7 = root.find("ReturnDataState/FormG7")
        assert g7.find("Month1/WithholdingAmount").text == "1250.00"
        assert g7.find("Month2/WithholdingAmount").text == "1100.00"
        assert g7.find("Month3/WithholdingAmount").text == "1350.00"

    def test_total_withholding(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)

        g7 = root.find("ReturnDataState/FormG7")
        total = Decimal(g7.find("TotalWithholding").text)
        assert total == Decimal("3700.00")

    def test_employee_counts(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)

        g7 = root.find("ReturnDataState/FormG7")
        assert g7.find("Month1/NumberOfEmployees").text == "5"
        assert g7.find("Month2/NumberOfEmployees").text == "5"
        assert g7.find("Month3/NumberOfEmployees").text == "6"

    def test_quarter_dates(self, fset_client):
        """Verify correct date ranges for each quarter."""
        for quarter, expected_start, expected_end in [
            (1, "2026-01-01", "2026-03-31"),
            (2, "2026-04-01", "2026-06-30"),
            (3, "2026-07-01", "2026-09-30"),
            (4, "2026-10-01", "2026-12-31"),
        ]:
            data = G7QuarterData(
                employer_name="TEST",
                employer_ein="999999999",
                ga_withholding_account_number="GA9999999",
                tax_year=2026,
                quarter=quarter,
                month1_withholding=Decimal("100"),
                month2_withholding=Decimal("100"),
                month3_withholding=Decimal("100"),
                total_wages_paid=Decimal("3000"),
                num_employees_month1=1,
                num_employees_month2=1,
                num_employees_month3=1,
            )
            xml_str = fset_client.generate_g7_xml(data)
            root = ET.fromstring(xml_str)
            header = root.find("ReturnHeaderState")
            assert header.find("TaxPeriodBeginDate").text == expected_start
            assert header.find("TaxPeriodEndDate").text == expected_end

    def test_total_wages_paid(self, fset_client, sample_g7_data):
        xml_str = fset_client.generate_g7_xml(sample_g7_data)
        root = ET.fromstring(xml_str)

        g7 = root.find("ReturnDataState/FormG7")
        assert g7.find("TotalWagesPaid").text == "45000.00"
