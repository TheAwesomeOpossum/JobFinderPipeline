"""0–100 relevance scorer for job postings."""

import logging
import re
from datetime import date, timedelta

from job_finder import config

logger = logging.getLogger(__name__)


def score(job: dict) -> int:
    """
    Score a job 0–100 based on keyword, location, seniority, and recency signals.
    Mutates job["score"] and returns the score.
    """
    total = 0
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    posted_at = job.get("posted_at")

    keywords = [kw.strip().lower() for kw in config.DEFAULT_KEYWORDS.split(",") if kw.strip()]

    # Signal 1: keyword in title (max 30)
    if any(kw in title for kw in keywords):
        total += 30

    # Signal 2: keyword in description (max 20)
    if any(kw in description for kw in keywords):
        total += 20

    # Signal 3: location match (max 20)
    location_pref = config.LOCATION_PREFERENCE.lower()
    if "remote" in location or location_pref in location:
        total += 20

    # Signal 4: seniority match (max 20, -10 penalty for junior/entry)
    seniority_targets = config.SENIORITY_TARGETS  # already lowercased list
    combined_text = title + " " + description
    if any(s in combined_text for s in seniority_targets):
        total += 20
    if re.search(r'\bjunior\b|\bentry.level\b|\bentry level\b', combined_text):
        total -= 10

    # Signal 5: recent posting (max 10)
    if posted_at:
        try:
            post_date = date.fromisoformat(posted_at)
            today = date.today()
            if post_date >= today - timedelta(days=1):
                total += 10
        except (ValueError, TypeError):
            pass

    result = max(0, min(100, total))
    job["score"] = result
    return result
