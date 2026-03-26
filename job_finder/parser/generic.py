"""BeautifulSoup fallback parser for Workday, Ashby, SmartRecruiters, and unknown ATS."""

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment

from job_finder.salary_extractor import extract_salary_from_text

logger = logging.getLogger(__name__)

_DESCRIPTION_MAX_CHARS = 5000
_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript"]


def _company_from_url(url: str) -> str:
    """Extract company name from ATS URL path segment."""
    try:
        path = urlparse(url).path.lstrip("/")
        slug = path.split("/")[0]
        # Remove trailing digits (e.g. "Tietoevry1" → "Tietoevry")
        slug = re.sub(r'\d+$', '', slug)
        # Convert kebab-case/CamelCase to readable: "my-company" → "My Company"
        slug = re.sub(r'[-_]', ' ', slug)
        return slug.strip()
    except Exception:
        return ""


def can_parse(url: str) -> bool:
    """Always returns True — this is the catch-all parser."""
    return True


def parse(raw: dict) -> dict | None:
    """
    Fetch the job posting page and extract text via BeautifulSoup.
    Returns None on failure.
    """
    url = raw.get("url", "")
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        # Critical: fix encoding before accessing .text
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.warning("generic.parse: fetch error for %s: %s", url, exc)
        return None

    # Remove noise tags
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    # Remove HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Extract title and company from page <title>
    # Common formats: "Job Title | Company" or "Job Title - Company | ATS" or "Job Title at Company"
    title_tag = soup.find("title")
    company_from_title = ""
    if title_tag and title_tag.string:
        raw_title = title_tag.string.strip()
        for sep in [" | ", " - ", " – "]:
            if sep in raw_title:
                parts = raw_title.split(sep)
                raw_title = parts[0].strip()
                if len(parts) > 1:
                    company_from_title = parts[1].strip()
                break
        title = raw_title
    else:
        title = raw.get("title", "")

    company = raw.get("company") or _company_from_url(url) or company_from_title

    visible_text = soup.get_text(" ", strip=True)
    description = visible_text[:_DESCRIPTION_MAX_CHARS]

    salary = extract_salary_from_text(description)

    return {
        **raw,
        "company":          company,
        "title":            title,
        "description":      description,
        "description_html": str(soup),
        "location":         "",
        "department":       None,
        "posted_at":        None,
        "url_hash":         raw.get("url_hash", ""),
        "score":            0,
        "mission":          None,
        "core_values":      [],
        "hq_address":       None,
        "website_url":      None,
        "sf_job_app_id":    None,
        "sf_account_id":    None,
        # Recruiter — not available from generic HTML pages
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
        # Salary (extracted from description text)
        **salary,
    }
