"""0–100 relevance scorer for job postings."""

import logging
import re
from datetime import date, timedelta

from job_finder import config

logger = logging.getLogger(__name__)


def score(job: dict, keywords: str | None = None, bonus_skills: list[str] | None = None) -> int:
    """
    Score a job 0–100 based on keyword, location, seniority, recency, and bonus skill signals.
    Mutates job["score"] and returns the score.

    keywords: comma-separated search keywords; falls back to config.DEFAULT_KEYWORDS.
    bonus_skills: skill tokens that add +5 each (max +20) when found in description.
    """
    total = 0
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    posted_at = job.get("posted_at")

    kw_source = keywords or config.DEFAULT_KEYWORDS
    kw_list = [kw.strip().lower() for kw in kw_source.split(",") if kw.strip()]

    def _kw_match(text: str) -> bool:
        """Match keyword if ALL tokens are present in any order (e.g. 'salesforce developer'
        matches 'Lead Developer - Salesforce' because both tokens appear in the title)."""
        for kw in kw_list:
            tokens = kw.split()
            if all(token in text for token in tokens):
                return True
        return False

    # Signal 1: keyword tokens in title (max 30)
    if _kw_match(title):
        total += 30

    # Signal 2: keyword in description (max 20)
    if _kw_match(description):
        total += 20

    # Signal 3: location match (max 20)
    # Check both the structured location field and description text
    location_pref = config.LOCATION_PREFERENCE.lower()
    combined_location = location + " " + description
    _REMOTE_RE = re.compile(
        r'\bremote\b'
        r'|\bwork.from.home\b|\bwfh\b'
        r'|\bfully.remote\b|\b100%.remote\b'
        r'|\bdistributed.team\b'
        r'|\banywhere.in.the.u\.?s\b'
    )
    if _REMOTE_RE.search(combined_location) or location_pref in combined_location:
        total += 20
    # Bonus for explicit US location signals
    if re.search(r'\b(united states|usa|\bus\b|u\.s\.)\b', combined_location):
        total += 10
    # Penalty for non-US locations — must be willing to hire US workers
    if re.search(
        r'\b(uk|united kingdom|germany|deutschland|canada|india|australia|europe|'
        r'netherlands|france|poland|sweden|denmark|norway|finland|ireland|spain|'
        r'portugal|italy|austria|switzerland)\b',
        combined_location,
    ):
        total -= 25

    # Signal 4: seniority match (max 20, -10 penalty for junior/entry)
    seniority_targets = config.SENIORITY_TARGETS  # already lowercased list
    combined_text = title + " " + description
    if any(s in combined_text for s in seniority_targets) or re.search(
        r'\bsr\b|\bii\b|\biii\b|\biv\b', title
    ):
        total += 20
    if re.search(r'\bjunior\b|\bentry.level\b|\bentry level\b|\binternship\b|\bintern\b', combined_text):
        total -= 10

    # Signal 5.5: technical role type — bonus for developer/architect/consultant unconditionally;
    # engineer/technical only if the title is not a non-dev role (support, recruiter, pre-sales, etc.)
    # "consultant" is included because SF Developer roles at implementation firms use this title.
    _NON_DEV_ROLE_RE = re.compile(
        r'\brecruiter\b|\bsupport\b'
        r'|\baccount\s+manager\b|\baccount\s+executive\b'
        r'|\bsales\s+engineer\b'
        r'|\bcustomer\s+success\b'
    )
    # "solutions engineer" exclusion only fires when "engineer" is paired with "solutions"
    # but NOT "architect" (so "solutions architect" keeps the +15).
    _SOLUTIONS_ENG_RE = re.compile(r'\bsolutions?\s+engineer\b')
    if re.search(r'\bdeveloper\b|\barchitect\b|\bconsultant\b', title):
        total += 15
    elif re.search(r'\bengineer\b|\btechnical\b', title) and not _NON_DEV_ROLE_RE.search(title) and not _SOLUTIONS_ENG_RE.search(title):
        total += 15
    else:
        total -= 20

    # Signal 5: recent posting (max 10)
    if posted_at:
        try:
            post_date = date.fromisoformat(posted_at)
            today = date.today()
            if post_date >= today - timedelta(days=1):
                total += 10
        except (ValueError, TypeError):
            pass

    # Signal 6: bonus skill match (+5 per skill in description, max 20)
    if bonus_skills:
        matches = sum(1 for s in bonus_skills if s.lower() in description)
        total += min(matches * 5, 20)

    result = max(0, min(100, total))
    job["score"] = result
    return result
