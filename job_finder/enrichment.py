"""Claude API company research — one call per unique company name per run."""

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
