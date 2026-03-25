"""Salesforce Account + Job_Application__c write operations."""

import logging
import time

from simple_salesforce import Salesforce, SalesforceExpiredSession

from job_finder import config

logger = logging.getLogger(__name__)


def connect() -> Salesforce:
    """Authenticate to Salesforce and return a session."""
    logger.info("Connecting to Salesforce as %s", config.SF_USERNAME)
    sf = Salesforce(
        username=config.SF_USERNAME,
        password=config.SF_PASSWORD,
        security_token=config.SF_SECURITY_TOKEN,
        domain=config.SF_DOMAIN,
    )
    logger.info("Connected. Instance: %s", sf.base_url)
    return sf


def _with_backoff(fn, max_retries: int = 5):
    """Retry a callable with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except SalesforceExpiredSession:
            raise
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning("Attempt %d failed: %s. Retrying in %ds...", attempt + 1, exc, wait)
            time.sleep(wait)


def _build_research_text(job: dict) -> str:
    """Format company research fields into a readable text block."""
    parts = []
    if job.get("mission"):
        parts.append(f"Mission: {job['mission']}")
    if job.get("core_values"):
        parts.append("Core Values: " + ", ".join(job["core_values"]))
    return "\n".join(parts)


def upsert_account(sf: Salesforce, job: dict) -> str:
    """
    Query-then-create an Account record.
    Primary match: Website (more unique than Name).
    Fallback: Name + Type.
    Returns the Account Id.
    """
    website = job.get("website_url") or ""
    safe_name = job.get("company", "").replace("'", "\\'")
    hq = job.get("hq_address") or {}

    payload = {
        "Name":            job.get("company", ""),
        "Type":            "Job Application",
        "Website":         website or None,
        "Company_Research__c": _build_research_text(job) or None,
        "BillingStreet":   hq.get("street"),
        "BillingCity":     hq.get("city"),
        "BillingState":    hq.get("state"),
        "BillingPostalCode": hq.get("postal_code"),
        "BillingCountry":  hq.get("country"),
    }
    # Remove None values to avoid overwriting with null
    payload = {k: v for k, v in payload.items() if v is not None}

    if website:
        safe_website = website.replace("'", "\\'")
        result = sf.query(
            f"SELECT Id FROM Account WHERE Website = '{safe_website}' AND Type = 'Job Application'"
        )
    else:
        result = sf.query(
            f"SELECT Id FROM Account WHERE Name = '{safe_name}' AND Type = 'Job Application'"
        )

    if result["totalSize"] == 1:
        account_id = result["records"][0]["Id"]
        _with_backoff(lambda: sf.Account.update(account_id, payload))
    else:
        account_id = _with_backoff(lambda: sf.Account.create(payload))["id"]

    return account_id


def create_job_application(sf: Salesforce, job: dict, account_id: str) -> str:
    """Create a Job_Application__c record and return its Salesforce Id."""
    payload = {
        # Do NOT set Name — Salesforce trigger auto-populates it
        "Job_Title__c":        job.get("title", ""),
        "Job_Description__c":  (job.get("description") or "")[:32768],
        "Job_Posting_URL__c":  job.get("url", ""),
        "Status__c":           "Draft",
        "Account__c":          account_id,
        "Company_Research__c": _build_research_text(job) or None,
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    result = _with_backoff(lambda: sf.Job_Application__c.create(payload))
    return result["id"]


def write_job(sf: Salesforce, job: dict) -> tuple[str, str]:
    """
    Write a job to Salesforce: upsert Account then create Job_Application__c.
    Returns (sf_job_app_id, sf_account_id).
    """
    account_id = upsert_account(sf, job)
    job_app_id = create_job_application(sf, job, account_id)
    return job_app_id, account_id
