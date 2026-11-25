"""Greenhouse Job Board API parser."""

import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from job_finder.salary_extractor import extract_greenhouse_salary

logger = logging.getLogger(__name__)

_GH_RE = re.compile(r'(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)')
_GH_JID_RE = re.compile(r'gh_jid=(\d+)|#.*/(\d{7,})|[?&/](\d{7,})')  # custom-domain fallback


def _company_from_domain(url: str) -> str:
    """Extract a company name from a custom careers domain (e.g. careers.astounddigital.com → Astound Digital)."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).hostname or ""
        # Strip common prefixes like careers., jobs., etc.
        parts = host.split(".")
        # Find the main domain part (e.g. "astounddigital" from "careers.astounddigital.com")
        if len(parts) >= 2:
            domain = parts[-2]  # second-to-last is the main domain
        else:
            return ""
        # Split camelCase, hyphens, underscores, and known compound words
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', domain)
        spaced = re.sub(r'[-_]', ' ', spaced)
        # Split known suffixes that appear glued to company names
        _SUFFIXES = r'(digital|commerce|tech|software|solutions|labs|works|group|global|systems|studio)'
        spaced = re.sub(rf'(?i)(\w)({_SUFFIXES})$', r'\1 \2', spaced)
        return spaced.strip().title()
    except Exception:
        return ""


def _extract_job_id_from_url(url: str) -> str | None:
    """Pull a Greenhouse job ID from a custom-domain URL (gh_jid param, fragment, or path segment)."""
    m = _GH_JID_RE.search(url)
    if m:
        return m.group(1) or m.group(2) or m.group(3)
    return None


def _resolve_greenhouse_slug(url: str, job_id: str) -> str | None:
    """
    Given a custom-domain Greenhouse URL and a job ID, discover the board slug
    by fetching the page and looking for Greenhouse embed markers.
    """
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36",
        })
        resp.raise_for_status()
        text = resp.text

        # Look for common Greenhouse embed patterns:
        #   boards.greenhouse.io/embed/job_board/js?for=SLUG
        #   boards-api.greenhouse.io/v1/boards/SLUG
        #   "boardToken":"SLUG"
        for pattern in [
            re.compile(r'boards\.greenhouse\.io/embed/job_board/js\?for=([a-zA-Z0-9_-]+)'),
            re.compile(r'boards-api\.greenhouse\.io/v1/boards/([a-zA-Z0-9_-]+)'),
            re.compile(r'"boardToken"\s*:\s*"([a-zA-Z0-9_-]+)"'),
        ]:
            m = pattern.search(text)
            if m:
                return m.group(1)
    except Exception as exc:
        logger.debug("_resolve_greenhouse_slug: failed to fetch %s: %s", url, exc)

    return None


def can_parse(url: str) -> bool:
    """Return True if URL matches the Greenhouse board pattern or contains a gh_jid param."""
    return bool(_GH_RE.search(url)) or "gh_jid=" in url


def parse(raw: dict) -> dict | None:
    """
    Fetch job details from Greenhouse Jobs Board API and return an internal job dict.
    Returns None on failure.
    """
    url = raw.get("url", "")
    match = _GH_RE.search(url)
    if match:
        company_slug, job_id = match.group(1), match.group(2)
    else:
        # Custom-domain Greenhouse embed — extract job ID and resolve slug
        job_id = _extract_job_id_from_url(url)
        if not job_id:
            logger.warning("greenhouse.parse: URL did not match pattern: %s", url)
            return None
        company_slug = _resolve_greenhouse_slug(url, job_id)
        if not company_slug:
            logger.warning("greenhouse.parse: could not resolve Greenhouse slug for %s", url)
            return None
        logger.info("greenhouse.parse: resolved custom domain → slug=%s, job_id=%s", company_slug, job_id)

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}?content=true&pay_transparency=true"

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
    # If the API returns a generic board name, try to extract from the custom domain
    _generic_names = {"global career website", "career site", "job board", "careers"}
    if company.strip().lower() in _generic_names:
        domain_company = _company_from_domain(url)
        if domain_company:
            company = domain_company

    salary = extract_greenhouse_salary(data.get("pay_input_ranges") or [])

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
        # Recruiter — public Greenhouse API does not expose hiring_team
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
        # Salary
        **salary,
    }
