"""LinkedIn job page parser.

Extracts job data from linkedin.com/jobs/view/* pages.
Prefers JSON-LD structured data embedded in the page; falls back to
HTML selectors; falls back to the Serper snippet for the description.
"""

import json
import logging
import re

import requests
from bs4 import BeautifulSoup

from job_finder.salary_extractor import extract_salary_from_text

logger = logging.getLogger(__name__)

_LI_RE = re.compile(r'linkedin\.com/jobs/view/')

_DESCRIPTION_MAX_CHARS = 5000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def can_parse(url: str) -> bool:
    return bool(_LI_RE.search(url))


def _parse_jsonld(soup: BeautifulSoup) -> dict:
    """Extract JobPosting fields from JSON-LD script tags. Returns partial dict."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        # JSON-LD may be a single object or an array
        if isinstance(data, list):
            data = next((d for d in data if d.get("@type") == "JobPosting"), {})
        if data.get("@type") != "JobPosting":
            continue

        title = data.get("title", "")
        company = (data.get("hiringOrganization") or {}).get("name", "")

        job_loc = data.get("jobLocation") or {}
        if isinstance(job_loc, list):
            job_loc = job_loc[0] if job_loc else {}
        addr = (job_loc.get("address") or {})
        location = (
            addr.get("addressLocality")
            or addr.get("addressRegion")
            or ""
        )

        desc_html = data.get("description", "")
        description = ""
        if desc_html:
            description = (
                BeautifulSoup(desc_html, "lxml")
                .get_text(" ", strip=True)[:_DESCRIPTION_MAX_CHARS]
            )

        posted_at = (data.get("datePosted") or "")[:10] or None

        return {
            "title":       title,
            "company":     company,
            "location":    location,
            "description": description,
            "posted_at":   posted_at,
        }
    return {}


def parse(raw: dict) -> dict | None:
    url = raw.get("url", "")
    try:
        resp = requests.get(url, timeout=15, headers=_HEADERS)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("linkedin.parse: fetch error for %s: %s", url, exc)
        return None

    fields = _parse_jsonld(soup)

    title = fields.get("title") or ""
    company = fields.get("company") or ""
    location = fields.get("location") or ""
    description = fields.get("description") or ""
    posted_at = fields.get("posted_at")

    # --- HTML selector fallbacks ---
    if not title:
        for sel in [
            "h1.top-card-layout__title",
            "h1.jobs-unified-top-card__job-title",
            "h1",
        ]:
            tag = soup.select_one(sel)
            if tag:
                title = tag.get_text(strip=True)
                break
    if not title:
        title = raw.get("title", "")

    if not company:
        for sel in [
            "a.topcard__org-name-link",
            ".top-card-layout__second-line a",
            ".jobs-unified-top-card__company-name a",
        ]:
            tag = soup.select_one(sel)
            if tag:
                company = tag.get_text(strip=True)
                break

    if not location:
        for sel in [
            ".topcard__flavor--bullet",
            ".jobs-unified-top-card__bullet",
        ]:
            tag = soup.select_one(sel)
            if tag:
                location = tag.get_text(strip=True)
                break

    if not description:
        for sel in [
            ".show-more-less-html__markup",
            ".description__text",
            "#job-details",
        ]:
            tag = soup.select_one(sel)
            if tag:
                description = tag.get_text(" ", strip=True)[:_DESCRIPTION_MAX_CHARS]
                break
    # Last resort — use the Serper snippet so the job isn't silently empty
    if not description:
        description = raw.get("snippet", "")

    salary = extract_salary_from_text(description)

    return {
        **raw,
        "title":            title,
        "company":          company,
        "description":      description,
        "description_html": str(soup),
        "location":         location,
        "department":       None,
        "posted_at":        posted_at,
        "url_hash":         raw.get("url_hash", ""),
        "score":            0,
        "mission":          None,
        "core_values":      [],
        "hq_address":       None,
        "website_url":      None,
        "sf_job_app_id":    None,
        "sf_account_id":    None,
        "recruiter_name":           None,
        "recruiter_email":          None,
        "recruiter_is_internal":    None,
        "recruiter_firm_name":      None,
        "recruiter_firm_mission":   None,
        "recruiter_firm_values":    [],
        "recruiter_firm_website":   None,
        "recruiter_firm_hq":        None,
        "sf_recruiter_account_id":  None,
        "sf_recruiter_contact_id":  None,
        **salary,
    }
