"""BeautifulSoup fallback parser for Workday, Ashby, SmartRecruiters, and unknown ATS."""

import logging

import requests
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

_DESCRIPTION_MAX_CHARS = 5000
_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript"]


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

    # Extract title: split on " | " or " - " and take first part
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        raw_title = title_tag.string.strip()
        for sep in [" | ", " - ", " – "]:
            if sep in raw_title:
                raw_title = raw_title.split(sep)[0].strip()
                break
        title = raw_title
    else:
        title = raw.get("title", "")

    visible_text = soup.get_text(" ", strip=True)
    description = visible_text[:_DESCRIPTION_MAX_CHARS]

    return {
        **raw,
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
    }
