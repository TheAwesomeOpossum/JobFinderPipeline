"""Greenhouse Job Board API parser."""

import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_GH_RE = re.compile(r'(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)')


def can_parse(url: str) -> bool:
    """Return True if URL matches the Greenhouse board pattern."""
    return bool(_GH_RE.search(url))


def parse(raw: dict) -> dict | None:
    """
    Fetch job details from Greenhouse Jobs Board API and return an internal job dict.
    Returns None on failure.
    """
    url = raw.get("url", "")
    match = _GH_RE.search(url)
    if not match:
        logger.warning("greenhouse.parse: URL did not match pattern: %s", url)
        return None

    company_slug, job_id = match.group(1), match.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}?content=true"

    try:
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("greenhouse.parse: API error for %s: %s", url, exc)
        return None

    # Extract plain text from HTML content
    content_html = data.get("content", "")
    description = BeautifulSoup(content_html, "lxml").get_text(" ", strip=True)

    # posted_at: take the date portion of first_published
    posted_at_raw = data.get("first_published", "") or ""
    posted_at = posted_at_raw[:10] if posted_at_raw else None

    departments = data.get("departments", [])
    department = departments[0]["name"] if departments else None

    location_data = data.get("location", {}) or {}
    location = location_data.get("name", "") or ""

    company = data.get("company_name") or company_slug

    return {
        **raw,
        "title":            data.get("title", raw.get("title", "")),
        "company":          company,
        "description":      description,
        "description_html": content_html,
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
    }
