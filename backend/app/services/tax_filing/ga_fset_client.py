"""
Georgia DOR FSET (Fed/State Employment Taxes) client stub (Phase 8B).

Georgia DOR accepts quarterly withholding (G-7) filings via FSET:
- Protocol: SFTP with XML file upload
- Testing: Apply at dor.georgia.gov for test credentials
- Production: Apply separately after passing testing

XML schemas available at: https://dor.georgia.gov/file-formats

This is a stub implementation. Full integration requires:
1. FSET test credentials from Georgia DOR (fset.support@dor.ga.gov)
2. Production credentials after passing testing
3. IP address registration with Georgia DOR

Reference: https://dor.georgia.gov/instructions-submit-fset
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

logger = logging.getLogger("app.tax_filing.ga_fset")


@dataclass
class GAFSETConfig:
    sftp_host: str = "fset.dor.ga.gov"
    sftp_port: int = 22
    sftp_username: str = ""
    sftp_password: str = ""
    is_test: bool = True


@dataclass
class G7QuarterData:
    """Data for a Georgia Form G-7 quarterly withholding return."""
    employer_name: str
    employer_ein: str
    ga_withholding_account_number: str
    tax_year: int
    quarter: int  # 1-4
    # Monthly withholding amounts
    month1_withholding: Decimal
    month2_withholding: Decimal
    month3_withholding: Decimal
    total_wages_paid: Decimal
    num_employees_month1: int
    num_employees_month2: int
    num_employees_month3: int


class GAFSETClient:
    """
    Client for Georgia DOR FSET (SFTP + XML) filing.

    STUB IMPLEMENTATION — methods generate valid XML per Georgia DOR
    schemas but do not upload via SFTP. Replace with paramiko SFTP
    calls when credentials are available.

    Typical workflow:
    1. Generate XML per Georgia DOR schema for G-7
    2. Connect to FSET SFTP server
    3. Upload XML file to designated directory
    4. Poll for acknowledgment file
    5. Parse acknowledgment for accept/reject status
    """

    def __init__(self, config: GAFSETConfig):
        self._config = config

    def generate_g7_xml(self, data: G7QuarterData) -> str:
        """
        Generate Georgia Form G-7 XML for FSET submission.

        XML structure follows Georgia DOR File Format specification.
        COMPLIANCE REVIEW NEEDED: Verify XML schema version matches
        current Georgia DOR requirements.

        Returns XML string.
        """
        total_withholding = (
            data.month1_withholding
            + data.month2_withholding
            + data.month3_withholding
        )

        # Quarter date ranges
        quarter_starts = {
            1: f"{data.tax_year}-01-01",
            2: f"{data.tax_year}-04-01",
            3: f"{data.tax_year}-07-01",
            4: f"{data.tax_year}-10-01",
        }
        quarter_ends = {
            1: f"{data.tax_year}-03-31",
            2: f"{data.tax_year}-06-30",
            3: f"{data.tax_year}-09-30",
            4: f"{data.tax_year}-12-31",
        }

        root = ET.Element("ReturnState")
        root.set("stateSchemaVersion", "GAWithholding2018.1")

        header = ET.SubElement(root, "ReturnHeaderState")
        ET.SubElement(header, "Jurisdiction").text = "GA"
        ET.SubElement(header, "ReturnType").text = "G-7"
        ET.SubElement(header, "TaxYear").text = str(data.tax_year)
        ET.SubElement(header, "TaxPeriodBeginDate").text = quarter_starts[data.quarter]
        ET.SubElement(header, "TaxPeriodEndDate").text = quarter_ends[data.quarter]

        filer = ET.SubElement(header, "Filer")
        ET.SubElement(filer, "EIN").text = data.employer_ein
        ET.SubElement(filer, "BusinessName").text = data.employer_name
        ET.SubElement(filer, "GAWithholdingAccountNumber").text = data.ga_withholding_account_number

        body = ET.SubElement(root, "ReturnDataState")
        g7 = ET.SubElement(body, "FormG7")

        ET.SubElement(g7, "Quarter").text = str(data.quarter)

        # Monthly breakdown
        m1 = ET.SubElement(g7, "Month1")
        ET.SubElement(m1, "WithholdingAmount").text = str(data.month1_withholding)
        ET.SubElement(m1, "NumberOfEmployees").text = str(data.num_employees_month1)

        m2 = ET.SubElement(g7, "Month2")
        ET.SubElement(m2, "WithholdingAmount").text = str(data.month2_withholding)
        ET.SubElement(m2, "NumberOfEmployees").text = str(data.num_employees_month2)

        m3 = ET.SubElement(g7, "Month3")
        ET.SubElement(m3, "WithholdingAmount").text = str(data.month3_withholding)
        ET.SubElement(m3, "NumberOfEmployees").text = str(data.num_employees_month3)

        ET.SubElement(g7, "TotalWithholding").text = str(total_withholding)
        ET.SubElement(g7, "TotalWagesPaid").text = str(data.total_wages_paid)

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    async def submit_g7(self, xml_content: str) -> dict:
        """
        Submit G-7 XML to Georgia DOR via FSET SFTP.

        STUB: Logs the submission but does not connect to SFTP.
        Replace with paramiko SFTP upload when credentials are available.

        Workflow:
        1. Connect to self._config.sftp_host:sftp_port
        2. Authenticate with username/password
        3. Upload XML file to /incoming/ directory
        4. Filename format: G7_{EIN}_{YYYY}Q{Q}_{timestamp}.xml

        Returns acknowledgment data.
        """
        logger.info(
            "STUB: GA FSET G-7 submission (test=%s, host=%s)",
            self._config.is_test,
            self._config.sftp_host,
        )
        # TODO: Replace with actual paramiko SFTP upload
        # import paramiko
        # transport = paramiko.Transport((self._config.sftp_host, self._config.sftp_port))
        # transport.connect(username=self._config.sftp_username, password=self._config.sftp_password)
        # sftp = paramiko.SFTPClient.from_transport(transport)
        # filename = f"G7_{ein}_{year}Q{quarter}_{timestamp}.xml"
        # sftp.putfo(io.BytesIO(xml_content.encode("utf-8")), f"/incoming/{filename}")
        # sftp.close()
        # transport.close()
        return {
            "status": "STUB_SUBMITTED",
            "message": "STUB: G-7 XML generated but not uploaded (SFTP credentials not configured)",
            "xml_size_bytes": len(xml_content.encode("utf-8")),
        }

    async def check_acknowledgment(self, submission_reference: str) -> dict:
        """
        Check for acknowledgment file on FSET SFTP server.

        Georgia DOR places acknowledgment files in /outgoing/ directory
        after processing. Typical turnaround: 1-3 business days.

        STUB: Returns pending status.
        """
        logger.info("STUB: GA FSET acknowledgment check (ref=%s)", submission_reference)
        return {
            "status": "PENDING",
            "message": "STUB: Acknowledgment check not implemented (SFTP credentials not configured)",
        }
