"""Claude API company research and recruiter context enrichment."""

import json
import logging

import anthropic

from job_finder import config

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

_SCHEMA = {
    "type": "object",
    "properties": {
        "mission":     {"type": ["string", "null"]},
        "core_values": {"type": "array", "items": {"type": "string"}},
        "website_url": {"type": ["string", "null"]},
        "hq_address":  {
            "type": ["object", "null"],
            "properties": {
                "street":      {"type": ["string", "null"]},
                "city":        {"type": ["string", "null"]},
                "state":       {"type": ["string", "null"]},
                "postal_code": {"type": ["string", "null"]},
                "country":     {"type": ["string", "null"]},
            },
        },
    },
    "required": ["mission", "core_values", "website_url", "hq_address"],
    "additionalProperties": False,
}

_EMPTY_ENRICHMENT = {
    "mission":     None,
    "core_values": [],
    "website_url": None,
    "hq_address":  None,
}


def enrich_company(company_name: str) -> dict:
    """
    Call Claude to research a company. Returns mission, core_values, website_url, hq_address.
    Returns empty dict on any failure.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = (
        f"Research the company '{company_name}'. "
        "Provide their mission statement, core values, official website URL, and headquarters address."
    )
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
        return json.loads(response.content[0].text)
    except Exception as exc:
        logger.warning("enrich_company failed for '%s': %s", company_name, exc)
        return dict(_EMPTY_ENRICHMENT)


# ---------------------------------------------------------------------------
# Recruiter context determination
# ---------------------------------------------------------------------------

_RECRUITER_SCHEMA = {
    "type": "object",
    "properties": {
        "is_internal":         {"type": "boolean"},
        "confidence":          {"type": "string", "enum": ["high", "medium", "low"]},
        "recruiter_firm_name": {"type": ["string", "null"]},
    },
    "required": ["is_internal", "confidence", "recruiter_firm_name"],
    "additionalProperties": False,
}

_RECRUITER_DEFAULT = {
    "is_internal":         True,
    "confidence":          "low",
    "recruiter_firm_name": None,
}


def determine_recruiter_context(
    recruiter_name: str,
    recruiter_email: str | None,
    company_name: str,
) -> dict:
    """
    Ask Claude whether a recruiter is an internal employee of the hiring company
    or an external staffing/recruiting agency representative.

    Returns: {is_internal: bool, confidence: str, recruiter_firm_name: str | None}

    On any failure, defaults to is_internal=True (conservative — never create
    a spurious Recruiter Account on API errors).
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    email_clause = f" (email: {recruiter_email})" if recruiter_email else ""
    prompt = (
        f"A job posting from '{company_name}' lists a recruiter: '{recruiter_name}'{email_clause}.\n\n"
        f"Is '{recruiter_name}' an internal employee of '{company_name}', or do they represent "
        f"an external recruiting or staffing agency?\n\n"
        f"Rules:\n"
        f"- If '{company_name}' is itself a staffing/recruiting firm, classify the recruiter as internal.\n"
        f"- If the email domain (when provided) matches '{company_name}''s known domain, lean internal.\n"
        f"- If you recognise the recruiter as being associated with a firm OTHER than '{company_name}', "
        f"  return is_internal=false and provide that firm's name.\n"
        f"- When uncertain, default to is_internal=true with confidence=low."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": _RECRUITER_SCHEMA}},
        )
        result = json.loads(response.content[0].text)
        logger.debug(
            "Recruiter context for '%s' at '%s': %s", recruiter_name, company_name, result
        )
        return result
    except Exception as exc:
        logger.warning(
            "determine_recruiter_context failed for '%s': %s — defaulting to internal",
            recruiter_name,
            exc,
        )
        return dict(_RECRUITER_DEFAULT)


def enrich_recruiter_jobs(jobs: list[dict]) -> list[dict]:
    """
    For each job that has a recruiter_name, call determine_recruiter_context().
    If the recruiter is external and a firm name is returned, also call enrich_company()
    for the firm and merge firm enrichment data into the job.

    Mutates each job dict in place. Returns the same list.
    """
    firm_cache: dict[str, dict] = {}

    for job in jobs:
        recruiter_name  = job.get("recruiter_name") or ""
        recruiter_email = job.get("recruiter_email") or None
        company_name    = job.get("company") or ""

        if not recruiter_name:
            continue

        ctx = determine_recruiter_context(recruiter_name, recruiter_email, company_name)
        job["recruiter_is_internal"] = ctx.get("is_internal", True)
        firm_name = ctx.get("recruiter_firm_name") or None

        if not job["recruiter_is_internal"] and firm_name:
            job["recruiter_firm_name"] = firm_name
            if firm_name not in firm_cache:
                logger.info("Enriching external recruiter firm: %s", firm_name)
                firm_cache[firm_name] = enrich_company(firm_name)
            firm_data = firm_cache[firm_name]
            job["recruiter_firm_mission"] = firm_data.get("mission")
            job["recruiter_firm_values"]  = firm_data.get("core_values") or []
            job["recruiter_firm_website"] = firm_data.get("website_url")
            job["recruiter_firm_hq"]      = firm_data.get("hq_address")
        else:
            # Internal — no separate firm enrichment needed
            job["recruiter_is_internal"] = True

    return jobs


def enrich_jobs(jobs: list[dict]) -> list[dict]:
    """
    Enrich each job with company research data.
    Makes one Claude API call per unique company name, then merges into each job.
    """
    # Build cache: one call per unique company
    company_cache: dict[str, dict] = {}
    for job in jobs:
        company = job.get("company", "")
        if company and company not in company_cache:
            logger.info("Enriching company: %s", company)
            company_cache[company] = enrich_company(company)

    # Merge enrichment into each job
    for job in jobs:
        company = job.get("company", "")
        enrichment = company_cache.get(company, dict(_EMPTY_ENRICHMENT))
        job.update(enrichment)

    return jobs
