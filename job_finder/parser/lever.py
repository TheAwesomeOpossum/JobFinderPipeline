"""Lever Postings API parser."""

import logging
import re
from datetime import datetime

import requests

from job_finder.salary_extractor import extract_lever_salary

logger = logging.getLogger(__name__)

_LV_RE = re.compile(r'jobs\.lever\.co/([^/]+)/([^/?]+)')


def can_parse(url: str) -> bool:
    """Return True if URL matches the Lever posting pattern."""
    return bool(_LV_RE.search(url))


def parse(raw: dict) -> dict | None:
    """
    Fetch job details from Lever Postings API and return an internal job dict.
    Returns None on failure.
    """
    url = raw.get("url", "")
    match = _LV_RE.search(url)
    if not match:
        logger.warning("lever.parse: URL did not match pattern: %s", url)
        return None

    company_slug, posting_id = match.group(1), match.group(2)
    api_url = f"https://api.lever.co/v0/postings/{company_slug}/{posting_id}?mode=json"

    try:
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("lever.parse: API error for %s: %s", url, exc)
        return None

    # createdAt is millisecond epoch — divide by 1000
    created_at_ms = data.get("createdAt")
    if created_at_ms is not None:
        try:
            posted_at = datetime.fromtimestamp(created_at_ms / 1000).strftime("%Y-%m-%d")
        except Exception:
            posted_at = None
    else:
        posted_at = None

    categories = data.get("categories", {}) or {}
    location = categories.get("location", "") or ""
    department = categories.get("department", "") or None

    description = data.get("descriptionPlain", "") or ""
    description_html = data.get("description", "") or ""
    company = data.get("company") or company_slug

    # Recruiter: Lever exposes hiring_managers in the public posting response
    hiring_managers = data.get("hiring_managers") or []
    if hiring_managers and isinstance(hiring_managers, list):
        hm = hiring_managers[0]
        recruiter_name  = hm.get("name") or None
        recruiter_email = hm.get("email") or None
    else:
        recruiter_name  = None
        recruiter_email = None

    salary = extract_lever_salary(data.get("salary") or {})

    return {
        **raw,
        "title":            data.get("text", raw.get("title", "")),
        "company":          company,
        "description":      description,
        "description_html": description_html,
        "location":         location,
        "department":       department,
        "posted_at":        posted_at,
        "url_hash":         raw.get("url_hash", ""),
        "score":            0,
        "mission":          None,
        "core_values":      [],
        "hq_address":       None,
        "website_url":      None,
        "sf_job_app_id":    None,
        "sf_account_id":    None,
        # Recruiter
        "recruiter_name":           recruiter_name,
        "recruiter_email":          recruiter_email,
        "recruiter_is_internal":    None,
        "recruiter_firm_name":      None,
        "recruiter_firm_mission":   None,
        "recruiter_firm_values":    [],
        "recruiter_firm_website":   None,
        "recruiter_firm_hq":        None,
        "sf_recruiter_account_id":  None,
        "sf_recruiter_contact_id":  None,
        # Salary
        **salary,
    }
