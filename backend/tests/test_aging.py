"""
Tests for AR/AP aging reports (bucket classification, schemas, HTML rendering).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.schemas.aging import AgingBucketSummary, AgingDetail, APAgingReport, ARAgingReport
from app.services.aging import BUCKET_LABELS, _build_aging_html, _classify_bucket, _format_currency


class TestBucketClassification:

    def test_current(self):
        assert _classify_bucket(0) == "Current"
        assert _classify_bucket(-5) == "Current"

    def test_1_to_30(self):
        assert _classify_bucket(1) == "1-30"
        assert _classify_bucket(15) == "1-30"
        assert _classify_bucket(30) == "1-30"

    def test_31_to_60(self):
        assert _classify_bucket(31) == "31-60"
        assert _classify_bucket(45) == "31-60"
        assert _classify_bucket(60) == "31-60"

    def test_61_to_90(self):
        assert _classify_bucket(61) == "61-90"
        assert _classify_bucket(75) == "61-90"
        assert _classify_bucket(90) == "61-90"

    def test_over_90(self):
        assert _classify_bucket(91) == "90+"
        assert _classify_bucket(180) == "90+"
        assert _classify_bucket(365) == "90+"


class TestBucketLabels:

    def test_all_buckets_present(self):
        assert BUCKET_LABELS == ["Current", "1-30", "31-60", "61-90", "90+"]


class TestFormatCurrency:

    def test_basic(self):
        assert _format_currency(Decimal("1234.56")) == "$1,234.56"

    def test_zero(self):
        assert _format_currency(Decimal("0.00")) == "$0.00"


class TestAgingSchemas:

    def test_ar_aging_report(self):
        report = ARAgingReport(
            client_id="00000000-0000-0000-0000-000000000001",
            as_of_date=date(2026, 3, 4),
            details=[
                AgingDetail(
                    id="00000000-0000-0000-0000-000000000002",
                    number="INV-001",
                    counterparty="Customer A",
                    date_issued=date(2026, 1, 15),
                    due_date=date(2026, 2, 15),
                    total_amount=Decimal("1000.00"),
                    amount_paid=Decimal("0.00"),
                    outstanding=Decimal("1000.00"),
                    days_past_due=17,
                    bucket="1-30",
                ),
            ],
            buckets=[
                AgingBucketSummary(bucket="Current", total=Decimal("0.00"), count=0),
                AgingBucketSummary(bucket="1-30", total=Decimal("1000.00"), count=1),
                AgingBucketSummary(bucket="31-60", total=Decimal("0.00"), count=0),
                AgingBucketSummary(bucket="61-90", total=Decimal("0.00"), count=0),
                AgingBucketSummary(bucket="90+", total=Decimal("0.00"), count=0),
            ],
            total_outstanding=Decimal("1000.00"),
        )
        assert report.total_outstanding == Decimal("1000.00")
        assert len(report.details) == 1
        assert report.details[0].bucket == "1-30"

    def test_ap_aging_report(self):
        report = APAgingReport(
            client_id="00000000-0000-0000-0000-000000000001",
            as_of_date=date(2026, 3, 4),
            details=[],
            buckets=[AgingBucketSummary(bucket=b, total=Decimal("0.00"), count=0) for b in BUCKET_LABELS],
            total_outstanding=Decimal("0.00"),
        )
        assert report.total_outstanding == Decimal("0.00")
        assert len(report.buckets) == 5


class TestAgingHTML:

    def _sample_ar_report(self) -> ARAgingReport:
        return ARAgingReport(
            client_id="00000000-0000-0000-0000-000000000001",
            as_of_date=date(2026, 3, 4),
            details=[
                AgingDetail(
                    id="00000000-0000-0000-0000-000000000002",
                    number="INV-001",
                    counterparty="Customer A",
                    date_issued=date(2026, 1, 15),
                    due_date=date(2026, 2, 15),
                    total_amount=Decimal("5000.00"),
                    outstanding=Decimal("5000.00"),
                    days_past_due=17,
                    bucket="1-30",
                ),
                AgingDetail(
                    id="00000000-0000-0000-0000-000000000003",
                    number="INV-002",
                    counterparty="Customer B",
                    date_issued=date(2025, 11, 1),
                    due_date=date(2025, 12, 1),
                    total_amount=Decimal("2000.00"),
                    outstanding=Decimal("2000.00"),
                    days_past_due=93,
                    bucket="90+",
                ),
            ],
            buckets=[
                AgingBucketSummary(bucket="Current", total=Decimal("0.00"), count=0),
                AgingBucketSummary(bucket="1-30", total=Decimal("5000.00"), count=1),
                AgingBucketSummary(bucket="31-60", total=Decimal("0.00"), count=0),
                AgingBucketSummary(bucket="61-90", total=Decimal("0.00"), count=0),
                AgingBucketSummary(bucket="90+", total=Decimal("2000.00"), count=1),
            ],
            total_outstanding=Decimal("7000.00"),
        )

    def test_html_contains_title(self):
        html = _build_aging_html(self._sample_ar_report())
        assert "Accounts Receivable Aging Report" in html

    def test_html_contains_customer_names(self):
        html = _build_aging_html(self._sample_ar_report())
        assert "Customer A" in html
        assert "Customer B" in html

    def test_html_contains_amounts(self):
        html = _build_aging_html(self._sample_ar_report())
        assert "$5,000.00" in html
        assert "$2,000.00" in html
        assert "$7,000.00" in html

    def test_html_contains_bucket_headers(self):
        html = _build_aging_html(self._sample_ar_report())
        for bucket in BUCKET_LABELS:
            assert bucket in html

    def test_html_valid_structure(self):
        html = _build_aging_html(self._sample_ar_report())
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_ap_aging_html_title(self):
        ap_report = APAgingReport(
            client_id="00000000-0000-0000-0000-000000000001",
            as_of_date=date(2026, 3, 4),
            details=[],
            buckets=[AgingBucketSummary(bucket=b, total=Decimal("0.00"), count=0) for b in BUCKET_LABELS],
            total_outstanding=Decimal("0.00"),
        )
        html = _build_aging_html(ap_report)
        assert "Accounts Payable Aging Report" in html

    def test_html_as_of_date(self):
        html = _build_aging_html(self._sample_ar_report())
        assert "2026-03-04" in html
