"""
TaxBandits API client stub (Phase 8B).

TaxBandits (developer.taxbandits.com) provides REST APIs for e-filing:
- 1099-NEC, 1099-MISC, and all 1099 variants
- W-2 (federal + state)
- 940, 941, 943, 944, 945 (employment tax forms)

This is a stub implementation. Full integration requires:
1. TaxBandits API credentials (sandbox + production)
2. OAuth 2.0 client credentials flow for authentication
3. Webhook endpoint for async acknowledgments

Pricing (as of 2026):
- 1099/W-2 federal: $2.75/form (1-10), scaling to $0.80/form (500+)
- State filing: $0.95/form standalone, free when combined with federal
- 94x payroll forms: $5.95/form (first), scaling to $3.00/form (500+)

Reference: https://developer.taxbandits.com/
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger("app.tax_filing.taxbandits")

# COMPLIANCE REVIEW NEEDED: TaxBandits API credentials must be stored securely.
# Do NOT hardcode credentials. Use environment variables or a secrets manager.

TAXBANDITS_SANDBOX_URL = "https://testoauth.expressauth.net/v2/tbauth"
TAXBANDITS_PRODUCTION_URL = "https://oauth.expressauth.net/v2/tbauth"
TAXBANDITS_SANDBOX_API = "https://testapi.taxbandits.com/v1.7.1"
TAXBANDITS_PRODUCTION_API = "https://api.taxbandits.com/v1.7.1"


@dataclass
class TaxBanditsConfig:
    client_id: str
    client_secret: str
    is_sandbox: bool = True

    @property
    def auth_url(self) -> str:
        return TAXBANDITS_SANDBOX_URL if self.is_sandbox else TAXBANDITS_PRODUCTION_URL

    @property
    def api_url(self) -> str:
        return TAXBANDITS_SANDBOX_API if self.is_sandbox else TAXBANDITS_PRODUCTION_API


class TaxBanditsClient:
    """
    Client for the TaxBandits REST API.

    STUB IMPLEMENTATION — methods document the expected API calls
    but do not make real HTTP requests. Replace with httpx calls
    when API credentials are available.

    Typical workflow:
    1. Authenticate via OAuth 2.0 client credentials → access_token
    2. Create a submission (POST /Form1099NEC/Create)
    3. Transmit the submission (POST /Form1099NEC/Transmit)
    4. Check status via webhook or polling (GET /Form1099NEC/Status)
    """

    def __init__(self, config: TaxBanditsConfig):
        self._config = config
        self._access_token: str | None = None

    async def authenticate(self) -> str:
        """
        Obtain an access token via OAuth 2.0 client credentials flow.

        POST {auth_url}
        Body: { "client_id": "...", "client_secret": "...", "grant_type": "client_credentials" }
        Response: { "access_token": "...", "token_type": "Bearer", "expires_in": 3600 }

        STUB: Returns a placeholder token.
        """
        logger.info(
            "STUB: TaxBandits OAuth authentication (sandbox=%s)",
            self._config.is_sandbox,
        )
        # TODO: Replace with actual httpx POST when credentials available
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         self._config.auth_url,
        #         json={
        #             "client_id": self._config.client_id,
        #             "client_secret": self._config.client_secret,
        #             "grant_type": "client_credentials",
        #         },
        #     )
        #     data = response.json()
        #     self._access_token = data["access_token"]
        #     return self._access_token
        self._access_token = "STUB_TOKEN"
        return self._access_token

    async def create_w2(self, submission_data: dict) -> dict:
        """
        Create a W-2 filing submission.

        POST {api_url}/FormW2/Create
        Headers: Authorization: Bearer {access_token}
        Body: W-2 data per TaxBandits schema

        STUB: Returns a placeholder submission ID.
        """
        logger.info("STUB: TaxBandits W-2 Create (employees=%s)", len(submission_data.get("employees", [])))
        return {
            "SubmissionId": "STUB_W2_SUBMISSION_ID",
            "StatusCode": 200,
            "StatusMessage": "STUB: W-2 submission created",
        }

    async def create_1099nec(self, submission_data: dict) -> dict:
        """
        Create a 1099-NEC filing submission.

        POST {api_url}/Form1099NEC/Create
        Headers: Authorization: Bearer {access_token}
        Body: 1099-NEC data per TaxBandits schema

        STUB: Returns a placeholder submission ID.
        """
        logger.info("STUB: TaxBandits 1099-NEC Create (recipients=%s)", len(submission_data.get("recipients", [])))
        return {
            "SubmissionId": "STUB_1099NEC_SUBMISSION_ID",
            "StatusCode": 200,
            "StatusMessage": "STUB: 1099-NEC submission created",
        }

    async def create_941(self, submission_data: dict) -> dict:
        """
        Create a Form 941 (Quarterly Federal Tax Return) filing.

        POST {api_url}/Form941/Create
        Headers: Authorization: Bearer {access_token}
        Body: 941 data per TaxBandits schema

        STUB: Returns a placeholder submission ID.
        """
        logger.info("STUB: TaxBandits 941 Create (quarter=%s)", submission_data.get("quarter"))
        return {
            "SubmissionId": "STUB_941_SUBMISSION_ID",
            "StatusCode": 200,
            "StatusMessage": "STUB: Form 941 submission created",
        }

    async def transmit(self, submission_id: str, form_type: str) -> dict:
        """
        Transmit a previously created submission to the IRS.

        POST {api_url}/{form_type}/Transmit
        Body: { "SubmissionId": "..." }

        STUB: Returns success status.
        """
        logger.info("STUB: TaxBandits Transmit (%s, id=%s)", form_type, submission_id)
        return {
            "SubmissionId": submission_id,
            "StatusCode": 200,
            "StatusMessage": f"STUB: {form_type} transmitted to IRS",
        }

    async def get_status(self, submission_id: str, form_type: str) -> dict:
        """
        Check the status of a filing submission.

        GET {api_url}/{form_type}/Status?SubmissionId={id}

        STUB: Returns pending status.
        """
        logger.info("STUB: TaxBandits Status (%s, id=%s)", form_type, submission_id)
        return {
            "SubmissionId": submission_id,
            "Status": "PENDING",
            "StatusMessage": "STUB: Awaiting IRS processing",
        }
