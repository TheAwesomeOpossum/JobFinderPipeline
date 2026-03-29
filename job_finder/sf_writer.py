"""Salesforce Account + JobApplication__c + Contact write operations."""

import logging
import time

from simple_salesforce import Salesforce, SalesforceExpiredSession

from job_finder import config
from job_finder.salary_extractor import annual_midpoint, hourly_midpoint

logger = logging.getLogger(__name__)

# Maps common country name variations → SF BillingCountry picklist codes.
# Countries not in this map have their BillingCountry field omitted (not blocked).
# Maps country name variations → SF BillingCountryCode integration values.
# With State/Country Picklists enabled, BillingCountryCode uses the integration
# value (typically ISO-2), NOT BillingCountry (which expects the full display name).
# Only countries enabled in your SF org are valid here.
_SF_COUNTRY_CODE_MAP = {
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "us": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "united kingdom": "UK",
    "uk": "UK",
    "great britain": "UK",
    "england": "UK",
    "britain": "UK",
}


def _normalize_country_code(country: str | None) -> str | None:
    """Map a country name to the SF BillingCountryCode integration value. Returns None if unsupported."""
    if not country:
        return None
    return _SF_COUNTRY_CODE_MAP.get(country.strip().lower())


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

    # With SF State/Country Picklists enabled:
    # - Use BillingCountryCode (ISO integration value), NOT BillingCountry (display name)
    # - BillingState requires a valid BillingCountryCode first — omit it to avoid
    #   state-code picklist validation failures on free-text values from Claude
    # - If country can't be mapped, omit ALL billing address fields
    billing_country_code = _normalize_country_code(hq.get("country"))
    logger.info("upsert_account: raw country=%r → BillingCountryCode=%r", hq.get("country"), billing_country_code)

    payload = {
        "Name":            job.get("company", ""),
        "Type":            "Job Application",
        "Website":         website or None,
        "Company_Research__c": _build_research_text(job) or None,
    }
    if billing_country_code:
        payload["BillingStreet"]      = hq.get("street")
        payload["BillingCity"]        = hq.get("city")
        payload["BillingPostalCode"]  = hq.get("postal_code")
        payload["BillingCountryCode"] = billing_country_code
    else:
        logger.info("upsert_account: omitting billing address fields (unsupported country: %r)", hq.get("country"))

    # Remove None values to avoid overwriting with null
    payload = {k: v for k, v in payload.items() if v is not None}
    logger.info("upsert_account payload: %s", payload)

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
    """Create a JobApplication__c record and return its Salesforce Id."""
    payload = {
        # Do NOT set Name — Salesforce trigger auto-populates it
        "Job_Title__c":        (job.get("title") or "")[:80],
        "Job_Description__c":  (job.get("description") or "")[:32768],
        "Job_Posting_URL__c":  job.get("url", ""),
        "Status__c":           "Draft",
        "Account__c":          account_id,
        "Company_Research__c": _build_research_text(job) or None,
        # Salary fields
        "Annual_Salary__c":    annual_midpoint(job),
        "Hourly_Rate__c":      hourly_midpoint(job),
        "Salary_Range__c":     (job.get("salary_range_text") or "")[:20] or None,
        # Search config lookup — populated once Job_Search_Config__c is live in SF
        "Search_Config__c":    job.get("sf_search_config_id") or None,
        # Relevance score from the pipeline scorer (0–100)
        "Job_Score__c":        job.get("score") if job.get("score") is not None else None,
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    result = _with_backoff(lambda: sf.JobApplication__c.create(payload))
    return result["id"]


def _build_recruiter_research_text(job: dict) -> str | None:
    """Format external recruiter firm research into a text block."""
    parts = []
    if job.get("recruiter_firm_mission"):
        parts.append(f"Mission: {job['recruiter_firm_mission']}")
    if job.get("recruiter_firm_values"):
        parts.append("Core Values: " + ", ".join(job["recruiter_firm_values"]))
    return "\n".join(parts) or None


def upsert_recruiter_account(sf: Salesforce, job: dict) -> str:
    """
    Create or update a Salesforce Account with Type='Recruiter Account'
    for an external recruiting firm.

    Dedup: Website first, then Name + Type fallback (mirrors upsert_account pattern).
    Returns the Account SF Id.
    """
    firm_name    = job.get("recruiter_firm_name", "")
    firm_website = job.get("recruiter_firm_website") or ""
    firm_hq      = job.get("recruiter_firm_hq") or {}

    billing_country_code = _normalize_country_code(firm_hq.get("country"))
    payload = {
        "Name":                firm_name,
        "Type":                "Recruiter Account",
        "Website":             firm_website or None,
        "Company_Research__c": _build_recruiter_research_text(job),
    }
    if billing_country_code:
        payload["BillingStreet"]      = firm_hq.get("street")
        payload["BillingCity"]        = firm_hq.get("city")
        payload["BillingPostalCode"]  = firm_hq.get("postal_code")
        payload["BillingCountryCode"] = billing_country_code
    payload = {k: v for k, v in payload.items() if v is not None}

    safe_name = firm_name.replace("'", "\\'")

    if firm_website:
        safe_website = firm_website.replace("'", "\\'")
        result = sf.query(
            f"SELECT Id FROM Account WHERE Website = '{safe_website}' AND Type = 'Recruiter Account'"
        )
    else:
        result = sf.query(
            f"SELECT Id FROM Account WHERE Name = '{safe_name}' AND Type = 'Recruiter Account'"
        )

    if result["totalSize"] == 1:
        account_id = result["records"][0]["Id"]
        _with_backoff(lambda: sf.Account.update(account_id, payload))
    else:
        account_id = _with_backoff(lambda: sf.Account.create(payload))["id"]

    logger.info("Upserted Recruiter Account: %s → %s", firm_name, account_id)
    return account_id


def upsert_recruiter_contact(sf: Salesforce, job: dict, account_id: str) -> str | None:
    """
    Create or update a Salesforce Contact for the recruiter listed in the job.
    Links to account_id (either the Job Application Account or a Recruiter Account).

    Dedup priority:
    1. Email match (when recruiter_email is not None)
    2. Name + AccountId fallback (when only name is known)

    Returns the Contact SF Id, or None if no recruiter_name is present.
    """
    recruiter_name  = (job.get("recruiter_name") or "").strip()
    recruiter_email = (job.get("recruiter_email") or "").strip()

    if not recruiter_name:
        logger.warning("upsert_recruiter_contact: no recruiter_name — skipping for %s", job.get("url"))
        return None

    # Split full name → FirstName / LastName
    parts = recruiter_name.split(" ", 1)
    first_name = parts[0] if len(parts) > 1 else None
    last_name  = parts[1] if len(parts) > 1 else parts[0]

    payload: dict = {"LastName": last_name, "AccountId": account_id}
    if first_name:
        payload["FirstName"] = first_name
    if recruiter_email:
        payload["Email"] = recruiter_email

    safe_name       = recruiter_name.replace("'", "\\'")
    safe_account_id = account_id.replace("'", "\\'")

    if recruiter_email:
        safe_email = recruiter_email.replace("'", "\\'")
        result = sf.query(f"SELECT Id FROM Contact WHERE Email = '{safe_email}' LIMIT 1")
    else:
        result = sf.query(
            f"SELECT Id FROM Contact WHERE Name = '{safe_name}' AND AccountId = '{safe_account_id}' LIMIT 1"
        )

    if result["totalSize"] == 1:
        contact_id = result["records"][0]["Id"]
        _with_backoff(lambda: sf.Contact.update(contact_id, payload))
    else:
        contact_id = _with_backoff(lambda: sf.Contact.create(payload))["id"]

    logger.info("Upserted recruiter Contact: %s → %s", recruiter_name, contact_id)
    return contact_id


def write_job(sf: Salesforce, job: dict) -> tuple[str, str, str | None]:
    """
    Write a job to Salesforce:
      1. Upsert company Account (Type='Job Application')
      2. Create JobApplication__c (with salary fields)
      3. Upsert recruiter Contact (and Recruiter Account if external firm)
      4. Link Recruiter__c on JobApplication__c

    Returns (sf_job_app_id, sf_account_id, sf_recruiter_contact_id).
    sf_recruiter_contact_id is None when no recruiter or if recruiter upsert failed.
    Recruiter errors are non-fatal — job was already pushed.
    SalesforceExpiredSession is always re-raised.
    """
    account_id = upsert_account(sf, job)
    job_app_id = create_job_application(sf, job, account_id)

    sf_recruiter_contact_id = None
    try:
        recruiter_name = job.get("recruiter_name") or ""
        if recruiter_name:
            # Determine which Account to link the Contact to
            is_internal   = job.get("recruiter_is_internal", True)
            firm_name     = job.get("recruiter_firm_name") or ""
            if not is_internal and firm_name:
                recruiter_account_id = upsert_recruiter_account(sf, job)
                job["sf_recruiter_account_id"] = recruiter_account_id
            else:
                recruiter_account_id = account_id  # internal — use company Account

            sf_recruiter_contact_id = upsert_recruiter_contact(sf, job, recruiter_account_id)
            if sf_recruiter_contact_id:
                _with_backoff(lambda: sf.JobApplication__c.update(
                    job_app_id, {"Recruiter__c": sf_recruiter_contact_id}
                ))
    except SalesforceExpiredSession:
        raise
    except Exception as exc:
        logger.warning(
            "Recruiter upsert failed for %s: %s — job was still pushed.", job.get("url"), exc
        )

    return job_app_id, account_id, sf_recruiter_contact_id
